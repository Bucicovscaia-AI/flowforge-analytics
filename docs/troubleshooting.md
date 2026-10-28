# Troubleshooting and limitations

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

## Known limitations

- CSV only; Excel files must be exported to CSV first. Files are processed in memory, so the size limit should stay modest.
- Single-user, single-server design with no per-user data separation.
- Business columns are detected from English column names; other names need manual mapping.
- Ambiguous dates are interpreted day-first (for example `03/04/2025` is 3 April), and the chosen format is shown.
- Revenue is treated as a single currency; the currency symbol is only a display label.
- Trends are straight-line fits over past periods, not forecasts.
- One AI provider is implemented, and AI output is labelled but not automatically fact-checked.
- Reports are generated on request; there is no scheduling.
