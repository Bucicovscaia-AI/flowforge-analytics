# Architecture

FlowForge Analytics is a single-page React application backed by a FastAPI service. The browser only talks to the API; all data processing, storage and calls to external services happen on the server.

```
Browser (React + Vite)
   │  JSON over /api  (same origin in development via the Vite proxy,
   │                   or served together by FastAPI in production)
   ▼
FastAPI routes ── app/api/routes/*.py      request validation, HTTP concerns only
   │
Services ──────── app/services/*.py        orchestrate a use case: import, clean,
   │                                        analyse, insights, reports, automation
   ├── Engine ─── app/engine/*.py          pure pandas logic, no HTTP or storage
   ├── Reporting  app/reporting/*.py       HTML, PDF, CSV and JSON renderers
   ├── Storage ── app/storage/*.py         SQLite repositories + file stores
   └── Integrations app/integrations/*     AI provider, Make.com webhook client
```

## Project structure

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

## Backend layers

**Routes** (`app/api/routes`) declare endpoints, path and query validation and response models. They hold no business logic. Dataset and report ids are validated against a 32-character hex pattern before anything touches the disk.

**Services** (`app/services`) implement each use case. `container.py` builds them once per application, which lets tests inject a fake AI provider or webhook transport.

| Service | Responsibility |
| --- | --- |
| `DatasetService` | Import, profiling, column mapping, preview, quality, cleaning, analysis, chart data, exports |
| `InsightService` | Rule-based insights, optional AI insights, aggregated AI summary |
| `ReportService` | Builds a report snapshot and renders it to every format, report history |
| `AutomationService` | Builds webhook payloads, sends them on request or by rule, delivery history, signed PDF and confirmation links |

**Engine** (`app/engine`) is independent of FastAPI and storage, so it can be tested directly:

- `loading.py` decodes the upload (UTF-8 or Windows-1252), detects the delimiter, cleans header names and reads every cell as text. Nothing in the file is evaluated.
- `profiling.py` infers a semantic type per column (numeric, datetime, boolean, categorical, text, identifier, empty) using a 90% parse threshold, records the date format it chose and detects business roles (date, revenue, quantity, unit price, category, product, region, status) from column names. Users can override the roles.
- `quality.py` runs a registry of checks: missing values, duplicate rows and identifiers, invalid numbers, unreadable or future dates, inconsistent category spelling, negative and extreme values, revenue that does not equal quantity × unit price, and constant columns. The score is `100 × (1 − weighted affected cells ÷ total cells)` with weights error 1.0, warning 0.5 and information 0.
- `cleaning.py` is a registry of operations (remove duplicates, fill missing values with a constant, mean, median or most common value, drop rows with missing values, convert to numbers or ISO dates, normalise text, remove invalid rows, drop a column), each with a preview and an apply step. Operations that remove rows or columns require confirmation. Operations run on the working copy; the original upload is never modified.
- `analytics.py` calculates metrics (revenue is taken from a revenue column or, if there is none, calculated as quantity × unit price and labelled as such), breakdowns, time series (with partial-period flags), period comparison, a fitted trend, distributions and correlations.
- `insights.py` turns analysis results into rule-based insights labelled as fact, interpretation or suggestion.

## Storage

All persistent state lives under `DATA_DIR` (default `backend/data`):

```
data/
├── flowforge.db                 SQLite: datasets, dataset_operations, reports,
│                                automation_runs, activity
├── datasets/<id>/original.csv   the file exactly as uploaded
├── datasets/<id>/working.csv    the copy that cleaning operations change
└── reports/<id>/report.{html,pdf,csv,json}
```

Repositories in `app/storage/repositories.py` are the only code that issues SQL. File stores in `app/storage/files.py` build paths from validated ids, never from user-supplied names. Parsed datasets are cached in memory (keyed by file modification time and column mapping), so repeated chart requests do not re-read the CSV.

Reports are rendered once when generated and stored as files. A report therefore stays the same after its dataset is cleaned further or deleted. Deleting a dataset removes its files and cleaning history but keeps its reports. The display currency setting is stored in the browser only.

Data survives restarts only when `DATA_DIR` is on a persistent disk, which is not the case on Render's free plan (see [deployment.md](deployment.md)).

## Frontend

```
frontend/src/
├── api/           typed client for every endpoint, ApiError
├── context/       selected dataset, system status, toasts
├── hooks/         useApi (keyed loading), sample loading, local storage
├── components/
│   ├── layout/    sidebar, top bar, responsive shell
│   ├── ui/        buttons, cards, badges, fields, dialogs, tables, states
│   └── charts/    Recharts wrappers with table views and shared styling
└── pages/         one file per section
```

The selected dataset is shared through `AppContext`. When data changes (upload, cleaning, mapping), `notifyDataChanged` refreshes the dataset list and then increments a version number that every data-loading key includes, so each page reloads the affected results. Pages other than the dashboard are code-split and loaded on first visit.

## API

With the backend running, interactive OpenAPI documentation is at `/api/docs` and the schema at `/api/openapi.json`. Main endpoints:

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Health check |
| `GET /api/system/status` | Integration status and limits (no secrets) |
| `POST /api/datasets/upload`, `POST /api/datasets/sample` | Upload a CSV (multipart field `file`, optional `name`) or import the sample dataset |
| `GET /api/datasets`, `GET/PATCH/DELETE /api/datasets/{id}` | List, read, rename, delete |
| `PUT /api/datasets/{id}/column-mapping` | Override detected business columns |
| `GET /api/datasets/{id}/preview`, `GET /api/datasets/{id}/export.csv` | Preview rows, download the working copy |
| `GET /api/datasets/{id}/quality` | Quality report |
| `GET /api/cleaning/operations`, `POST /api/datasets/{id}/cleaning/preview` / `apply` / `reset` | Cleaning |
| `GET /api/datasets/{id}/analysis` | Full analysis |
| `GET /api/datasets/{id}/charts/aggregate`, `timeseries`, `distribution`, `aggregate.csv` | Chart data |
| `POST /api/datasets/{id}/insights` | Insights (`{"use_ai": false}` for rule-based only) |
| `POST /api/reports`, `GET /api/reports`, `GET/DELETE /api/reports/{id}` | Reports and history |
| `GET /api/reports/{id}/download?format=html\|pdf\|csv\|json` | Download a report |
| `GET /api/automation/status`, `POST /api/automation/preview`, `POST /api/automation/trigger`, `GET /api/automation/runs` | Make.com |
| `GET /api/automation/runs/{id}/report.pdf`, `POST /api/automation/runs/{id}/confirmation` | Signed links used by the Make.com scenario |

## Error handling

Every API error uses one shape:

```json
{ "error": { "code": "file_too_large", "message": "Readable explanation", "details": {} } }
```

The frontend shows `message` directly. Unexpected server errors are logged and returned as a generic 500 without internal details.
