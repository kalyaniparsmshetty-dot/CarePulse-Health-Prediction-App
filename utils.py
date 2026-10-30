"""Small shared helpers: dates, timestamps, formatting."""
from datetime import date, datetime, timezone

from flask import current_app


def now_str():
    """UTC timestamp stored in the database."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def today():
    """Today's date. Tests can freeze it with config TODAY_OVERRIDE."""
    return current_app.config.get("TODAY_OVERRIDE") or date.today()


def iso_to_display(value):
    """'1960-01-28' -> '28/01/1960'."""
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def timestamp_to_display(value):
    """'2026-10-28 09:30:00' -> '28/10/2026 09:30 UTC'."""
    if not value:
        return "—"
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M UTC")
    except ValueError:
        return value


def age_in_years(dob_iso, on_date):
    born = datetime.strptime(dob_iso, "%Y-%m-%d").date()
    years = on_date.year - born.year
    if (on_date.month, on_date.day) < (born.month, born.day):
        years -= 1
    return years


def fmt_number(value):
    """150.0 -> '150', 13.5 -> '13.5'."""
    if value is None:
        return ""
    return f"{value:g}"
