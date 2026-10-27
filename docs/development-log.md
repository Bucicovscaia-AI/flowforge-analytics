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
