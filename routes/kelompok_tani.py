from flask import Blueprint, render_template, request, session, redirect, flash
from extensions import mysql
from datetime import datetime
import uuid
import re
import os
import shutil
from werkzeug.utils import secure_filename

try:
    import pytesseract
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional dependency at runtime
    pytesseract = None
    Image = None
    ImageOps = None

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

KTP_OCR_KEYWORDS = ["nik", "ktp", "nama", "alamat"]
SIMLUHTAN_OCR_KEYWORDS = ["simluhtan", "kelompok tani", "penyuluh"]

KTP_OCR_ALIASES = {
    "nik": ["n1k", "nlk", "n ik", "n!k"],
    "ktp": ["e-ktp", "ektp", "kartu tanda penduduk"],
    "nama": ["narna", "narna", "namaa"],
    "alamat": ["alarnat"],
}

SIMLUHTAN_OCR_ALIASES = {
    "simluhtan": ["simluh tan", "simlutan", "simluhthan"],
    "kelompok tani": ["kelornpok tani", "kelompoktani"],
    "penyuluh": ["penyuiuh", "penyuih"],
}

OCR_ENGINE_READY = bool(pytesseract and Image)
if OCR_ENGINE_READY:
    detected_tesseract_cmd = None
    for t_path in TESSERACT_WINDOWS_PATHS:
        if os.path.exists(t_path):
            detected_tesseract_cmd = t_path
            break

    if not detected_tesseract_cmd:
        detected_tesseract_cmd = shutil.which("tesseract")

    if detected_tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = detected_tesseract_cmd
    else:
        OCR_ENGINE_READY = False

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

    def _run_ocr_on_image(image_obj):
        ocr_results = []
        for lang in ("ind+eng", "eng"):
            for config in ("--oem 3 --psm 6", "--oem 3 --psm 11"):
                try:
                    extracted = pytesseract.image_to_string(image_obj, lang=lang, config=config)
                    if extracted and extracted.strip():
                        ocr_results.append(extracted.lower())
                except Exception:
                    continue
        return ocr_results

    try:
        with Image.open(file_path) as img:
            base_img = ImageOps.exif_transpose(img) if ImageOps else img.copy()

            variants = [base_img]

            gray = base_img.convert("L")
            if ImageOps:
                gray = ImageOps.autocontrast(gray)
            variants.append(gray)

            # Simple binarization often helps on ID cards with uneven lighting.
            bw = gray.point(lambda px: 255 if px > 165 else 0).convert("L")
            variants.append(bw)

            if min(base_img.size) < 1200:
                resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                upscaled = gray.resize((base_img.width * 2, base_img.height * 2), resample=resample)
                variants.append(upscaled)

            all_texts = []
            for variant in variants:
                all_texts.extend(_run_ocr_on_image(variant))

            unique_texts = [text.strip() for text in dict.fromkeys(all_texts) if text and text.strip()]
            return "\n".join(unique_texts).lower()
    except Exception:
        return ""


def _normalize_ocr_text(text):
    normalized = str(text or "").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.translate(str.maketrans({
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "|": "i",
        "!": "i",
    }))
    return normalized.replace("rn", "m")


def _extract_nik_16_candidates(text):
    raw_text = str(text or "")

    direct_digits = re.sub(r"[^\d]", "", raw_text)
    direct_candidates = re.findall(r"\d{16}", direct_digits)
    if direct_candidates:
        return direct_candidates

    digit_friendly = raw_text.translate(str.maketrans({
        "O": "0", "o": "0",
        "I": "1", "l": "1", "L": "1",
        "B": "8",
        "S": "5", "s": "5",
    }))
    normalized_digits = re.sub(r"[^\d]", "", digit_friendly)
    return re.findall(r"\d{16}", normalized_digits)


