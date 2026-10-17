"""Small helpers that check upstream data before we store or show it.

Rule used everywhere: if a value is missing or invalid we return None.
We never guess, fill in, or invent a number.
"""

import math
from typing import Optional


def to_number(raw_value) -> Optional[float]:
    """Turn an upstream value into a finite float, or None if it is unusable."""
    if raw_value is None or isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, str):
        cleaned_text = raw_value.replace(",", "").strip()
        if cleaned_text in ("", "-", "--"):
            return None
        try:
            raw_value = float(cleaned_text)
        except ValueError:
            return None
    if not isinstance(raw_value, (int, float)):
        return None
    number = float(raw_value)
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def align_series_by_year(series_by_name: dict, max_years: int = 10):
    """Combine several {year: value} maps into one list of years and equal-length value lists.

    Example input : {"india": {2022: 7.0, 2023: 8.2}, "world": {2023: 3.1}}
    Example output: ([2022, 2023], {"india": [7.0, 8.2], "world": [None, 3.1]})
    A year where a series has no value gets None (shown as "---" in the UI).
    """
    all_years = set()
    for year_to_value in series_by_name.values():
        all_years.update(year_to_value.keys())
    years_to_show = sorted(all_years)[-max_years:]

    aligned_values = {}
    for series_name, year_to_value in series_by_name.items():
        aligned_values[series_name] = [year_to_value.get(year) for year in years_to_show]
    return years_to_show, aligned_values


def latest_value_with_change(years: list, values: list, change_mode: str) -> dict:
    """Find the newest non-missing value and how much it changed from the one before.

    change_mode "difference" -> change in percentage points (new - old)
    change_mode "percent"    -> percentage growth ((new - old) / old * 100)
    """
    present_positions = [position for position, value in enumerate(values) if value is not None]
    if not present_positions:
        return {"value": None, "change": None, "period": None}

    newest_position = present_positions[-1]
    newest_value = values[newest_position]
    summary = {"value": round(newest_value, 2), "change": None, "period": str(years[newest_position])}

    if len(present_positions) >= 2:
        older_value = values[present_positions[-2]]
        if change_mode == "difference":
            summary["change"] = round(newest_value - older_value, 2)
        elif older_value != 0:
            summary["change"] = round((newest_value - older_value) / abs(older_value) * 100, 2)
    return summary
