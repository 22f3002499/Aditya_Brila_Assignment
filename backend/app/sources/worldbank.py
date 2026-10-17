"""World Bank Open Data (non-NSE public source).

NSE does not publish GDP, inflation, trade or debt figures, so those come from the
World Bank API: https://api.worldbank.org/v2/country/<code>/indicator/<indicator>
Each call returns a list: [paging_info, [ {date: "2023", value: 8.15}, ... ]].
"""

from datetime import datetime

import httpx

from ..validators import to_number

WORLD_BANK_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
WORLD_BANK_SITE = "https://data.worldbank.org"


def parse_worldbank_series(response_body) -> dict:
    """Validate a World Bank response and return {year: value}, skipping missing years."""
    # Error responses look like [{"message": [...]}] (one element), so check the shape.
    if not isinstance(response_body, list) or len(response_body) != 2:
        raise ValueError("World Bank response has an unexpected shape")

    rows = response_body[1] or []
    year_to_value = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            year = int(row.get("date"))
        except (TypeError, ValueError):
            continue  # not a plain year such as "2023"; ignore
        value = to_number(row.get("value"))
        if value is None:
            continue  # the World Bank has no figure for this year: leave it out
        year_to_value[year] = value

    if not year_to_value:
        raise ValueError("World Bank returned no observations")
    return year_to_value


async def fetch_worldbank_series(client: httpx.AsyncClient, country_code: str, indicator_code: str) -> dict:
    """Download one indicator for one country (e.g. IND, NY.GDP.MKTP.KD.ZG)."""
    this_year = datetime.now().year
    response = await client.get(
        WORLD_BANK_URL.format(country=country_code, indicator=indicator_code),
        params={"format": "json", "per_page": 100, "date": f"{this_year - 14}:{this_year}"},
    )
    response.raise_for_status()
    return parse_worldbank_series(response.json())
