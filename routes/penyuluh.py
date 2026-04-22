from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from extensions import mysql
from MySQLdb.cursors import DictCursor
from datetime import datetime
import json

penyuluh_bp = Blueprint("penyuluh", __name__, url_prefix="/penyuluh")


def _normalize_wilayah_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    return " ".join(text.split())


def _normalize_wilayah_key(value):
    text = _normalize_wilayah_text(value)
    text = text.replace("kabupaten", "")
    text = text.replace("kecamatan", "")
    text = text.replace("kab.", "")
    text = text.replace("kec.", "")
    return "".join(text.split())


def _wilayah_matches(wilayah_binaan, kecamatan, kabupaten):
    wilayah_key = _normalize_wilayah_key(wilayah_binaan)
    if not wilayah_key:
        return True

    kecamatan_key = _normalize_wilayah_key(kecamatan)
    kabupaten_key = _normalize_wilayah_key(kabupaten)

    candidates = [k for k in (kecamatan_key, kabupaten_key) if k]
    if not candidates:
        return False

    for candidate in candidates:
        if wilayah_key == candidate:
            return True
        if wilayah_key in candidate or candidate in wilayah_key:
            return True

    return False


def _normalize_asset_path(path_value):
    if not path_value:
        return None

    raw = str(path_value).strip()
    if not raw:
        return None

    # Keep data URL as-is for canvas signatures.
    if raw.startswith("data:image/"):
        return raw

    normalized = raw.replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    if normalized.lower().startswith("static/"):
        normalized = normalized[7:]

    return normalized


def _build_image_src(path_value):
    normalized = _normalize_asset_path(path_value)
    if not normalized:
        return None

    if normalized.startswith("data:image/"):
        return normalized

    lower = normalized.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")):
        return url_for("static", filename=normalized)

    return None


# =====================================================
# DASHBOARD PENYULUH
# =====================================================
@penyuluh_bp.route("/dashboard")
def dashboard():

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    id_penyuluh = session.get("id_penyuluh")
    wilayah_session = str(session.get("wilayah_binaan") or "").strip()

    cur = mysql.connection.cursor(DictCursor)
    profil_ttd = None
    wilayah_profil = ""

    if id_penyuluh:
        cur.execute("""
            SELECT ttd_penyuluh, kecamatan
            FROM penyuluh
            WHERE id_penyuluh = %s
        """, (id_penyuluh,))
        profil = cur.fetchone()
        if profil:
            profil_ttd = profil.get("ttd_penyuluh")
            wilayah_profil = str(profil.get("kecamatan") or "").strip()

    wilayah = wilayah_session
    if wilayah_profil and (
        not wilayah
        or _normalize_wilayah_text(wilayah) != _normalize_wilayah_text(wilayah_profil)
    ):
        wilayah = wilayah_profil
        session["wilayah_binaan"] = wilayah_profil

    cur.execute(f"""
        SELECT 
            p.id_proposal,
            kt.nama_kelompok,
            kt.kecamatan,
            kt.kabupaten,
            p.status,
            p.nama_ppl,
            p.ttd_ppl,
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
        ORDER BY p.tanggal_pengajuan DESC
    """)

    all_rows = cur.fetchall()
    if wilayah:
        data = [
            row for row in all_rows
            if _wilayah_matches(wilayah, row.get("kecamatan"), row.get("kabupaten"))
        ]
    else:
        flash("Wilayah binaan penyuluh belum diatur. Menampilkan semua proposal.", "warning")
        data = all_rows

    cur.close()

    has_ttd_profil = bool(profil_ttd and str(profil_ttd).strip())

    return render_template(
        "penyuluh/dashboard.html",
        data=data,
        nama=session.get("nama_penyuluh"),
        nip=session.get("nip_penyuluh"),
        ttd_penyuluh=profil_ttd,
        has_ttd_profil=has_ttd_profil
    )


@penyuluh_bp.route("/simpan-ttd-akun", methods=["POST"])
def simpan_ttd_akun():

    if session.get("role") != "penyuluh":
        return redirect("/login/penyuluh")

    signature = request.form.get("signature", "").strip()

    if not signature.startswith("data:image/"):
        flash("TTD tidak valid. Silakan tanda tangan ulang.", "danger")
        return redirect(url_for("penyuluh.dashboard"))

    id_penyuluh = session.get("id_penyuluh")
    if not id_penyuluh:
        flash("Profil penyuluh tidak ditemukan. Silakan login ulang.", "danger")
        return redirect("/login/penyuluh")

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE penyuluh
        SET ttd_penyuluh = %s
        WHERE id_penyuluh = %s
    """, (signature, id_penyuluh))
    mysql.connection.commit()
    cur.close()

    flash("TTD akun penyuluh berhasil disimpan.", "success")

    return redirect(url_for("penyuluh.dashboard"))


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

    proposal["ktp_ketua_src"] = _build_image_src(proposal.get("ktp_ketua"))
    proposal["simluhtan_src"] = _build_image_src(proposal.get("simluhtan"))

    proposal["ttd_poktan_src"] = _build_image_src(
        proposal.get("ttd_poktan") or proposal.get("ttd_ketua")
    )

    raw_ttd_ppl = proposal.get("ttd_ppl")
    proposal["ttd_ppl_src"] = _build_image_src(raw_ttd_ppl)
    if proposal["ttd_ppl_src"]:
        proposal["ttd_ppl_text"] = None
    else:
        proposal["ttd_ppl_text"] = str(raw_ttd_ppl).strip() if raw_ttd_ppl else None

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
    id_penyuluh = session.get("id_penyuluh")

    cur = mysql.connection.cursor(DictCursor)

    # Selalu ambil versi terbaru TTD dari tabel profil penyuluh.
    cur.execute("""
        SELECT ttd_penyuluh
        FROM penyuluh
        WHERE id_penyuluh = %s
    """, (id_penyuluh,))
    profil = cur.fetchone()

    signature = profil.get("ttd_penyuluh") if profil else None

    if not signature or not str(signature).strip():
        cur.close()
        flash("TTD akun belum disimpan. Tambahkan TTD dulu di dashboard.", "warning")
        return redirect(url_for("penyuluh.dashboard"))

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

    flash("Proposal berhasil ditandatangani.", "success")

    return redirect(url_for("penyuluh.dashboard"))


# =====================================================
# LOGOUT
# =====================================================
@penyuluh_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login/penyuluh")