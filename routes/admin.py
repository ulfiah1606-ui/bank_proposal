from flask import Blueprint, render_template, redirect, session, flash, request
from extensions import mysql
from services.gemini_service import analisis_narasi
from services.clustering_service import proses_kmeans
from MySQLdb.cursors import DictCursor

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _table_exists(cur, table_name):
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
    """, (table_name,))
    return cur.fetchone()[0] > 0


def _column_exists(cur, table_name, column_name):
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
    """, (table_name, column_name))
    return cur.fetchone()[0] > 0


def _has_komoditas_schema(cur):
    return _table_exists(cur, "komoditas") and _column_exists(cur, "proposal", "id_komoditas")


def _archive_schema_ready(cur):
    return _column_exists(cur, "proposal", "is_archived") and _column_exists(cur, "proposal", "archived_at")

# ===============================
# DASHBOARD + GRAFIK KOMODITAS
# ===============================
@admin_bp.route('/proposal')
def proposal():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()
    has_komoditas = _has_komoditas_schema(cur)
    has_catatan_ocr = _column_exists(cur, "proposal", "catatan_ocr")
    has_kelompok_komoditas = _column_exists(cur, "kelompok_tani", "komoditas")
    archive_ready = _archive_schema_ready(cur)

    komoditas_select = "IFNULL(kt.komoditas, '-') AS nama_komoditas" if has_kelompok_komoditas else "'-' AS nama_komoditas"
    catatan_ocr_select = "IFNULL(p.catatan_ocr, '-') AS catatan_ocr" if has_catatan_ocr else "'-' AS catatan_ocr"
    active_where = "WHERE IFNULL(p.is_archived, 0) = 0" if archive_ready else ""
    archive_where = "WHERE IFNULL(p.is_archived, 0) = 1" if archive_ready else ""
    archived_at_select = "p.archived_at" if archive_ready else "NULL AS archived_at"

    # ======================
    # DATA PROPOSAL AKTIF
    # ======================
    cur.execute(f"""
        SELECT
            p.id_proposal,
            {komoditas_select},
            kt.nama_kelompok,
            p.tanggal_pengajuan,
            p.status,
            IFNULL(h.skor_kelayakan, 0) AS skor_kelayakan,
            IFNULL(h.skor_urgensi, 0) AS skor_urgensi,
            {catatan_ocr_select},
            {archived_at_select}
        FROM proposal p
        LEFT JOIN kelompok_tani kt ON p.id_kelompok = kt.id_kelompok
        LEFT JOIN hasil_ai h ON p.id_proposal = h.id_proposal
        {active_where}
        ORDER BY p.tanggal_pengajuan DESC
    """)
    active_data = cur.fetchall()

    archived_data = []
    if archive_ready:
        cur.execute(f"""
            SELECT
                p.id_proposal,
                {komoditas_select},
                kt.nama_kelompok,
                p.tanggal_pengajuan,
                p.status,
                IFNULL(h.skor_kelayakan, 0) AS skor_kelayakan,
                IFNULL(h.skor_urgensi, 0) AS skor_urgensi,
                {catatan_ocr_select},
                p.archived_at
            FROM proposal p
            LEFT JOIN kelompok_tani kt ON p.id_kelompok = kt.id_kelompok
            LEFT JOIN hasil_ai h ON p.id_proposal = h.id_proposal
            {archive_where}
            ORDER BY p.archived_at DESC, p.tanggal_pengajuan DESC
        """)
        archived_data = cur.fetchall()

    # ======================
    # CHART KOMODITAS
    # ======================
    chart_where = "WHERE IFNULL(p.is_archived, 0) = 0" if archive_ready else ""
    if has_komoditas:
        cur.execute(f"""
            SELECT k.nama_komoditas, COUNT(*)
            FROM proposal p
            LEFT JOIN komoditas k ON p.id_komoditas = k.id
            {chart_where}
            GROUP BY k.nama_komoditas
        """)
        chart = cur.fetchall()
        komoditas_chart = [
            {"nama": c[0] or "Lainnya", "jumlah": c[1]} for c in chart
        ]
    else:
        komoditas_chart = [{"nama": "Tanpa Komoditas", "jumlah": len(active_data)}] if active_data else []

    # ======================
    # LIST KOMODITAS (FILTER)
    # ======================
    komoditas_set = sorted({
        str(row[1]).strip() for row in active_data
        if row[1] and str(row[1]).strip() and str(row[1]).strip() != "-"
    })
    komoditas_list = [(k,) for k in komoditas_set]

    cur.close()

    # ======================
    # HITUNG DATA
    # ======================
    total = len(active_data)
    valid = len([d for d in active_data if str(d[4] or "").strip().lower() == 'selesai'])
    ditolak = len([d for d in active_data if str(d[4] or "").strip().lower() == 'ditolak'])
    arsip_total = len(archived_data)

    # ======================
    # FORMAT DATA
    # ======================
    def _map_row(row):
        return {
            "id_proposal": row[0],
            "nama_komoditas": row[1] or "-",
            "nama_kelompok": row[2],
            "tanggal_pengajuan": row[3],
            "status": row[4],
            "kelayakan": row[5],
            "urgensi": row[6],
            "catatan_ocr": row[7] or "-",
            "archived_at": row[8],
            "ai": "✔" if row[6] and float(row[6]) > 0 else "-"
        }

    proposals = []
    for d in active_data:
        proposals.append(_map_row(d))

    archived_proposals = []
    for d in archived_data:
        archived_proposals.append(_map_row(d))

    # ======================
    # DEFAULT (BIAR TIDAK ERROR)
    # ======================
    prioritas_chart = []

    return render_template(
        'admin/proposal.html',
        proposals=proposals,
        archived_proposals=archived_proposals,
        total=total,
        valid=valid,
        ditolak=ditolak,
        arsip_total=arsip_total,
        archive_ready=archive_ready,
        komoditas_chart=komoditas_chart,
        prioritas_chart=prioritas_chart,
        komoditas_list=komoditas_list
    )


