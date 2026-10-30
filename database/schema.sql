-- Schema is idempotent: it is safe to run on every start (nothing is dropped).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name        TEXT    NOT NULL,
    dob              TEXT    NOT NULL,            -- ISO YYYY-MM-DD
    email            TEXT    NOT NULL,
    glucose          REAL    NOT NULL,            -- mg/dL
    haemoglobin      REAL    NOT NULL,            -- g/dL
    cholesterol      REAL    NOT NULL,            -- mg/dL
    user_remarks     TEXT,                        -- typed by the user
    ai_remarks       TEXT,                        -- written by the AI only
    ai_status        TEXT    NOT NULL DEFAULT 'pending'
                     CHECK (ai_status IN ('pending','completed','failed','unavailable','outdated')),
    ai_assessed_at   TEXT,
    import_key       TEXT,                        -- only set by the safe import script
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_patients_owner ON patients(owner_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_import_key
    ON patients(owner_id, import_key) WHERE import_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS assessments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    requested_at   TEXT    NOT NULL,
    completed_at   TEXT,
    status         TEXT    NOT NULL,
    ai_remarks     TEXT,
    error_category TEXT
);
CREATE INDEX IF NOT EXISTS idx_assessments_patient ON assessments(patient_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT    NOT NULL,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    email_attempted TEXT,
    success         INTEGER NOT NULL DEFAULT 1,
    ip_address      TEXT,
    details         TEXT,                          -- short safe text, never secrets
    created_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
