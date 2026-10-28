# Integrations

Both integrations are optional. Without them FlowForge still imports, cleans, analyses and reports on data, and uses its rule-based insights. Configuration lives only in the backend environment (`backend/.env` or real environment variables). Keys, webhook URLs and secrets are never sent to the browser or included in API responses; a test checks this.

## AI insights

### Configuration

```env
AI_PROVIDER=anthropic          # the provider currently implemented; selected automatically when a key is set
AI_API_KEY=your-api-key
AI_MODEL=claude-opus-5-5       # any model id the provider offers to your key
AI_TIMEOUT_SECONDS=45
AI_MAX_OUTPUT_TOKENS=4000
```

Restart the backend after changing these values. **Settings** and **AI Insights** show whether a provider is active. Set `AI_PROVIDER=none` to switch AI off while keeping the key in the file.

### When the provider is called

Only when a user asks for it: by switching on **Use the AI provider** and pressing **Generate with AI** on the AI Insights page, or by switching on **Include AI insights** when generating a report. Opening a page never calls the provider, and changing the data does not repeat an earlier AI request.

### What is sent

`build_ai_summary` in `backend/app/services/insights.py` reduces the analysis to aggregated figures:

- column names and inferred types, and the detected business roles
- calculated metrics (totals, averages, counts, date range)
- grouped totals for up to 10 values per category, product, region and status column
- totals per time period (up to the last 36 periods), the period comparison and the fitted trend
- correlation coefficients
- the data quality score and the titles of up to 10 findings

Raw rows are never sent. Group labels (for example product or region names) are sent, so avoid the AI option if those values are confidential.

### How the response is used

The provider is asked for structured JSON matching a schema (`INSIGHT_SCHEMA` in `backend/app/integrations/ai/base.py`). The prompt tells it to use only figures from the summary, to label each insight as fact, interpretation or suggestion, and not to claim causes. Responses are length-limited and normalised before display, and each AI insight is labelled **AI-generated** next to the rule-based ones. The AI output is not independently fact-checked, so the interface asks users to verify figures on the Data Analysis page.

### Failure behaviour

Authentication errors, missing models, rate limits, timeouts, refusals, truncated or invalid responses are all caught. The user gets the rule-based insights with a notice explaining why AI insights are missing. Reports are still generated.

### Adding another provider

Implement the `InsightProvider` protocol in `backend/app/integrations/ai/base.py` (a `name` attribute and `generate(summary) -> dict`), raise `AIProviderError` for failures, and register it in `factory.py`.

## Make.com automation

FlowForge sends events to a Make.com **Custom webhook**. The main use is report delivery: a `report.generated` event carries the report's KPIs and a temporary signed link to its PDF, so a scenario can download the PDF, email it as a Gmail attachment, and tell FlowForge whether the email was sent.

```
FlowForge ──POST event──▶ Make.com webhook
                              │
                              ├─ HTTP: GET report.pdf (signed link, expires)  ──▶ FlowForge
                              ├─ Gmail: send email with the PDF attached
                              └─ HTTP: POST confirmation (signed link)        ──▶ FlowForge
```

The PDF is not embedded in the webhook body. Sending a link keeps events small, keeps report files out of Make.com execution logs and delivery history, and lets the scenario use a standard **HTTP › Get a file** module. Each link works for one event only and expires (60 minutes by default); its signature is the credential, so Make.com needs no login.

### Configuration

