"""Application configuration (all secrets come from environment variables)."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def default_config():
    """Settings read from the environment (.env file). No secrets live in code."""
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "").strip(),
        "GEMINI_MODEL": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "AI_TIMEOUT_SECONDS": int(os.environ.get("AI_TIMEOUT_SECONDS", "20")),
        # Set SESSION_COOKIE_SECURE=true when the site is served over HTTPS.
        "SESSION_COOKIE_SECURE": os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=2),
        "PBKDF2_ITERATIONS": int(os.environ.get("PBKDF2_ITERATIONS", "600000")),
        "TODAY_OVERRIDE": None,  # tests can freeze "today" with a datetime.date
        "WTF_CSRF_TIME_LIMIT": 7200,
    }


def load_or_create_secret_key(instance_path):
    """Use SECRET_KEY from the environment, else create one once and keep it
    in instance/secret_key.txt (git-ignored) so sessions survive restarts."""
    path = Path(instance_path) / "secret_key.txt"
    if path.exists():
        return path.read_text().strip()
    Path(instance_path).mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key)
    return key
