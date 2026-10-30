
"""Patient-related business logic: AI assessment orchestration and statistics."""

from datetime import timedelta

from services import ai_service
from utils import age_in_years, now_str, today

COMPLETED = "completed"
NOT_COMPLETED = ("pending", "failed", "unavailable", "outdated")

STATUS_LABELS = {
    "completed": "Remarks Ready",
    "pending": "Remarks Pending",
    "failed": "Remarks Generation Failed",
    "unavailable": "AI Not Configured",
    "outdated": "Remarks Outdated",
}


def run_assessment(db, patient, config):
    """Request or retry AI remarks without deleting the patient record."""
    requested = now_str()
    age = age_in_years(patient["dob"], today())

    result = ai_service.generate_assessment(
        age,
        patient["glucose"],
        patient["haemoglobin"],
        patient["cholesterol"],
        config.get("GEMINI_API_KEY"),
        config.get("GEMINI_MODEL"),
        config.get("AI_TIMEOUT_SECONDS", 20),
    )

    now = now_str()

    if result.ok:
        db.execute(
            "UPDATE patients SET ai_remarks=?, ai_status='completed', "
            "ai_assessed_at=?, updated_at=? WHERE id=?",
            (result.text, now, now, patient["id"]),
        )

        db.execute(
            "INSERT INTO assessments "
            "(patient_id, requested_at, completed_at, status, ai_remarks) "
            "VALUES (?,?,?,?,?)",
            (patient["id"], requested, now, "completed", result.text),
        )

    else:
        status = (
            "unavailable"
            if result.error_category == "not_configured"
            else "failed"
        )

        # Clear old AI remarks when a new generation attempt fails.
        db.execute(
            "UPDATE patients SET ai_remarks=NULL, ai_status=?, "
            "updated_at=? WHERE id=?",
            (status, now, patient["id"]),
        )

        db.execute(
            "INSERT INTO assessments "
            "(patient_id, requested_at, completed_at, status, error_category) "
            "VALUES (?,?,?,?,?)",
            (
                patient["id"],
                requested,
                now,
                status,
                result.error_category,
            ),
        )

    db.commit()
    return result


def new_status_after_edit(old, cleaned):
    """Mark completed remarks outdated when relevant patient data changes."""
    changed = any(
        old[key] != cleaned[key]
        for key in ("glucose", "haemoglobin", "cholesterol", "dob")
    )

    if changed and old["ai_status"] == "completed":
        return "outdated"

    return old["ai_status"]


def _status_counts(db, where, params):
    completed = db.execute(
        f"SELECT COUNT(*) FROM patients {where}"
        f"{' AND' if where else 'WHERE'} ai_status='completed'",
        params,
    ).fetchone()[0]

    return completed


def build_stats(db, owner_id=None):
    """Calculate patient statistics for a user or administrator."""
    where, params = (
        ("WHERE owner_id = ?", (owner_id,))
        if owner_id is not None
        else ("", ())
    )

    total = db.execute(
        f"SELECT COUNT(*) FROM patients {where}", params
    ).fetchone()[0]

    completed = _status_counts(db, where, params)
    cutoff = (today() - timedelta(days=7)).isoformat()

    recent = db.execute(
        f"SELECT COUNT(*) FROM patients {where}"
        f"{' AND' if where else 'WHERE'} substr(created_at,1,10) >= ?",
        params + (cutoff,),
    ).fetchone()[0]

    return {
        "total": total,
        "recent": recent,
        "completed": completed,
        "pending_failed": total - completed,
    }


def chart_data(db, owner_id=None):
    """Prepare chart data for measurements and AI remarks status."""
    where, params = (
        ("WHERE owner_id = ?", (owner_id,))
        if owner_id is not None
        else ("", ())
    )

    rows = db.execute(
        f"SELECT id, full_name, glucose, haemoglobin, cholesterol "
        f"FROM patients {where} ORDER BY id DESC LIMIT 12",
        params,
    ).fetchall()[::-1]

    labels = [row["full_name"] for row in rows]

    status_rows = db.execute(
        f"SELECT ai_status, COUNT(*) AS n FROM patients "
        f"{where} GROUP BY ai_status",
        params,
    ).fetchall()

    return {
        "glucose": {
            "type": "bar",
            "labels": labels,
            "label": "Glucose (mg/dL)",
            "data": [row["glucose"] for row in rows],
        },
        "haemoglobin": {
            "type": "bar",
            "labels": labels,
            "label": "Haemoglobin (g/dL)",
            "data": [row["haemoglobin"] for row in rows],
        },
        "cholesterol": {
            "type": "bar",
            "labels": labels,
            "label": "Cholesterol (mg/dL)",
            "data": [row["cholesterol"] for row in rows],
        },
        "status": {
            "type": "doughnut",
            "labels": [
                STATUS_LABELS.get(row["ai_status"], row["ai_status"])
                for row in status_rows
            ],
            "label": "Patients",
            "data": [row["n"] for row in status_rows],
        },
    }


def averages(db, owner_id=None):
    """Calculate average patient measurements."""
    where, params = (
        ("WHERE owner_id = ?", (owner_id,))
        if owner_id is not None
        else ("", ())
    )

    row = db.execute(
        f"SELECT AVG(glucose) g, AVG(haemoglobin) h, "
        f"AVG(cholesterol) c, COUNT(*) n FROM patients {where}",
        params,
    ).fetchone()

    return {
        "count": row["n"],
        "glucose": row["g"],
        "haemoglobin": row["h"],
        "cholesterol": row["c"],
    }

