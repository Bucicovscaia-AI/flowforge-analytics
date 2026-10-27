# FlowForge Analytics

An automation platform that turns a business CSV dataset into data-quality
checks, KPIs, charts and a downloadable report.

Built as the mini-project for PFD200 Professional Development (FdSc Computing).

> **Status:** Stage 1 of 10 (project scaffold). Features are added stage by
> stage; see [docs/development-log.md](docs/development-log.md).

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, Tailwind CSS, Recharts |
| Backend | Python 3, FastAPI, Pandas |
| Tests | pytest (backend) |
| Automation | Make.com webhook (planned, Stage 8) |

## Project structure

```
flowforge-analytics/
├── backend/            FastAPI app (app/) and pytest tests (tests/)
├── frontend/           React + Vite single-page app
├── sample-data/        Fabricated demonstration datasets
├── docs/               Plan, development log, architecture notes
└── .env.example        Example settings, no real secrets
```

## Running locally

Prerequisites: Python 3.11+ and Node.js 20+.

**Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

API docs are then at http://localhost:8000/docs.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The status pill shows whether the backend is reachable.

## Tests

```bash
cd backend
python -m pytest -v
```

## Data and privacy

Only synthetic data is used. No real personal or business data is processed
or sent to external services.
