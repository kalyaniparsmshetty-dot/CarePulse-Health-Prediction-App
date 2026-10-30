"""Session helpers, role decorators, password hashing and audit logging."""
import json
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db
from utils import now_str

# Used so that a login for an unknown email takes about as long as a real one.
_DUMMY_HASH = generate_password_hash("not-a-real-password", method="pbkdf2:sha256:1000")


def hash_password(password):
    iterations = current_app.config["PBKDF2_ITERATIONS"]
    return generate_password_hash(password, method=f"pbkdf2:sha256:{iterations}")


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash or _DUMMY_HASH, password)


def audit(event_type, user_id=None, email=None, success=True, details=None):
    """Write an audit row. Never pass passwords, hashes, cookies or tokens here."""
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (event_type, user_id, email_attempted, success, ip_address, details, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (event_type, user_id, email, 1 if success else 0, request.remote_addr,
         json.dumps(details) if isinstance(details, dict) else details, now_str()),
    )
    db.commit()


def current_user():
    """The logged-in user row (re-read from the DB on each request), or None."""
    if "user" in g:
        return g.user
    user = None
    uid = session.get("user_id")
    if uid is not None:
        user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if user is None or not user["is_active"]:
            session.clear()   # deleted or deactivated accounts lose access immediately
            user = None
    g.user = user
    return user


def start_session(user):
    session.clear()           # prevents session fixation
    session["user_id"] = user["id"]
    session.permanent = True


def safe_next_url(target):
    """Allow only relative in-site redirects."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please sign in as an administrator.", "warning")
            return redirect(url_for("auth.admin_login"))
        if user["role"] != "admin":
            audit("admin_access_denied", user_id=user["id"], success=False, details=request.path)
            abort(403)
        return view(*args, **kwargs)
    return wrapped
