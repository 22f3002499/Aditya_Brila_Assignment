"""NSE India: live index values for the ticker.

Endpoint used: https://www.nseindia.com/api/allIndices  (public, no credentials).
NSE only answers requests that carry cookies from its home page, so we first
visit the home page (to receive cookies) and then call the API with them.

NOTE: SENSEX is a BSE index and is NOT published by NSE, so the ticker uses
NSE indices instead (documented in the README).
"""

from datetime import datetime

import httpx

from ..validators import to_number

NSE_HOME_URL = "https://www.nseindia.com"
NSE_INDICES_URL = "https://www.nseindia.com/api/allIndices"

# Index names exactly as NSE spells them, in the order they appear in the ticker.
TICKER_INDEX_NAMES = [
    "NIFTY 50",
    "NIFTY BANK",
    "NIFTY IT",
    "NIFTY NEXT 50",
    "NIFTY FIN SERVICE",
    "NIFTY AUTO",
    "NIFTY PHARMA",
    "NIFTY FMCG",
]

# NSE rejects requests that do not look like they come from a normal browser.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/live-market-indices",
}


def parse_nse_indices(response_body) -> tuple:
    """Validate NSE's JSON and return (ticker_payload, as_of_text).

    Raises ValueError if the structure is not what we expect, so that bad data
    is never stored. Individual bad rows are skipped, not repaired.
    """
    if not isinstance(response_body, dict) or not isinstance(response_body.get("data"), list):
        raise ValueError("NSE response has no 'data' list")

    rows_by_name = {}
    for row in response_body["data"]:
        if isinstance(row, dict) and isinstance(row.get("index"), str):
            rows_by_name[row["index"].strip().upper()] = row

    ticker_items = []
    for index_name in TICKER_INDEX_NAMES:
        row = rows_by_name.get(index_name)
        if row is None:
            continue
        last_price = to_number(row.get("last"))
        point_change = to_number(row.get("variation"))
        percent_change = to_number(row.get("percentChange"))
        # An index level must be a positive number; otherwise skip this row.
        if last_price is None or last_price <= 0 or percent_change is None:
            continue
        ticker_items.append(
            {
                "name": index_name,
                "last": round(last_price, 2),
                "change": round(point_change, 2) if point_change is not None else None,
                "percent_change": round(percent_change, 2),
            }
        )

    if not ticker_items:
        raise ValueError("NSE response contained no valid index rows")

    # NSE reports when the figures were produced, e.g. "17-Oct-2026 15:30:00".
    as_of_text = str(response_body.get("timestamp") or "").strip()
    if as_of_text == "":
        as_of_text = datetime.now().strftime("%d-%b-%Y %H:%M")
    return {"items": ticker_items}, as_of_text


async def fetch_nse_ticker(timeout_seconds: int) -> tuple:
    """Download and validate the ticker data. Raises on any failure."""
    async with httpx.AsyncClient(
        headers=BROWSER_HEADERS, timeout=timeout_seconds, follow_redirects=True
    ) as client:
        # Step 1: visit the home page so NSE gives us session cookies.
        await client.get(NSE_HOME_URL)
        # Step 2: call the data endpoint (the client re-sends the cookies automatically).
        response = await client.get(NSE_INDICES_URL)
        response.raise_for_status()
        return parse_nse_indices(response.json())
