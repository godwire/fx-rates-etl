"""
Load layer.

Writes a tidy rates DataFrame into the `fx_rates` SQLite table using
INSERT OR REPLACE, keyed on (date, base, currency). This makes the load
idempotent: re-running the pipeline for a date range you already loaded
simply overwrites those rows with fresh values instead of creating
duplicates -- an important property for any pipeline that might be
re-run or backfilled.
"""

import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)


def upsert_rates(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """Upsert all rows of `df` into fx_rates. Returns the number of rows written."""
    rows = list(
        df[["date", "base", "currency", "rate", "loaded_at"]].itertuples(
            index=False, name=None
        )
    )
    conn.executemany(
        """
        INSERT OR REPLACE INTO fx_rates (date, base, currency, rate, loaded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    logger.info("Upserted %d row(s) into fx_rates", len(rows))
    return len(rows)