@admin_bp.route('/archive/<id_proposal>')
def archive_proposal(id_proposal):
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()
    archive_ready = _archive_schema_ready(cur)

    if not archive_ready:
        cur.close()
        flash("Fitur arsip belum aktif. Jalankan migrasi arsip surat terlebih dahulu.", "warning")
        return redirect("/admin/proposal")

    cur.execute("SELECT status FROM proposal WHERE id_proposal=%s", (id_proposal,))
    row = cur.fetchone()

    if not row:
        cur.close()
        flash("Proposal tidak ditemukan.", "warning")
        return redirect("/admin/proposal")

    status = str(row[0] or "").strip().lower()
    if status != "selesai":
        cur.close()
        flash("Hanya proposal berstatus selesai yang bisa diarsipkan.", "warning")
        return redirect("/admin/proposal")

    cur.execute("""
        UPDATE proposal
        SET is_archived = 1,
            archived_at = NOW()
        WHERE id_proposal = %s
    """, (id_proposal,))
    mysql.connection.commit()
    cur.close()

    flash("Proposal berhasil diarsipkan.", "success")
    return redirect("/admin/proposal")


@admin_bp.route('/unarchive/<id_proposal>')
def unarchive_proposal(id_proposal):
    if session.get("role") != "admin":
        return redirect("/login/admin")

    cur = mysql.connection.cursor()
    archive_ready = _archive_schema_ready(cur)

    if not archive_ready:
        cur.close()
        flash("Fitur arsip belum aktif. Jalankan migrasi arsip surat terlebih dahulu.", "warning")
        return redirect("/admin/proposal")

    cur.execute("""
        UPDATE proposal
        SET is_archived = 0,
            archived_at = NULL
        WHERE id_proposal = %s
    """, (id_proposal,))
    mysql.connection.commit()
    cur.close()

    flash("Proposal berhasil dikembalikan dari arsip.", "success")
    return redirect("/admin/proposal")
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
    has_komoditas = _has_komoditas_schema(cur)

    if has_komoditas:
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
    else:
        cur.execute("""
            SELECT 
                pm.id_proposal,
                pm.luas_lahan,
                pm.jumlah_bantuan_sebelumnya,
                pm.pagu_anggaran,
                ha.skor_kelayakan,
                ha.skor_urgensi,
                'Tanpa Komoditas' AS nama_komoditas
            FROM proposal_metrik pm
            JOIN hasil_ai ha ON pm.id_proposal = ha.id_proposal
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
    has_komoditas = _has_komoditas_schema(cur)

    if has_komoditas:
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
    else:
        cur.execute("""
            SELECT 
                p.id_proposal,
                '-' AS nama_komoditas,
                kt.nama_kelompok,
                h.cluster,
                h.kategori_prioritas
            FROM hasil_clustering h
            JOIN proposal p ON h.id_proposal = p.id_proposal
            LEFT JOIN kelompok_tani kt ON p.id_kelompok = kt.id_kelompok
        """)

    data = cur.fetchall()
    cur.close()

    return render_template("admin/hasil_clustering.html", data=data)