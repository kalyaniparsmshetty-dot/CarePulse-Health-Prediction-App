# Health Prediction & Patient Management System

A Flask web app for managing patient records (glucose, haemoglobin, cholesterol), with a user dashboard,
a separate admin dashboard and optional AI-written informational remarks from Google Gemini.

> **AI-generated information is for educational purposes only and is not a medical diagnosis. Consult a qualified healthcare professional for medical advice.**
> This is a learning/evaluation project. It is **not** production-ready and **not** HIPAA-compliant.

## Features
- Register, sign in, sign out (hashed passwords, sessions, CSRF protection). Public sign-up always creates the `user` role.
- Separate **Admin Login**; first admin is created only from the command line.
- Patient CRUD with the seven fields in this order: Full Name, DOB, Email, Glucose, Haemoglobin, Cholesterol, **Remarks** (directly below Cholesterol).
- Dates are shown as **DD/MM/YYYY** and stored as ISO `YYYY-MM-DD`; impossible and future dates are rejected.
- Search by name or email; dashboard cards and Chart.js charts calculated from real database rows.
- Admin: statistics, all patients (with owner), user management (activate/deactivate), audit history.
- AI assessment (Gemini) using only age + the three measurements; Retry, "outdated" marking when measurements change.
- Works without a Gemini key (AI shows "unavailable"; everything else works).

## Tech stack
Python 3.10+, Flask, Flask-WTF (CSRF), SQLite, HTML/CSS/JavaScript (own CSS, no CDN), Chart.js (bundled in `static/js`), google-genai, pytest.

## Folder structure
```
app.py            app factory, error handlers, CLI commands (init-db, create-admin)
config.py         settings from environment variables
validation.py     strict date/email/number validation
auth_utils.py     sessions, role decorators, password hashing, audit log
utils.py          date/time helpers
routes/           auth.py, patients.py, admin.py
services/         ai_service.py (Gemini), patient_service.py (assessment + statistics)
database/         schema.sql, db.py
scripts/          validate_records.py, import_valid_records.py, supplied_records.py
templates/ static/ tests/ docs/
```

## Setup on Windows (PowerShell)
```powershell
cd health-prediction-app
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```
If PowerShell blocks activation:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## Initialise the database
```powershell
python -m flask --app app init-db
```
Safe to repeat: it only creates missing tables and never deletes data. The database file is `instance\health_app.db`.

## Create the first administrator (secure)
```powershell
python -m flask --app app create-admin
```
You are prompted for name, email and password (hidden). No admin password exists in the source code or docs.
It refuses duplicates. Roles cannot be changed from the web app.

## Run the app
```powershell
python app.py
```
Open **http://127.0.0.1:5000** in your browser.
- Users: click *Create an account*, then sign in.
- Admins: open **http://127.0.0.1:5000/admin/login** (a regular user's credentials are refused there).

## Configure Gemini (optional)
1. Create a key in Google AI Studio.
2. Open `.env` and set `GEMINI_API_KEY=` to your key (keep `.env` private; it is git-ignored).
3. Restart the app. New patients get an assessment after saving; use **Retry assessment** if it fails.

Without a key the app starts normally and patients show "AI not configured". Only age and the three measurements are sent
(never name, email, exact DOB, or your remarks). Assessment runs during the save request (up to `AI_TIMEOUT_SECONDS`, default 20).

## Run the tests
```powershell
python -m pytest -q
```
Tests use a temporary database and a mocked AI (no internet, no cost). One optional live-Gemini test is marked `live` and skipped.

## Validate and import the supplied records
```powershell
python -m scripts.validate_records
```
Reports each of the 10 records as VALID/INVALID with reasons (evaluation date 28/10/2026; use `--today now` for your computer's date).
Source dates are `DD.MM.YYYY`. Expected: records **2, 4, 8 invalid**; 7 valid.

```powershell
python -m scripts.import_valid_records --owner-email you@example.com
```
Imports only valid records into an existing user's account. Never runs at startup. **Duplicate rule:** each record has an import key
(hash of lower-cased name, ISO DOB, lower-cased email and measurements); a record whose key already exists for that owner is skipped and reported.
So rows 1 and 6 (identical) import once, and repeating the import adds nothing. Expected first run: 6 imported, 3 invalid skipped, 1 duplicate skipped.
Ordinary patients added in the web form are never de-duplicated.

## Design decisions
- Units: glucose mg/dL, haemoglobin g/dL, cholesterol mg/dL. Input limits (not medical thresholds): 20–1000, 1–30, 50–1000.
- Admins can view, edit, delete and re-assess any patient (audited); they cannot add patients to other users.
- Other users' records return 404 (existence is not revealed).
- "Pending or Failed" counts every patient whose AI status is not "completed" (not assessed, failed, unavailable, outdated).
- "Recent Patients" = added in the last 7 days.
- Timestamps are stored and shown in UTC.

## Security notes
Password hashing (PBKDF2-SHA256), CSRF tokens, parameterised SQL, escaped output, strict Content-Security-Policy, role checks on the server,
audit log without secrets, `HttpOnly`/`SameSite=Lax` cookies. For real deployment use HTTPS and set `SESSION_COOKIE_SECURE=true`.

## Known limitations
No login rate-limiting or lockout, no email verification or password reset, no pagination on audit history (latest 200 shown),
AI call is synchronous, live Gemini calls were not tested in the build environment, not independently security-audited.

## Publish to GitHub
See `docs/GITHUB_PUBLISHING.md`.
