"""Describes every indicator and knows how to build its dashboard data.

Each builder returns:  (payload, as_of_text)
  payload    - the validated data the frontend draws (years, series, summary)
  as_of_text - the observation date/period of the newest figure
"""

import httpx

from .config import settings
from .sources.curated import load_gst_collections, load_union_expenditure
from .sources.nse import NSE_HOME_URL, fetch_nse_ticker
from .sources.worldbank import WORLD_BANK_SITE, fetch_worldbank_series
from .validators import align_series_by_year, latest_value_with_change

# The RBI's official medium-term CPI inflation target (policy constant, 4% with a +/-2% band).
RBI_INFLATION_TARGET = 4.0

ONE_BILLION = 1_000_000_000


def newest_year_label(years: list, prefix: str = "") -> str:
    return f"{prefix}{years[-1]}"


# ---------------------------------------------------------------- World Bank based

async def build_gdp(client: httpx.AsyncClient):
    india = await fetch_worldbank_series(client, "IND", "NY.GDP.MKTP.KD.ZG")
    world = await fetch_worldbank_series(client, "WLD", "NY.GDP.MKTP.KD.ZG")
    years, series = align_series_by_year({"india": india, "world": world})
    payload = {
        "years": years,
        "series": series,
        "summary": {
            "india": latest_value_with_change(years, series["india"], "difference"),
            "world": latest_value_with_change(years, series["world"], "difference"),
        },
    }
    return payload, newest_year_label(years)


async def build_debt(client: httpx.AsyncClient):
    india = await fetch_worldbank_series(client, "IND", "GC.DOD.TOTL.GD.ZS")
    usa = await fetch_worldbank_series(client, "USA", "GC.DOD.TOTL.GD.ZS")
    years, series = align_series_by_year({"india": india, "usa": usa})
    payload = {
        "years": years,
        "series": series,
        "summary": {
            "india": latest_value_with_change(years, series["india"], "difference"),
            "usa": latest_value_with_change(years, series["usa"], "difference"),
        },
    }
    return payload, newest_year_label(years)


async def build_trade(client: httpx.AsyncClient):
    exports_usd = await fetch_worldbank_series(client, "IND", "NE.EXP.GNFS.CD")
    imports_usd = await fetch_worldbank_series(client, "IND", "NE.IMP.GNFS.CD")

    # Convert US dollars to billions of dollars.
    exports = {year: round(value / ONE_BILLION, 1) for year, value in exports_usd.items()}
    imports = {year: round(value / ONE_BILLION, 1) for year, value in imports_usd.items()}

    # Trade balance = exports - imports, only for years where BOTH figures exist.
    balance = {}
    for year in exports:
        if year in imports:
            balance[year] = round(exports[year] - imports[year], 1)

    years, series = align_series_by_year({"exports": exports, "imports": imports, "balance": balance})
    payload = {
        "years": years,
        "series": series,
        "summary": {
            "exports": latest_value_with_change(years, series["exports"], "percent"),
            "imports": latest_value_with_change(years, series["imports"], "percent"),
        },
    }
    return payload, newest_year_label(years)


async def build_inflation(client: httpx.AsyncClient):
    india = await fetch_worldbank_series(client, "IND", "FP.CPI.TOTL.ZG")
    years, series = align_series_by_year({"india": india})
    payload = {
        "years": years,
        "series": series,
        "target": RBI_INFLATION_TARGET,
        "summary": {
            "rate": latest_value_with_change(years, series["india"], "difference"),
            "target": {"value": RBI_INFLATION_TARGET, "change": None, "period": "Target"},
        },
    }
    return payload, newest_year_label(years)


# ---------------------------------------------------------------- curated CSV based

async def build_gst(client: httpx.AsyncClient):
    year_to_total = load_gst_collections()
    # Monthly average = yearly total divided by 12 months.
    year_to_monthly_average = {year: round(total / 12, 2) for year, total in year_to_total.items()}
    years, series = align_series_by_year(
        {"collections": year_to_total, "monthly_average": year_to_monthly_average}
    )
    payload = {
        "years": years,
        "series": series,
        "summary": {
            "collections": latest_value_with_change(years, series["collections"], "percent"),
            "monthly_average": latest_value_with_change(years, series["monthly_average"], "percent"),
        },
    }
    return payload, newest_year_label(years, "FY")


async def build_expenditure(client: httpx.AsyncClient):
    year_to_total, year_to_capital = load_union_expenditure()
    # Revenue expenditure = total expenditure - capital expenditure.
    year_to_revenue = {year: round(year_to_total[year] - year_to_capital[year], 2) for year in year_to_total}
    years, series = align_series_by_year(
        {"total": year_to_total, "capital": year_to_capital, "revenue": year_to_revenue}
    )
    payload = {
        "years": years,
        "series": series,
        "summary": {
            "total": latest_value_with_change(years, series["total"], "percent"),
            "capital": latest_value_with_change(years, series["capital"], "percent"),
        },
    }
    return payload, newest_year_label(years, "FY")


async def build_ticker(client: httpx.AsyncClient):
    # The ticker uses its own client inside fetch_nse_ticker (it needs NSE cookies).
    return await fetch_nse_ticker(settings.upstream_timeout_seconds)


# ---------------------------------------------------------------- registry

HOUR = 3600

INDICATORS = {
    "ticker": {
        "title": "Market Ticker",
        "source_name": "NSE India (allIndices)",
        "source_url": NSE_HOME_URL,
        "is_nse": True,
        "stale_after_seconds": 3 * HOUR,
        "builder": build_ticker,
    },
    "gdp": {
        "title": "GDP Growth - India vs World",
        "source_name": "World Bank Open Data (NY.GDP.MKTP.KD.ZG)",
        "source_url": WORLD_BANK_SITE,
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_gdp,
    },
    "debt": {
        "title": "Debt to GDP Ratio - India",
        "source_name": "World Bank Open Data (GC.DOD.TOTL.GD.ZS)",
        "source_url": WORLD_BANK_SITE,
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_debt,
    },
    "trade": {
        "title": "Imports, Exports & Trade Balance",
        "source_name": "World Bank Open Data (NE.EXP.GNFS.CD, NE.IMP.GNFS.CD)",
        "source_url": WORLD_BANK_SITE,
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_trade,
    },
    "gst": {
        "title": "GST Tax Collection",
        "source_name": "Ministry of Finance / PIB press releases (curated CSV)",
        "source_url": "https://pib.gov.in",
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_gst,
    },
    "inflation": {
        "title": "Inflation - India",
        "source_name": "World Bank Open Data (FP.CPI.TOTL.ZG); RBI target is a policy constant",
        "source_url": WORLD_BANK_SITE,
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_inflation,
    },
    "expenditure": {
        "title": "Government Expenditure",
        "source_name": "Union Budget documents, Ministry of Finance (curated CSV)",
        "source_url": "https://www.indiabudget.gov.in",
        "is_nse": False,
        "stale_after_seconds": 48 * HOUR,
        "builder": build_expenditure,
    },
}

# Slow-moving indicators refreshed together on the macro schedule.
MACRO_KEYS = [key for key in INDICATORS if key != "ticker"]
