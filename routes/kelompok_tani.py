from flask import Blueprint, render_template, request, session, redirect
from extensions import mysql
from datetime import datetime
import uuid
import re
import os

tani_bp = Blueprint("tani", __name__, url_prefix="/proposal")

# ===============================
# KONFIG UPLOAD
# ===============================
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===============================
# HELPER
# ===============================
def angka_bersih(value):
    if not value:
        return 0
    return int(re.sub(r"[^\d]", "", value))


# =====================================================
# REGISTER KELOMPOK TANI
# =====================================================
@tani_bp.route("/register", methods=["GET", "POST"])
def register_kelompok():

    if request.method == "POST":
        cur = mysql.connection.cursor()

        try:
            # Insert ke tabel kelompok_tani (profil)
            cur.execute("""
                INSERT INTO kelompok_tani
                (nama_kelompok, nama_ketua, kecamatan, desa,
                 jumlah_anggota, created_at, password)
                VALUES (%s,%s,%s,%s,%s,NOW(),%s)
            """, (
                request.form.get("nama_kelompok"),
                request.form.get("nama_ketua"),
                request.form.get("kecamatan"),
                request.form.get("desa"),
                request.form.get("jumlah_anggota"),
                request.form.get("password")
            ))

            id_kelompok_baru = cur.lastrowid

            # Insert ke tabel users (autentikasi)
            cur.execute("""
                INSERT INTO users
                (nama, username, password, role, id_kelompok, wilayah_binaan)
                VALUES (%s, %s, %s, 'kelompok_tani', %s, %s)
            """, (
                request.form.get("nama_kelompok"),
                str(id_kelompok_baru),
                request.form.get("password"),
                id_kelompok_baru,
                request.form.get("kecamatan")
            ))

            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            return f"ERROR: {str(e)}"

        cur.close()

        return render_template(
            "kelompok_tani/register.html",
            sukses=True,
            id_kelompok=id_kelompok_baru
        )

    return render_template("kelompok_tani/register.html")


