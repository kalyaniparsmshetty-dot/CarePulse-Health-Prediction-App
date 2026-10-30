# CarePulse – Health Prediction & Patient Management System

CarePulse is a Python Flask web application for managing patient records, including glucose, haemoglobin and cholesterol measurements. It provides patient management, user and administrator dashboards, data analytics, input validation, duplicate detection and optional AI-generated informational remarks using the Google Gemini API.

> **Medical Disclaimer:** AI-generated information is for educational and informational purposes only. It is not a medical diagnosis or a substitute for professional medical advice. Always consult a qualified healthcare professional.

This is a learning and evaluation project. It is not production-ready and is not HIPAA-compliant.

---

## 1. Features

### User Management

* User registration, login and logout.
* Password hashing and session management.
* CSRF protection.
* Separate administrator login.
* Public registration creates only the regular user role.
* Administrator account creation through a command-line command.

### Patient Management

* Create, Read, Update and Delete (CRUD) patient records.
* Patient information includes:

  * Full Name
  * Date of Birth
  * Email Address
  * Glucose
  * Haemoglobin
  * Cholesterol
  * Remarks
* Search patient records by name or email.
* Patient details and assessment history.

### Input Validation

* Email format validation.
* Date of birth validation.
* Impossible calendar dates are rejected.
* Future dates of birth are rejected.
* Numeric blood test values are validated.
* Clear validation messages are displayed when information is invalid.

### Duplicate Detection

* The application checks existing patient records before creating a new entry.
* Identical duplicate records for the same user are rejected.
* A duplicate warning is displayed instead of creating another copy.
* The supplied-record import script also uses an import key to identify duplicate records and prevent repeated imports.

### Dashboard and Analytics

* Separate user and administrator dashboards.
* Patient statistics calculated from database records.
* Visual charts using Chart.js.
* Patient measurement summaries.
* Administrator statistics and user management.
* Audit history.

### AI Integration

* Optional integration with the Google Gemini API.
* AI-generated informational health assessment remarks.
* Assessment based on age, glucose, haemoglobin and cholesterol values.
* Retry functionality for failed assessments.
* Assessment status tracking, including pending, failed and outdated states.
* The application continues to support patient management when the AI service is unavailable.

---

## 2. Technology Stack

| Component         | Technology            |
| ----------------- | --------------------- |
| Backend           | Python, Flask         |
| Frontend          | HTML, CSS, JavaScript |
| Database          | SQLite                |
| AI Integration    | Google Gemini API     |
| Charts            | Chart.js              |
| Form Security     | Flask-WTF, CSRF       |
| Testing           | Pytest                |
| Password Security | PBKDF2-SHA256         |

---

## 3. Project Structure

```text
CarePulse-Health-Prediction-App/
│
├── app.py
├── auth_utils.py
├── config.py
├── validation.py
├── utils.py
├── requirements.txt
├── pytest.ini
├── README.md
├── .gitignore
├── .env.example
│
├── database/
│   ├── db.py
│   └── schema.sql
│
├── routes/
│   ├── auth.py
│   ├── patients.py
│   └── admin.py
│
├── services/
│   ├── ai_service.py
│   └── patient_service.py
│
├── scripts/
│   ├── supplied_records.py
│   ├── validate_records.py
│   └── import_valid_records.py
│
├── templates/
├── static/
├── tests/
│
└── docs/
    ├── Evaluation_checklist.md
    └── Github_publishing.md
```

---

## 4. Requirements

* Python 3.10 or later.
* Windows, macOS or Linux.
* pip package manager.
* Google Gemini API key (optional, for AI assessments).

---

## 5. Installation on Windows

Open PowerShell and navigate to the downloaded or cloned project folder.

Create a virtual environment:

```powershell
py -m venv venv
```

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

Create your local environment configuration:

```powershell
Copy-Item .env.example .env
```

---

## 6. Database Initialization

Initialize the database using:

```powershell
python -m flask --app app init-db
```

The database initialization command creates missing tables without deleting existing data.

The local database is stored in:

```text
instance/health_app.db
```

The local database is excluded from GitHub using `.gitignore`.

---

## 7. Create the Administrator Account

Create the first administrator using:

```powershell
python -m flask --app app create-admin
```

The application prompts for:

* Administrator name
* Email address
* Password

The password is entered securely through the command line and is not stored in the source code.

---

## 8. Run the Application

Start the Flask application:

```powershell
python app.py
```

Open the following address in your browser:

http://127.0.0.1:5000

### User Login

Users can register through the Create an Account option and then sign in.

### Administrator Login

Open:

http://127.0.0.1:5000/admin/login

Regular user credentials cannot be used for administrator login.

---

## 9. Configure Google Gemini AI (Optional)

CarePulse supports optional AI-generated assessment remarks using the Google Gemini API.

To configure it:

