"""
Extraction layer.

Pulls foreign-exchange rate data from the free, keyless Frankfurter API
(https://www.frankfurter.app), backed by European Central Bank reference rates.

Two entry points:
  - fetch_latest(base, symbols)                 -> single day of rates
  - fetch_range(start_date, end_date, base, sym) -> a time series of rates

Both return the raw parsed JSON as returned by the API; parsing into a
tabular shape happens in transform.py, so this module has exactly one
responsibility: talk to the network and hand back raw data.
"""

import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.frankfurter.app"
DEFAULT_TIMEOUT = 10  # seconds


class ExtractError(RuntimeError):
    """Raised when the upstream API can't be reached or returns bad data."""


def _get(url: str, params: dict) -> dict:
    logger.info("GET %s params=%s", url, params)
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExtractError(f"Request to Frankfurter API failed: {exc}") from exc

    payload = response.json()
    if "rates" not in payload:
        raise ExtractError(f"Unexpected API response shape: {payload}")
    return payload


def fetch_latest(base: str, symbols: list[str]) -> dict:
    """Fetch the most recent available exchange rates for `base` -> `symbols`."""
    url = f"{BASE_URL}/latest"
    params = {"from": base, "to": ",".join(symbols)}
    return _get(url, params)


def fetch_on_date(date: str, base: str, symbols: list[str]) -> dict:
    """Fetch exchange rates for a specific ISO date (YYYY-MM-DD)."""
    url = f"{BASE_URL}/{date}"
    params = {"from": base, "to": ",".join(symbols)}
    return _get(url, params)


def fetch_range(start_date: str, end_date: str, base: str, symbols: list[str]) -> dict:
    """Fetch a time series of exchange rates between two ISO dates (inclusive)."""
    url = f"{BASE_URL}/{start_date}..{end_date}"
    params = {"from": base, "to": ",".join(symbols)}
    return _get(url, params)
