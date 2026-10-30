"""Safely import ONLY the valid supplied records for one existing user.

Run:  python -m scripts.import_valid_records --owner-email you@example.com

Duplicate rule: each record gets an import key = SHA-256 of the lower-cased name, ISO DOB,
lower-cased email and the three measurements. A record whose key already exists for that
owner (earlier in the same run, or from a previous run) is SKIPPED and reported.
So repeating the import never duplicates data, and rows 1 and 6 (identical) import once.
"""
import argparse
import hashlib
from datetime import date

from app import create_app
from database.db import get_db
from scripts.supplied_records import EVALUATION_DATE
from scripts.validate_records import validate_all
from utils import now_str


def import_key(c):
    text = "|".join([c["full_name"].lower(), c["dob"], c["email"].lower(),
                     f"{c['glucose']:g}", f"{c['haemoglobin']:g}", f"{c['cholesterol']:g}"])
    return hashlib.sha256(text.encode()).hexdigest()


def run_import(owner_email, today):
    """Must run inside an app context. Returns a list of (record_no, name, outcome)."""
    db = get_db()
    owner = db.execute("SELECT id FROM users WHERE email=?", (owner_email.strip().lower(),)).fetchone()
    if owner is None:
        raise SystemExit(f"No user with email {owner_email}. Register that account first.")
    report = []
    for rec, cleaned, errors in validate_all(today):
        no, name = rec[0], rec[1]
        if errors:
            report.append((no, name, "SKIPPED invalid: " + "; ".join(errors.values())))
            continue
        key = import_key(cleaned)
        if db.execute("SELECT 1 FROM patients WHERE owner_id=? AND import_key=?", (owner["id"], key)).fetchone():
            report.append((no, name, "SKIPPED duplicate (already imported)"))
            continue
        now = now_str()
        db.execute(
            "INSERT INTO patients (owner_id,full_name,dob,email,glucose,haemoglobin,cholesterol,ai_status,"
            "import_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,'pending',?,?,?)",
            (owner["id"], cleaned["full_name"], cleaned["dob"], cleaned["email"], cleaned["glucose"],
             cleaned["haemoglobin"], cleaned["cholesterol"], key, now, now))
        report.append((no, name, "IMPORTED"))
    db.commit()
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--owner-email", required=True)
    p.add_argument("--today", default=EVALUATION_DATE, help="YYYY-MM-DD or 'now'")
    args = p.parse_args(argv)
    today = date.today() if args.today == "now" else date.fromisoformat(args.today)
    app = create_app()
    with app.app_context():
        report = run_import(args.owner_email, today)
    for no, name, outcome in report:
        print(f"#{no:<2} {name:<14} {outcome}")
    imported = sum(1 for r in report if r[2] == "IMPORTED")
    print(f"\nImported {imported} of {len(report)} supplied records; {len(report) - imported} skipped (see above).")


if __name__ == "__main__":
    main()