def _keyword_match_details(text, keywords, aliases=None):
    aliases = aliases or {}
    raw_text = str(text or "").lower()
    normalized_text = _normalize_ocr_text(raw_text)

    found_keywords = []
    missing_keywords = []

    for keyword in keywords:
        candidates = [keyword] + aliases.get(keyword, [])
        is_found = False

        for candidate in candidates:
            raw_candidate = str(candidate).lower().strip()
            normalized_candidate = _normalize_ocr_text(raw_candidate)

            if raw_candidate and (raw_candidate in raw_text or normalized_candidate in normalized_text):
                is_found = True
                break

        if is_found:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    return found_keywords, missing_keywords


def _format_keywords(keywords):
    return ", ".join(keywords) if keywords else "-"


def _parse_ocr_note_for_view(catatan_ocr):
    raw_note = str(catatan_ocr or "-").strip() or "-"
    lower_note = raw_note.lower()

    summary = raw_note
    ktp_reason = None
    simluhtan_reason = None

    # Extract per-document reasons from stored note text.
    ktp_match = re.search(r"KTP:\s*(.*?)(?:\s*\|\s*Simluhtan:|$)", raw_note, flags=re.IGNORECASE)
    if ktp_match:
        ktp_reason = ktp_match.group(1).strip()

    simluhtan_match = re.search(r"Simluhtan:\s*(.*)$", raw_note, flags=re.IGNORECASE)
    if simluhtan_match:
        simluhtan_reason = simluhtan_match.group(1).strip()

    first_reason_indices = [
        idx for idx in (lower_note.find("ktp:"), lower_note.find("simluhtan:"))
        if idx != -1
    ]
    if first_reason_indices:
        first_reason_idx = min(first_reason_indices)
        summary = raw_note[:first_reason_idx].strip()
        if summary.endswith("|"):
            summary = summary[:-1].strip()
        if not summary:
            summary = raw_note

    is_invalid = "tidak valid" in lower_note
    ocr_inactive = ("tidak aktif" in lower_note) or ("belum tersedia" in lower_note)
    is_warning = ocr_inactive

    if is_invalid:
        summary_class = "danger"
    elif is_warning:
        summary_class = "warning"
    elif "valid ocr" in lower_note:
        summary_class = "success"
    else:
        summary_class = "secondary"

    def _reason_class(reason_text):
        if not reason_text:
            return "secondary"

        reason_lower = reason_text.lower()
        if "tidak valid" in reason_lower or "tidak terdeteksi" in reason_lower:
            return "danger"
        if "valid" in reason_lower or "terdeteksi" in reason_lower:
            return "success"
        return "secondary"

    def _extract_missing_keywords(reason_text):
        if not reason_text:
            return []

        match = re.search(r"tidak terdeteksi:\s*(.+)$", reason_text, flags=re.IGNORECASE)
        if not match:
            return []

        raw_keywords = match.group(1).strip()
        if not raw_keywords or raw_keywords == "-":
            return []

        cleaned_keywords = []
        for keyword in raw_keywords.split(","):
            cleaned = keyword.strip().strip(".;:")
            if cleaned and cleaned != "-":
                cleaned_keywords.append(cleaned)

        return cleaned_keywords

    def _extract_detected_keywords(reason_text, expected_keywords, missing_keywords):
        if not reason_text:
            return []

        explicit_match = re.search(r"keyword\s+terdeteksi:\s*(.+)$", reason_text, flags=re.IGNORECASE)
        if explicit_match:
            explicit_keywords = []
            for keyword in explicit_match.group(1).split(","):
                cleaned = keyword.strip().strip(".;:")
                if cleaned and cleaned != "-":
                    explicit_keywords.append(cleaned)
            return explicit_keywords

        if not missing_keywords:
            return []

        missing_set = {keyword.lower() for keyword in missing_keywords}
        return [keyword for keyword in expected_keywords if keyword.lower() not in missing_set]

    ktp_missing_keywords = _extract_missing_keywords(ktp_reason)
    simluhtan_missing_keywords = _extract_missing_keywords(simluhtan_reason)
    ktp_found_keywords = _extract_detected_keywords(ktp_reason, KTP_OCR_KEYWORDS, ktp_missing_keywords)
    simluhtan_found_keywords = _extract_detected_keywords(
        simluhtan_reason,
        SIMLUHTAN_OCR_KEYWORDS,
        simluhtan_missing_keywords
    )

    if ocr_inactive:
        ktp_unknown_keywords = KTP_OCR_KEYWORDS
        simluhtan_unknown_keywords = SIMLUHTAN_OCR_KEYWORDS
    else:
        ktp_unknown_keywords = []
        simluhtan_unknown_keywords = []

    return {
        "raw": raw_note,
        "summary": summary,
        "summary_class": summary_class,
        "ocr_inactive": ocr_inactive,
        "ktp_reason": ktp_reason,
        "simluhtan_reason": simluhtan_reason,
        "ktp_class": _reason_class(ktp_reason),
        "simluhtan_class": _reason_class(simluhtan_reason),
        "ktp_found_keywords": ktp_found_keywords,
        "simluhtan_found_keywords": simluhtan_found_keywords,
        "ktp_missing_keywords": ktp_missing_keywords,
        "simluhtan_missing_keywords": simluhtan_missing_keywords,
        "ktp_unknown_keywords": ktp_unknown_keywords,
        "simluhtan_unknown_keywords": simluhtan_unknown_keywords,
    }


