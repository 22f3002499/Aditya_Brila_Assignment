"""Curated public data for indicators that have no free machine-readable API.

GST monthly collections and Union Budget expenditure are published by the Indian
government as press releases / PDF documents, not as a stable JSON API. We keep
the published annual figures in two small CSV files (backend/app/data/) and
validate them every time they are loaded.

The README tells the reader exactly where each number comes from. Update the CSV
files when new fiscal-year figures are published.
"""

import csv
from pathlib import Path

from ..validators import to_number

DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"


def read_csv_rows(file_name: str) -> list:
    with open(DATA_FOLDER / file_name, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def load_gst_collections() -> dict:
    """Return {fiscal_year: gross GST collection in Rs lakh crore}."""
    year_to_amount = {}
    for row in read_csv_rows("gst_collections.csv"):
        year = int(row["fiscal_year"])
        amount = to_number(row["gross_gst_collection_lakh_crore"])
        if amount is None or amount <= 0:
            raise ValueError(f"Invalid GST value for {year}")
        year_to_amount[year] = amount
    if not year_to_amount:
        raise ValueError("GST data file is empty")
    return year_to_amount


def load_union_expenditure() -> tuple:
    """Return ({year: total}, {year: capital}) in Rs lakh crore."""
    year_to_total = {}
    year_to_capital = {}
    for row in read_csv_rows("union_budget_expenditure.csv"):
        year = int(row["fiscal_year"])
        total = to_number(row["total_expenditure_lakh_crore"])
        capital = to_number(row["capital_expenditure_lakh_crore"])
        # Capital spending is a part of total spending, so it can never be larger.
        if total is None or capital is None or total <= 0 or capital < 0 or capital > total:
            raise ValueError(f"Invalid expenditure values for {year}")
        year_to_total[year] = total
        year_to_capital[year] = capital
    if not year_to_total:
        raise ValueError("Expenditure data file is empty")
    return year_to_total, year_to_capital
