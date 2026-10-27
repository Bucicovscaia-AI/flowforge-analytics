# Development log

This log records work actually carried out. Code was produced with the help
of an AI coding assistant (Claude), which should be declared on the
assessment cover sheet. Add your own notes on what you reviewed, ran,
changed and learned in each entry.

---

## 27 Oct 2026: Stage 1, environment and project structure

**Work completed**
* Checked the development environment: Node 22.22.0, npm 10.9.4, Python 3.13,
  Git 2.43.0; npm and PyPI were reachable.
* Read the PFD200 assessment brief and portfolio template to extract the
  requirements the project must evidence.
* Created a monorepo with `frontend/` (React + Vite + Tailwind) and
  `backend/` (FastAPI), plus `docs/`, `sample-data/`, `.gitignore` and
  `.env.example`.
* Added a `GET /api/health` endpoint and a frontend status indicator that
  calls it through a service layer.

**Technical decisions**: see `docs/project-plan.md`, section 4.

**Problems encountered and resolution**
* Installing the frontend test tools (Vitest, Testing Library) failed with an
  npm internal error (`Cannot read properties of null (reading 'edgesOut')`).
  Frontend tests are not needed until Stage 2, so the install was postponed
  rather than investigated now.
* The first pytest run printed a deprecation warning: FastAPI's test client
  now expects the `httpx2` package instead of `httpx`. Swapping the
  dependency in `requirements-dev.txt` removed the warning.

**Testing (actual results)**
* `python -m pytest -v` in `backend/`: 2 passed (health check returns 200,
  unknown route returns 404).
* `npm run build` in `frontend/`: build succeeded.
* `npx oxlint` in `frontend/`: no problems reported.
* Browser check with both servers running: status pill showed
  "Backend online (v0.1.0)" (screenshot captured).

**Skills developed**: project scaffolding, dependency management with pinned
versions, development proxies and CORS, environment-variable configuration.

**Evidence produced**: `evidence/stage1-frontend-backend-connected.png`,
pytest output, this log entry.

**Remaining limitations**: no GitHub remote yet; no frontend tests yet.

---

## 27 Oct 2026: Stage 2, dashboard interface

**Work completed**
* Built the application layout: dark sidebar, top bar with page title,
  "Demo data" badge and live API status, and a slide-in menu for mobile.
* Built reusable components: KPI card, card, page header, data table, status
  badge, alert, empty state, spinner, button, pipeline steps, and two chart
  components (line and ranked horizontal bar).
* Built the seven pages (Dashboard, Dataset Upload, Data Analysis, AI
  Insights, Reports, Report History, Settings) plus a "page not found" page.
* Created a fabricated sample dataset module. Every page that shows it carries
  a "Demonstration data" notice.
* Added browser-side CSV validation (file type, empty file, 5 MB limit) with
  readable error messages.
* Added data-security guidance to the Upload and Settings pages (the security
  awareness campaign for portfolio section 1.4).
* Planned how the lecturer can test the app from his device
  (`docs/project-plan.md`, section 6).

**Technical decisions**
* React Router for page navigation with one shared layout (`AppLayout`).
* Sample data kept in one file (`src/data/sampleData.js`) with KPIs derived
  from it, so it can be swapped for API results in Stage 5.
* Ranked horizontal bar charts instead of pie charts, because bar lengths are
  easier to compare. Chart colours come from a colour-blind-checked palette,
  and status badges use an icon and text as well as colour.
* Hosting plan: a single Render web service serving both the API and the
  built frontend.

**Problems encountered and resolution**
* Installing Vitest failed again with the same npm error as Stage 1. The npm
  debug log showed the crash inside npm's own dependency resolver
  (`@npmcli/arborist`, `#loadPeerSet`) while handling Vitest's optional peer
  dependencies, which pointed to a bug in npm 10. Running the install with a
  newer npm (`npx npm@11 install -D vitest`) worked. A clean `npm ci` with the
  normal npm 10 then succeeded from the lock file, so anyone running the
  project is not affected.
* Rendering pages in tests produced Recharts warnings that the chart size was
  0×0, because the test environment (jsdom) does not lay out pages. A test
  setup file gives charts a fixed size, which removed the warnings.
* The first dashboard screenshot caught the line chart mid-animation, with
  points not yet joined. Screenshots were retaken after waiting for the
  animation to finish.
* A review of the sample insight text found "revenue rose in 5 of 6 months",
  which was inaccurate (there are only 5 month-on-month changes and 4 were
  rises). It was corrected to "4 of the 5 month-on-month changes".

**Testing (actual results)**
* `npm test` (frontend): 3 test files, 21 tests passed.
* `python -m pytest -v` (backend): 2 passed.
* `npm run build`: succeeded. Vite warned that the JavaScript bundle is over
  500 kB, mostly because of the chart library. This is acceptable for now and
  is recorded as a limitation.
* `npx oxlint`: no problems.
* Browser check of every page with Playwright: no console errors. At 390 px
  (phone) width there is no horizontal page scrolling.

**Evidence produced**: `docs/evidence/stage2/` (11 screenshots),
`docs/stage-reports/stage-2.md`.

**Remaining limitations**: all figures are sample data; upload does not reach
the backend yet; download and report history are not functional yet.

## 27 Oct 2026: Full application (backend pipeline, connected frontend, tests, CI)

**What was built**
* Backend: strict CSV validation (`services/csv_loader.py`), data-quality
  profile and eight documented cleaning rules (`services/cleaning.py`), KPIs
  with per-KPI column checks (`services/kpis.py`), rule-based observations,
  optional AI insights through the Anthropic SDK with a labelled fallback,
  PDF reports with ReportLab, report history, and a Make.com webhook.
* Frontend: migrated to strict TypeScript. The hard-coded sample data was
  removed; every page now reads from the API. Report download, history
  delete and webhook test buttons work, and controls that need configuration
  are disabled with an explanation.
* Two seeded synthetic datasets with a generator script
  (`sample-data/generate_sample_data.py`).
* GitHub Actions workflow, Dockerfile, Playwright end-to-end script, README
  screenshots and docs (`docs/architecture.md`, `api.md`,
  `data-cleaning-rules.md`, `ai-insights.md`, `make-integration.md`,
  `testing.md`).

**Decisions**
* CSV parsing uses Python's `csv` module in strict mode rather than
  `pandas.read_csv`, because pandas silently accepted rows with extra fields.
* Only aggregated figures are sent to the AI service and to Make.com.
* Storage is JSON and PDF files on disk; a database was out of scope.
* FastAPI serves the built frontend, so the app runs as one web service.

**Problems found and fixed**: see `docs/testing.md`, "Problems found by
testing and fixed".

**Testing (actual results)**
* `python -m pytest`: 80 passed.
* `npm run lint`, `npm run typecheck`: no problems. `npm test`: 38 passed.
  `npm run build`: succeeded with no warnings.
* `node scripts/e2e-smoke.mjs`: 12 of 12 steps passed.
* Not run: live Anthropic call and live Make.com delivery (no credentials;
  covered by mocked tests), and a local Docker build (Docker Hub rate limit;
  the CI job builds it).

**Remaining limitations**: not deployed; single-user, file-based storage.
