"""SQLite connection and schema management for the FX rates warehouse."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS fx_rates (
    date        TEXT NOT NULL,
    base        TEXT NOT NULL,
    currency    TEXT NOT NULL,
    rate        REAL NOT NULL,
    loaded_at   TEXT NOT NULL,
    PRIMARY KEY (date, base, currency)
);

CREATE INDEX IF NOT EXISTS idx_fx_rates_currency ON fx_rates (currency);
CREATE INDEX IF NOT EXISTS idx_fx_rates_date ON fx_rates (date);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection, creating the parent folder if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables/indexes if they don't already exist."""
    conn.executescript(SCHEMA)
    conn.commit()
