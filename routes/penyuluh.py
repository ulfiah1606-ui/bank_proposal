from flask import Blueprint, render_template, request, redirect, session, url_for
from extensions import mysql
from MySQLdb.cursors import DictCursor
from datetime import datetime
import json

penyuluh_bp = Blueprint("penyuluh", __name__, url_prefix="/penyuluh")


# =====================================================
# DASHBOARD PENYULUH
# =====================================================
@penyuluh_bp.route("/dashboard")
def dashboard():

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    wilayah = session.get("wilayah_binaan")

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT 
            p.id_proposal,
            kt.nama_kelompok,
            p.status,
            p.nama_ppl,
            hc.kategori_prioritas,
            ha.skor_kelayakan,
            ha.skor_urgensi
        FROM proposal p
        JOIN kelompok_tani kt 
            ON p.id_kelompok = kt.id_kelompok
        LEFT JOIN hasil_ai ha 
            ON p.id_proposal = ha.id_proposal
        LEFT JOIN hasil_clustering hc 
            ON p.id_proposal = hc.id_proposal
        WHERE kt.kecamatan = %s
        ORDER BY p.tanggal_pengajuan DESC
    """, (wilayah,))

    data = cur.fetchall()
    cur.close()

    return render_template(
        "penyuluh/dashboard.html",
        data=data,
        nama=session.get("nama_penyuluh"),
        nip=session.get("nip_penyuluh")
    )


# =====================================================
# DETAIL PROPOSAL
# =====================================================
@penyuluh_bp.route("/detail/<id_proposal>")
def detail_proposal(id_proposal):

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    cur = mysql.connection.cursor(DictCursor)

    # JOIN proposal + kelompok_tani + proposal_narasi + proposal_dokumen
    cur.execute("""
        SELECT p.*, kt.nama_kelompok, kt.kecamatan, kt.desa, kt.kabupaten,
               kt.nama_ketua AS kt_nama_ketua, kt.nik_ketua, kt.ttd_ketua,
               pn.latar_belakang, pn.maksud, pn.tujuan AS narasi_tujuan,
               pn.kebutuhan AS usulan_kebutuhan, pn.data_kelompok,
               pn.lokasi, pn.penutup, pn.permohonan_bantuan,
               pn.nomor_surat, pn.tanggal_surat, pn.lampiran,
               pn.perihal, pn.tujuan_surat, pn.lokasi_tujuan,
               pd.foto_ktp AS ktp_ketua, pd.ss_simluhtan AS simluhtan
        FROM proposal p
        JOIN kelompok_tani kt 
            ON p.id_kelompok = kt.id_kelompok
        LEFT JOIN proposal_narasi pn
            ON p.id_proposal = pn.id_proposal
        LEFT JOIN proposal_dokumen pd
            ON p.id_proposal = pd.id_proposal
        WHERE p.id_proposal = %s
    """, (id_proposal,))

    proposal = cur.fetchone()
    cur.close()

    if not proposal:
        return redirect(url_for("penyuluh.dashboard"))

    # Parse data_kelompok JSON untuk tabel CPCL
    anggota_kelompok = []
    total_luas = 0
    total_kebutuhan = 0

    if proposal.get("data_kelompok"):
        try:
            anggota_kelompok = json.loads(proposal["data_kelompok"])
            for a in anggota_kelompok:
                total_luas += float(a.get("luas", 0))
                total_kebutuhan += float(a.get("kebutuhan", 0))
        except (json.JSONDecodeError, ValueError):
            anggota_kelompok = []

    # Pastikan field tujuan narasi tersedia sebagai proposal.tujuan
    if proposal.get("narasi_tujuan"):
        proposal["tujuan"] = proposal["narasi_tujuan"]

    return render_template(
        "penyuluh/detail_proposal.html",
        proposal=proposal,
        anggota_kelompok=anggota_kelompok,
        total_luas=total_luas,
        total_kebutuhan=total_kebutuhan,
        now=datetime.now()
    )


# =====================================================
# SIMPAN TTD DIGITAL
# =====================================================
@penyuluh_bp.route("/simpan-ttd/<id_proposal>", methods=["POST"])
def simpan_ttd(id_proposal):

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    signature = request.form.get("signature")
    nama = session.get("nama_penyuluh")
    nip = session.get("nip_penyuluh")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE proposal
        SET 
            nama_ppl = %s,
            nip_ppl = %s,
            ttd_ppl = %s,
            tanggal_ttd = NOW(),
            status = 'Diverifikasi Penyuluh'
        WHERE id_proposal = %s
    """, (nama, nip, signature, id_proposal))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for("penyuluh.detail_proposal",
                            id_proposal=id_proposal))


# =====================================================
# TTD CEPAT
# =====================================================
@penyuluh_bp.route("/ttd/<id_proposal>")
def ttd_proposal(id_proposal):

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    nama = session.get("nama_penyuluh")
    nip = session.get("nip_penyuluh")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE proposal
        SET 
            nama_ppl = %s,
            nip_ppl = %s,
            ttd_ppl = 'Disetujui',
            tanggal_ttd = NOW(),
            status = 'Diverifikasi Penyuluh'
        WHERE id_proposal = %s
    """, (nama, nip, id_proposal))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for("penyuluh.dashboard"))


# =====================================================
# LOGOUT
# =====================================================
@penyuluh_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login/penyuluh")