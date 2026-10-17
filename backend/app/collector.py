"""Background collector: the only part of the system that talks to upstream sites.

Two loops run for as long as the API server runs:
  * ticker loop - NSE index values. Every TICKER_REFRESH_SECONDS while the market
                  is open, every 30 minutes otherwise, and it slows down after failures.
  * macro loop  - World Bank / curated indicators, every MACRO_REFRESH_HOURS.

Browsers never call these sites. They only read what we stored in the database.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from . import database
from .config import settings
from .indicators import INDICATORS, MACRO_KEYS

INDIA_TIME = timezone(timedelta(hours=5, minutes=30))
MARKET_CLOSED_REFRESH_SECONDS = 30 * 60
MAX_BACKOFF_SECONDS = 10 * 60
MACRO_RETRY_SECONDS = 15 * 60


def is_market_open() -> bool:
    """NSE trades Monday-Friday, 09:15-15:30 India time (holidays are not tracked)."""
    now_in_india = datetime.now(INDIA_TIME)
    if now_in_india.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    minutes_since_midnight = now_in_india.hour * 60 + now_in_india.minute
    return 9 * 60 + 15 <= minutes_since_midnight <= 15 * 60 + 30


def describe_error(error: Exception) -> str:
    """Short, safe description stored with a failed refresh."""
    return f"{type(error).__name__}: {error}"[:300]


async def refresh_indicator(indicator_key: str, client: httpx.AsyncClient) -> bool:
    """Fetch -> validate -> store one indicator. Returns True on success.

    If anything goes wrong we only record the error. The previous good snapshot
    stays in the database, so the dashboard can show it labelled as stale.
    """
    indicator = INDICATORS[indicator_key]
    try:
        payload, as_of_text = await indicator["builder"](client)
    except Exception as error:  # network error, timeout, bad JSON, failed validation...
        print(f"[collector] {indicator_key} refresh failed: {describe_error(error)}")
        database.record_failed_refresh(indicator_key, describe_error(error))
        return False

    database.save_snapshot(
        indicator_key, payload, indicator["source_name"], indicator["source_url"], as_of_text
    )
    print(f"[collector] {indicator_key} refreshed (as of {as_of_text})")
    return True


async def run_ticker_loop() -> None:
    consecutive_failures = 0
    while True:
        succeeded = await refresh_indicator("ticker", None)
        if succeeded:
            consecutive_failures = 0
            wait_seconds = (
                settings.ticker_refresh_seconds if is_market_open() else MARKET_CLOSED_REFRESH_SECONDS
            )
        else:
            # Back off: 2x, 4x, 8x ... the normal delay, up to 10 minutes.
            consecutive_failures += 1
            wait_seconds = min(settings.ticker_refresh_seconds * (2**consecutive_failures), MAX_BACKOFF_SECONDS)
        await asyncio.sleep(wait_seconds)


async def run_macro_loop() -> None:
    while True:
        all_succeeded = True
        async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
            for indicator_key in MACRO_KEYS:
                # Each indicator is independent: one failure must not block the others.
                if not await refresh_indicator(indicator_key, client):
                    all_succeeded = False
        wait_seconds = settings.macro_refresh_hours * 3600 if all_succeeded else MACRO_RETRY_SECONDS
        await asyncio.sleep(wait_seconds)
