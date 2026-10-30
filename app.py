"""Health Prediction & Patient Management System - application entry point."""
import os
import re
import sqlite3

import click
from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import default_config, load_or_create_secret_key
from database import db as dbm
from utils import fmt_number, iso_to_display, timestamp_to_display

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(default_config())
    app.config["DATABASE"] = os.path.join(app.instance_path, "health_app.db")
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = load_or_create_secret_key(app.instance_path)
    os.makedirs(app.instance_path, exist_ok=True)

    csrf.init_app(app)
    app.teardown_appcontext(dbm.close_db)
    with app.app_context():
        dbm.init_db()   # CREATE TABLE IF NOT EXISTS only: existing data is never touched

    from routes import admin, auth, patients
    app.register_blueprint(auth.bp)
    app.register_blueprint(patients.bp)
    app.register_blueprint(admin.bp)

    register_template_helpers(app)
    register_error_handlers(app)
    register_cli(app)

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'")
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"   # no cached pages after logout
        return response

    return app


def register_template_helpers(app):
    from auth_utils import current_user
    from services import ai_service
    from services.patient_service import STATUS_LABELS

    app.jinja_env.filters["dmy"] = iso_to_display
    app.jinja_env.filters["timestamp"] = timestamp_to_display
    app.jinja_env.filters["num"] = fmt_number
    app.jinja_env.globals["status_labels"] = STATUS_LABELS   # macros cannot see context vars

    @app.context_processor
    def inject():
        return {
            "current_user": current_user(),
            "ai_configured": bool(app.config.get("GEMINI_API_KEY")),
            "disclaimer": ai_service.DISCLAIMER,
        }


def register_error_handlers(app):
    def show(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(_e):
        return show(400, "Bad request", "The request could not be processed.")

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return show(400, "Security check failed", "Your form expired or was invalid. Go back, reload the page and try again.")

    @app.errorhandler(403)
    def forbidden(_e):
        return show(403, "Access denied", "You do not have permission to view this page.")

    @app.errorhandler(404)
    def not_found(_e):
        return show(404, "Page not found", "We could not find what you were looking for.")

    @app.errorhandler(sqlite3.Error)
    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Server error")   # details go to the server log only
        return show(500, "Something went wrong", "An unexpected error occurred. Your data was not exposed. Please try again.")


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables if they do not exist (safe to repeat)."""
        dbm.init_db()
        click.echo(f"Database ready: {app.config['DATABASE']}")

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Administrator full name")
    @click.option("--email", prompt="Administrator email")
    @click.option("--password", prompt="Password", hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create an administrator account (password is typed hidden, never stored in code)."""
        from auth_utils import audit, hash_password
        from utils import now_str
        from validation import validate_email, validate_full_name, validate_password

        name, err1 = validate_full_name(name)
        email, err2 = validate_email(email)
        err3 = validate_password(password)
        for err in (err1, err2, err3):
            if err:
                raise click.ClickException(err)
        db = dbm.get_db()
        if db.execute("SELECT 1 FROM users WHERE email=?", (email.lower(),)).fetchone():
            raise click.ClickException("An account with this email already exists. Nothing was changed.")
        now = now_str()
        cur = db.execute(
            "INSERT INTO users (full_name,email,password_hash,role,is_active,created_at,updated_at) "
            "VALUES (?,?,?,'admin',1,?,?)", (name, email.lower(), hash_password(password), now, now))
        db.commit()
        with app.test_request_context():
            audit("admin_created_cli", user_id=cur.lastrowid, email=email.lower(), details="created via CLI")
        click.echo(f"Administrator created: {email.lower()}")


app = create_app() if os.environ.get("FLASK_RUN_FROM_CLI") or __name__ == "__main__" else None

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
