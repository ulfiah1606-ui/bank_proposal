from flask import Blueprint, render_template, request, redirect, session, url_for
from extensions import mysql
from MySQLdb.cursors import DictCursor

auth_bp = Blueprint("auth", __name__)


# ======================================================
# LOGIN UNIFIED (ADMIN + PENYULUH)
# Semua autentikasi dari tabel `users`
# ======================================================
@auth_bp.route("/login/<role>", methods=["GET", "POST"])
def login(role):

    if role not in ["admin", "penyuluh"]:
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        cur = mysql.connection.cursor(DictCursor)

        # Query dari tabel users
        cur.execute("""
            SELECT id_user, nama, username, password, role,
                   nip, id_penyuluh, id_kelompok, wilayah_binaan
            FROM users
            WHERE username = %s AND role = %s
        """, (username, role))
        user = cur.fetchone()
        cur.close()

        if user and user["password"] == password:
            session.clear()
            session["user_id"] = user["id_user"]
            session["role"] = user["role"]
            session["nama_user"] = user["nama"]

            if role == "admin":
                return redirect("/admin/proposal")

            if role == "penyuluh":
                # Set session data penyuluh
                session["id_penyuluh"] = user["id_penyuluh"]
                session["nama_penyuluh"] = user["nama"]
                session["nip_penyuluh"] = user["nip"]
                session["wilayah_binaan"] = user["wilayah_binaan"]

                # Ambil TTD dari tabel penyuluh (jika ada)
                if user["id_penyuluh"]:
                    cur2 = mysql.connection.cursor(DictCursor)
                    cur2.execute("""
                        SELECT ttd_penyuluh
                        FROM penyuluh
                        WHERE id_penyuluh = %s
                    """, (user["id_penyuluh"],))
                    profil = cur2.fetchone()
                    cur2.close()
                    if profil:
                        session["ttd_penyuluh"] = profil["ttd_penyuluh"]

                return redirect("/penyuluh/dashboard")

        template = "admin/login.html" if role == "admin" else "penyuluh/login.html"
        return render_template(template, error="Username atau password salah")

    template = "admin/login.html" if role == "admin" else "penyuluh/login.html"
    return render_template(template)


# ======================================================
# REGISTER PENYULUH
# Insert ke users + penyuluh
# ======================================================
@auth_bp.route("/register/penyuluh", methods=["GET", "POST"])
def register_penyuluh():

    if request.method == "POST":
        nama_lengkap = request.form.get("nama_lengkap", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        kecamatan = request.form.get("kecamatan", "").strip()
        nip_penyuluh = request.form.get("nip_penyuluh", "").strip()

        cur = mysql.connection.cursor(DictCursor)

        # Cek username sudah dipakai
        cur.execute(
            "SELECT id_user FROM users WHERE username = %s",
            (username,)
        )
        existing = cur.fetchone()

        if existing:
            cur.close()
            return render_template(
                "penyuluh/register.html",
                error="Username sudah digunakan"
            )

        try:
            # Insert ke tabel penyuluh (profil)
            cur.execute("""
                INSERT INTO penyuluh (nama_lengkap, nip_penyuluh, username, password, kecamatan)
                VALUES (%s, %s, %s, %s, %s)
            """, (nama_lengkap, nip_penyuluh, username, password, kecamatan))

            id_penyuluh_baru = cur.lastrowid

            # Insert ke tabel users (autentikasi)
            cur.execute("""
                INSERT INTO users (nama, username, password, role, nip, id_penyuluh, wilayah_binaan)
                VALUES (%s, %s, %s, 'penyuluh', %s, %s, %s)
            """, (nama_lengkap, username, password, nip_penyuluh, id_penyuluh_baru, kecamatan))

            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            return render_template(
                "penyuluh/register.html",
                error=f"Gagal mendaftar: {str(e)}"
            )

        cur.close()
        return redirect("/login/penyuluh")

    return render_template("penyuluh/register.html")


# ======================================================
# LUPA PASSWORD (UNTUK SEMUA ROLE)
# Update password di tabel users
# ======================================================
@auth_bp.route("/lupa-password/<role>", methods=["GET", "POST"])
def lupa_password(role):

    if role == "penyuluh":
        template = "penyuluh/lupa_password.html"
    elif role == "admin":
        template = "admin/lupa_password.html"
    else:
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password_baru = request.form.get("password", "").strip()

        if not username or not password_baru:
            return render_template(template, error="Username dan Password baru wajib diisi")

        cur = mysql.connection.cursor(DictCursor)

        # Cek user ada
        cur.execute(
            "SELECT id_user FROM users WHERE username = %s AND role = %s",
            (username, role)
        )
        user = cur.fetchone()

        if not user:
            cur.close()
            return render_template(template, error="Username tidak ditemukan")

        # Update password di tabel users
        cur.execute("""
            UPDATE users
            SET password = %s
            WHERE username = %s AND role = %s
        """, (password_baru, username, role))

        # Juga update di tabel penyuluh (supaya tetap sinkron)
        if role == "penyuluh":
            cur.execute("""
                UPDATE penyuluh
                SET password = %s
                WHERE username = %s
            """, (password_baru, username))

        mysql.connection.commit()
        cur.close()

        return render_template(template, sukses="Password berhasil diperbarui. Silakan login.")

    return render_template(template)