# =====================================================
# LOGIN KELOMPOK TANI
# =====================================================
@tani_bp.route("/login", methods=["GET", "POST"])
def login_kelompok():

    if request.method == "POST":
        id_kelompok = request.form.get("id_kelompok", "").strip()
        password = request.form.get("password", "").strip()

        cur = mysql.connection.cursor()

        # Login dari tabel users
        cur.execute("""
            SELECT id_user, nama, id_kelompok
            FROM users
            WHERE username = %s AND password = %s AND role = 'kelompok_tani'
        """, (id_kelompok, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session.clear()
            session["kelompok_login"] = True
            session["role"] = "kelompok_tani"
            session["id_kelompok"] = user[2]
            session["nama_kelompok"] = user[1]
            return redirect("/proposal/input")

        return render_template(
            "kelompok_tani/login_kelompok.html",
            error="ID atau Password salah"
        )

    return render_template("kelompok_tani/login_kelompok.html")


# =====================================================
# LOGOUT
# =====================================================
@tani_bp.route("/logout")
def logout_kelompok():
    session.clear()
    return redirect("/proposal/login")


# =====================================================
# INPUT PROPOSAL FINAL FIX
# =====================================================
@tani_bp.route("/input", methods=["GET", "POST"])
def input_proposal():

    if not session.get("kelompok_login"):
        return redirect("/proposal/login")

    if request.method == "POST":

        id_kelompok = session.get("id_kelompok")
        id_proposal = str(uuid.uuid4())[:12]

        # ========================
        # DATA FORM
        # ========================
        latar_belakang = request.form.get("latar_belakang")
        maksud = request.form.get("maksud")
        tujuan = request.form.get("tujuan")
        kebutuhan = request.form.get("kebutuhan")
        data_kelompok = request.form.get("data_kelompok_json")
        kondisi_lahan = request.form.get("kondisi_lahan")
        penutup = request.form.get("penutup")
        permohonan_bantuan = request.form.get("permohonan_bantuan")
        nomor_surat = request.form.get("nomor_surat")
        tanggal_surat = request.form.get("tanggal_surat")
        lampiran = request.form.get("lampiran")
        perihal = request.form.get("perihal")
        tujuan_surat = request.form.get("tujuan_surat")
        lokasi_tujuan = request.form.get("lokasi_tujuan")

        nama_ketua = request.form.get("nama_ketua")
        nip_ketua = request.form.get("nip_ketua")
        ttd_poktan = request.form.get("ttd_poktan")

        # ========================
        # UPLOAD FILE
        # ========================
        foto_ktp = request.files.get("foto_ktp")
        ss_simluhtan = request.files.get("ss_simluhtan")

        path_ktp = None
        path_simluhtan = None

        if foto_ktp and foto_ktp.filename:
            filename = f"{id_proposal}_ktp.jpg"
            path_ktp = os.path.join(UPLOAD_FOLDER, filename)
            foto_ktp.save(path_ktp)

        if ss_simluhtan and ss_simluhtan.filename:
            filename = f"{id_proposal}_simluhtan.jpg"
            path_simluhtan = os.path.join(UPLOAD_FOLDER, filename)
            ss_simluhtan.save(path_simluhtan)

        cur = mysql.connection.cursor()

        try:
            # ==================================================
            # INSERT KE TABEL PROPOSAL (SUDAH SESUAI STRUKTUR)
            # ==================================================
            cur.execute("""
                INSERT INTO proposal
                (id_proposal, id_kelompok, tanggal_pengajuan, status,
                 nama_ketua, nip_ketua, ttd_poktan,
                 nama_ppl, nip_ppl, ttd_ppl,
                 nama_kepala, nip_kepala, ttd_kepala)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                id_proposal,
                id_kelompok,
                datetime.now(),
                "diajukan",
                nama_ketua,
                nip_ketua,
                ttd_poktan,
                None,
                None,
                None,
                None,
                None,
                None
            ))

            # INSERT NARASI (SUDAH TERMASUK PERMOHONAN BANTUAN)
            cur.execute("""
                INSERT INTO proposal_narasi
                (id_proposal, latar_belakang, maksud, tujuan,
                kebutuhan, data_kelompok, lokasi, penutup,
                permohonan_bantuan,
                nomor_surat, tanggal_surat, lampiran,
                perihal, tujuan_surat, lokasi_tujuan)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                id_proposal,
                latar_belakang,
                maksud,
                tujuan,
                kebutuhan,
                data_kelompok,
                kondisi_lahan,
                penutup,
                permohonan_bantuan,
                nomor_surat,
                tanggal_surat,
                lampiran,
                perihal,
                tujuan_surat,
                lokasi_tujuan
            ))

            # INSERT DOKUMEN
            cur.execute("""
                INSERT INTO proposal_dokumen
                (id_proposal, foto_ktp, ss_simluhtan)
                VALUES (%s,%s,%s)
            """, (
                id_proposal,
                path_ktp,
                path_simluhtan
            ))

            mysql.connection.commit()

        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            return f"ERROR DATABASE: {str(e)}"

        cur.close()

        return render_template(
            "kelompok_tani/input_proposal.html",
            sukses=True,
            id_proposal=id_proposal
        )

    return render_template("kelompok_tani/input_proposal.html")


# =====================================================
# CEK STATUS
# =====================================================
@tani_bp.route("/status", methods=["GET", "POST"])
def status_proposal():

    data = None

    if request.method == "POST":
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id_proposal, status
            FROM proposal
            WHERE id_proposal=%s
        """, (request.form.get("id_proposal"),))
        row = cur.fetchone()
        cur.close()

        if row:
            data = {
                "id_proposal": row[0],
                "status": row[1]
            }

    return render_template("kelompok_tani/status_proposal.html", data=data)