1. Create an API key using Google AI Studio.
2. Open your local `.env` file.
3. Add your API key to the `GEMINI_API_KEY` setting.
4. Set the Gemini model using the `GEMINI_MODEL` setting.
5. Save the file and restart the application.

Example configuration:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.8-flash
SECRET_KEY=replace_with_a_secure_secret
SESSION_COOKIE_SECURE=false
```

**Never upload your actual `.env` file or API key to GitHub.**

The AI service receives only the relevant assessment information, such as age and the three blood test measurements. Patient names, email addresses and exact dates of birth are not sent.

The application handles AI service errors, including rate limits, temporary service unavailability and timeouts. Patient records can still be managed when AI assessment is unavailable.

AI-generated remarks are informational only and must not be treated as medical diagnoses.

---

## 10. Automated Testing

The application uses Pytest for automated testing.

Run all tests using:

```powershell
python -m pytest -v
```

Alternatively:

```powershell
python -m pytest -q
```

The test suite covers application functionality, including:

* Input validation.
* Patient CRUD operations.
* Database operations.
* Authentication and authorization.
* Duplicate detection.
* AI-related functionality and error handling.

Tests use a temporary database and mocked AI responses, so ordinary tests do not require a live Gemini API request.

One optional live-Gemini test may be skipped.

In a previous test run, the project completed with **79 passed and 1 skipped**. Results may vary after code changes.

---

## 11. Validate the Supplied Patient Records

The assignment provides ten patient records.

Run the validation script:

```powershell
python -m scripts.validate_records
```

The script checks the supplied records and reports whether each record is valid or invalid, including the reason for any validation failure.

The evaluation date used for the supplied records is 28/10/2026.

The invalid records are:

| Record | Patient     | Reason                                 |
| ------ | ----------- | -------------------------------------- |
| 2      | John Hunter | Invalid email address                  |
| 4      | Peter Larry | Impossible date: 31 November 2001      |
| 8      | Kris Wu     | Future date of birth and invalid email |

Record 6 is an exact duplicate of record 1.

### Import Valid Records

After creating a user account, import valid unique records using:

```powershell
python -m scripts.import_valid_records --owner-email you@example.com
```

Replace `you@example.com` with the email address of the user account that should own the imported records.

Expected first import:

* 6 valid unique records imported.
* 3 invalid records skipped.
* 1 duplicate record skipped.

The import script does not run automatically when the application starts.

---

## 12. Design Decisions

### Measurement Units

| Measurement | Unit  |
| ----------- | ----- |
| Glucose     | mg/dL |
| Haemoglobin | g/dL  |
| Cholesterol | mg/dL |

The application uses input validation limits to reject unreasonable or incorrectly entered numeric values. These limits are software validation rules, not medical diagnostic thresholds.

### Date Handling

* Dates are displayed in DD/MM/YYYY format.
* Dates are stored in ISO YYYY-MM-DD format.
* Impossible and future dates are rejected.

### Access Control

* Users can access their own patient records.
* Administrators have access to administrative patient management features.
* Unauthorized access to another user's records is restricted.
* Administrative actions are recorded in the audit log.

### Dashboard Statistics

* Dashboard statistics are calculated from database records.
* Recent Patients represents records added during the last seven days.
* Pending or Failed includes assessments that are not completed.
* Timestamps are stored and displayed in UTC.

---

## 13. Security Features

The application includes:

* Password hashing using PBKDF2-SHA256.
* CSRF protection.
* Session-based authentication.
* Role-based access control.
* Parameterized SQL queries.
* Escaped output.
* Content Security Policy.
* HTTP-only and SameSite cookie settings.
* Audit logging without storing secrets.
* Environment-based configuration.

For a real deployment, HTTPS should be enabled and:

```env
SESSION_COOKIE_SECURE=true
```

should be configured.

---

## 14. Known Limitations

* No login rate limiting or account lockout.
* No email verification.
* No password reset functionality.
* Audit history displays only the latest 200 entries.
* AI assessment is synchronous.
* Live Gemini API availability depends on the external service and account limits.
* The application has not undergone an independent security audit.
* The application is not intended for real clinical use.

---

## 15. Repository and Documentation

The project source code is available on GitHub:

https://github.com/kalyaniparsmshetty-dot/CarePulse-Health-Prediction-App

Supporting documentation is available in the `docs` folder:

* `Evaluation_checklist.md`
* `Github_publishing.md`

---

## 16. Conclusion

CarePulse demonstrates the development of a Python Flask web application that combines patient record management, database operations, input validation, duplicate detection, dashboard analytics, automated testing and external AI integration.

The project demonstrates practical application development skills using Python, Flask, SQLite, HTML, CSS, JavaScript and the Google Gemini API.

**CarePulse is developed as a learning and evaluation project to demonstrate Python programming, web application development, database management and AI integration.**
