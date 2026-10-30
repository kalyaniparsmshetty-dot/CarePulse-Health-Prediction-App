"""Strict validation shared by the web forms and the supplied-record scripts.

Dates are parsed with a regular expression for the exact shape and then with
datetime.date(), which rejects impossible calendar dates (e.g. 31/11/2001).
Nothing is ever "fixed" silently.
"""
import math
import re
from datetime import date

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
DISPLAY_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")   # DD/MM/YYYY (web app)
SOURCE_DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")  # DD.MM.YYYY (supplied data)

# Input limits (NOT medical thresholds).
LIMITS = {
    "glucose": (20.0, 1000.0, "mg/dL"),
    "haemoglobin": (1.0, 30.0, "g/dL"),
    "cholesterol": (50.0, 1000.0, "mg/dL"),
}
LABELS = {"glucose": "Glucose", "haemoglobin": "Haemoglobin", "cholesterol": "Cholesterol"}
MAX_REMARKS = 1000
MAX_NAME = 120
MIN_PASSWORD = 8


def parse_date(text, separator, today):
    """Parse DD/MM/YYYY (separator '/') or DD.MM.YYYY (separator '.').
    Returns a date. Raises ValueError with a user-friendly message."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Date of birth is required.")
    pattern = DISPLAY_DATE_RE if separator == "/" else SOURCE_DATE_RE
    fmt = "DD/MM/YYYY" if separator == "/" else "DD.MM.YYYY"
    match = pattern.match(text)
    if not match:
        raise ValueError(f"Enter the date of birth as {fmt}, for example 28{separator}01{separator}1960.")
    day, month, year = (int(g) for g in match.groups())
    try:
        parsed = date(year, month, day)   # day first, always
    except ValueError:
        raise ValueError(f"{text} is not a real calendar date.") from None
    if parsed > today:
        raise ValueError("Date of birth cannot be in the future.")
    return parsed


def validate_email(value):
    value = (value or "").strip()
    if not value:
        return None, "Email is required."
    if len(value) > 254 or not EMAIL_RE.match(value):
        return None, "Enter a valid email address, for example name@example.com."
    return value, None


def validate_full_name(value):
    value = " ".join((value or "").split())  # trims and collapses spaces
    if not value:
        return None, "Full name is required."
    if len(value) < 2:
        return None, "Full name must have at least 2 characters."
    if len(value) > MAX_NAME:
        return None, f"Full name must be at most {MAX_NAME} characters."
    if any(c in value for c in "<>") or any(ord(c) < 32 for c in value):
        return None, "Full name contains characters that are not allowed."
    return value, None


def validate_measurement(field, raw):
    label = LABELS[field]
    low, high, unit = LIMITS[field]
    raw = (raw or "").strip()
    if not raw:
        return None, f"{label} is required."
    try:
        number = float(raw)
    except ValueError:
        return None, f"{label} must be a number."
    if not math.isfinite(number):
        return None, f"{label} must be a number."
    if number < 0:
        return None, f"{label} cannot be negative."
    if not (low <= number <= high):
        return None, f"{label} must be between {low:g} and {high:g} {unit}."
    return number, None


def validate_password(password, confirm=None):
    if not password:
        return "Password is required."
    if len(password) < MIN_PASSWORD:
        return f"Password must have at least {MIN_PASSWORD} characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    if confirm is not None and password != confirm:
        return "Password and confirmation do not match."
    return None


def validate_patient(data, today, date_separator="/"):
    """data: dict with full_name, dob, email, glucose, haemoglobin, cholesterol, remarks.
    Returns (cleaned, errors). `cleaned['dob']` is an ISO string."""
    cleaned, errors = {}, {}

    value, err = validate_full_name(data.get("full_name"))
    (errors.__setitem__("full_name", err) if err else cleaned.__setitem__("full_name", value))

    try:
        cleaned["dob"] = parse_date(data.get("dob"), date_separator, today).isoformat()
    except ValueError as exc:
        errors["dob"] = str(exc)

    value, err = validate_email(data.get("email"))
    (errors.__setitem__("email", err) if err else cleaned.__setitem__("email", value))

    for field in LIMITS:
        value, err = validate_measurement(field, str(data.get(field, "") if data.get(field) is not None else ""))
        (errors.__setitem__(field, err) if err else cleaned.__setitem__(field, value))

    remarks = (data.get("remarks") or "").strip()
    if len(remarks) > MAX_REMARKS:
        errors["remarks"] = f"Remarks must be at most {MAX_REMARKS} characters."
    else:
        cleaned["remarks"] = remarks or None

    return cleaned, errors
