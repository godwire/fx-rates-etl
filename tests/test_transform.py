from src import transform


def test_raw_to_dataframe_single_date():
    payload = {
        "base": "EUR",
        "date": "2024-01-02",
        "rates": {"USD": 1.09, "GBP": 0.87},
    }

    df = transform.raw_to_dataframe(payload)

    assert list(df.columns) == ["date", "base", "currency", "rate", "loaded_at"]
    assert len(df) == 2
    assert set(df["currency"]) == {"USD", "GBP"}
    assert (df["date"] == "2024-01-02").all()
    assert (df["base"] == "EUR").all()
    usd_rate = df.loc[df["currency"] == "USD", "rate"].iloc[0]
    assert usd_rate == 1.09


def test_raw_to_dataframe_time_series():
    payload = {
        "base": "EUR",
        "start_date": "2024-01-01",
        "end_date": "2024-01-02",
        "rates": {
            "2024-01-01": {"USD": 1.10, "GBP": 0.88},
            "2024-01-02": {"USD": 1.09, "GBP": 0.87},
        },
    }

    df = transform.raw_to_dataframe(payload)

    assert len(df) == 4
    assert set(df["date"]) == {"2024-01-01", "2024-01-02"}
    assert set(df["currency"]) == {"USD", "GBP"}
