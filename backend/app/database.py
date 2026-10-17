"""Database access (SQLite, plain parameterized SQL).

SECURITY NOTE: every query below passes user-controlled values through "?"
placeholders. We never build SQL text by joining strings with input.

SQLite is a file inside the API server. It has no network port, so it cannot
be reached from the internet - only the backend process can open the file.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import BACKEND_FOLDER, settings

# How many historical snapshots to keep per indicator (older rows are deleted).
SNAPSHOTS_TO_KEEP = 200


def current_utc_text() -> str:
    """Current time as an ISO 8601 UTC string, e.g. 2026-10-17T08:12:00+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_connection() -> sqlite3.Connection:
    """Open a new connection. Rows can be read like dictionaries."""
    database_file = Path(settings.database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_file, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables() -> None:
    """Create tables from schema.sql if they do not exist yet."""
    schema_text = (BACKEND_FOLDER / "schema.sql").read_text(encoding="utf-8")
    with open_connection() as connection:
        connection.executescript(schema_text)


def check_database_is_working() -> bool:
    """Used by the health-check route."""
    try:
        with open_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------- users

def find_user_by_username(username: str):
    with open_connection() as connection:
        return connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def create_or_update_user(username: str, password_hash: str) -> None:
    """Insert the user, or replace the password if the user already exists."""
    with open_connection() as connection:
        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing_user is None:
            connection.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, current_utc_text()),
            )
        else:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (password_hash, username),
            )


# ---------------------------------------------------------------- snapshots

def save_snapshot(indicator_key: str, payload: dict, source_name: str, source_url: str, as_of: str) -> None:
    """Store a validated observation and mark the refresh as successful."""
    now_text = current_utc_text()
    with open_connection() as connection:
        connection.execute(
            "INSERT INTO snapshots (indicator_key, payload_json, source_name, source_url, as_of, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (indicator_key, json.dumps(payload), source_name, source_url, as_of, now_text),
        )
        # Keep only the newest rows so the table cannot grow forever.
        connection.execute(
            "DELETE FROM snapshots WHERE indicator_key = ? AND id NOT IN "
            "(SELECT id FROM snapshots WHERE indicator_key = ? ORDER BY id DESC LIMIT ?)",
            (indicator_key, indicator_key, SNAPSHOTS_TO_KEEP),
        )
        connection.execute(
            "INSERT INTO fetch_status (indicator_key, last_attempt_at, last_success_at, last_error) "
            "VALUES (?, ?, ?, NULL) "
            "ON CONFLICT(indicator_key) DO UPDATE SET "
            "last_attempt_at = excluded.last_attempt_at, "
            "last_success_at = excluded.last_success_at, last_error = NULL",
            (indicator_key, now_text, now_text),
        )


def record_failed_refresh(indicator_key: str, error_message: str) -> None:
    """Remember that a refresh failed. The OLD snapshot is left untouched."""
    now_text = current_utc_text()
    with open_connection() as connection:
        connection.execute(
            "INSERT INTO fetch_status (indicator_key, last_attempt_at, last_success_at, last_error) "
            "VALUES (?, ?, NULL, ?) "
            "ON CONFLICT(indicator_key) DO UPDATE SET "
            "last_attempt_at = excluded.last_attempt_at, last_error = excluded.last_error",
            (indicator_key, now_text, error_message[:300]),
        )


def get_latest_snapshot(indicator_key: str):
    with open_connection() as connection:
        return connection.execute(
            "SELECT payload_json, source_name, source_url, as_of, fetched_at FROM snapshots "
            "WHERE indicator_key = ? ORDER BY id DESC LIMIT 1",
            (indicator_key,),
        ).fetchone()


def get_fetch_status(indicator_key: str):
    with open_connection() as connection:
        return connection.execute(
            "SELECT last_attempt_at, last_success_at, last_error FROM fetch_status WHERE indicator_key = ?",
            (indicator_key,),
        ).fetchone()
