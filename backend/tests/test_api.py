"""Backend tests. Run from the backend folder with:  pytest

Upstream websites are never contacted: we feed the parsers sample responses.
"""

import asyncio
import os
import tempfile

# Settings must be in place BEFORE the app is imported.
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ENABLE_COLLECTOR"] = "false"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123456"
os.environ["EVAL_USERNAME"] = "panel"
os.environ["EVAL_PASSWORD"] = "correct-horse-battery"
os.environ["FRONTEND_ORIGIN"] = "https://frontend.example.com"

import httpx
import pytest
from fastapi.testclient import TestClient

from app import collector, database
from app.main import app
from app.sources.nse import parse_nse_indices
from app.sources.worldbank import parse_worldbank_series
from app.validators import align_series_by_year, latest_value_with_change, to_number


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:  # "with" runs the startup code
        yield test_client


def login_and_get_headers(client) -> dict:
    response = client.post("/api/auth/login", json={"username": "panel", "password": "correct-horse-battery"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------- routes

def test_health_check_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_requires_login(client):
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/ticker").status_code == 401


def test_bad_token_is_rejected(client):
    response = client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_wrong_password_is_rejected(client):
    response = client.post("/api/auth/login", json={"username": "panel", "password": "wrong"})
    assert response.status_code == 401


def test_sql_injection_text_is_just_a_wrong_username(client):
    response = client.post("/api/auth/login", json={"username": "' OR 1=1 --", "password": "x"})
    assert response.status_code == 401


def test_dashboard_with_empty_database_is_pending_not_invented(client):
    headers = login_and_get_headers(client)
    body = client.get("/api/dashboard", headers=headers).json()
    assert set(body["indicators"]) == {"ticker", "gdp", "debt", "trade", "gst", "inflation", "expenditure"}
    assert body["indicators"]["gdp"]["status"] == "pending"
    assert body["indicators"]["gdp"]["data"] is None


def test_cors_only_allows_the_frontend_origin(client):
    allowed = client.get("/health", headers={"Origin": "https://frontend.example.com"})
    assert allowed.headers.get("access-control-allow-origin") == "https://frontend.example.com"
    blocked = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in blocked.headers


def test_failed_refresh_keeps_old_data_and_marks_it_stale(client):
    headers = login_and_get_headers(client)
    database.save_snapshot("gdp", {"years": [2023], "series": {"india": [8.1], "world": [3.0]}, "summary": {}},
                           "Test source", "https://example.com", "2023")
    assert client.get("/api/indicators/gdp", headers=headers).json()["status"] == "ok"

    database.record_failed_refresh("gdp", "TimeoutException: upstream too slow")
    body = client.get("/api/indicators/gdp", headers=headers).json()
    assert body["status"] == "stale"
    assert body["data"]["series"]["india"] == [8.1]  # old valid data is still there
    assert "TimeoutException" in body["last_error"]


def test_collector_records_failure_when_validation_fails(client):
    async def failing_builder(_client):
        raise ValueError("World Bank returned no observations")

    from app.indicators import INDICATORS
    original_builder = INDICATORS["debt"]["builder"]
    INDICATORS["debt"]["builder"] = failing_builder
    try:
        succeeded = asyncio.run(collector.refresh_indicator("debt", None))
    finally:
        INDICATORS["debt"]["builder"] = original_builder
    assert succeeded is False
    headers = login_and_get_headers(client)
    assert client.get("/api/indicators/debt", headers=headers).json()["status"] == "unavailable"


def test_unknown_indicator_is_404(client):
    headers = login_and_get_headers(client)
    assert client.get("/api/indicators/nope", headers=headers).status_code == 404


# ---------------------------------------------------------------- parsers

def test_parse_nse_indices_accepts_valid_rows_and_skips_bad_ones():
    sample_response = {
        "timestamp": "17-Oct-2026 15:30:00",
        "data": [
            {"index": "NIFTY 50", "last": 24500.5, "variation": 120.3, "percentChange": 0.49},
            {"index": "NIFTY BANK", "last": "52,100.10", "variation": -80, "percentChange": "-0.15"},
            {"index": "NIFTY IT", "last": None, "variation": 1, "percentChange": 1},  # invalid: skipped
        ],
    }
    payload, as_of_text = parse_nse_indices(sample_response)
    names = [item["name"] for item in payload["items"]]
    assert names == ["NIFTY 50", "NIFTY BANK"]
    assert payload["items"][1]["last"] == 52100.10
    assert as_of_text == "17-Oct-2026 15:30:00"


def test_parse_nse_indices_rejects_garbage():
    with pytest.raises(ValueError):
        parse_nse_indices({"unexpected": True})
    with pytest.raises(ValueError):
        parse_nse_indices({"data": []})


def test_parse_worldbank_skips_missing_years_and_rejects_errors():
    sample_response = [
        {"page": 1},
        [{"date": "2024", "value": None}, {"date": "2023", "value": 8.15}, {"date": "2022", "value": 7.0}],
    ]
    assert parse_worldbank_series(sample_response) == {2023: 8.15, 2022: 7.0}
    with pytest.raises(ValueError):
        parse_worldbank_series([{"message": [{"id": "120", "value": "Invalid value"}]}])
    with pytest.raises(ValueError):
        parse_worldbank_series([{"page": 1}, [{"date": "2024", "value": None}]])


def test_trade_builder_with_mocked_world_bank():
    from app.indicators import build_trade

    def fake_world_bank(request: httpx.Request) -> httpx.Response:
        if "NE.EXP.GNFS.CD" in str(request.url):
            rows = [{"date": "2023", "value": 8.0e11}, {"date": "2022", "value": 7.0e11}]
        else:
            rows = [{"date": "2023", "value": 9.0e11}]  # no 2022 import figure
        return httpx.Response(200, json=[{"page": 1}, rows])

    async def run_builder():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake_world_bank)) as mock_client:
            return await build_trade(mock_client)

    payload, as_of_text = asyncio.run(run_builder())
    assert as_of_text == "2023"
    assert payload["years"] == [2022, 2023]
    assert payload["series"]["balance"] == [None, -100.0]  # 2022 balance is NOT invented
    assert payload["series"]["imports"] == [None, 900.0]


# ---------------------------------------------------------------- helpers

def test_to_number_rejects_invalid_values():
    assert to_number("1,234.5") == 1234.5
    for bad_value in [None, "", "--", "abc", True, float("nan"), float("inf")]:
        assert to_number(bad_value) is None


def test_align_series_and_latest_change():
    years, values = align_series_by_year({"a": {2022: 1.0, 2023: 3.0}, "b": {2023: 2.0}})
    assert years == [2022, 2023]
    assert values == {"a": [1.0, 3.0], "b": [None, 2.0]}
    assert latest_value_with_change(years, values["a"], "difference")["change"] == 2.0
    assert latest_value_with_change(years, values["a"], "percent")["change"] == 200.0
    assert latest_value_with_change(years, values["b"], "difference") == {"value": 2.0, "change": None, "period": "2023"}
    assert latest_value_with_change([2022], [None], "difference")["value"] is None


def test_curated_csv_files_are_valid():
    from app.sources.curated import load_gst_collections, load_union_expenditure
    assert len(load_gst_collections()) >= 5
    totals, capitals = load_union_expenditure()
    assert all(capitals[year] <= totals[year] for year in totals)
