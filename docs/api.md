# API reference

Base path: `/api`. All responses are JSON unless stated. Interactive
documentation (Swagger UI) is served by the running backend at
**`/docs`**, and the OpenAPI schema at `/openapi.json`.

## Errors

| Status | Meaning |
| --- | --- |
| 400 | Empty file or no data |
| 404 | Unknown sample, analysis or report |
| 409 | Integration not configured (Make.com) |
| 413 | File or row count over the limit |
| 415 | Not a CSV (extension, content type or binary content) |
| 422 | Malformed CSV, missing required columns, or invalid request body |
| 502 | Make.com rejected or did not accept the event |

Upload errors use a structured body so every problem can be shown:

```json
{ "detail": { "message": "Required columns are missing: quantity, unit_price. Found: order_id, order_date, amount.",
              "problems": ["Required columns are missing: quantity, unit_price. Found: order_id, order_date, amount."] } }
```

Other errors use `{"detail": "text"}`; request-validation errors use
FastAPI's list format.

## System

| Method & path | Description |
| --- | --- |
| `GET /api/health` | `{"status": "ok", "version": "1.0.0"}` |
| `GET /api/config` | Upload limits, required/optional columns, cleaning rules, and whether AI and Make.com are configured (`ai.configured`, `ai.model`, `webhook.configured`, `webhook.target_host`, `webhook.api_key_set`). Never contains secrets |
| `POST /api/integrations/make/test` | Sends a `test.ping` event. 200 with `{delivered, status_code, event_id, response, attempts}`; 409 if not configured; 502 if delivery failed |

## Datasets and analyses

| Method & path | Description |
| --- | --- |
| `GET /api/samples` | Synthetic sample datasets: `[{id, file, name, description, size_bytes, synthetic}]` |
| `POST /api/samples/{sample_id}/analyse` | Runs the full pipeline on a sample. **201** with an *Analysis* |
| `POST /api/datasets/upload` | `multipart/form-data` with `file` (CSV) and optional `synthetic` (`true`/`false`, default `true`). **201** with an *Analysis* |
| `GET /api/analyses` | Stored analyses, newest first (summary fields only) |
| `GET /api/analyses/{id}` | One *Analysis* |
| `GET /api/analyses/{id}/ai-payload` | Exactly what would be sent to the AI service |
| `POST /api/analyses/{id}/insights` | Generates insights and stores them on the analysis. Returns `{source: "ai" \| "rule-based", model, generated_at, summary, insights: [{title, evidence, recommendation, kind}], caveats, notice}` |

### Analysis object

```text
id                 "ana_" + 12 hex characters
created_at         ISO 8601 UTC
dataset            file_name, size_bytes, encoding, columns, original_columns,
                   renamed_columns, synthetic, sample_id
profile            rows, columns, duplicate_rows, missing_cells, completeness_pct,
                   column_profile[ {name, type, role, missing, missing_pct, invalid,
                   unique, examples} ]
quality            rows_received, rows_analysed, rows_removed, duplicate_rows,
                   missing_cells, completeness_pct, quality_score
cleaning_steps[]   {rule, description, rows_removed, cells_changed, detail}
kpis.summary       total_revenue, order_count, units_sold, average_order_value,
                   order_lines, average_units_per_order, currency, date_from, date_to
kpis.breakdowns    revenue_over_time[ {period, label, revenue, orders, units} ],
                   revenue_by_category / _region / _channel / _customer_type,
                   top_products: [ {name, revenue, orders, units, share_pct,
                   average_order_value} ]
kpis.unavailable[] {kpi, label, missing_columns}
observations[]     rule-based {kind, title, evidence, recommendation}
preview            {columns, rows}: first 25 cleaned rows
insights           null, or the latest insights result
```

Example:

```bash
curl -F "file=@sample-data/retail_sales_2026_synthetic.csv" -F "synthetic=true" \
     http://localhost:8000/api/datasets/upload
```

## Reports

| Method & path | Description |
| --- | --- |
| `POST /api/reports` | Body `{analysis_id, title?, include_insights?, notify_make?}` (title ≤ 120 chars). Builds and stores a PDF. **201** with a *Report* |
| `GET /api/reports` | Report history, newest first |
| `GET /api/reports/{id}/download` | The PDF (`application/pdf`, as an attachment) |
| `POST /api/reports/{id}/notify` | Sends the report summary to Make.com. 409 if not configured, 502 if it fails |
| `DELETE /api/reports/{id}` | Deletes the report and its PDF. **204** |

### Report object

```json
{
  "id": "rpt_174dd9b77842",
  "analysis_id": "ana_952cbc18f963",
  "title": "Sales performance report: retail_sales_2026_synthetic.csv",
  "dataset": "retail_sales_2026_synthetic.csv",
  "synthetic": true,
  "created_at": "2026-10-27T16:14:55.595541+00:00",
  "size_bytes": 10739,
  "insight_source": "rule-based",
  "total_revenue": 107833.46,
  "webhook": { "status": "not_configured" }
}
```

`webhook.status` is one of `not_configured`, `not_requested`, `delivered`
or `failed` (with `message` and `at`).
