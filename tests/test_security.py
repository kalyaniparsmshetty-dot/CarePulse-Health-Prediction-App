import sqlite3

import pytest

from conftest import VALID_PATIENT, add_patient, add_user, make_app, patient_id_from
from database.db import get_db


def test_foreign_keys_enforced(app):
    with app.app_context():
        db = get_db()
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO patients (owner_id,full_name,dob,email,glucose,haemoglobin,cholesterol,created_at,updated_at)"
                       " VALUES (999,'x','2000-01-01','a@b.co',1,1,1,'t','t')")


def test_email_unique_constraint(app):
    add_user(app, "dup@example.com")
    with app.app_context(), pytest.raises(sqlite3.IntegrityError):
        get_db().execute("INSERT INTO users (full_name,email,password_hash,role,created_at,updated_at) "
                         "VALUES ('x','DUP@example.com','h','user','t','t')")


def test_csrf_protection(tmp_path, fake_ai):
    app = make_app(tmp_path / "csrf.db", csrf=True)
    add_user(app, "c@example.com")
    c = app.test_client()
    assert c.post("/login", data={"email": "c@example.com", "password": "x"}).status_code == 400
    # a valid token works
    import re
    token = re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").data.decode()).group(1)
    assert c.post("/login", data={"email": "c@example.com", "password": "x", "csrf_token": token}).status_code == 200


def test_post_only_actions_reject_get(user_client):
    pid = patient_id_from(add_patient(user_client))
    assert user_client.get(f"/patients/{pid}/delete").status_code == 405
    assert user_client.get("/logout").status_code == 405


def test_sql_injection_in_search_is_harmless(user_client):
    add_patient(user_client)
    r = user_client.get("/patients?q=' OR '1'='1")
    assert r.status_code == 200 and b"Robyn Pears" not in r.data


def test_security_headers_and_no_cache(user_client):
    r = user_client.get("/dashboard")
    assert r.headers["X-Frame-Options"] == "DENY" and "no-store" in r.headers["Cache-Control"]
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]


def test_no_password_hash_in_pages(app, admin_client):
    for path in ["/admin", "/admin/users", "/admin/users/1", "/admin/audit", "/profile"]:
        assert b"pbkdf2" not in admin_client.get(path).data, path


def test_open_redirect_blocked(app, client):
    add_user(app, "r@example.com")
    from conftest import PASSWORD
    r = client.post("/login?next=//evil.com", data={"email": "r@example.com", "password": PASSWORD})
    assert r.headers["Location"].endswith("/dashboard")


def test_error_page_hides_details(user_client):
    r = user_client.get("/patients/99999")
    assert r.status_code == 404 and b"Traceback" not in r.data


def test_audit_requires_admin(user_client, client):
    assert user_client.get("/admin/audit").status_code == 403
    assert client.get("/admin/audit").status_code == 302
