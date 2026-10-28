# Development guide

How to configure, test, build and deploy FlowForge Analytics. The quick start is in the [README](../README.md#getting-started).

## Repository layout

```
backend/app/        FastAPI application: api, services, engine, reporting, storage, integrations
backend/tests/      pytest suite
frontend/src/       React application: api client, components, pages, hooks, context
sample-data/        synthetic demonstration dataset
scripts/            sample data generator and browser walkthrough
screenshots/        screenshots of the running application
docs/               project documentation
Dockerfile          single image serving the frontend and API
render.yaml         Render Blueprint for the hosted demo
```

## Configuration

All settings are read by the backend from environment variables or from `backend/.env` (or `.env` in the repository root). Real environment variables take precedence. Copy [`.env.example`](../.env.example) as a starting point; every value is optional.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATA_DIR` | `backend/data` | Database, datasets and reports (relative paths resolve from `backend/`) |
| `SAMPLE_DATA_PATH` | `sample-data/flowforge-retail-sample.csv` | Dataset used by **Load sample dataset** |
| `MAX_UPLOAD_MB` / `MAX_ROWS` / `MAX_COLUMNS` | `10` / `500000` / `200` | Upload limits |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Browser origins allowed to call the API directly |
| `FRONTEND_DIST_DIR` | empty | Path to `frontend/dist` to serve the built frontend from the backend |
| `STORAGE_PERSISTENT` | `true` | Set to `false` where the disk is wiped on restart; the app then warns users |
| `LOAD_SAMPLE_ON_STARTUP` | `false` | Import the sample dataset at start-up when there are no datasets |
| `PUBLIC_BASE_URL` | empty | Public address used for signed report links (falls back to Render's `RENDER_EXTERNAL_URL`) |
| `LOG_LEVEL` | `INFO` | Python log level |
| `AI_PROVIDER` | set automatically when a key is present | AI provider; `none` disables AI |
| `AI_API_KEY` | empty | Provider API key; AI insights are off without it |
| `AI_MODEL` | see `.env.example` | Model id |
| `AI_TIMEOUT_SECONDS` / `AI_MAX_OUTPUT_TOKENS` | `45` / `4000` | Provider request limits |
| `MAKE_WEBHOOK_URL` | empty | Make.com custom webhook address (HTTPS) |
| `MAKE_WEBHOOK_SECRET` | empty | Optional HMAC signing secret |
| `MAKE_TIMEOUT_SECONDS` | `10` | Webhook request timeout |
| `AUTOMATION_TRIGGER_ON_REPORT` | `false` | Send every newly generated report to Make.com |
| `REPORT_LINK_SECRET` | random per start | Key for signed PDF and confirmation links; set it to keep links valid across restarts |
| `REPORT_LINK_TTL_MINUTES` | `60` | Lifetime of signed links |

The frontend has one optional build-time variable, `VITE_API_BASE_URL` (default `/api`). Never put secrets in `VITE_` variables: they are compiled into the browser bundle. In development, Vite proxies `/api` to `http://127.0.0.1:8000`; set `FLOWFORGE_API_URL` before `npm run dev` if the backend runs elsewhere.

Integration setup is described in [integrations.md](integrations.md).

## Tests and checks

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
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

The sample dataset is reproducible with `python scripts/generate_sample_data.py`.

## Production build

```bash
cd frontend
npm ci
npm run build                  # type checks, then writes frontend/dist

cd ../backend
FRONTEND_DIST_DIR=../frontend/dist uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

The backend then serves the application at `/` and the API at `/api` from one origin. Run it behind an HTTPS reverse proxy, keep `DATA_DIR` on persistent storage and back it up.

### Docker and Render

The `Dockerfile` builds the frontend and serves it from the backend; it listens on `PORT` (default `8000`). `render.yaml` is a Render Blueprint that deploys this image as a free web service and redeploys on every push to `main`. To deploy your own copy, choose **New → Blueprint** in Render, select the repository and apply it, then add optional secrets such as `AI_API_KEY` or `MAKE_WEBHOOK_URL` under the service's **Environment** tab.

On Render's free plan the service sleeps after about 15 minutes without traffic and its disk is not persistent, so datasets and reports are cleared on every restart or redeploy. The Blueprint sets `STORAGE_PERSISTENT=false`, so the app tells users this, and `LOAD_SAMPLE_ON_STARTUP=true`, so the sample dataset is always available.

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| Top bar shows **API unreachable** | The backend is not running on port 8000, or `FLOWFORGE_API_URL` points elsewhere. |
| `Error loading ASGI app` | Run uvicorn from `backend/` with `app.main:create_app --factory`; there is no module-level `app`. |
| Upload rejected as too large | Raise `MAX_UPLOAD_MB` (and `MAX_ROWS` if needed) and restart the backend. |
| "The file appears to be binary" | The file is not plain text, for example an `.xlsx` renamed to `.csv`. Export it as CSV. |
| "The header has N columns but the data has M" | A row has extra delimiters or unbalanced quotes. Fix the row or re-export with quoting. |
| Revenue or dates missing from the analysis | Check the column mapping on Data Analysis and convert text columns with the cleaning operations. |
| AI option is disabled or falls back to rule-based | `AI_API_KEY` is missing or invalid, or the backend was not restarted. Settings and the insights notice show the reason. |
| **Send to Make.com** is disabled | `MAKE_WEBHOOK_URL` is missing or not HTTPS. The Automation page shows the problem. |
| PDF shows `?` for some characters | The built-in PDF fonts cover Western European characters only; use the HTML report instead. |
