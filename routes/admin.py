from flask import Blueprint, render_template, redirect, session, flash, request
from extensions import mysql
from services.gemini_service import analisis_narasi
from services.clustering_service import proses_kmeans
from MySQLdb.cursors import DictCursor

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ===============================
# DASHBOARD + GRAFIK KOMODITAS
# ===============================
@admin_bp.route('/proposal')
def proposal():
    cur = mysql.connection.cursor()

    # ======================
    # DATA PROPOSAL
    # ======================
    cur.execute("""
        SELECT 
            p.id_proposal,
            kt.nama_kelompok,
            p.tanggal_pengajuan,
            p.status,
            IFNULL(h.skor_kelayakan, 0),
            IFNULL(h.skor_urgensi, 0),
            k.nama_komoditas
        FROM proposal p
        LEFT JOIN kelompok_tani kt ON p.id_kelompok = kt.id_kelompok
        LEFT JOIN hasil_ai h ON p.id_proposal = h.id_proposal
        LEFT JOIN komoditas k ON p.id_komoditas = k.id
        ORDER BY p.tanggal_pengajuan DESC
    """)
    data = cur.fetchall()

    # ======================
    # CHART KOMODITAS
    # ======================
    cur.execute("""
        SELECT k.nama_komoditas, COUNT(*)
        FROM proposal p
        LEFT JOIN komoditas k ON p.id_komoditas = k.id
        GROUP BY k.nama_komoditas
    """)
    chart = cur.fetchall()

    komoditas_chart = [
        {"nama": c[0] or "Lainnya", "jumlah": c[1]} for c in chart
    ]

    # ======================
    # LIST KOMODITAS (FILTER)
    # ======================
    cur.execute("SELECT nama_komoditas FROM komoditas")
    komoditas_list = cur.fetchall()

    cur.close()

    # ======================
    # HITUNG DATA
    # ======================
    total = len(data)
    valid = len([d for d in data if d[3] == 'Selesai'])
    ditolak = len([d for d in data if d[3] == 'Ditolak'])

    # ======================
    # FORMAT DATA
    # ======================
    proposals = []
    for d in data:
        proposals.append({
            "id_proposal": d[0],
            "nama_kelompok": d[1],
            "tanggal_pengajuan": d[2],
            "status": d[3],
            "kelayakan": d[4],
            "urgensi": d[5],
            "nama_komoditas": d[6] or "-",
            "ai": "✔" if d[4] > 0 else "-"
        })

    # ======================
    # DEFAULT (BIAR TIDAK ERROR)
    # ======================
    prioritas_chart = []

    return render_template(
        'admin/proposal.html',
        proposals=proposals,
        total=total,
        valid=valid,
        ditolak=ditolak,
        komoditas_chart=komoditas_chart,
        prioritas_chart=prioritas_chart,
        komoditas_list=komoditas_list
    )
# ===============================
# EDIT PROPOSAL
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

        cur.execute("UPDATE proposal SET status=%s WHERE id_proposal=%s", (status, id_proposal))

        cur.execute("SELECT id_ai FROM hasil_ai WHERE id_proposal=%s", (id_proposal,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE hasil_ai
                SET skor_kelayakan=%s, skor_urgensi=%s, ringkasan=%s
                WHERE id_proposal=%s
            """, (skor_kelayakan, skor_urgensi, ringkasan, id_proposal))
        else:
            cur.execute("""
                INSERT INTO hasil_ai (id_proposal, skor_kelayakan, skor_urgensi, ringkasan)
                VALUES (%s,%s,%s,%s)
            """, (id_proposal, skor_kelayakan, skor_urgensi, ringkasan))

        mysql.connection.commit()
        cur.close()

        flash("Data berhasil diperbarui", "success")
        return redirect("/admin/proposal")

    cur.execute("""
        SELECT * FROM proposal p
        LEFT JOIN hasil_ai ha ON p.id_proposal = ha.id_proposal
        WHERE p.id_proposal=%s
    """, (id_proposal,))
    data = cur.fetchone()

    cur.close()
    return render_template("admin/edit_proposal.html", data=data)

# ===============================
# DELETE
# ===============================
@admin_bp.route("/delete/<id_proposal>")
def delete_proposal(id_proposal):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM hasil_clustering WHERE id_proposal=%s", (id_proposal,))
    cur.execute("DELETE FROM hasil_ai WHERE id_proposal=%s", (id_proposal,))
    cur.execute("DELETE FROM proposal WHERE id_proposal=%s", (id_proposal,))

    mysql.connection.commit()
    cur.close()

    flash("Proposal berhasil dihapus", "success")
    return redirect("/admin/proposal")

# ===============================
# CLUSTERING PER KOMODITAS (FIX)
# ===============================
@admin_bp.route("/clustering")
def clustering():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            pm.id_proposal,
            pm.luas_lahan,
            pm.jumlah_bantuan_sebelumnya,
            pm.pagu_anggaran,
            ha.skor_kelayakan,
            ha.skor_urgensi,
            k.nama_komoditas
        FROM proposal_metrik pm
        JOIN hasil_ai ha ON pm.id_proposal = ha.id_proposal
        JOIN proposal p ON pm.id_proposal = p.id_proposal
        JOIN komoditas k ON p.id_komoditas = k.id
    """)

    rows = cur.fetchall()

    kelompok = {}
    for r in rows:
        kelompok.setdefault(r[6], []).append(r)

    prioritas_map = {
        0: "Prioritas 1",
        1: "Prioritas 2",
        2: "Prioritas 3"
    }

    for kom, data in kelompok.items():
        fitur = [d[1:6] for d in data]
        ids = [d[0] for d in data]

        if len(fitur) < 3:
            continue

        labels = proses_kmeans(fitur)

        for pid, label in zip(ids, labels):
            cur.execute("""
                REPLACE INTO hasil_clustering
                (id_proposal, cluster, kategori_prioritas)
                VALUES (%s,%s,%s)
            """, (pid, int(label), prioritas_map[int(label)]))

    mysql.connection.commit()
    cur.close()

    flash("Clustering berhasil", "success")
    return redirect("/admin/proposal")

# ===============================
# HASIL CLUSTERING
# ===============================
@admin_bp.route("/hasil-clustering")
def hasil_clustering():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.id_proposal,
            k.nama_komoditas,
            kt.nama_kelompok,
            h.cluster,
            h.kategori_prioritas
        FROM hasil_clustering h
        JOIN proposal p ON h.id_proposal = p.id_proposal
        LEFT JOIN kelompok_tani kt ON p.id_kelompok = kt.id_kelompok
        LEFT JOIN komoditas k ON p.id_komoditas = k.id
    """)

    data = cur.fetchall()
    cur.close()

    return render_template("admin/hasil_clustering.html", data=data)