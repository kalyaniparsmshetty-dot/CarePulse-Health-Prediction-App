import re
from datetime import date

import pytest

from app import create_app
from auth_utils import hash_password
from database.db import get_db
from services import ai_service
from utils import now_str

PASSWORD = "Passw0rd!x"
VALID_PATIENT = {"full_name": "Robyn Pears", "dob": "28/01/1960", "email": "robyn@gmail.com",
                 "glucose": "232", "haemoglobin": "13.5", "cholesterol": "180", "remarks": "my own note"}


def make_app(db_path, csrf=False, api_key="test-key"):
    return create_app({
        "TESTING": True, "DATABASE": str(db_path), "SECRET_KEY": "test-secret", "WTF_CSRF_ENABLED": csrf,
        "PBKDF2_ITERATIONS": 1000, "GEMINI_API_KEY": api_key, "TODAY_OVERRIDE": date(2026, 10, 28),
    })


@pytest.fixture
def fake_ai(monkeypatch):
    """Mocked Gemini: no network. Set fake_ai['fail'] to an exception to simulate failure."""
    state = {"fail": None, "text": "Mock educational remark.", "calls": []}

    def fake(prompt, api_key, model, timeout):
        state["calls"].append(prompt)
        if state["fail"]:
            raise state["fail"]
        return state["text"]
    monkeypatch.setattr(ai_service, "_call_gemini", fake)
    return state


@pytest.fixture
def app(tmp_path, fake_ai):
    return make_app(tmp_path / "test.db")


@pytest.fixture
def client(app):
    return app.test_client()


def add_user(app, email, role="user", name="Test User", active=1):
    with app.app_context():
        db = get_db()
        now = now_str()
        cur = db.execute("INSERT INTO users (full_name,email,password_hash,role,is_active,created_at,updated_at) "
                         "VALUES (?,?,?,?,?,?,?)", (name, email, hash_password(PASSWORD), role, active, now, now))
        db.commit()
        return cur.lastrowid


def login(client, email, admin=False):
    return client.post("/admin/login" if admin else "/login", data={"email": email, "password": PASSWORD},
                       follow_redirects=True)


@pytest.fixture
def user_client(app):
    add_user(app, "alice@example.com", name="Alice")
    c = app.test_client()
    login(c, "alice@example.com")
    return c


@pytest.fixture
def admin_client(app):
    add_user(app, "boss@example.com", role="admin", name="Boss")
    c = app.test_client()
    login(c, "boss@example.com", admin=True)
    return c


def add_patient(client, **overrides):
    data = {**VALID_PATIENT, **overrides}
    return client.post("/patients/new", data=data, follow_redirects=False)


def patient_id_from(response):
    return int(re.search(r"/patients/(\d+)", response.headers["Location"]).group(1))
