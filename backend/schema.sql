-- Database schema (SQLite). Run automatically at startup by app/database.py.
-- All statements are idempotent ("IF NOT EXISTS"), so running them twice is safe.

-- People who may sign in. Passwords are stored only as salted scrypt hashes.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

-- Every successfully validated observation we collected (history).
-- The newest row for an indicator_key is what the dashboard shows.
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_key TEXT    NOT NULL,   -- e.g. 'gdp', 'ticker'
    payload_json  TEXT    NOT NULL,   -- validated data, stored as JSON text
    source_name   TEXT    NOT NULL,   -- who published the numbers
    source_url    TEXT    NOT NULL,
    as_of         TEXT    NOT NULL,   -- observation date/period reported by the source
    fetched_at    TEXT    NOT NULL    -- when WE downloaded it (UTC, ISO 8601)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_key_id ON snapshots (indicator_key, id DESC);

-- One row per indicator describing how the most recent refresh attempts went.
-- A non-empty last_error means the latest refresh failed, so the data shown is "stale".
CREATE TABLE IF NOT EXISTS fetch_status (
    indicator_key   TEXT PRIMARY KEY,
    last_attempt_at TEXT,
    last_success_at TEXT,
    last_error      TEXT
);
