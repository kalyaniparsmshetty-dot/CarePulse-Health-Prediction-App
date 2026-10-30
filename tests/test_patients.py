from conftest import VALID_PATIENT, add_patient, add_user, login, make_app, patient_id_from
from database.db import get_db


def test_add_and_view_patient_with_dd_mm_yyyy(app, user_client):
    r = add_patient(user_client)
    assert r.status_code == 302
    pid = patient_id_from(r)
    html = user_client.get(f"/patients/{pid}").data.decode()
    assert "28/01/1960" in html and "robyn@gmail.com" in html and "my own note" in html
    with app.app_context():
        assert get_db().execute("SELECT dob FROM patients WHERE id=?", (pid,)).fetchone()[0] == "1960-01-28"


def test_form_has_seven_fields_in_order_remarks_below_cholesterol(user_client):
    html = user_client.get("/patients/new").data.decode()
    order = [html.index(f'name="{n}"') for n in
             ["full_name", "dob", "email", "glucose", "haemoglobin", "cholesterol", "remarks"]]
    assert order == sorted(order)
    assert 'id="remarks"' in html and "DD/MM/YYYY" in html
    between = html[order[5]:order[6]]
    assert 'name="' not in between.replace('name="cholesterol"', "").replace('name="remarks"', "")


def test_edit_form_prepopulated_and_updates(app, user_client):
    pid = patient_id_from(add_patient(user_client))
    html = user_client.get(f"/patients/{pid}/edit").data.decode()
    assert 'value="28/01/1960"' in html and 'name="remarks"' in html
    r = user_client.post(f"/patients/{pid}/edit", data={**VALID_PATIENT, "email": "gokul@infocare.com"})
    assert r.status_code == 302
    assert b"gokul@infocare.com" in user_client.get(f"/patients/{pid}").data


def test_validation_failure_preserves_values(user_client):
    r = user_client.post("/patients/new", data={**VALID_PATIENT, "email": "bad", "remarks": "keep me"})
    assert r.status_code == 200 and b"valid email" in r.data and b"keep me" in r.data and b"Robyn Pears" in r.data


def test_delete_patient(app, user_client):
    pid = patient_id_from(add_patient(user_client))
    assert user_client.post(f"/patients/{pid}/delete").status_code == 302
    assert user_client.get(f"/patients/{pid}").status_code == 404


def test_search_by_name_and_email(user_client):
    add_patient(user_client)
    add_patient(user_client, full_name="Sam Kerr", email="sam@news.com.au")
    assert b"Sam Kerr" in user_client.get("/patients?q=kerr").data
    assert b"Robyn Pears" not in user_client.get("/patients?q=kerr").data
    assert b"Robyn Pears" in user_client.get("/patients?q=ROBYN@gmail").data
    assert b"No patients to show" in user_client.get("/patients?q=%25").data   # % is literal, not wildcard


def test_persistence_after_restart(tmp_path, fake_ai):
    path = tmp_path / "persist.db"
    app1 = make_app(path)
    add_user(app1, "p@example.com")
    c1 = app1.test_client(); login(c1, "p@example.com"); add_patient(c1)
    app2 = make_app(path)           # "restart": new app on the same file
    c2 = app2.test_client(); login(c2, "p@example.com")
    assert b"Robyn Pears" in c2.get("/patients").data


def test_ownership_isolation(app, user_client):
    pid = patient_id_from(add_patient(user_client))
    add_user(app, "bob@example.com")
    bob = app.test_client(); login(bob, "bob@example.com")
    assert b"Robyn Pears" not in bob.get("/patients").data
    assert bob.get(f"/patients/{pid}").status_code == 404
    assert bob.post(f"/patients/{pid}/edit", data=VALID_PATIENT).status_code == 404
    assert bob.post(f"/patients/{pid}/delete").status_code == 404
    assert bob.post(f"/patients/{pid}/assess").status_code == 404
    assert b"Robyn Pears" in user_client.get(f"/patients/{pid}").data


def test_dashboard_stats_from_real_data(user_client):
    assert b"<strong>0</strong>" in user_client.get("/dashboard").data
    add_patient(user_client)
    html = user_client.get("/dashboard").data.decode()
    assert "<strong>1</strong>" in html and "232" in html


def test_import_is_safe_and_idempotent(app):
    from scripts.import_valid_records import run_import
    from datetime import date
    add_user(app, "imp@example.com")
    with app.app_context():
        first = run_import("imp@example.com", date(2026, 10, 28))
        assert sum(1 for r in first if r[2] == "IMPORTED") == 6
        assert [r[0] for r in first if "duplicate" in r[2]] == [6]
        assert {r[0] for r in first if "invalid" in r[2]} == {2, 4, 8}
        second = run_import("imp@example.com", date(2026, 10, 28))
        assert all(r[2] != "IMPORTED" for r in second)
        assert get_db().execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 6
