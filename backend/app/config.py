"""Application settings.

Every setting comes from an environment variable so that no secret is ever
written into the source code. Each setting has a safe default for local work.
"""

import os
import secrets
from pathlib import Path

BACKEND_FOLDER = Path(__file__).resolve().parent.parent


def read_int_setting(name: str, default_value: int) -> int:
    """Read an integer environment variable, falling back to a default."""
    raw_value = os.environ.get(name, "").strip()
    if raw_value == "":
        return default_value
    try:
        return int(raw_value)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be a whole number, got '{raw_value}'")


class Settings:
    def __init__(self) -> None:
        # --- Security ---
        jwt_secret = os.environ.get("JWT_SECRET", "").strip()
        if len(jwt_secret) < 32:
            # No usable secret supplied: make a random one for this process only.
            # Tokens will stop working after a restart, which is safe for local work.
            print("WARNING: JWT_SECRET missing or shorter than 32 characters; using a temporary random secret.")
            jwt_secret = secrets.token_urlsafe(48)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = read_int_setting("JWT_EXPIRE_MINUTES", 60)

        # Comma-separated list of browser origins allowed to call this API (CORS).
        origins_text = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
        self.allowed_origins = [origin.strip().rstrip("/") for origin in origins_text.split(",") if origin.strip()]

        # Optional account that is created on startup for the interview panel.
        self.eval_username = os.environ.get("EVAL_USERNAME", "").strip()
        self.eval_password = os.environ.get("EVAL_PASSWORD", "")

        # --- Database ---
        self.database_path = os.environ.get("DATABASE_PATH", str(BACKEND_FOLDER / "data" / "dashboard.db"))

        # --- Collector ---
        self.enable_collector = os.environ.get("ENABLE_COLLECTOR", "true").lower() != "false"
        # Never hit NSE more often than every 30 seconds, whatever the setting says.
        self.ticker_refresh_seconds = max(30, read_int_setting("TICKER_REFRESH_SECONDS", 60))
        self.macro_refresh_hours = max(1, read_int_setting("MACRO_REFRESH_HOURS", 12))
        self.upstream_timeout_seconds = max(3, read_int_setting("UPSTREAM_TIMEOUT_SECONDS", 10))


settings = Settings()
