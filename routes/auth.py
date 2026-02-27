from flask import Blueprint, render_template, request, redirect, session
from extensions import mysql
from MySQLdb.cursors import DictCursor

auth_bp = Blueprint("auth", __name__)


# ======================================================
# LOGIN (ADMIN ONLY — via tabel users)
# Penyuluh punya route sendiri di /penyuluh/login
# ======================================================
@auth_bp.route("/login/<role>", methods=["GET", "POST"])
def login(role):

    # Penyuluh punya login sendiri, redirect ke route yang benar
    if role == "penyuluh":
        return redirect("/penyuluh/login")

    if role != "admin":
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        cur = mysql.connection.cursor(DictCursor)
        cur.execute("""
            SELECT id_user, username, password, role
            FROM users
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()
        cur.close()

        if user and user["role"] == "admin" and user["password"] == password:
            session.clear()
            session["user_id"] = user["id_user"]
            session["role"] = user["role"]
            return redirect("/admin/proposal")

        return render_template("admin/login.html", error="Username atau password salah")

    return render_template("admin/login.html")


# ======================================================
# LUPA PASSWORD (STABIL & TIDAK MERUSAK LOGIN)
# ======================================================
@auth_bp.route("/lupa-password/<role>", methods=["GET"])
def lupa_password(role):

    if role == "penyuluh":
        return render_template("penyuluh/lupa_password.html")

    if role == "admin":
        return render_template("admin/lupa_password.html")

    return redirect("/")