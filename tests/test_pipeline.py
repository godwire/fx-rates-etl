from unittest.mock import patch

from src import pipeline


def _fake_fetch_latest(base, symbols):
    return {
        "base": base,
        "date": "2024-01-02",
        "rates": {s: 1.0 + i * 0.05 for i, s in enumerate(symbols)},
    }


def _fake_fetch_range(start, end, base, symbols):
    return {
        "base": base,
        "rates": {
            "2024-01-01": {s: 1.0 + i * 0.05 for i, s in enumerate(symbols)},
            "2024-01-02": {s: 1.01 + i * 0.05 for i, s in enumerate(symbols)},
        },
    }


@patch("src.extract.fetch_latest", side_effect=_fake_fetch_latest)
def test_run_latest_calls_fetch_once_per_base(mock_fetch, tmp_path):
    db_path = str(tmp_path / "test.db")
    bases = ["EUR", "USD"]
    symbols = ["EUR", "USD", "GBP", "JPY"]

    written = pipeline.run_latest(bases, symbols, db_path)

    assert mock_fetch.call_count == len(bases)
    assert written == len(bases) * (len(symbols) - 1)  # each base excludes itself


@patch("src.extract.fetch_latest", side_effect=_fake_fetch_latest)
def test_run_latest_excludes_base_from_its_own_symbols(mock_fetch, tmp_path):
    db_path = str(tmp_path / "test.db")
    pipeline.run_latest(["EUR", "USD"], ["EUR", "USD", "GBP"], db_path)

    for call in mock_fetch.call_args_list:
        base_arg, symbols_arg = call[0]
        assert base_arg not in symbols_arg


@patch("src.extract.fetch_latest", side_effect=_fake_fetch_latest)
def test_run_latest_writes_distinct_bases_to_db(mock_fetch, tmp_path):
    import sqlite3

    db_path = str(tmp_path / "test.db")
    bases = ["EUR", "USD", "GBP"]
    pipeline.run_latest(bases, ["EUR", "USD", "GBP", "JPY"], db_path)

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT DISTINCT base FROM fx_rates").fetchall()
    conn.close()

    assert {row[0] for row in rows} == set(bases)


@patch("src.extract.fetch_range", side_effect=_fake_fetch_range)
def test_run_backfill_calls_fetch_once_per_base(mock_fetch, tmp_path):
    db_path = str(tmp_path / "test.db")
    bases = ["EUR", "GBP"]

    written = pipeline.run_backfill("2024-01-01", "2024-01-02", bases, ["EUR", "GBP", "USD"], db_path)

    assert mock_fetch.call_count == len(bases)
    assert written == len(bases) * 2 * 2  # 2 bases * 2 dates * 2 target currencies each


def test_run_latest_skips_base_with_no_remaining_symbols(tmp_path):
    db_path = str(tmp_path / "test.db")
    # Only currency in the universe is the base itself -> nothing to fetch.
    with patch("src.extract.fetch_latest") as mock_fetch:
        written = pipeline.run_latest(["EUR"], ["EUR"], db_path)

    mock_fetch.assert_not_called()
    assert written == 0