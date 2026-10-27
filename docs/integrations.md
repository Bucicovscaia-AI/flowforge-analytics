# Integrations

Both integrations are optional. Without them FlowForge still imports, cleans, analyses and reports on data, and uses its rule-based insights. Configuration lives only in the backend environment (`backend/.env` or real environment variables). Keys, webhook URLs and secrets are never sent to the browser or included in API responses; a test checks this.

## AI insights

### Configuration

```env
AI_PROVIDER=anthropic          # the provider currently implemented; used by default when a key is set
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

### Setting up a scenario

1. In Make.com, create a scenario whose first module is **Webhooks › Custom webhook**, and copy the webhook address.
2. Add it to the backend environment and restart:

   ```env
   MAKE_WEBHOOK_URL=https://hook.eu1.make.com/your-webhook-id
   MAKE_WEBHOOK_SECRET=a-long-random-string    # optional
   MAKE_TIMEOUT_SECONDS=10
   PUBLIC_BASE_URL=https://flowforge.example.com  # optional, adds report download links
   ```

3. Open **Automation**, choose **automation.test** and press **Send to Make.com**. Make.com uses the first request it receives to learn the data structure.
4. Add the modules you need after the webhook (email, Slack, Google Sheets and so on) and map fields from the payload.

The URL must use HTTPS. Redirects are not followed.

### When events are sent

- **Manually:** the **Send to Make.com** button on the Automation page or after generating a report.
- **By rule:** only if `AUTOMATION_TRIGGER_ON_REPORT=true`, in which case every newly generated report (other than a failed one) is sent once. The Automation page shows whether the rule is on.

Nothing else sends events. Every attempt, successful or not, is recorded in the delivery history with the payload, HTTP status, duration and a readable message.

### Payload

Use **Preview payload** on the Automation page to see the exact body for any event without sending it. A `report.generated` event looks like this (generated from the sample dataset):

```json
{
  "event": "report.generated",
  "event_id": "6beccfa52edc4a8f8a597ddd89e7a3c0",
  "occurred_at": "2026-10-27T21:04:20+00:00",
  "source": "flowforge-analytics",
  "schema_version": 1,
  "trigger": "manual",
  "status": "completed",
  "dataset": {
    "id": "e6e7ad2ed9a74e40acd5b67d37aa5c03",
    "name": "Retail orders (synthetic sample)",
    "is_sample": true,
    "record_count": 1198,
    "column_count": 10,
    "quality_score": 99.7
  },
  "report": {
    "id": "42a6f9825ac1425b81deb0d4db324ea3",
    "title": "Monthly review",
    "created_at": "2026-10-27T21:04:20+00:00",
    "status": "completed",
    "insight_mode": "rule_based",
    "formats": ["json", "html", "csv", "pdf"],
    "download_url": "https://flowforge.example.com/api/reports/42a6f9825ac1425b81deb0d4db324ea3/download?format=html"
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
  }
}
```

`download_url` is only present when `PUBLIC_BASE_URL` is set. `dataset.analysed` events carry `dataset` and `summary`; `automation.test` events carry only a message. No raw rows are included in any event.

### Verifying the signature

When `MAKE_WEBHOOK_SECRET` is set, each request has the header

```
X-FlowForge-Signature: sha256=<hex HMAC-SHA256 of the raw request body using the secret>
```

Compute the same HMAC over the received body and compare before trusting the request.

### Failure behaviour

Timeouts, connection errors and non-2xx responses are recorded as failed runs with an explanation and shown to the user. A failed automation never fails report generation. If the webhook is not configured, the send endpoint returns HTTP 409 with `automation_not_configured` and nothing is recorded.
