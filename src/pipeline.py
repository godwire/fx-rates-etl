"""
Pipeline orchestration + CLI.

Wires extract -> transform -> validate -> load together and exposes a
small command-line interface so the pipeline can be run locally, from
cron, or from a scheduled GitHub Actions workflow.

Examples
--------
Fetch and load the latest available rates:
    python -m src.pipeline latest --base EUR --symbols USD,GBP,JPY

Backfill a date range (e.g. for an initial load):
    python -m src.pipeline backfill --start 2024-01-01 --end 2024-01-31 \\
        --base EUR --symbols USD,GBP,JPY
"""

import argparse
import logging
import sys

from src import extract, load, quality_checks, transform
from src.db import get_connection, init_db

DEFAULT_DB_PATH = "data/fx_rates.db"
DEFAULT_BASE = "EUR"
DEFAULT_SYMBOLS = ["USD", "GBP", "JPY", "CHF", "CZK"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def run_latest(base: str, symbols: list[str], db_path: str) -> int:
    logger.info("Running LATEST pipeline: base=%s symbols=%s", base, symbols)
    payload = extract.fetch_latest(base, symbols)
    return _transform_validate_load(payload, db_path)


def run_backfill(start: str, end: str, base: str, symbols: list[str], db_path: str) -> int:
    logger.info(
        "Running BACKFILL pipeline: %s..%s base=%s symbols=%s", start, end, base, symbols
    )
    payload = extract.fetch_range(start, end, base, symbols)
    return _transform_validate_load(payload, db_path)


def _transform_validate_load(payload: dict, db_path: str) -> int:
    df = transform.raw_to_dataframe(payload)
    logger.info("Transformed %d row(s)", len(df))

    quality_checks.validate(df)
    logger.info("Data quality checks passed")

    conn = get_connection(db_path)
    try:
        init_db(conn)
        written = load.upsert_rates(conn, df)
    finally:
        conn.close()

    logger.info("Pipeline complete: %d row(s) written to %s", written, db_path)
    return written


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FX rates ETL pipeline")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base currency, e.g. EUR")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated target currencies, e.g. USD,GBP,JPY",
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to the SQLite DB file")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    subparsers.add_parser("latest", help="Fetch and load the most recent rates")

    backfill_parser = subparsers.add_parser("backfill", help="Fetch and load a date range")
    backfill_parser.add_argument("--start", required=True, help="Start date, YYYY-MM-DD")
    backfill_parser.add_argument("--end", required=True, help="End date, YYYY-MM-DD")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    try:
        if args.mode == "latest":
            run_latest(args.base.upper(), symbols, args.db_path)
        elif args.mode == "backfill":
            run_backfill(args.start, args.end, args.base.upper(), symbols, args.db_path)
    except Exception:
        logger.exception("Pipeline failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
