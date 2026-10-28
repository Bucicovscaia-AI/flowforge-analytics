# Configuration

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

The frontend has one optional build-time variable, `VITE_API_BASE_URL` (default `/api`). Never put secrets in `VITE_` variables: they are compiled into the browser bundle.

Setup of the AI provider and Make.com is described in [integrations.md](integrations.md). Deployment-specific settings are in [deployment.md](deployment.md).

