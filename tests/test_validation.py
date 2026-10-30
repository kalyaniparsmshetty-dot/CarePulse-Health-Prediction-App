from datetime import date

import pytest

from validation import parse_date, validate_email, validate_measurement, validate_patient

TODAY = date(2026, 10, 28)


def test_display_date_is_day_first():
    assert parse_date("10/12/1990", "/", TODAY) == date(1990, 12, 10)   # 10 December, not 12 October
    assert parse_date("28/01/1960", "/", TODAY) == date(1960, 1, 28)


def test_source_format_parsing_and_display():
    assert parse_date("28.01.1960", ".", TODAY) == date(1960, 1, 28)
    assert parse_date("09.12.2006", ".", TODAY).strftime("%d/%m/%Y") == "09/12/2006"


def test_old_historical_date_is_valid():
    assert parse_date("01/01/1901", "/", TODAY) == date(1901, 1, 1)


@pytest.mark.parametrize("text,sep", [("31.11.2001", "."), ("31/11/2001", "/"), ("29/02/2001", "/"), ("2001-01-01", "/"),
                                      ("1/1/2001", "/"), ("28.01.1960", "/"), ("28/01/1960", "."), ("", "/")])
def test_invalid_dates_rejected(text, sep):
    with pytest.raises(ValueError):
        parse_date(text, sep, TODAY)


def test_future_dob_rejected():
    with pytest.raises(ValueError, match="future"):
        parse_date("19.10.2030", ".", TODAY)
    assert parse_date("28/10/2026", "/", TODAY)   # today itself is allowed


def test_emails():
    assert validate_email("robyn@gmail.com")[1] is None
    for bad in ["hunter@gmail", "Kris.wu.gmail.com", "", "a@b", "a b@c.com"]:
        assert validate_email(bad)[1], bad


@pytest.mark.parametrize("field,raw", [("glucose", "abc"), ("glucose", "-5"), ("glucose", ""), ("glucose", "nan"),
                                       ("haemoglobin", "0"), ("haemoglobin", "99"), ("cholesterol", "inf"), ("cholesterol", "5")])
def test_invalid_measurements(field, raw):
    assert validate_measurement(field, raw)[1]


def test_valid_measurement():
    assert validate_measurement("haemoglobin", "13.5") == (13.5, None)


def test_missing_required_fields():
    _c, errors = validate_patient({}, TODAY)
    assert set(errors) == {"full_name", "dob", "email", "glucose", "haemoglobin", "cholesterol"}


def test_supplied_records_expected_outcome():
    from scripts.validate_records import validate_all
    res = {rec[0]: errors for rec, _c, errors in validate_all(TODAY)}
    assert {n for n, e in res.items() if e} == {2, 4, 8}
    assert "email" in res[2] and "dob" in res[4] and set(res[8]) == {"dob", "email"}


def test_form_remarks_and_injection_escaped(user_client):
    from conftest import add_patient, patient_id_from
    r = add_patient(user_client, remarks="<script>alert(1)</script>", full_name="Eve O'Neil-Smith")
    html = user_client.get(f"/patients/{patient_id_from(r)}").data
    assert b"<script>alert(1)</script>" not in html and b"&lt;script&gt;" in html


def test_name_with_angle_brackets_rejected(user_client):
    from conftest import add_patient
    assert b"not allowed" in add_patient(user_client, full_name="<b>x</b>").data


def test_form_dates_validation_messages(user_client):
    from conftest import add_patient
    assert b"not a real calendar date" in add_patient(user_client, dob="31/11/2001").data
    assert b"future" in add_patient(user_client, dob="19/10/2030").data
    assert b"DD/MM/YYYY" in add_patient(user_client, dob="1960-01-28").data
