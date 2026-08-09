"""
Transformation layer.

Converts the raw JSON returned by the Frankfurter API (either a single-day
response or a time-series response) into a tidy pandas DataFrame with one
row per (date, base, currency) observation:

    date        | base | currency | rate
    ------------+------+----------+------
    2024-01-02  | EUR  | USD      | 1.094
    2024-01-02  | EUR  | GBP      | 0.869

This "long" / tidy shape is what gets loaded into the warehouse table and
makes downstream querying and charting straightforward.
"""

from datetime import datetime, timezone

import pandas as pd


def raw_to_dataframe(payload: dict) -> pd.DataFrame:
    """
    Normalize a Frankfurter API response into a tidy DataFrame.

    Handles both response shapes:
      - single date:  {"base": "EUR", "date": "2024-01-02", "rates": {"USD": 1.09, ...}}
      - time series:  {"base": "EUR", "rates": {"2024-01-02": {"USD": 1.09, ...}, ...}}
    """
    base = payload["base"]
    rates = payload["rates"]

    if "date" in payload:
        # Single-day response: rates maps currency -> value directly.
        rows = [
            {"date": payload["date"], "base": base, "currency": currency, "rate": rate}
            for currency, rate in rates.items()
        ]
    else:
        # Time-series response: rates maps date -> {currency: value}.
        rows = [
            {"date": date, "base": base, "currency": currency, "rate": rate}
            for date, day_rates in rates.items()
            for currency, rate in day_rates.items()
        ]

    df = pd.DataFrame(rows, columns=["date", "base", "currency", "rate"])
    df["loaded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return df
