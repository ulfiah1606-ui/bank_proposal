from flask import Flask, render_template
from config import Config
from extensions import mysql

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = "bank_proposal_gowa_2026"

    mysql.init_app(app)

    # REGISTER BLUEPRINT
    from routes.auth import auth_bp
    from routes.kelompok_tani import tani_bp
    from routes.admin import admin_bp
    from routes.penyuluh import penyuluh_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tani_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(penyuluh_bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)