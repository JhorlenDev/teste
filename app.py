from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "catalog.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fametro-secret-key")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "fametro123")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            modality TEXT NOT NULL,
            description TEXT NOT NULL,
            image_path TEXT,
            contact_label TEXT,
            contact_url TEXT,
            secondary_label TEXT,
            secondary_url TEXT,
            featured INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    course_count = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if course_count == 0:
        db.executemany(
            """
            INSERT INTO courses (
                title, category, modality, description, image_path,
                contact_label, contact_url, secondary_label, secondary_url, featured
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Tecnico em Administracao",
                    "Tecnico",
                    "Presencial",
                    "Formacao voltada para rotinas administrativas, organizacao empresarial e suporte a processos de gestao.",
                    "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80",
                    "Falar com a Fametro",
                    "https://wa.me/5592999999999",
                    "Solicitar informações",
                    "mailto:atendimento@fametro.edu.br",
                    1,
                ),
                (
                    "Tecnico em Enfermagem",
                    "Tecnico",
                    "Presencial",
                    "Curso com base pratica, laboratorios e preparacao para atuacao responsavel na area da saude.",
                    "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=900&q=80",
                    "Agendar atendimento",
                    "https://wa.me/5592999999999",
                    "Ver detalhes",
                    "mailto:atendimento@fametro.edu.br",
                    0,
                ),
                (
                    "Tecnico em Informatica",
                    "Tecnico",
                    "Semipresencial",
                    "Formacao para quem deseja atuar com suporte, desenvolvimento, redes e recursos digitais no mercado.",
                    "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80",
                    "Quero me inscrever",
                    "https://wa.me/5592999999999",
                    "Falar com consultor",
                    "mailto:atendimento@fametro.edu.br",
                    1,
                ),
            ],
        )
    else:
        db.execute(
            """
            UPDATE courses
            SET category = 'Tecnico',
                secondary_label = '',
                secondary_url = '',
                contact_label = CASE
                    WHEN contact_label IS NULL OR TRIM(contact_label) = '' THEN 'Entrar em contato'
                    ELSE 'Entrar em contato'
                END
            """
        )
    db.commit()
    db.close()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image() -> str | None:
    file = request.files.get("image")
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        raise ValueError("Envie uma imagem JPG, PNG ou WEBP.")

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    destination = UPLOAD_FOLDER / unique_name
    file.save(destination)
    return f"uploads/{unique_name}"


def is_admin() -> bool:
    return bool(session.get("is_admin"))


def remove_uploaded_image(image_path: str | None) -> None:
    if not image_path or image_path.startswith("http"):
        return

    file_path = BASE_DIR / "static" / image_path
    if file_path.exists():
        file_path.unlink()


def fetch_courses() -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        "SELECT * FROM courses ORDER BY featured DESC, created_at DESC, id DESC"
    ).fetchall()


def validate_course_form(form: Any) -> str | None:
    required_fields = {
        "title": "Informe o titulo do curso.",
        "modality": "Selecione a modalidade do curso.",
        "description": "Informe uma descricao para o curso.",
        "contact_url": "Informe o link de contato do curso.",
    }
    for field_name, message in required_fields.items():
        if not form.get(field_name, "").strip():
            return message
    return None


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {"is_admin": is_admin()}


@app.route("/")
def home() -> str:
    courses = fetch_courses()
    return render_template("index.html", courses=courses)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login() -> str:
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Senha incorreta.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout() -> str:
    session.clear()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("home"))


@app.route("/admin")
def admin_dashboard() -> str:
    if not is_admin():
        return redirect(url_for("admin_login"))

    courses = fetch_courses()
    return render_template("admin_dashboard.html", courses=courses, editing_course=None)


@app.route("/admin/courses", methods=["POST"])
def create_course() -> str:
    if not is_admin():
        return redirect(url_for("admin_login"))

    form = request.form
    validation_error = validate_course_form(form)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("admin_dashboard"))

    try:
        image_path = save_image() or form.get("image_url", "").strip() or None
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute(
        """
        INSERT INTO courses (
            title, category, modality, description, image_path,
            contact_label, contact_url, secondary_label, secondary_url, featured
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            form.get("title", "").strip(),
            "Tecnico",
            form.get("modality", "").strip(),
            form.get("description", "").strip(),
            image_path,
            "Entrar em contato",
            form.get("contact_url", "").strip(),
            "",
            "",
            1 if form.get("featured") == "on" else 0,
        ),
    )
    db.commit()
    flash("Curso cadastrado com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/courses/<int:course_id>/edit")
def edit_course(course_id: int) -> str:
    if not is_admin():
        return redirect(url_for("admin_login"))

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    courses = fetch_courses()
    if course is None:
        flash("Curso não encontrado.", "error")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_dashboard.html", courses=courses, editing_course=course)


@app.route("/admin/courses/<int:course_id>", methods=["POST"])
def update_course(course_id: int) -> str:
    if not is_admin():
        return redirect(url_for("admin_login"))

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if course is None:
        flash("Curso não encontrado.", "error")
        return redirect(url_for("admin_dashboard"))

    form = request.form
    validation_error = validate_course_form(form)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("edit_course", course_id=course_id))

    image_path = course["image_path"]
    try:
        uploaded_image = save_image()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("edit_course", course_id=course_id))

    if uploaded_image:
        remove_uploaded_image(course["image_path"])
        image_path = uploaded_image
    elif form.get("image_url", "").strip():
        remove_uploaded_image(course["image_path"])
        image_path = form.get("image_url", "").strip()

    db.execute(
        """
        UPDATE courses
        SET title = ?, category = ?, modality = ?, description = ?, image_path = ?,
            contact_label = ?, contact_url = ?, secondary_label = ?, secondary_url = ?,
            featured = ?
        WHERE id = ?
        """,
        (
            form.get("title", "").strip(),
            "Tecnico",
            form.get("modality", "").strip(),
            form.get("description", "").strip(),
            image_path,
            "Entrar em contato",
            form.get("contact_url", "").strip(),
            "",
            "",
            1 if form.get("featured") == "on" else 0,
            course_id,
        ),
    )
    db.commit()
    flash("Curso atualizado com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/courses/<int:course_id>/delete", methods=["POST"])
def delete_course(course_id: int) -> str:
    if not is_admin():
        return redirect(url_for("admin_login"))

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if course is None:
        flash("Curso não encontrado.", "error")
        return redirect(url_for("admin_dashboard"))

    remove_uploaded_image(course["image_path"])
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    flash("Curso removido com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
