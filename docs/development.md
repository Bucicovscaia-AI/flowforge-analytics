# Development

The quick start is in the [README](../README.md#getting-started).

## Prerequisites

- Python 3.12 or newer (CI uses 3.13)
- Node.js 20.19+ or 22.12+ with npm (CI uses Node 22)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt     # includes pytest and Ruff
uvicorn app.main:create_app --factory --reload --port 8000

cd frontend
npm install
npm run dev
```

In development, Vite proxies `/api` to `http://127.0.0.1:8000`. Set `FLOWFORGE_API_URL` before `npm run dev` if the backend runs elsewhere. `npm run preview` serves a production build locally with the same proxy.

## Tests and checks

```bash
# Backend
cd backend
pytest
ruff check .
ruff format --check .

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test
```

Backend tests cover parsing and validation, every quality rule and cleaning operation, analytics checked against hand-calculated values, insights and AI fallback, report rendering in every format, webhook delivery and signed links, and the API end to end. AI and Make.com tests use fakes and never contact external services. Frontend tests cover formatting, file validation, the API client and interactive components.

GitHub Actions runs the backend checks, the frontend checks and production build, and a Docker build with a smoke test on every push to `main` and every pull request.

[`scripts/e2e_walkthrough.cjs`](../scripts/e2e_walkthrough.cjs) drives the built application in Chromium through the main workflow and refreshes the images in `screenshots/`. It needs Playwright with Chromium, a fresh backend on port 8000 and `npm run preview` running in `frontend/`.

## Sample data

[`sample-data/flowforge-retail-sample.csv`](../sample-data/flowforge-retail-sample.csv) contains 1,198 synthetic retail orders for 2025 (order id, date, product, category, quantity, unit price, revenue, region, channel, status). It does not describe a real business and is labelled as demonstration data in the interface and in webhook payloads (`is_sample: true`). It deliberately includes duplicated rows, unreadable dates, missing values and inconsistent region spelling so the quality checks have something to find. Regenerate it with `python scripts/generate_sample_data.py`.