def _validate_ocr_documents(path_ktp_file, path_simluhtan_file):
    if not OCR_ENGINE_READY:
        return {
            "engine_ready": False,
            "ktp_valid": True,
            "simluhtan_valid": True,
            "ktp_score": 0,
            "simluhtan_score": 0,
            "ktp_nik16_found": False,
            "ktp_text": "",
            "simluhtan_text": "",
            "ktp_found_keywords": [],
            "ktp_missing_keywords": [],
            "simluhtan_found_keywords": [],
            "simluhtan_missing_keywords": [],
            "ktp_reason": "Validasi OCR tidak aktif.",
            "simluhtan_reason": "Validasi OCR tidak aktif.",
        }

    ktp_text = _extract_ocr_text(path_ktp_file)
    simluhtan_text = _extract_ocr_text(path_simluhtan_file)

    ktp_keywords = KTP_OCR_KEYWORDS
    simluhtan_keywords = SIMLUHTAN_OCR_KEYWORDS

    ktp_found_keywords, ktp_missing_keywords = _keyword_match_details(
        ktp_text,
        ktp_keywords,
        aliases=KTP_OCR_ALIASES
    )
    simluhtan_found_keywords, simluhtan_missing_keywords = _keyword_match_details(
        simluhtan_text,
        simluhtan_keywords,
        aliases=SIMLUHTAN_OCR_ALIASES
    )

    ktp_score = len(ktp_found_keywords)
    simluhtan_score = len(simluhtan_found_keywords)
    ktp_nik16_found = bool(_extract_nik_16_candidates(ktp_text))
    ktp_core_hits = [keyword for keyword in ktp_found_keywords if keyword in ("nik", "nama", "alamat")]

    # KTP valid when at least one core KTP field is readable, or NIK 16-digit is detected.
    ktp_valid = bool(ktp_core_hits) or ktp_nik16_found
    simluhtan_valid = simluhtan_score >= 1

    if ktp_valid:
        ktp_reason = f"Valid. Keyword terdeteksi: {_format_keywords(ktp_found_keywords)}"
    else:
        ktp_reason = (
            "Tidak valid. Keyword KTP yang tidak terdeteksi: "
            f"{_format_keywords(ktp_missing_keywords)}"
        )

    if simluhtan_valid:
        simluhtan_reason = f"Valid. Keyword terdeteksi: {_format_keywords(simluhtan_found_keywords)}"
    else:
        simluhtan_reason = (
            "Tidak valid. Keyword Simluhtan yang tidak terdeteksi: "
            f"{_format_keywords(simluhtan_missing_keywords)}"
        )

    return {
        "engine_ready": True,
        "ktp_valid": ktp_valid,
        "simluhtan_valid": simluhtan_valid,
        "ktp_score": ktp_score,
        "simluhtan_score": simluhtan_score,
        "ktp_nik16_found": ktp_nik16_found,
        "ktp_text": ktp_text,
        "simluhtan_text": simluhtan_text,
        "ktp_found_keywords": ktp_found_keywords,
        "ktp_missing_keywords": ktp_missing_keywords,
        "simluhtan_found_keywords": simluhtan_found_keywords,
        "simluhtan_missing_keywords": simluhtan_missing_keywords,
        "ktp_reason": ktp_reason,
        "simluhtan_reason": simluhtan_reason,
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
                (nama_kelompok, nama_ketua, kecamatan, desa, komoditas,
                 jumlah_anggota, created_at, password)
                VALUES (%s,%s,%s,%s,%s,%s,NOW(),%s)
            """, (
                request.form.get("nama_kelompok"),
                request.form.get("nama_ketua"),
                request.form.get("kecamatan"),
                request.form.get("desa"),
                request.form.get("komoditas"),
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
                f"Simluhtan={ocr_result['simluhtan_score']}). "
                f"KTP: {ocr_result['ktp_reason']} | "
                f"Simluhtan: {ocr_result['simluhtan_reason']}"
            )
        else:
            invalid_reasons = []
            if not ocr_result["ktp_valid"]:
                invalid_reasons.append(f"KTP: {ocr_result['ktp_reason']}")
            if not ocr_result["simluhtan_valid"]:
                invalid_reasons.append(f"Simluhtan: {ocr_result['simluhtan_reason']}")

            catatan_ocr = (
                f"Tidak valid OCR (KTP={ocr_result['ktp_score']}, "
                f"Simluhtan={ocr_result['simluhtan_score']}). "
                + " | ".join(invalid_reasons)
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
            invalid_reasons = []
            if not ocr_result["ktp_valid"]:
                invalid_reasons.append(f"KTP: {ocr_result['ktp_reason']}")
            if not ocr_result["simluhtan_valid"]:
                invalid_reasons.append(f"Simluhtan: {ocr_result['simluhtan_reason']}")

            flash(
                f"Dokumen terdeteksi tidak valid (KTP skor: {ocr_result['ktp_score']}, Simluhtan skor: {ocr_result['simluhtan_score']}). Proposal otomatis berstatus ditolak.",
                "danger"
            )
            flash(
                "Alasan detail: " + " | ".join(invalid_reasons),
                "danger"
            )
        else:
            flash(
                "Dokumen tervalidasi OCR. "
                f"KTP: {ocr_result['ktp_reason']} | "
                f"Simluhtan: {ocr_result['simluhtan_reason']}",
                "success"
            )

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
    not_found = False

    if request.method == "POST":
        cur = mysql.connection.cursor()
        id_proposal = (request.form.get("id_proposal") or "").strip()
        has_catatan_ocr = _column_exists(cur, "proposal", "catatan_ocr")
        catatan_ocr_select = "IFNULL(p.catatan_ocr, '-') AS catatan_ocr" if has_catatan_ocr else "'-' AS catatan_ocr"

        cur.execute(f"""
            SELECT
                p.id_proposal,
                p.status,
                IFNULL(hc.kategori_prioritas, '-') AS kategori_prioritas,
                IFNULL(ha.skor_kelayakan, 0) AS skor_kelayakan,
                IFNULL(ha.skor_urgensi, 0) AS skor_urgensi,
                {catatan_ocr_select}
            FROM proposal p
            LEFT JOIN hasil_ai ha ON p.id_proposal = ha.id_proposal
            LEFT JOIN hasil_clustering hc ON p.id_proposal = hc.id_proposal
            WHERE p.id_proposal = %s
        """, (id_proposal,))
        row = cur.fetchone()
        cur.close()

        if row:
            ocr_view = _parse_ocr_note_for_view(row[5])
            data = {
                "id_proposal": row[0],
                "status": row[1],
                "kategori": row[2],
                "kelayakan": row[3],
                "urgensi": row[4],
                "catatan_ocr": row[5],
                "ocr": ocr_view,
            }
        else:
            not_found = True

    return render_template("kelompok_tani/status_proposal.html", data=data, not_found=not_found)