# Fleet Compliance Portal

An internal web application shaped like what a commercial engine services
organization runs to track regulatory compliance across a managed engine fleet.
It records engines, service bulletins (SBs) and airworthiness directives (ADs),
per-engine compliance records, and shop visits.

Fictional company **Talon Engine Services**; fictional engine families `TF-9`
and `TF-7X`; fictional operators **Northwind Air** (NWA), **Cascadia Cargo**
(CCG) and **Commercial Engines** (CE). No real product names or customers.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2. SQLite by default (zero
  setup); Postgres via `docker compose` for a more production-like run.
- **Frontend:** React + TypeScript + Vite.

## Quick start

```bash
make dev          # backend on :8000 and frontend on :5173 (two processes)
```

Or run each side yourself:

```bash
# backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000

# frontend (separate shell)
cd frontend
npm install
npm run dev
```

The backend creates the SQLite schema and seeds demo data on first start. Open
<http://localhost:5173>. The frontend proxies `/api` to the backend.

### Postgres profile

```bash
docker compose up -d db
cd backend && . .venv/bin/activate
DATABASE_URL=postgresql+psycopg://compliance:compliance@localhost:5432/compliance \
  uvicorn app.main:app --reload --port 8000
```

## Pages

- **Engines** — fleet list with serial, family, operator, cycles/hours, position.
- **Engine detail** — overview, raw SB records logged against the engine, and
  shop visits for that engine.
- **Service Bulletins** — SB catalog with category, status, applicability and
  related AD.
- **Shop Visits** — induction/release records across the fleet.

## API

Base path `/api/v1`.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness. |
| GET | `/engines` | List engines (includes `overdueMandatoryCount`). |
| GET | `/engines/{id}` | Engine detail. |
| GET | `/engines/{id}/compliance` | Applicable SBs for an engine with compliance status and `overdue` flag. |
| GET | `/engines/{id}/sb-records` | Raw compliance records logged against an engine. |
| GET | `/engines/{id}/shop-visits` | Shop visits for an engine. |
| GET | `/service-bulletins?family=` | List SBs, optional family filter. |
| GET | `/service-bulletins/{id}` | SB detail. |
| GET | `/shop-visits` | List shop visits. |
| GET | `/shop-visits/{id}` | Shop visit detail. |
| POST | `/shop-visits/{id}/release` | Release a shop visit (`{"releasedBy": "..."}`). 409 with `detail.blockingSbs` while an active mandatory SB is overdue. |

Interactive docs at <http://localhost:8000/docs>.

## Tests

```bash
cd backend && . .venv/bin/activate && pytest -q     # backend
cd frontend && npm run build                        # frontend typecheck + build
cd frontend && npm run e2e                          # Playwright (starts its own backend on :8001 with a throw-away SQLite DB)
```

## Specs

The compliance view per engine and the mandatory-SB release gate are specified
in [`docs/tickets/CES-482-...`](docs/tickets/CES-482-engine-compliance-view-and-release-gate.md)
and [`docs/sdd/NO-196-...`](docs/sdd/NO-196-engine-compliance-view-and-release-gate.md).
