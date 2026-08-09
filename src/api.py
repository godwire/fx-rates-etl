"""
FastAPI backend for the FX rates warehouse.

Thin read/write layer on top of the existing ETL pipeline: the pipeline
and SQLite warehouse are unchanged, this just exposes them over HTTP as
JSON so a separate frontend (React or anything else) can consume them.

Run locally with:
    uvicorn src.api:app --reload

Endpoints:
    GET  /api/health                                     liveness check
    GET  /api/meta                                        available bases/currencies
    GET  /api/rates?base=EUR&currencies=USD,GBP&start=..&end=..
    POST /api/refresh                                     pull latest rates now
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src import pipeline
from src.pipeline import DEFAULT_BASES, DEFAULT_SYMBOLS

DB_PATH = "data/fx_rates.db"
BACKFILL_DAYS = 30

app = FastAPI(title="FX Rates API", version="1.0.0")

# Wide open for a demo project. If you deploy this for real, replace "*"
# with your actual frontend origin (e.g. https://fx-rates-etl.vercel.app).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_needs_bootstrap(db_path: Optional[str] = None) -> bool:
    """True if the DB file doesn't exist yet, or the table is empty."""
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return True
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM fx_rates").fetchone()
        return count is None or count[0] == 0
    except sqlite3.OperationalError:
        return True  # table doesn't exist yet
    finally:
        conn.close()


def bootstrap_if_needed(db_path: Optional[str] = None) -> None:
    """First-run / fresh-deploy convenience: populate the DB if it's empty."""
    db_path = db_path or DB_PATH
    if db_needs_bootstrap(db_path):
        start = (date.today() - timedelta(days=BACKFILL_DAYS)).isoformat()
        end = date.today().isoformat()
        pipeline.run_backfill(start, end, DEFAULT_BASES, DEFAULT_SYMBOLS, db_path)


@app.on_event("startup")
def on_startup() -> None:
    bootstrap_if_needed()


def query_rates(
    base: Optional[str] = None,
    currencies: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """Query fx_rates with optional filters. Pure function, no FastAPI dependency."""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        sql = "SELECT date, base, currency, rate FROM fx_rates WHERE 1=1"
        params: list = []

        if base:
            sql += " AND base = ?"
            params.append(base.upper())
        if currencies:
            placeholders = ",".join("?" for _ in currencies)
            sql += f" AND currency IN ({placeholders})"
            params.extend(c.upper() for c in currencies)
        if start:
            sql += " AND date >= ?"
            params.append(start)
        if end:
            sql += " AND date <= ?"
            params.append(end)

        sql += " ORDER BY date"
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def query_meta(db_path: Optional[str] = None) -> dict:
    """Pure function returning available bases/currencies plus configured defaults."""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        bases = [r[0] for r in conn.execute("SELECT DISTINCT base FROM fx_rates ORDER BY base")]
        currencies = [
            r[0] for r in conn.execute("SELECT DISTINCT currency FROM fx_rates ORDER BY currency")
        ]
    except sqlite3.OperationalError:
        bases, currencies = [], []
    finally:
        conn.close()

    return {
        "bases": bases,
        "currencies": currencies,
        "default_bases": DEFAULT_BASES,
        "default_symbols": DEFAULT_SYMBOLS,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return query_meta()


@app.get("/api/rates")
def get_rates(
    base: str = Query(..., description="Base currency, e.g. EUR"),
    currencies: str = Query(..., description="Comma-separated target currencies, e.g. USD,GBP"),
    start: Optional[str] = Query(None, description="Start date, YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date, YYYY-MM-DD"),
):
    currency_list = [c.strip().upper() for c in currencies.split(",") if c.strip()]
    df = query_rates(base=base, currencies=currency_list, start=start, end=end)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data for the given parameters")

    return df.to_dict(orient="records")


@app.post("/api/refresh")
def refresh():
    written = pipeline.run_latest(DEFAULT_BASES, DEFAULT_SYMBOLS, DB_PATH)
    return {"rows_written": written}