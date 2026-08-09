from datetime import date, timedelta

import pandas as pd
import pytest

from src.quality_checks import DataQualityError, validate


def _valid_df():
    return pd.DataFrame(
        [
            {
                "date": "2024-01-02",
                "base": "EUR",
                "currency": "USD",
                "rate": 1.09,
                "loaded_at": "2024-01-02T00:00:00+00:00",
            },
            {
                "date": "2024-01-02",
                "base": "EUR",
                "currency": "GBP",
                "rate": 0.87,
                "loaded_at": "2024-01-02T00:00:00+00:00",
            },
        ]
    )


def test_valid_dataframe_passes():
    validate(_valid_df())  # should not raise


def test_empty_dataframe_fails():
    with pytest.raises(DataQualityError, match="empty"):
        validate(pd.DataFrame(columns=["date", "base", "currency", "rate", "loaded_at"]))


def test_negative_rate_fails():
    df = _valid_df()
    df.loc[0, "rate"] = -1.0
    with pytest.raises(DataQualityError, match="non-positive"):
        validate(df)


def test_malformed_currency_code_fails():
    df = _valid_df()
    df.loc[0, "currency"] = "usd"  # lowercase, should be rejected
    with pytest.raises(DataQualityError, match="malformed currency"):
        validate(df)


def test_future_date_fails():
    df = _valid_df()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    df.loc[0, "date"] = tomorrow
    with pytest.raises(DataQualityError, match="future"):
        validate(df)


def test_duplicate_rows_fail():
    df = pd.concat([_valid_df(), _valid_df()], ignore_index=True)
    with pytest.raises(DataQualityError, match="duplicate"):
        validate(df)


def test_null_rate_fails():
    df = _valid_df()
    df.loc[0, "rate"] = None
    with pytest.raises(DataQualityError, match="Null values"):
        validate(df)
