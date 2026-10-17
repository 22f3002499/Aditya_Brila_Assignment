"""Turns database rows into the JSON shape the frontend receives.

Status values sent to the browser:
  ok          - fresh data
  stale       - data exists, but the latest refresh failed or the data is too old
  unavailable - the collector tried and has no data at all
  pending     - the collector has not finished its first attempt yet ("loading")
"""

import json
from datetime import datetime, timezone

from . import database
from .indicators import INDICATORS


def seconds_since(iso_text: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso_text)).total_seconds()


def build_indicator_response(indicator_key: str) -> dict:
    indicator = INDICATORS[indicator_key]
    snapshot = database.get_latest_snapshot(indicator_key)
    fetch_status = database.get_fetch_status(indicator_key)
    last_error = fetch_status["last_error"] if fetch_status else None

    response = {
        "key": indicator_key,
        "title": indicator["title"],
        "status": "pending",
        "source": {
            "name": indicator["source_name"],
            "url": indicator["source_url"],
            "is_nse": indicator["is_nse"],
        },
        "as_of": None,
        "fetched_at": None,
        "last_error": last_error,
        "data": None,
    }

    if snapshot is None:
        # Never succeeded. If we already tried and failed, say "unavailable", else "pending".
        response["status"] = "unavailable" if fetch_status else "pending"
        return response

    response["data"] = json.loads(snapshot["payload_json"])
    response["as_of"] = snapshot["as_of"]
    response["fetched_at"] = snapshot["fetched_at"]
    response["source"]["name"] = snapshot["source_name"]
    response["source"]["url"] = snapshot["source_url"]

    data_is_too_old = seconds_since(snapshot["fetched_at"]) > indicator["stale_after_seconds"]
    refresh_failed = last_error is not None
    response["status"] = "stale" if (refresh_failed or data_is_too_old) else "ok"
    return response


def build_dashboard_response() -> dict:
    return {
        "generated_at": database.current_utc_text(),
        "indicators": {key: build_indicator_response(key) for key in INDICATORS},
    }
