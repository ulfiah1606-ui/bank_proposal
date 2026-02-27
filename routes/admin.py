from flask import Blueprint, render_template, redirect, session, flash, request
from extensions import mysql
from services.gemini_service import analisis_narasi
from services.clustering_service import proses_kmeans
from MySQLdb.cursors import DictCursor

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ===============================
# DATA PROPOSAL (READ)
# ===============================
@admin_bp.route("/proposal")
def proposal():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT 
            p.id_proposal,
            p.status,
            ha.skor_kelayakan,
            ha.skor_urgensi
        FROM proposal p
        LEFT JOIN hasil_ai ha
            ON p.id_proposal = ha.id_proposal
        ORDER BY p.tanggal_pengajuan DESC
    """)
    data = cur.fetchall()
    cur.close()

    return render_template("admin/proposal.html", proposal=data)


# ===============================
# FORM EDIT (UPDATE)
# ===============================
@admin_bp.route("/edit/<id_proposal>", methods=["GET", "POST"])
def edit_proposal(id_proposal):
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor(DictCursor)

    if request.method == "POST":
        status = request.form.get("status")
        skor_kelayakan = request.form.get("skor_kelayakan") or 0
        skor_urgensi = request.form.get("skor_urgensi") or 0
        ringkasan = request.form.get("ringkasan") or "-"

        try:
            # Update status proposal
            cur.execute("""
                UPDATE proposal
                SET status=%s
                WHERE id_proposal=%s
            """, (status, id_proposal))

            # Cek apakah hasil_ai sudah ada
            cur.execute("""
                SELECT id_ai FROM hasil_ai
                WHERE id_proposal=%s
            """, (id_proposal,))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE hasil_ai
                    SET skor_kelayakan=%s,
                        skor_urgensi=%s,
                        ringkasan=%s
                    WHERE id_proposal=%s
                """, (
                    skor_kelayakan,
                    skor_urgensi,
                    ringkasan,
                    id_proposal
                ))
            else:
                cur.execute("""
                    INSERT INTO hasil_ai
                    (id_proposal, skor_kelayakan, skor_urgensi, ringkasan)
                    VALUES (%s,%s,%s,%s)
                """, (
                    id_proposal,
                    skor_kelayakan,
                    skor_urgensi,
                    ringkasan
                ))

            mysql.connection.commit()
            flash("Data berhasil diperbarui", "success")

        except Exception as e:
            mysql.connection.rollback()
            print("ERROR EDIT:", e)
            flash("Gagal memperbarui data", "danger")

        finally:
            cur.close()

        return redirect("/admin/proposal")

    # GET (ambil data)
    cur.execute("""
    SELECT 
        p.id_proposal,
        p.status,
        ha.skor_kelayakan,
        ha.skor_urgensi,
        ha.ringkasan,
        pn.latar_belakang,
        pn.tujuan,
        pn.kebutuhan,
        pn.lokasi,
        pm.luas_lahan,
        pm.jumlah_bantuan_sebelumnya,
        pm.pagu_anggaran
    FROM proposal p
    LEFT JOIN hasil_ai ha
        ON p.id_proposal = ha.id_proposal
    LEFT JOIN proposal_narasi pn
        ON p.id_proposal = pn.id_proposal
    LEFT JOIN proposal_metrik pm
        ON p.id_proposal = pm.id_proposal
    WHERE p.id_proposal=%s
""", (id_proposal,))
    data = cur.fetchone()
    cur.close()

    return render_template("admin/edit_proposal.html", data=data)


# ===============================
# DELETE (DELETE)
# ===============================
@admin_bp.route("/delete/<id_proposal>")
def delete_proposal(id_proposal):
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()

    try:
        # Hapus relasi dulu
        cur.execute("DELETE FROM hasil_clustering WHERE id_proposal=%s", (id_proposal,))
        cur.execute("DELETE FROM hasil_ai WHERE id_proposal=%s", (id_proposal,))
        cur.execute("DELETE FROM proposal_dokumen WHERE id_proposal=%s", (id_proposal,))
        cur.execute("DELETE FROM proposal_metrik WHERE id_proposal=%s", (id_proposal,))
        cur.execute("DELETE FROM proposal_narasi WHERE id_proposal=%s", (id_proposal,))
        cur.execute("DELETE FROM proposal WHERE id_proposal=%s", (id_proposal,))

        mysql.connection.commit()
        flash("Proposal berhasil dihapus", "success")

    except Exception as e:
        mysql.connection.rollback()
        print("ERROR DELETE:", e)
        flash("Gagal menghapus proposal", "danger")

    finally:
        cur.close()

    return redirect("/admin/proposal")