Set these in the backend environment (`backend/.env`, or the service's **Environment** tab on Render) and restart:

```env
MAKE_WEBHOOK_URL=https://hook.eu1.make.com/your-webhook-id   # required, HTTPS
MAKE_WEBHOOK_SECRET=a-long-random-string                     # optional, signs each request
MAKE_TIMEOUT_SECONDS=10
AUTOMATION_TRIGGER_ON_REPORT=false                           # true = send every new report automatically

PUBLIC_BASE_URL=https://flowforge.example.com   # address Make.com uses to reach FlowForge
REPORT_LINK_SECRET=another-long-random-string   # optional, keeps links valid across restarts
REPORT_LINK_TTL_MINUTES=60                      # 5 minutes to 7 days
```

- `PUBLIC_BASE_URL` is needed for links. On Render it can be left empty: Render sets `RENDER_EXTERNAL_URL` for every web service and FlowForge uses it. It must use HTTPS (plain HTTP is allowed only for `localhost`).
- Without `REPORT_LINK_SECRET`, a random key is created at start-up and links stop working after a restart. On hosts without a persistent disk (such as Render's free plan) the report files are deleted on restart anyway, so the secret only matters when `DATA_DIR` is persistent.

The **Automation** page shows whether the webhook is configured, whether PDF links are available (and why not), and how long they stay valid.

### When events are sent

- **Manually:** **Send to Make.com** on the Automation page or after generating a report.
- **By rule:** only if `AUTOMATION_TRIGGER_ON_REPORT=true`, in which case every newly generated report (other than a failed one) is sent once.

Sending the same report a second time asks for confirmation (the API returns HTTP 409 `already_sent` unless `resend` is true), unless the earlier attempt was not accepted or the scenario reported a failure. FlowForge does not retry automatically, so a webhook timeout never produces a duplicate email. Every event has a unique `event_id`; a scenario that needs strict de-duplication can store it in a Make.com data store and skip IDs it has seen.

### Payload (schema version 2)

Use **Preview payload** on the Automation page to see the exact body for any event; link signatures are replaced by `added-when-sent` in previews and by `redacted` in the delivery history. A `report.generated` event for the sample dataset:

```json
{
  "event": "report.generated",
  "event_id": "ce7e462e7f4f433dafad253c626c9b85",
  "occurred_at": "2026-10-28T10:39:47+00:00",
  "source": "flowforge-analytics",
  "schema_version": 2,
  "trigger": "manual",
  "status": "completed",
  "dataset": {
    "id": "56a23ce1c13d4e9bb3ab517d8f1b8298",
    "name": "Retail orders (synthetic sample)",
    "is_sample": true,
    "record_count": 1198,
    "column_count": 10,
    "quality_score": 99.7
  },
  "report": {
    "id": "111146153af54a7197ab3dd4bb8bb8d8",
    "title": "Monthly review",
    "created_at": "2026-10-28T10:39:47+00:00",
    "status": "completed",
    "insight_mode": "rule_based",
    "formats": ["json", "html", "csv", "pdf"],
    "pdf": {
      "available": true,
      "filename": "monthly-review.pdf",
      "content_type": "application/pdf",
      "size_bytes": 15194,
      "download_url": "https://flowforge.example.com/api/automation/runs/ce7e462e7f4f433dafad253c626c9b85/report.pdf?expires=1793187587&signature=…",
      "expires_at": "2026-10-28T11:39:47+00:00"
    }
  },
  "summary": {
    "records": 1198,
    "columns": 10,
    "total_revenue": 111516.87,
    "average_transaction_value": 93.09,
    "median_transaction_value": 46.76,
    "total_quantity": 2625.0,
    "categories": 5,
    "products": 20,
    "regions": 11,
    "date_range": { "start": "2025-01-01", "end": "2025-12-31" }
  },
  "kpis": [
    { "key": "records", "label": "Total records", "format": "integer", "display": "1,198", "value": 1198 },
    { "key": "total_revenue", "label": "Total revenue", "format": "currency", "display": "111,516.87", "value": 111516.87 },
    { "key": "date_range", "label": "Date range", "format": "date_range", "display": "2025-01-01 to 2025-12-31", "value": null, "start": "2025-01-01", "end": "2025-12-31" }
  ],
  "kpi_summary_html": "<ul><li><strong>Total records:</strong> 1,198</li>…</ul>",
  "delivery": {
    "confirmation_url": "https://flowforge.example.com/api/automation/runs/ce7e462e7f4f433dafad253c626c9b85/confirmation?expires=1793187587&signature=…",
    "expires_at": "2026-10-28T11:39:47+00:00"
  }
}
```

(`kpis` is shortened here; it lists every metric in `summary`.)

Field notes:

- `summary` holds the KPIs as numbers. Keys appear only when the analysis can calculate them: `records` and `columns` are always present; `total_revenue`, `average_transaction_value` and `median_transaction_value` need a revenue column (or quantity and unit price); `total_quantity` needs a quantity column; `categories`, `products` and `regions` are counts of distinct values; `date_range` needs a date column. Currency values have no currency symbol, because the dataset does not record one. Map KPI fields in Make.com with an `ifempty()` fallback.
- `kpis` has the same values with a label and display text, in report order. `kpi_summary_html` is that list as HTML, ready for an email body. Labels are HTML-escaped.
- For `report.generated`, `dataset` and the KPIs come from the report snapshot, so they match the PDF even if the dataset was cleaned or deleted afterwards. For `dataset.analysed`, they are calculated from the current data.
- `report.pdf.available` is `false`, with a `reason`, when the report has no PDF, the file is no longer stored, the PDF is over 20 MB, or no public address is configured.
- `delivery` is `null` when no public address is configured. `automation.test` events contain only the event fields, a message and `delivery`; no dataset or report data.

Version 2 replaced the earlier unsigned `report.download_url` with `report.pdf` and added `kpis`, `kpi_summary_html` and `delivery`. When the payload changes, open the scenario's webhook module, choose **Redetermine data structure** and send an event so Make.com learns the new fields.

### Signed links

| Link | Method | Purpose |
| --- | --- | --- |
| `report.pdf.download_url` | `GET` | Returns the PDF (`application/pdf`, `Content-Disposition: attachment`, `Cache-Control: no-store`) |
| `delivery.confirmation_url` | `POST` | Records the scenario's outcome. JSON body: `{"status": "sent" \| "failed", "message": "optional, up to 300 characters"}` |

Each link is signed with HMAC-SHA256 over its purpose, the event ID and the expiry time. A link for one event cannot be used for another, a PDF link cannot be used as a confirmation link, and changing the expiry breaks the signature. Responses: `403 link_invalid` for a wrong signature, `410 link_expired` after expiry, `404` if the report or its PDF has been deleted. The first PDF download is recorded and shown in the delivery history.

### Make.com scenario: email the report PDF

Modules, in order:

1. **Webhooks › Custom webhook.** Click **Redetermine data structure**, then send a report from FlowForge (one generated from the built-in sample dataset is ideal).
2. **Filter** between modules 1 and 2: `event` *Equal to* `report.generated` **and** `report.pdf.available` *Equal to (boolean)* `true`. Add a second route from module 1 if you also want to handle other events.
3. **HTTP › Get a file** (called **Download a file** in newer versions of the HTTP app)
   - URL: `{{1.report.pdf.download_url}}`
   - Evaluate all states as errors: **Yes**
   - No authentication: the link itself is the credential.
4. **Gmail › Send an email**
   - To: the recipient address (fixed in the scenario; FlowForge never sends addresses)
   - Subject: `FlowForge report: {{1.report.title}}`
   - Content (HTML):

     ```html
     <p>Hello,</p>
     <p>The report <strong>{{1.report.title}}</strong> for the dataset <strong>{{1.dataset.name}}</strong> is attached.</p>
     {{1.kpi_summary_html}}
     <p>Records analysed: {{1.dataset.record_count}} · Data quality score: {{1.dataset.quality_score}}/100</p>
     <p>Generated {{formatDate(1.report.created_at; "D MMM YYYY HH:mm")}} by FlowForge Analytics.</p>
     ```

     To pick individual figures instead, map for example `{{ifempty(1.summary.total_revenue; "n/a")}}`.
   - Attachments › Add item: File name `{{3.fileName}}` (or `{{1.report.pdf.filename}}`), Data `{{3.data}}`.
5. **HTTP › Make a request** (confirmation)
   - URL: `{{1.delivery.confirmation_url}}`, Method: `POST`, Body type: Raw, Content type: JSON
   - Request content: `{"status": "sent", "message": "Emailed to the finance team"}`
6. Error handling: right-click module 3 and module 4 › **Add error handler** › **HTTP › Make a request** to `{{1.delivery.confirmation_url}}` with body `{"status": "failed", "message": "PDF download failed"}` (or `"Email could not be sent"`), followed by the **Ignore** directive (or **Break** if you want Make.com to keep the execution for a manual retry within the link lifetime).

Optional logging: add **Google Sheets › Add a row** after module 4 with columns such as `{{1.event_id}}`, `{{1.occurred_at}}`, `{{1.dataset.name}}`, `{{1.report.title}}`, `{{1.summary.total_revenue}}`, `{{1.summary.records}}`, `{{1.dataset.quality_score}}`.

The delivery history on the Automation page then shows each step: **Accepted, not confirmed** (the webhook took the event), *PDF downloaded*, and **Confirmed by Make.com** or **Scenario failed** with the scenario's message. FlowForge never reports an email as delivered on the strength of the webhook's HTTP 200 alone.

### Testing without private data

- `automation.test` contains no dataset or report data. Its `delivery.confirmation_url` lets you check the confirmation step on its own.
- To test the full PDF email, load the built-in synthetic sample dataset (**Data Upload › Load sample dataset**), generate a report from it and send that report.

### Verifying the request signature

When `MAKE_WEBHOOK_SECRET` is set, each request has the header

```
X-FlowForge-Signature: sha256=<hex HMAC-SHA256 of the raw request body using the secret>
```

Compute the same HMAC over the received body and compare before trusting the request.

### Failure behaviour

Timeouts, connection errors and non-2xx responses are recorded as failed runs with an explanation and shown to the user. A failed or misconfigured automation never fails report generation. If the webhook is not configured, the send endpoint returns HTTP 409 with `automation_not_configured` and nothing is recorded. Server logs record the event type, event ID and outcome, never the webhook URL, link signatures or report content.

### Security notes and limitations

- FlowForge has no user accounts: anyone who can open the application can also download reports through the normal download endpoint. The signed links add no new exposure, and they keep working for Make.com if a login is added later.
- Signed links are stored with their signature removed, so the delivery history (which is visible to anyone using the app) cannot be used to download PDFs.
- On hosts without persistent storage, reports, links and delivery history disappear when the server restarts. Make.com downloads the PDF within seconds of the event, so this only affects scenarios that run much later (for example scheduled or retried executions). Use a persistent disk if that matters.
