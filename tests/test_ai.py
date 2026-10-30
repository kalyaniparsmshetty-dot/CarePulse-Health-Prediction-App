import pytest

from conftest import VALID_PATIENT, add_patient, add_user, login, make_app, patient_id_from
from database.db import get_db
from services import ai_service


def row(app, pid):
    with app.app_context():
        return dict(get_db().execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone())


def test_successful_ai_response_saved_separately(app, user_client, fake_ai):
    pid = patient_id_from(add_patient(user_client))
    r = row(app, pid)
    assert r["ai_status"] == "completed" and r["ai_remarks"] == "Mock educational remark."
    assert r["user_remarks"] == "my own note"
    html = user_client.get(f"/patients/{pid}").data
    assert b"Mock educational remark." in html and b"AI-generated" in html and b"not a medical diagnosis" in html


def test_only_measurements_sent_to_ai(app, user_client, fake_ai):
    add_patient(user_client)
    prompt = fake_ai["calls"][0]
    for secret in ["Robyn", "robyn@gmail.com", "1960", "my own note", "alice"]:
        assert secret not in prompt
    assert "66 years" in prompt and "232" in prompt


def test_ai_failure_keeps_record_and_no_fake_remarks(app, user_client, fake_ai):
    fake_ai["fail"] = ConnectionError("secret-detail-xyz")
    r = add_patient(user_client)
    pid = patient_id_from(r)
    data = row(app, pid)
    assert data["ai_status"] == "failed" and data["ai_remarks"] is None and data["full_name"] == "Robyn Pears"
    html = user_client.get(f"/patients/{pid}").data
    assert b"Retry assessment" in html and b"secret-detail-xyz" not in html


def test_missing_api_key_handled(tmp_path, fake_ai):
    app = make_app(tmp_path / "nokey.db", api_key="")
    add_user(app, "k@example.com")
    c = app.test_client(); login(c, "k@example.com")
    r = add_patient(c)
    data = row(app, patient_id_from(r))
    assert data["ai_status"] == "unavailable" and data["ai_remarks"] is None and not fake_ai["calls"]
    assert b"unavailable" in c.get("/dashboard").data


def test_retry_works(app, user_client, fake_ai):
    fake_ai["fail"] = TimeoutError("slow")
    pid = patient_id_from(add_patient(user_client))
    assert row(app, pid)["ai_status"] == "failed"
    fake_ai["fail"] = None
    user_client.post(f"/patients/{pid}/assess")
    assert row(app, pid)["ai_status"] == "completed"
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM assessments WHERE patient_id=?", (pid,)).fetchone()[0] == 2


def test_measurement_change_marks_outdated_then_reassess(app, user_client):
    pid = patient_id_from(add_patient(user_client))
    user_client.post(f"/patients/{pid}/edit", data={**VALID_PATIENT, "glucose": "100"})
    assert row(app, pid)["ai_status"] == "outdated"
    assert b"may no longer apply" in user_client.get(f"/patients/{pid}").data
    user_client.post(f"/patients/{pid}/assess")
    assert row(app, pid)["ai_status"] == "completed"


def test_email_only_edit_keeps_assessment_current(app, user_client):
    pid = patient_id_from(add_patient(user_client))
    user_client.post(f"/patients/{pid}/edit", data={**VALID_PATIENT, "email": "gokul@infocare.com"})
    assert row(app, pid)["ai_status"] == "completed"


def test_empty_ai_response(app, user_client, fake_ai):
    fake_ai["text"] = "   "
    assert row(app, patient_id_from(add_patient(user_client)))["ai_status"] == "failed"


@pytest.mark.parametrize("exc,cat", [(TimeoutError("t"), "timeout"), (ConnectionError("c"), "network")])
def test_error_classification(monkeypatch, exc, cat):
    def boom(*a):
        raise exc
    monkeypatch.setattr(ai_service, "_call_gemini", boom)
    res = ai_service.generate_assessment(30, 90, 14, 180, "k", "m")
    assert not res.ok and res.error_category == cat


def test_rate_limit_and_key_classification():
    class E(Exception):
        def __init__(self, code):
            self.code = code
    assert ai_service._classify(E(429)) == "rate_limit"
    assert ai_service._classify(E(403)) == "invalid_key"


@pytest.mark.live
@pytest.mark.skip(reason="Optional live test: remove skip and set GEMINI_API_KEY to call the real API")
def test_live_gemini():
    import os
    res = ai_service.generate_assessment(40, 95, 14, 180, os.environ["GEMINI_API_KEY"], "gemini-2.5-flash")
    assert res.ok
