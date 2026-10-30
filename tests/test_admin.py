from click.testing import CliRunner

from conftest import PASSWORD, add_patient, add_user, login, patient_id_from
from database.db import get_db


def test_regular_user_cannot_access_admin_pages(user_client):
    for path in ["/admin", "/admin/users", "/admin/patients", "/admin/audit", "/admin/analytics", "/admin/users/1"]:
        assert user_client.get(path).status_code == 403, path


def test_unauthorized_cannot_manage_accounts(app, client, user_client):
    assert client.post("/admin/users/1/toggle").status_code == 302
    assert user_client.post("/admin/users/1/toggle").status_code == 403


def test_user_cannot_change_role_via_profile(app, user_client):
    user_client.post("/profile", data={"full_name": "Alice", "role": "admin"})
    with app.app_context():
        assert get_db().execute("SELECT role FROM users WHERE email='alice@example.com'").fetchone()["role"] == "user"


def test_admin_dashboard_uses_real_counts(app, admin_client, user_client):
    add_patient(user_client)
    r = admin_client.get("/admin")
    assert r.status_code == 200 and b"Total Patient Records" in r.data
    assert b'"data": [1]' in r.data or b'"data":[1]' in r.data


def test_admin_can_toggle_user_and_it_is_audited(app, admin_client):
    uid = add_user(app, "target@example.com")
    admin_client.post(f"/admin/users/{uid}/toggle")
    with app.app_context():
        assert get_db().execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()[0] == 0
        assert get_db().execute("SELECT 1 FROM audit_log WHERE event_type='account_deactivated'").fetchone()
    assert b"Invalid email" in login(app.test_client(), "target@example.com").data


def test_cannot_deactivate_only_admin_or_self(app, admin_client):
    with app.app_context():
        aid = get_db().execute("SELECT id FROM users WHERE email='boss@example.com'").fetchone()[0]
    admin_client.post(f"/admin/users/{aid}/toggle")
    with app.app_context():
        assert get_db().execute("SELECT is_active FROM users WHERE id=?", (aid,)).fetchone()[0] == 1


def test_admin_sees_owner_and_can_edit_delete_with_audit(app, admin_client, user_client):
    pid = patient_id_from(add_patient(user_client))
    assert b"alice@example.com" in admin_client.get("/admin/patients").data
    assert b"Record owner" in admin_client.get(f"/patients/{pid}").data
    admin_client.post(f"/patients/{pid}/edit", data={"full_name": "Robyn Pears", "dob": "28/01/1960",
                      "email": "robyn@gmail.com", "glucose": "100", "haemoglobin": "13.5", "cholesterol": "180"})
    admin_client.post(f"/patients/{pid}/delete")
    with app.app_context():
        ev = [r[0] for r in get_db().execute("SELECT event_type FROM audit_log")]
    assert "patient_admin_edit" in ev and "patient_admin_delete" in ev


def test_audit_page_hides_secrets_and_is_admin_only(app, admin_client):
    r = admin_client.get("/admin/audit")
    assert r.status_code == 200 and b"pbkdf2" not in r.data


def test_create_admin_cli(app):
    runner = app.test_cli_runner()
    ok = runner.invoke(args=["create-admin"], input=f"Root Admin\nroot@example.com\n{PASSWORD}\n{PASSWORD}\n")
    assert ok.exit_code == 0 and "Administrator created" in ok.output
    with app.app_context():
        row = get_db().execute("SELECT * FROM users WHERE email='root@example.com'").fetchone()
    assert row["role"] == "admin" and row["password_hash"] != PASSWORD
    dup = runner.invoke(args=["create-admin"], input=f"Root\nroot@example.com\n{PASSWORD}\n{PASSWORD}\n")
    assert dup.exit_code != 0 and "already exists" in dup.output
    assert PASSWORD not in ok.output
    bad = runner.invoke(args=["create-admin"], input="Root\nbad-email\nshort\nshort\n")
    assert bad.exit_code != 0