# ===============================
# ANALISIS AI (TETAP AMAN)
# ===============================
@admin_bp.route("/analisis-ai/<id_proposal>")
def analisis_ai(id_proposal):
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()

    try:
        cur.execute("""
            UPDATE proposal
            SET status='diproses'
            WHERE id_proposal=%s
        """, (id_proposal,))
        mysql.connection.commit()

        cur.execute("""
            SELECT CONCAT(latar_belakang,' ',tujuan,' ',kebutuhan,' ',lokasi)
            FROM proposal_narasi
            WHERE id_proposal=%s
        """, (id_proposal,))
        row = cur.fetchone()

        if not row:
            flash("Narasi proposal tidak ditemukan", "danger")
            return redirect("/admin/proposal")

        hasil = analisis_narasi(row[0])

        skor_kelayakan = hasil.get("kelayakan", 0)
        skor_urgensi = hasil.get("urgensi", 0)
        ringkasan = hasil.get("ringkasan", "-")

        cur.execute("""
            SELECT id_ai FROM hasil_ai
            WHERE id_proposal=%s
        """, (id_proposal,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE hasil_ai
                SET skor_kelayakan=%s,
                    skor_urgensi=%s,
                    ringkasan=%s
                WHERE id_proposal=%s
            """, (
                skor_kelayakan,
                skor_urgensi,
                ringkasan,
                id_proposal
            ))
        else:
            cur.execute("""
                INSERT INTO hasil_ai
                (id_proposal, skor_kelayakan, skor_urgensi, ringkasan)
                VALUES (%s,%s,%s,%s)
            """, (
                id_proposal,
                skor_kelayakan,
                skor_urgensi,
                ringkasan
            ))

        cur.execute("""
            UPDATE proposal
            SET status='selesai'
            WHERE id_proposal=%s
        """, (id_proposal,))

        mysql.connection.commit()

    except Exception as e:
        mysql.connection.rollback()
        print("ERROR ANALISIS AI:", e)
        flash("Terjadi kesalahan saat proses AI", "danger")

    finally:
        cur.close()

    flash("Analisis AI berhasil dijalankan", "success")
    return redirect("/admin/proposal")


# ===============================
# CLUSTERING (TETAP AMAN)
# ===============================
@admin_bp.route("/clustering")
def clustering():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT pm.id_proposal,
               pm.luas_lahan,
               pm.jumlah_bantuan_sebelumnya,
               pm.pagu_anggaran,
               ha.skor_kelayakan,
               ha.skor_urgensi
        FROM proposal_metrik pm
        JOIN hasil_ai ha 
            ON pm.id_proposal = ha.id_proposal
    """)
    rows = cur.fetchall()

    if not rows:
        flash("Belum ada data untuk clustering", "warning")
        return redirect("/admin/proposal")

    ids = [r[0] for r in rows]
    data = [r[1:] for r in rows]

    labels = proses_kmeans(data)

    prioritas_map = {
        0: "Prioritas 1",
        1: "Prioritas 2",
        2: "Prioritas 3"
    }

    for pid, label in zip(ids, labels):
        cur.execute("""
            SELECT id_proposal FROM hasil_clustering
            WHERE id_proposal=%s
        """, (pid,))
        exist = cur.fetchone()

        if exist:
            cur.execute("""
                UPDATE hasil_clustering
                SET cluster=%s,
                    kategori_prioritas=%s
                WHERE id_proposal=%s
            """, (
                int(label),
                prioritas_map[int(label)],
                pid
            ))
        else:
            cur.execute("""
                INSERT INTO hasil_clustering
                (id_proposal, cluster, kategori_prioritas)
                VALUES (%s,%s,%s)
            """, (
                pid,
                int(label),
                prioritas_map[int(label)]
            ))

    mysql.connection.commit()
    cur.close()

    flash("K-Means Clustering berhasil dijalankan", "success")
    return redirect("/admin/proposal")


# ===============================
# HASIL PRIORITAS
# ===============================
@admin_bp.route("/hasil-prioritas")
def hasil_prioritas():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT 
            hc.id_proposal,
            hc.kategori_prioritas
        FROM hasil_clustering hc
        ORDER BY 
            FIELD(hc.kategori_prioritas,
                'Prioritas 1',
                'Prioritas 2',
                'Prioritas 3')
    """)
    data = cur.fetchall()
    cur.close()

    return render_template("admin/hasil_prioritas.html", data=data)