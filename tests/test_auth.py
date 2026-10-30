from conftest import PASSWORD, add_user, login
from database.db import get_db


def reg(client, **kw):
    data = {"full_name": "New User", "email": "new@example.com", "password": PASSWORD, "confirm_password": PASSWORD}
    data.update(kw)
    return client.post("/register", data=data)


def test_registration_succeeds_and_password_is_hashed(app, client):
    r = reg(client)
    assert r.status_code == 302
    with app.app_context():
        row = get_db().execute("SELECT * FROM users WHERE email='new@example.com'").fetchone()
    assert row["role"] == "user"
    assert row["password_hash"] != PASSWORD and PASSWORD not in row["password_hash"]
    assert row["password_hash"].startswith("pbkdf2:")


def test_duplicate_email_rejected(client):
    reg(client)
    r = reg(client, email="NEW@example.com")
    assert b"already exists" in r.data


def test_public_registration_cannot_create_admin(app, client):
    reg(client, role="admin", is_admin="1")
    with app.app_context():
        assert get_db().execute("SELECT role FROM users WHERE email='new@example.com'").fetchone()["role"] == "user"


def test_registration_validation(client):
    assert b"valid email" in reg(client, email="bad").data
    assert b"do not match" in reg(client, confirm_password="other1234").data
    assert b"at least 8" in reg(client, password="a1", confirm_password="a1").data


def test_login_success_and_invalid(app, client):
    add_user(app, "a@example.com")
    assert b"Invalid email or password" in client.post("/login", data={"email": "a@example.com", "password": "wrong"}).data
    assert b"Invalid email or password" in client.post("/login", data={"email": "nobody@example.com", "password": "x"}).data
    r = login(client, "a@example.com")
    assert b"Dashboard" in r.data


def test_logout_ends_session(app, user_client):
    assert user_client.get("/dashboard").status_code == 200
    user_client.post("/logout")
    assert user_client.get("/dashboard").status_code == 302


def test_protected_routes_require_login(client):
    for path in ["/dashboard", "/patients", "/patients/new", "/analytics", "/profile", "/patients/1", "/admin"]:
        assert client.get(path).status_code == 302, path


def test_admin_login_rejects_regular_user(app, client):
    add_user(app, "u@example.com")
    r = login(client, "u@example.com", admin=True)
    assert b"Invalid email or password" in r.data
    assert client.get("/admin").status_code == 302


def test_admin_login_accepts_admin(app, client):
    add_user(app, "adm@example.com", role="admin")
    r = login(client, "adm@example.com", admin=True)
    assert b"Admin Dashboard" in r.data


def test_admin_cannot_use_user_login_page(app, client):
    add_user(app, "adm@example.com", role="admin")
    assert b"Invalid email or password" in login(client, "adm@example.com").data


def test_audit_history_recorded(app, client):
    add_user(app, "a@example.com")
    client.post("/login", data={"email": "a@example.com", "password": "bad"})
    login(client, "a@example.com")
    client.post("/logout")
    with app.app_context():
        events = [(r["event_type"], r["success"]) for r in get_db().execute("SELECT * FROM audit_log ORDER BY id")]
        dump = str(list(map(tuple, get_db().execute("SELECT * FROM audit_log"))))
    assert ("login_failed", 0) in events and ("login_success", 1) in events and ("logout", 1) in events
    assert PASSWORD not in dump and "pbkdf2" not in dump


def test_deactivated_user_cannot_login(app, client):
    add_user(app, "off@example.com", active=0)
    assert b"Invalid email or password" in login(client, "off@example.com").data
