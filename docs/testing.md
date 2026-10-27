# Testing

All results below are from runs on 27 October 2026 in the development
container (Python 3.13.17, Node 22.22.0, npm 10.9.4, Chromium via
Playwright 1.63.0). Nothing here is estimated.

## How to run

```bash
# Backend: unit and API integration tests
cd backend && python -m pytest -v

# Frontend: lint, type-check, component tests, production build
cd frontend && npm run lint && npm run typecheck && npm test && npm run build

# Browser end-to-end test (backend running on :8000 and frontend built)
cd backend && uvicorn app.main:app --port 8000      # serves frontend/dist too
node scripts/e2e-smoke.mjs                          # from the repository root
SCREENSHOT_DIR=screenshots node scripts/e2e-smoke.mjs   # also refreshes screenshots
```

GitHub Actions (`.github/workflows/ci.yml`) runs all of these on every push
and pull request, and also builds the Docker image and checks it serves the
app.

## Results

| Suite | Command | Result |
| --- | --- | --- |
| Backend (pytest) | `python -m pytest` | **80 passed**, 0 failed |
| Frontend lint (oxlint) | `npm run lint` | 0 warnings, 0 errors |
| Frontend type-check (TypeScript strict) | `npm run typecheck` | 0 errors |
| Frontend tests (Vitest + Testing Library) | `npm test` | **38 passed** in 3 files, 0 failed |
| Production build (Vite) | `npm run build` | Succeeded, no warnings |
| Browser end-to-end (Playwright) | `node scripts/e2e-smoke.mjs` | **12 passed**, 0 failed |
| Docker image | `docker build .` | **Not verified locally**: Docker Hub returned HTTP 429 (rate limit) when pulling the base images. The CI `docker` job builds and smoke-tests it |
| Live Anthropic API call | – | **Not run**: no API key was available. Covered by mocked tests (see below) |
| Live Make.com delivery | – | **Not run**: no Make account or webhook URL was available. Covered by mocked tests |

## What is covered

Required scenario → where it is tested:

| Scenario | Tests |
| --- | --- |
| Valid CSV upload | `test_api.py::test_valid_upload_returns_full_analysis`, `test_csv_loader.py::test_valid_csv_is_loaded_as_text`, e2e "real CSV upload…" |
| Invalid file formats | `test_csv_loader.py::test_rejects_non_csv_extension` (4 cases), `…_disallowed_content_type`, `…_binary_content_with_csv_name`; `test_api.py::test_invalid_uploads_return_readable_errors`; Vitest `validateCsvFile`, upload page; e2e "rejects a non-CSV file" |
| Empty or malformed datasets | `test_csv_loader.py`: empty, whitespace-only, header without rows, malformed rows (3 cases: extra fields, uneven rows, unclosed quote), too many rows/columns, duplicate headers |
| Missing values | `test_cleaning.py::test_profile_counts_missing_values_per_column`, `…_rows_missing_required_values_are_removed`, `…_category_spelling_made_consistent_and_missing_filled`; `test_api.py::test_upload_reports_missing_values_and_duplicates` |
| Duplicate records | `test_cleaning.py::test_exact_duplicates_are_removed_keeping_first`, `…_profile_counts_duplicates_and_invalid_values`; `test_api.py::test_sample_datasets_are_listed_and_analysed` (15 duplicates in the sample) |
| KPI calculations | `test_kpis.py` (hand-checked totals: revenue £205, 4 orders, 9 units, AOV £51.25; breakdowns; monthly series; empty dataset) |
| Missing required columns | `test_csv_loader.py::test_reports_all_missing_required_columns`, `test_kpis.py::test_kpis_needing_missing_columns_are_reported_unavailable`, `…_missing_order_id_disables_order_kpis`; e2e "server rejects a CSV without the required columns" |
| Report generation | `test_api.py::test_report_generation_download_history_and_delete`, `…_report_pdf_contains_analysis_figures` (extracts the PDF text with pypdf); Vitest reports page; e2e "report is generated and the PDF downloads" |
| API error handling | `test_api.py`: 404s, 409 when Make is not configured, 413 oversize, 415/422 uploads, request validation, secrets never in `/api/config`, unknown `/api` routes stay 404 with the SPA mounted; Vitest `api.test.ts` |
| AI insights | `test_insights.py`: fallback without key (labelled), AI result labelled with model, refusal, 401/429/500/connection errors, real SDK request shape against a mocked HTTP endpoint, no rows in the payload |
| Make.com webhook | `test_webhook.py`: not configured, http refused, success with JSON + API-key header, 5xx retried once, 4xx not retried, timeout, host-only description, aggregate-only payload; `test_api.py::test_report_notifies_make_when_configured` |
| Interface | Vitest: every page renders, empty states, KPI values from a real backend fixture, upload success and server-error display, breakdown switcher, AI vs rule-based labels, report download link, history delete, settings status |
| Responsive layout | e2e: all seven pages at 390 px wide have no horizontal scrolling |

The frontend fixtures in `frontend/src/test/fixtures/` were produced by
running the real backend on a five-row CSV, so the component tests use
genuine API output.

## Problems found by testing and fixed

* **Malformed rows were silently accepted.** `pandas.read_csv` treated a row
  with extra fields as an index column instead of failing. Parsing was
  switched to Python's `csv` module in strict mode, which reports the line.
* **Phone layout scrolled sideways (759–869 px wide).** Tables inside grid
  cells stretched their cards, and screen-reader-only text inside table
  headers escaped the scroll container. Fixed with `min-w-0` on cards and a
  positioned table wrapper; the e2e test now checks every page.
* **The generator produced accidental duplicates** (the same product twice
  in one order), so the sample had 21 duplicates instead of the 15 injected.
  Orders now never repeat a product.
* **"Unknown" (the fill value from rule C8) was reported as the smallest
  channel.** Observations now ignore the placeholder group.
* **Chart animations** were captured half-drawn in screenshots and could
  leave bars empty after a resize; animations were turned off.
* **Bundle-size warning** from Vite: the chart library and React are now
  split into separate cacheable chunks.
