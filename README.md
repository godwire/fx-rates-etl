# fx-rates-etl

![CI](https://github.com/godwire/fx-rates-etl/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A small, complete **data pipeline + full-stack app**: a Python ETL pipeline
pulls daily foreign-exchange rates from a public API into a SQLite warehouse,
a FastAPI backend exposes that data as JSON, and a React frontend visualizes
it — built to demonstrate core data engineering fundamentals *and* how to
serve that data to a real client, in a project small enough to read
end-to-end in one sitting.

![Architecture](assets/architecture.svg)

## Why this project

Most portfolio pipelines stop at "call an API and print the result." This one
tries to look like a (very small) production system instead:

- **Idempotent loads** — re-running the pipeline for the same dates never creates duplicates (`INSERT OR REPLACE` keyed on `date, base, currency`)
- **Data quality gate** — data is validated *before* it's loaded, and a bad batch fails loudly instead of silently corrupting the warehouse
- **Separation of concerns** — extract / transform / validate / load each live in their own module and are independently testable
- **Multi-base** — pulls rates for several base currencies in one run (EUR, USD, GBP, JPY by default), not just a single fixed base
- **Decoupled frontend/backend** — FastAPI serves plain JSON over a versioned `/api/*` surface; the React app is just one possible client of it
- **Tested** — pipeline, quality checks, and the API are all covered by pytest with the network fully mocked
- **Automated** — GitHub Actions runs the Python test suite *and* builds the frontend on every push

## Project structure

```
fx-rates-etl/
├── src/
│   ├── extract.py          # talks to the Frankfurter API
│   ├── transform.py        # raw JSON -> tidy DataFrame
│   ├── quality_checks.py   # validation gate before load
│   ├── load.py              # idempotent upsert into SQLite
│   ├── db.py                 # connection + schema
│   ├── pipeline.py          # orchestration + CLI (multi-base)
│   └── api.py                # FastAPI backend (JSON over HTTP)
├── frontend/                 # React + Vite app
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js            # fetch wrappers around the FastAPI backend
│   │   └── components/
│   └── package.json
├── tests/                    # pytest, network fully mocked
├── .github/workflows/ci.yml  # Python tests + frontend build on push
├── data/                      # fx_rates.db lives here (gitignored)
└── assets/                    # README diagram
```

## Quickstart

You'll run two processes locally: the FastAPI backend and the React dev
server.

### 1. Backend (FastAPI)

```bash
git clone https://github.com/godwire/fx-rates-etl.git
cd fx-rates-etl

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn src.api:app --reload
```

On first request, the API bootstraps itself: it notices `data/fx_rates.db`
is empty and backfills the last 30 days automatically, so there's no manual
"load some data first" step. The API is now live at `http://localhost:8000`
(interactive docs at `http://localhost:8000/docs`, courtesy of FastAPI).

You can also drive the pipeline directly from the CLI, independent of the API:

```bash
python -m src.pipeline latest
python -m src.pipeline backfill --start 2024-01-01 --end 2024-01-31 --base EUR,USD --symbols GBP,JPY,CHF
```

### 2. Frontend (React + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. It talks to the API at `http://localhost:8000`
by default (see `frontend/.env.example` if you need to point it elsewhere).

### Running the tests

```bash
pytest -v
```

## Deploying (live demo links)

Two separate deploys: the backend (Python) and the frontend (static React
build). Both have generous free tiers.

**Backend — Render:**
1. Push the repo to GitHub.
2. On [render.com](https://render.com), create a **New Web Service** from this repo.
3. Runtime: Python 3. Build command: `pip install -r requirements.txt`. Start command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`.
4. Deploy. Render gives you a URL like `https://fx-rates-etl-api.onrender.com`.

**Frontend — Vercel:**
1. On [vercel.com](https://vercel.com), import this repo.
2. Set the project root to `frontend/`. Framework preset: Vite.
3. Add an environment variable `VITE_API_URL` pointing to your Render URL from above.
4. Deploy. Vercel gives you a URL like `https://fx-rates-etl.vercel.app`.

Add the resulting frontend URL to the top of this README (and to your GitHub
repo's "About" section) so anyone looking at the project can click straight
through to a working, live interface instead of just reading code.

> Free-tier note: Render's free web services spin down after inactivity and
> take ~30–60s to wake up on the first request — normal for a demo project,
> just don't be surprised by the first load being slow.

## Data source

Rates come from the [Frankfurter API](https://www.frankfurter.app), a free,
keyless API backed by European Central Bank reference rates. No API key or
signup is required, which keeps the project runnable by anyone who clones it.

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Liveness check |
| `/api/meta` | GET | Available bases/currencies in the warehouse, plus configured defaults |
| `/api/rates?base=EUR&currencies=USD,GBP&start=..&end=..` | GET | Rate rows matching the filters |
| `/api/refresh` | POST | Pull fresh "latest" rates for all default bases right now |

## Design notes

- **Why SQLite?** Zero setup, and the `fx_rates` table would map onto Postgres
  or a warehouse table without changes — this is meant to be a starting point,
  not a ceiling.
- **Why upsert instead of append-only?** Exchange rate providers occasionally
  revise a day's figures after publishing; upserting means a re-run always
  reflects the latest known-good value for that date.
- **Why validate before load, not after?** Catching bad data at the gate
  keeps the warehouse itself trustworthy — nothing downstream (the API, the
  frontend, future consumers) has to defend against malformed rows.
- **Why a separate API instead of querying SQLite straight from the frontend?**
  A browser can't open a SQLite file directly — and even if it could, keeping
  a real API boundary means the frontend, a future mobile app, or a data
  analyst with `curl` all get the same contract.

## Possible extensions

- Swap SQLite for Postgres and add a `docker-compose.yml`
- Add a `dbt` layer on top for further transformations
- Replace the GitHub Actions cron with a proper Airflow/Prefect DAG
- Add authentication to `/api/refresh` so it's not publicly triggerable
- Add more source currencies or a second data source (e.g. crypto rates) to
  practice merging multiple pipelines into one warehouse

## License

MIT — see [LICENSE](LICENSE).
