"""Administrator-only pages. Every route uses @admin_required (server-side)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from auth_utils import admin_required, audit, current_user
from database.db import get_db
from routes.patients import escape_like, list_patients
from services import patient_service

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_charts(db):
    charts = patient_service.chart_data(db, None)
    owners = db.execute(
        "SELECT u.full_name, COUNT(p.id) n FROM users u JOIN patients p ON p.owner_id=u.id "
        "GROUP BY u.id ORDER BY n DESC LIMIT 10").fetchall()
    signups = db.execute(
        "SELECT substr(created_at,1,10) d, COUNT(*) n FROM users GROUP BY d ORDER BY d DESC LIMIT 14").fetchall()[::-1]
    return {
        "status": charts["status"],
        "owners": {"type": "bar", "labels": [o["full_name"] for o in owners], "label": "Patients per user",
                   "data": [o["n"] for o in owners]},
        "signups": {"type": "bar", "labels": [s["d"] for s in signups], "label": "New accounts",
                    "data": [s["n"] for s in signups]},
    }


@bp.route("")
@admin_required
def dashboard():
    db = get_db()
    one = lambda sql: db.execute(sql).fetchone()[0]  # noqa: E731
    stats = {
        "users": one("SELECT COUNT(*) FROM users WHERE role='user'"),
        "patients": one("SELECT COUNT(*) FROM patients"),
        "completed": one("SELECT COUNT(*) FROM patients WHERE ai_status='completed'"),
        "pending_failed": one("SELECT COUNT(*) FROM patients WHERE ai_status!='completed'"),
    }
    activity = db.execute(
        "SELECT a.*, u.full_name FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
        "ORDER BY a.id DESC LIMIT 8").fetchall()
    return render_template("admin_dashboard.html", stats=stats, charts=admin_charts(db), activity=activity)


@bp.route("/analytics")
@admin_required
def analytics():
    db = get_db()
    return render_template("admin_analytics.html", charts=admin_charts(db), avg=patient_service.averages(db, None))


@bp.route("/patients")
@admin_required
def patients():
    q = request.args.get("q", "").strip()[:100]
    rows, total, page, pages = list_patients(None, q, request.args.get("page", 1, type=int), include_owner_search=True)
    return render_template("patients.html", patients=rows, q=q, total=total, page=page, pages=pages, admin_mode=True)


@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()[:100]
    like = f"%{escape_like(q.lower())}%"
    rows = get_db().execute(
        "SELECT u.*, (SELECT COUNT(*) FROM patients p WHERE p.owner_id=u.id) AS patient_count, "
        "(SELECT MAX(created_at) FROM audit_log a WHERE a.user_id=u.id AND a.success=1 "
        " AND a.event_type IN ('login_success','admin_login_success')) AS last_login "
        "FROM users u WHERE lower(u.full_name) LIKE ? ESCAPE '\\' OR lower(u.email) LIKE ? ESCAPE '\\' "
        "ORDER BY u.id", (like, like)).fetchall()
    return render_template("user_management.html", users=rows, q=q)


@bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    db = get_db()
    row = db.execute("SELECT id, full_name, email, role, is_active, created_at, updated_at FROM users WHERE id=?",
                     (user_id,)).fetchone()
    if row is None:
        abort(404)
    logins = db.execute("SELECT * FROM audit_log WHERE user_id=? ORDER BY id DESC LIMIT 15", (user_id,)).fetchall()
    count = db.execute("SELECT COUNT(*) FROM patients WHERE owner_id=?", (user_id,)).fetchone()[0]
    return render_template("user_detail.html", u=row, logins=logins, patient_count=count)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    admin = current_user()
    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if target is None:
        abort(404)
    if target["is_active"]:
        if target["id"] == admin["id"]:
            flash("You cannot deactivate your own account.", "danger")
            return redirect(url_for("admin.users"))
        if target["role"] == "admin":
            active_admins = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1").fetchone()[0]
            if active_admins <= 1:
                flash("The only active administrator cannot be deactivated.", "danger")
                return redirect(url_for("admin.users"))
    new_state = 0 if target["is_active"] else 1
    from utils import now_str
    db.execute("UPDATE users SET is_active=?, updated_at=? WHERE id=?", (new_state, now_str(), user_id))
    db.commit()
    audit("account_activated" if new_state else "account_deactivated", user_id=admin["id"],
          details=f"target user {user_id}")
    flash(f"Account {'activated' if new_state else 'deactivated'}.", "success")
    return redirect(request.form.get("back") if request.form.get("back", "").startswith("/admin/") else url_for("admin.users"))


@bp.route("/audit")
@admin_required
def audit_history():
    q = request.args.get("event", "").strip()
    db = get_db()
    sql = ("SELECT a.*, u.full_name FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
           "{} ORDER BY a.id DESC LIMIT 200")
    rows = (db.execute(sql.format("WHERE a.event_type = ?"), (q,)) if q else db.execute(sql.format(""))).fetchall()
    types = [r[0] for r in db.execute("SELECT DISTINCT event_type FROM audit_log ORDER BY 1")]
    return render_template("audit_history.html", rows=rows, event=q, types=types)
