"""
Data quality layer.

A handful of cheap, high-signal checks that run after transform and before
load. The goal is to catch obviously broken data early rather than silently
loading garbage into the warehouse -- a small-scale stand-in for the kind
of checks a tool like Great Expectations or dbt tests would run in a bigger
pipeline.

`validate()` raises `DataQualityError` on the first failed check with a
message describing exactly what was wrong and how many rows were affected.
"""

from datetime import date

import pandas as pd

REQUIRED_COLUMNS = {"date", "base", "currency", "rate", "loaded_at"}


class DataQualityError(ValueError):
    """Raised when a DataFrame fails one of the quality checks."""


def validate(df: pd.DataFrame) -> None:
    """Run all checks against `df`, raising DataQualityError on the first failure."""
    _check_not_empty(df)
    _check_required_columns(df)
    _check_no_nulls(df)
    _check_rates_positive(df)
    _check_currency_codes(df)
    _check_dates_not_in_future(df)
    _check_no_duplicates(df)


def _check_not_empty(df: pd.DataFrame) -> None:
    if df.empty:
        raise DataQualityError("DataFrame is empty - nothing to load.")


def _check_required_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DataQualityError(f"Missing required columns: {sorted(missing)}")


def _check_no_nulls(df: pd.DataFrame) -> None:
    null_counts = df[list(REQUIRED_COLUMNS)].isnull().sum()
    bad = null_counts[null_counts > 0]
    if not bad.empty:
        raise DataQualityError(f"Null values found in columns: {bad.to_dict()}")


def _check_rates_positive(df: pd.DataFrame) -> None:
    bad_rows = df[df["rate"] <= 0]
    if not bad_rows.empty:
        raise DataQualityError(
            f"Found {len(bad_rows)} row(s) with a non-positive rate: "
            f"{bad_rows[['date', 'currency', 'rate']].to_dict('records')}"
        )


def _check_currency_codes(df: pd.DataFrame) -> None:
    invalid = df[~df["currency"].str.match(r"^[A-Z]{3}$")]
    if not invalid.empty:
        raise DataQualityError(
            f"Found {len(invalid)} row(s) with a malformed currency code: "
            f"{invalid['currency'].unique().tolist()}"
        )


def _check_dates_not_in_future(df: pd.DataFrame) -> None:
    today = date.today().isoformat()
    future_rows = df[df["date"] > today]
    if not future_rows.empty:
        raise DataQualityError(
            f"Found {len(future_rows)} row(s) dated in the future: "
            f"{future_rows['date'].unique().tolist()}"
        )


def _check_no_duplicates(df: pd.DataFrame) -> None:
    dupes = df[df.duplicated(subset=["date", "base", "currency"], keep=False)]
    if not dupes.empty:
        raise DataQualityError(
            f"Found {len(dupes)} duplicate (date, base, currency) row(s)."
        )
