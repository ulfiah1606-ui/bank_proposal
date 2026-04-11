from flask import Blueprint, render_template, request, session, redirect, flash
from extensions import mysql
from datetime import datetime
import uuid
import re
import os
from werkzeug.utils import secure_filename

try:
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency at runtime
    pytesseract = None
    Image = None

tani_bp = Blueprint("tani", __name__, url_prefix="/proposal")

# ===============================
# KONFIG UPLOAD
# ===============================
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

OCR_ENGINE_READY = bool(pytesseract and Image)
if OCR_ENGINE_READY:
    for t_path in TESSERACT_WINDOWS_PATHS:
        if os.path.exists(t_path):
            pytesseract.pytesseract.tesseract_cmd = t_path
            break

# ===============================
# HELPER
# ===============================
def angka_bersih(value):
    if not value:
        return 0
    return int(re.sub(r"[^\d]", "", value))


def _column_exists(cur, table_name, column_name):
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
    """, (table_name, column_name))
    return cur.fetchone()[0] > 0


def _extract_ocr_text(file_path):
    if not OCR_ENGINE_READY or not file_path or not os.path.exists(file_path):
        return ""

    try:
        with Image.open(file_path) as img:
            return pytesseract.image_to_string(img, lang="ind+eng").lower()
    except Exception:
        try:
            with Image.open(file_path) as img:
                return pytesseract.image_to_string(img, lang="eng").lower()
        except Exception:
            return ""


def _validate_ocr_documents(path_ktp_file, path_simluhtan_file):
    if not OCR_ENGINE_READY:
        return {
            "engine_ready": False,
            "ktp_valid": True,
            "simluhtan_valid": True,
            "ktp_score": 0,
            "simluhtan_score": 0,
            "ktp_text": "",
            "simluhtan_text": "",
        }

    ktp_text = _extract_ocr_text(path_ktp_file)
    simluhtan_text = _extract_ocr_text(path_simluhtan_file)

    ktp_keywords = ["nik", "nama", "alamat"]
    simluhtan_keywords = ["simluhtan", "kelompok tani", "penyuluh"]

    ktp_score = sum(1 for k in ktp_keywords if k in ktp_text)
    simluhtan_score = sum(1 for k in simluhtan_keywords if k in simluhtan_text)

    return {
        "engine_ready": True,
        "ktp_valid": ktp_score >= 2,
        "simluhtan_valid": simluhtan_score >= 1,
        "ktp_score": ktp_score,
        "simluhtan_score": simluhtan_score,
        "ktp_text": ktp_text,
        "simluhtan_text": simluhtan_text,
    }


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
        save_path_ktp = None
        save_path_simluhtan = None

        if foto_ktp and foto_ktp.filename:
            ext = os.path.splitext(secure_filename(foto_ktp.filename))[1].lower() or ".jpg"
            filename = f"{id_proposal}_ktp{ext}"
            save_path_ktp = os.path.join(UPLOAD_FOLDER, filename)
            foto_ktp.save(save_path_ktp)
            path_ktp = f"uploads/{filename}"

        if ss_simluhtan and ss_simluhtan.filename:
            ext = os.path.splitext(secure_filename(ss_simluhtan.filename))[1].lower() or ".jpg"
            filename = f"{id_proposal}_simluhtan{ext}"
            save_path_simluhtan = os.path.join(UPLOAD_FOLDER, filename)
            ss_simluhtan.save(save_path_simluhtan)
            path_simluhtan = f"uploads/{filename}"

        ocr_result = _validate_ocr_documents(save_path_ktp, save_path_simluhtan)
        dokumen_valid = ocr_result["ktp_valid"] and ocr_result["simluhtan_valid"]
        status_proposal = "diajukan" if dokumen_valid else "ditolak"

        if not ocr_result["engine_ready"]:
            catatan_ocr = "Validasi OCR tidak aktif (modul OCR/Tesseract belum tersedia)."
        elif dokumen_valid:
            catatan_ocr = (
                f"Valid OCR (KTP={ocr_result['ktp_score']}, "
                f"Simluhtan={ocr_result['simluhtan_score']})"
            )
        else:
            catatan_ocr = (
                f"Tidak valid OCR (KTP={ocr_result['ktp_score']}, "
                f"Simluhtan={ocr_result['simluhtan_score']})"
            )

        cur = mysql.connection.cursor()

        try:
            has_catatan_ocr = _column_exists(cur, "proposal", "catatan_ocr")

            # ==================================================
            # INSERT KE TABEL PROPOSAL (SUDAH SESUAI STRUKTUR)
            # ==================================================
            if has_catatan_ocr:
                cur.execute("""
                    INSERT INTO proposal
                    (id_proposal, id_kelompok, tanggal_pengajuan, status, catatan_ocr,
                     nama_ketua, nip_ketua, ttd_poktan,
                     nama_ppl, nip_ppl, ttd_ppl,
                     nama_kepala, nip_kepala, ttd_kepala)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    id_proposal,
                    id_kelompok,
                    datetime.now(),
                    status_proposal,
                    catatan_ocr,
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
            else:
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
                    status_proposal,
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

        if not ocr_result["engine_ready"]:
            flash("Proposal berhasil dikirim. Catatan: validasi OCR belum aktif karena modul OCR belum terpasang.", "warning")
        elif not dokumen_valid:
            flash(
                f"Dokumen terdeteksi tidak valid (KTP skor: {ocr_result['ktp_score']}, Simluhtan skor: {ocr_result['simluhtan_score']}). Proposal otomatis berstatus ditolak.",
                "danger"
            )
        else:
            flash("Dokumen tervalidasi OCR. Proposal berhasil dikirim.", "success")

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