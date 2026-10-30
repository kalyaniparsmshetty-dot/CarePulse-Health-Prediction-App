"""Registration, user login, admin login, logout and profile."""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from auth_utils import (audit, current_user, hash_password, login_required, safe_next_url,
                        start_session, verify_password)
from database.db import get_db
from utils import now_str
from validation import validate_email, validate_full_name, validate_password

bp = Blueprint("auth", __name__)
GENERIC_LOGIN_ERROR = "Invalid email or password."


@bp.route("/")
def index():
    user = current_user()
    if user is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("admin.dashboard" if user["role"] == "admin" else "patients.dashboard"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    user = current_user()
    if user:
        return redirect(url_for("auth.index"))
    errors, values = {}, {}
    if request.method == "POST":
        # NOTE: any "role" field in the request is ignored on purpose.
        values = {"full_name": request.form.get("full_name", ""), "email": request.form.get("email", "")}
        name, err = validate_full_name(values["full_name"])
        if err:
            errors["full_name"] = err
        email, err = validate_email(values["email"])
        if err:
            errors["email"] = err
        password = request.form.get("password", "")
        err = validate_password(password, request.form.get("confirm_password", ""))
        if err:
            errors["password"] = err
        if not errors:
            db = get_db()
            try:
                now = now_str()
                cur = db.execute(
                    "INSERT INTO users (full_name,email,password_hash,role,is_active,created_at,updated_at) "
                    "VALUES (?,?,?,'user',1,?,?)", (name, email.lower(), hash_password(password), now, now))
                db.commit()
            except sqlite3.IntegrityError:
                errors["email"] = "An account with this email already exists."
            else:
                audit("register", user_id=cur.lastrowid, email=email.lower())
                flash("Account created. You can sign in now.", "success")
                return redirect(url_for("auth.login"))
    return render_template("register.html", errors=errors, values=values)


def _authenticate(email, password):
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    ok = verify_password(row["password_hash"] if row else None, password)
    return row if (row and ok) else None


@bp.route("/login", methods=["GET", "POST"])
def login():
    user = current_user()
    if user:
        return redirect(url_for("auth.index"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        row = _authenticate(email, request.form.get("password", ""))
        if row is None or not row["is_active"]:
            reason = "inactive" if (row and not row["is_active"]) else "bad credentials"
            audit("login_failed", user_id=row["id"] if row else None, email=email.lower()[:254],
                  success=False, details=reason)
            flash(GENERIC_LOGIN_ERROR, "danger")
        elif row["role"] == "admin":
            audit("login_failed", user_id=row["id"], email=email.lower(), success=False,
                  details="admin must use admin login")
            flash(GENERIC_LOGIN_ERROR + " Administrators sign in on the Admin Login page.", "danger")
        else:
            start_session(row)
            audit("login_success", user_id=row["id"], email=row["email"])
            return redirect(safe_next_url(request.args.get("next")) or url_for("patients.dashboard"))
    return render_template("login.html", email=email)


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    user = current_user()
    if user and user["role"] == "admin":
        return redirect(url_for("admin.dashboard"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        row = _authenticate(email, request.form.get("password", ""))
        if row is None or not row["is_active"]:
            audit("admin_login_failed", user_id=row["id"] if row else None, email=email.lower()[:254],
                  success=False, details="bad credentials")
            flash(GENERIC_LOGIN_ERROR, "danger")
        elif row["role"] != "admin":
            # Valid user credentials never grant admin access.
            audit("admin_login_denied", user_id=row["id"], email=row["email"], success=False,
                  details="not an administrator")
            flash(GENERIC_LOGIN_ERROR, "danger")
        else:
            start_session(row)
            audit("admin_login_success", user_id=row["id"], email=row["email"])
            return redirect(url_for("admin.dashboard"))
    return render_template("admin_login.html", email=email)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user = current_user()
    was_admin = user["role"] == "admin"
    audit("logout", user_id=user["id"], email=user["email"])
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.admin_login" if was_admin else "auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    errors = {}
    if request.method == "POST":
        # Only the name (and optionally the password) can change. Role is never read from the form.
        name, err = validate_full_name(request.form.get("full_name"))
        if err:
            errors["full_name"] = err
        new_pw = request.form.get("new_password", "")
        if new_pw:
            if not verify_password(user["password_hash"], request.form.get("current_password", "")):
                errors["current_password"] = "Current password is incorrect."
            else:
                err = validate_password(new_pw, request.form.get("confirm_password", ""))
                if err:
                    errors["new_password"] = err
        if not errors:
            db = get_db()
            if new_pw:
                db.execute("UPDATE users SET full_name=?, password_hash=?, updated_at=? WHERE id=?",
                           (name, hash_password(new_pw), now_str(), user["id"]))
            else:
                db.execute("UPDATE users SET full_name=?, updated_at=? WHERE id=?", (name, now_str(), user["id"]))
            db.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("profile.html", errors=errors)
