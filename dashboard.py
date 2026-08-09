"""
Streamlit dashboard for browsing the FX rates warehouse.

Run locally with:
    streamlit run dashboard.py

If data/fx_rates.db doesn't exist yet (e.g. on a fresh clone, or on a
fresh deploy to Streamlit Community Cloud where the filesystem is
ephemeral), the dashboard bootstraps itself on first load by running
the pipeline for the last 30 days -- no manual setup step required.
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from src import pipeline
from src.pipeline import DEFAULT_BASES, DEFAULT_SYMBOLS

DB_PATH = "data/fx_rates.db"
BACKFILL_DAYS = 30

st.set_page_config(page_title="FX Rates Dashboard", page_icon="💱", layout="wide")
st.title("💱 FX Rates Dashboard")
st.caption("Live data from a small ETL pipeline — see the code: fx-rates-etl on GitHub")


@st.cache_data(ttl=3600, show_spinner=False)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("SELECT * FROM fx_rates ORDER BY date", conn)
    finally:
        conn.close()


def bootstrap_if_needed() -> None:
    """First-run / fresh-deploy convenience: populate the DB if it's empty."""
    needs_bootstrap = True
    if Path(DB_PATH).exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            count = conn.execute("SELECT COUNT(*) FROM fx_rates").fetchone()
            needs_bootstrap = count is None or count[0] == 0
        except sqlite3.OperationalError:
            needs_bootstrap = True  # table doesn't exist yet
        finally:
            conn.close()

    if needs_bootstrap:
        with st.spinner("First run: loading the last 30 days of exchange rates..."):
            start = (date.today() - timedelta(days=BACKFILL_DAYS)).isoformat()
            end = date.today().isoformat()
            pipeline.run_backfill(start, end, DEFAULT_BASES, DEFAULT_SYMBOLS, DB_PATH)
        load_data.clear()


# --- Sidebar -----------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Fetch latest rates"):
        with st.spinner("Fetching latest rates..."):
            pipeline.run_latest(DEFAULT_BASES, DEFAULT_SYMBOLS, DB_PATH)
        load_data.clear()
        st.success("Updated.")

    st.caption(
        f"Bases: **{', '.join(DEFAULT_BASES)}** · "
        f"Tracked: {', '.join(DEFAULT_SYMBOLS)}"
    )

# --- Data ---------------------------------------------------------------
bootstrap_if_needed()
df = load_data()

if df.empty:
    st.info("The database is empty. Click **Fetch latest rates** in the sidebar.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    base = st.selectbox("Base currency", sorted(df["base"].unique()))
with col2:
    available = sorted(df.loc[df["base"] == base, "currency"].unique())
    currencies = st.multiselect(
        "Currencies", available, default=available[: min(3, len(available))]
    )

filtered = df[(df["base"] == base) & (df["currency"].isin(currencies))]

if filtered.empty:
    st.info("Pick at least one currency to see the chart.")
else:
    latest_date = filtered["date"].max()
    prev_dates = sorted(filtered["date"].unique())
    prev_date = prev_dates[-2] if len(prev_dates) > 1 else latest_date

    st.subheader(f"Latest rates ({latest_date})")
    metric_cols = st.columns(len(currencies))
    for col, currency in zip(metric_cols, currencies):
        latest_row = filtered[(filtered["date"] == latest_date) & (filtered["currency"] == currency)]
        prev_row = filtered[(filtered["date"] == prev_date) & (filtered["currency"] == currency)]
        if latest_row.empty:
            continue
        latest_rate = latest_row["rate"].iloc[0]
        delta = None
        if not prev_row.empty:
            delta = latest_rate - prev_row["rate"].iloc[0]
        col.metric(f"{base} → {currency}", f"{latest_rate:.4f}", f"{delta:+.4f}" if delta is not None else None)

    st.subheader("Trend")
    pivot = filtered.pivot(index="date", columns="currency", values="rate")
    st.line_chart(pivot)

with st.expander("Raw data"):
    st.dataframe(df, hide_index=True)