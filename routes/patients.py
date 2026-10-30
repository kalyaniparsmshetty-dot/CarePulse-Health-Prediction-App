
"""User dashboard, analytics and patient CRUD (owner-scoped; admins may also manage)."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from auth_utils import audit, current_user, login_required
from database.db import get_db
from services import ai_service, patient_service
from utils import now_str, today
from validation import validate_patient

bp = Blueprint("patients", __name__)
PER_PAGE = 10

FORM_FIELDS = (
    "full_name",
    "dob",
    "email",
    "glucose",
    "haemoglobin",
    "cholesterol",
    "remarks",
)


def escape_like(text):
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def load_patient(patient_id):
    """Return a patient the current user may access, else 404."""
    user = current_user()

    row = get_db().execute(
        "SELECT p.*, u.full_name AS owner_name, u.email AS owner_email "
        "FROM patients p JOIN users u ON u.id = p.owner_id WHERE p.id = ?",
        (patient_id,),
    ).fetchone()

    if row is None or (
        user["role"] != "admin" and row["owner_id"] != user["id"]
    ):
        abort(404)

    return row


def list_patients(owner_id, q, page, include_owner_search=False):
    db = get_db()
    clauses, params = [], []

    if owner_id is not None:
        clauses.append("p.owner_id = ?")
        params.append(owner_id)

    if q:
        like = f"%{escape_like(q.lower())}%"
        fields = ["lower(p.full_name)", "lower(p.email)"]

        if include_owner_search:
            fields += ["lower(u.full_name)", "lower(u.email)"]

        clauses.append(
            "(" + " OR ".join(
                f"{field} LIKE ? ESCAPE '\\'" for field in fields
            ) + ")"
        )
        params += [like] * len(fields)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    base = f"FROM patients p JOIN users u ON u.id = p.owner_id {where}"

    total = db.execute(
        f"SELECT COUNT(*) {base}", params
    ).fetchone()[0]

    pages = max(1, -(-total // PER_PAGE))
    page = min(max(page, 1), pages)

    rows = db.execute(
        f"SELECT p.*, u.full_name AS owner_name, u.email AS owner_email {base} "
        "ORDER BY p.id DESC LIMIT ? OFFSET ?",
        params + [PER_PAGE, (page - 1) * PER_PAGE],
    ).fetchall()

    return rows, total, page, pages


@bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    db = get_db()

    recent = db.execute(
        "SELECT * FROM patients WHERE owner_id=? ORDER BY id DESC LIMIT 5",
        (user["id"],),
    ).fetchall()

    return render_template(
        "dashboard.html",
        stats=patient_service.build_stats(db, user["id"]),
        charts=patient_service.chart_data(db, user["id"]),
        recent=recent,
    )


@bp.route("/analytics")
@login_required
def analytics():
    user = current_user()
    db = get_db()

    return render_template(
        "analytics.html",
        stats=patient_service.build_stats(db, user["id"]),
        charts=patient_service.chart_data(db, user["id"]),
        avg=patient_service.averages(db, user["id"]),
    )


@bp.route("/patients")
@login_required
def list_view():
    user = current_user()
    q = request.args.get("q", "").strip()[:100]
    page = request.args.get("page", 1, type=int)

    rows, total, page, pages = list_patients(
        user["id"], q, page
    )

    return render_template(
        "patients.html",
        patients=rows,
        q=q,
        total=total,
        page=page,
        pages=pages,
        admin_mode=False,
    )


def _form_values(source):
    return {field: source.get(field, "") for field in FORM_FIELDS}


@bp.route("/patients/new", methods=["GET", "POST"])
@login_required
def create():
    user = current_user()
    values, errors = _form_values({}), {}

    if request.method == "POST":
        values = _form_values(request.form)
        cleaned, errors = validate_patient(values, today(), "/")

        if not errors:
            db = get_db()

            # Check whether this user already has the exact same patient record.
            duplicate = db.execute(
                """
                SELECT id
                FROM patients
                WHERE owner_id = ?
                  AND lower(trim(full_name)) = lower(trim(?))
                  AND dob = ?
                  AND lower(trim(email)) = lower(trim(?))
                  AND glucose = ?
                  AND haemoglobin = ?
                  AND cholesterol = ?
                LIMIT 1
                """,
                (
                    user["id"],
                    cleaned["full_name"],
                    cleaned["dob"],
                    cleaned["email"],
                    cleaned["glucose"],
                    cleaned["haemoglobin"],
                    cleaned["cholesterol"],
                ),
            ).fetchone()

            if duplicate:
                errors["_form"] = (
                    "This exact patient record already exists."
                )
                flash(
                    "Duplicate record! This patient has already been added.",
                    "danger",
                )
            else:
                now = now_str()

                cur = db.execute(
                    "INSERT INTO patients "
                    "(owner_id,full_name,dob,email,glucose,haemoglobin,"
                    "cholesterol,user_remarks,ai_status,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?, 'pending', ?, ?)",
                    (
                        user["id"],
                        cleaned["full_name"],
                        cleaned["dob"],
                        cleaned["email"],
                        cleaned["glucose"],
                        cleaned["haemoglobin"],
                        cleaned["cholesterol"],
                        cleaned["remarks"],
                        now,
                        now,
                    ),
                )

                db.commit()

                patient = db.execute(
                    "SELECT * FROM patients WHERE id=?",
                    (cur.lastrowid,),
                ).fetchone()

                from flask import current_app

                result = patient_service.run_assessment(
                    db, patient, current_app.config
                )

                if result.ok:
                    flash(
                        "Patient saved and AI assessment completed.",
                        "success",
                    )
                else:
                    flash(
                        f"Patient saved. {result.message}",
                        "warning",
                    )

                return redirect(
                    url_for(
                        "patients.detail",
                        patient_id=cur.lastrowid,
                    )
                )

        else:
            flash(
                "Please fix the highlighted fields.",
                "danger",
            )

    return render_template(
        "patient_form.html",
        mode="create",
        values=values,
        errors=errors,
        patient=None,
    )


@bp.route("/patients/<int:patient_id>")
@login_required
def detail(patient_id):
    return render_template(
        "patient_detail.html",
        p=load_patient(patient_id),
        disclaimer=ai_service.DISCLAIMER,
    )


def _iso_to_dmy(iso):
    from utils import iso_to_display

    return iso_to_display(iso)


@bp.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit(patient_id):
    user = current_user()
    patient = load_patient(patient_id)
    errors = {}

    values = {
        "full_name": patient["full_name"],
        "dob": _iso_to_dmy(patient["dob"]),
        "email": patient["email"],
        "glucose": f"{patient['glucose']:g}",
        "haemoglobin": f"{patient['haemoglobin']:g}",
        "cholesterol": f"{patient['cholesterol']:g}",
        "remarks": patient["user_remarks"] or "",
    }

    if request.method == "POST":
        values = _form_values(request.form)
        cleaned, errors = validate_patient(values, today(), "/")

        if not errors:
            db = get_db()
            status = patient_service.new_status_after_edit(
                patient, cleaned
            )

            db.execute(
                "UPDATE patients SET full_name=?, dob=?, email=?, "
                "glucose=?, haemoglobin=?, cholesterol=?, user_remarks=?, "
                "ai_status=?, updated_at=? WHERE id=?",
                (
                    cleaned["full_name"],
                    cleaned["dob"],
                    cleaned["email"],
                    cleaned["glucose"],
                    cleaned["haemoglobin"],
                    cleaned["cholesterol"],
                    cleaned["remarks"],
                    status,
                    now_str(),
                    patient_id,
                ),
            )

            db.commit()

            if patient["owner_id"] != user["id"]:
                audit(
                    "patient_admin_edit",
                    user_id=user["id"],
                    details=f"patient {patient_id}",
                )

            msg = "Patient updated."

            if status == "outdated":
                msg += (
                    " The previous AI assessment is now outdated; "
                    "request a new one."
                )

            flash(msg, "success")

            return redirect(
                url_for(
                    "patients.detail",
                    patient_id=patient_id,
                )
            )

        flash(
            "Please fix the highlighted fields.",
            "danger",
        )

    return render_template(
        "patient_form.html",
        mode="edit",
        values=values,
        errors=errors,
        patient=patient,
    )


@bp.route("/patients/<int:patient_id>/delete", methods=["POST"])
@login_required
def delete(patient_id):
    user = current_user()
    patient = load_patient(patient_id)
    db = get_db()

    db.execute(
        "DELETE FROM patients WHERE id=?",
        (patient_id,),
    )
    db.commit()

    if patient["owner_id"] != user["id"]:
        audit(
            "patient_admin_delete",
            user_id=user["id"],
            details=f"patient {patient_id}, owner {patient['owner_id']}",
        )

    flash("Patient deleted.", "success")

    return redirect(
        url_for(
            "admin.patients"
            if user["role"] == "admin"
            else "patients.list_view"
        )
    )


@bp.route("/patients/<int:patient_id>/assess", methods=["POST"])
@login_required
def assess(patient_id):
    from flask import current_app

    patient = load_patient(patient_id)

    result = patient_service.run_assessment(
        get_db(), patient, current_app.config
    )

    flash(
        "AI assessment completed." if result.ok else result.message,
        "success" if result.ok else "warning",
    )

    return redirect(
        url_for(
            "patients.detail",
            patient_id=patient_id,
        )
    )

