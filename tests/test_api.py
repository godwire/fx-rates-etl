from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src import api, pipeline


def _fake_fetch_latest(base, symbols):
    return {
        "base": base,
        "date": "2024-01-02",
        "rates": {s: 1.0 + i * 0.1 for i, s in enumerate(symbols)},
    }


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Point the API at a temp DB pre-populated with a couple of bases."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(api, "DB_PATH", db_path)
    with patch("src.extract.fetch_latest", side_effect=_fake_fetch_latest):
        pipeline.run_latest(["EUR", "USD"], ["EUR", "USD", "GBP", "JPY"], db_path)
    return db_path


@pytest.fixture
def client(seeded_db):
    # seeded_db must run first: it patches api.DB_PATH and pre-populates the
    # DB, so that when the TestClient context manager fires the startup
    # event (which calls bootstrap_if_needed), it sees a non-empty DB and
    # skips making a real network call.
    with TestClient(api.app) as c:
        yield c


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_returns_bases_and_currencies(client):
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert set(body["bases"]) == {"EUR", "USD"}
    assert "default_bases" in body
    assert "default_symbols" in body


def test_rates_filters_by_base_and_currency(client):
    response = client.get("/api/rates", params={"base": "EUR", "currencies": "USD"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["base"] == "EUR"
    assert rows[0]["currency"] == "USD"


def test_rates_404_when_no_data(client):
    response = client.get("/api/rates", params={"base": "EUR", "currencies": "XXX"})
    assert response.status_code == 404


def test_refresh_calls_pipeline(client):
    with patch("src.extract.fetch_latest", side_effect=_fake_fetch_latest) as mock_fetch:
        response = client.post("/api/refresh")
    assert response.status_code == 200
    assert response.json()["rows_written"] > 0
    assert mock_fetch.called