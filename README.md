# FlowForge Analytics

**Turn a raw CSV export into clean data, clear KPIs, charts and a shareable PDF report, in minutes.**

![FlowForge Analytics dashboard](screenshots/06-dashboard.png)

## Overview

Small teams often receive sales and operations data as spreadsheet exports from different systems. Before anyone can trust a total, someone has to find duplicated rows, unreadable dates, misspelt categories and missing values, recalculate the same metrics and write them up again.

FlowForge Analytics makes that routine repeatable. It shows exactly what is wrong with a file and how it affects the numbers, fixes it without touching the original upload, and produces a report in which every figure comes from the data. Reports can be emailed automatically through Make.com.

**Live demo:** [flowforge-analytics.onrender.com](https://flowforge-analytics.onrender.com)

The demo runs on a free hosting plan: the first visit after a period of inactivity can take up to a minute, and uploaded data is cleared when the service restarts. It loads a synthetic sample dataset, so you can explore it straight away.

## Screenshots

| Data quality and cleaning | Visualisations |
| --- | --- |
| ![Data quality findings and cleaning operations](screenshots/04-quality.png) | ![Chart builder with trend and category charts](screenshots/08-visualisations.png) |
| **Insights** | **Generated report** |
| ![Insights labelled as fact, interpretation or suggestion](screenshots/09-insights.png) | ![Self-contained HTML report](screenshots/14-html-report.png) |

## Features

- **Import and validation:** CSV upload with automatic encoding and delimiter detection, clear rejection of malformed files, and column type and business-column detection.
- **Data quality:** checks for missing values, duplicates, invalid numbers and dates, inconsistent categories, outliers and revenue mismatches, with a transparent quality score.
- **Cleaning:** previewable operations such as removing duplicates, filling missing values, converting types and normalising text. The original file is always kept, and cleaning can be reset in one step.
- **Analysis:** revenue, transaction value, quantity and period-over-period comparison, breakdowns by category, product, region and status, column statistics and correlations.
- **Visualisations:** trend and category charts plus a chart builder, each with a table view and CSV download.
- **Insights:** rule-based insights that are always available, optionally extended by an AI provider using aggregated figures only.
- **Reports:** HTML, PDF, CSV and JSON reports with a full report history.
- **Automation:** Make.com webhook integration that emails report PDFs through signed, short-lived download links and records whether delivery was confirmed.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Recharts, React Router |
| Backend | Python, FastAPI, Pydantic, pandas, NumPy, ReportLab, httpx |
| Storage | SQLite and local file storage |
| Integrations | Make.com webhooks, optional AI provider for insights |
| Quality | pytest, Ruff, Vitest, Testing Library, ESLint |
| Delivery | Docker, Render, GitHub Actions |

## Architecture

```
React single-page app ──/api──▶ FastAPI
                                  ├── Services      import, cleaning, analysis, insights, reports, automation
                                  ├── Engine        pure pandas logic: loading, profiling, quality, cleaning, analytics
                                  ├── Reporting     HTML, PDF, CSV and JSON renderers
                                  ├── Storage       SQLite metadata, original and working copies of each dataset
                                  └── Integrations  Make.com webhook client, optional AI provider
```

The browser talks only to the API, and all processing, storage and external calls happen on the server. In production a single Docker image serves the built frontend and the API from one origin. More detail is in [docs/architecture.md](docs/architecture.md).

## Getting started

Requirements: Python 3.11+ and Node.js 20.19+ or 22.12+. No database server is needed.

```bash
git clone https://github.com/Bucicovscaia-AI/flowforge-analytics.git
cd flowforge-analytics

# Backend (http://127.0.0.1:8000, API docs at /api/docs)
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload --port 8000

# Frontend, in a second terminal (http://localhost:5173)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and choose **Load sample dataset** to try it with synthetic data. Every setting is optional; copy [`.env.example`](.env.example) to `backend/.env` to configure upload limits, the AI provider or Make.com.

Or run everything in one container:

```bash
docker build -t flowforge . && docker run -p 8000:8000 flowforge
```

## Documentation

- [Development guide](docs/development.md): configuration, tests, deployment and troubleshooting
- [Architecture](docs/architecture.md): backend layers, storage layout, frontend structure and API overview
- [Integrations](docs/integrations.md): AI insights and the Make.com report email workflow
- [Security and limitations](docs/security.md)

The sample dataset in [`sample-data/`](sample-data/) is synthetic and does not describe any real business.
