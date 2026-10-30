"""Report every supplied record as VALID or INVALID with reasons.

Run:  python -m scripts.validate_records            (evaluation date 28/10/2026)
      python -m scripts.validate_records --today now (use this computer's date)
Nothing is written to the database and nothing is corrected silently.
"""
import argparse
from datetime import date

from scripts.supplied_records import EVALUATION_DATE, SUPPLIED_RECORDS
from validation import validate_patient


def record_to_form(rec):
    _no, name, dob, email, glucose, hb, chol = rec
    return {"full_name": name, "dob": dob, "email": email, "glucose": str(glucose),
            "haemoglobin": str(hb), "cholesterol": str(chol), "remarks": ""}


def validate_all(today):
    """Returns a list of (record, cleaned, errors)."""
    results = []
    for rec in SUPPLIED_RECORDS:
        cleaned, errors = validate_patient(record_to_form(rec), today, date_separator=".")
        results.append((rec, cleaned, errors))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--today", default=EVALUATION_DATE, help="YYYY-MM-DD, or 'now'")
    args = parser.parse_args(argv)
    today = date.today() if args.today == "now" else date.fromisoformat(args.today)

    print(f"Validating {len(SUPPLIED_RECORDS)} supplied records (evaluation date {today.strftime('%d/%m/%Y')})\n")
    valid = 0
    for rec, cleaned, errors in validate_all(today):
        no, name = rec[0], rec[1]
        if errors:
            print(f"#{no:<2} {name:<14} INVALID")
            for field, msg in errors.items():
                print(f"      - {field}: {msg}")
        else:
            valid += 1
            from utils import iso_to_display
            print(f"#{no:<2} {name:<14} VALID   (DOB shown as {iso_to_display(cleaned['dob'])})")
    print(f"\nSummary: {valid} valid, {len(SUPPLIED_RECORDS) - valid} invalid.")
    print("Note: records 1 and 6 are identical duplicates; the import script skips the second one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
