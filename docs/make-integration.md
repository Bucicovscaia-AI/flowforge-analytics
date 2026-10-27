# Make.com webhook integration

When a report is generated (and the user ticks **Send a summary to the
Make.com workflow**), or when **Send** is pressed in Report History, the
backend sends a JSON summary of the report to a Make.com *custom webhook*.
A Make scenario can then post the KPIs to Slack or Teams, append a row to a
Google Sheet, or email the team.

Code: `backend/app/services/webhook.py`. Tests: `backend/tests/test_webhook.py`
(no network: an HTTP mock transport is used).

> **Status.** The integration code is complete and tested against a mocked
> HTTP endpoint. A live Make.com scenario has **not** been configured from
> this repository, because that needs a Make account and a webhook URL, which
> is a secret. The steps below are what remains to be done.

## Trigger

| Trigger | Endpoint | Event |
| --- | --- | --- |
| Report generated with "Send a summary" ticked | `POST /api/reports` with `"notify_make": true` | `report.generated` |
| Re-send an existing report (Report History → Send) | `POST /api/reports/{id}/notify` | `report.generated` |
| Connection test (Settings → Send test event) | `POST /api/integrations/make/test` | `test.ping` |

The webhook is only called when `MAKE_WEBHOOK_URL` is set on the server. The
browser never sees the URL.

## JSON payload (`report.generated`)

```json
{
  "event_id": "5b0f3c1e-6f0e-4d7a-9a55-0d6f7f2b8c11",
  "sent_at": "2026-10-27T16:10:42.120931+00:00",
  "source": "flowforge-analytics",
  "app_version": "1.0.0",
  "event": "report.generated",
  "report": {
    "id": "rpt_3f2a9c1d8e7b",
    "title": "Sales performance report: retail_sales_2026_synthetic.csv",
    "created_at": "2026-10-27T16:10:41.902114+00:00",
    "download_path": "/api/reports/rpt_3f2a9c1d8e7b/download"
  },
  "dataset": {
    "file_name": "retail_sales_2026_synthetic.csv",
    "synthetic": true,
    "rows_received": 1152,
    "rows_analysed": 1125,
    "data_quality_score": 97.66
  },
  "kpis": {
    "currency": "GBP",
    "total_revenue": 107833.46,
    "order_count": 834,
    "units_sold": 2518,
    "average_order_value": 129.3,
    "date_from": "2026-01-01",
    "date_to": "2026-06-30"
  },
  "top_category": { "name": "Electronics", "revenue": 51440.75, "orders": 239, "units": 551, "share_pct": 47.7, "average_order_value": 215.23 },
  "top_region": { "name": "West", "revenue": 29507.55, "orders": 227, "units": 676, "share_pct": 27.36, "average_order_value": 129.99 },
  "insight_source": "rule-based",
  "highlights": [
    "Monthly revenue grew over the period",
    "Electronics is the largest category",
    "West is the largest region",
    "Online is the largest channel",
    "Average order value differs by region"
  ]
}
```

The values above were produced by running the app on the bundled synthetic
sample; ids and timestamps are examples. Only aggregated figures are sent:
never individual rows, the uploaded file or credentials. `download_path` is
relative; the scenario adds the app's public address if it needs a link.

The `test.ping` event has the same envelope (`event_id`, `sent_at`, `source`,
`app_version`) plus `"event": "test.ping"` and a `message`.

## Configuring the scenario in Make

1. In Make, create a scenario and add **Webhooks → Custom webhook** as the
   first module. Click **Add**, name it (e.g. *FlowForge reports*), and
   optionally turn on **API key authentication** and create a key.
2. Copy the webhook address (`https://hook.<zone>.make.com/<id>`).
3. On the FlowForge server, set in `backend/.env` (or the host's environment):
   ```
   MAKE_WEBHOOK_URL=https://hook.eu1.make.com/your-webhook-id
   MAKE_WEBHOOK_API_KEY=the-key-from-step-1   # only if you enabled it
   ```
   Restart the backend. Settings now shows the webhook as *Configured*.
4. In Make, click **Run once**, then press **Send test event** in FlowForge
   Settings. Make learns the data structure from the payload.
5. Add a **Router** or **Filter** on `event = report.generated` and the
   action modules you want, for example:
   * **Slack → Create a message**: `New report: {{report.title}} — revenue £{{kpis.total_revenue}}, {{dataset.rows_analysed}} rows (quality {{dataset.data_quality_score}}%).`
   * **Google Sheets → Add a row** with `report.created_at`, `kpis.total_revenue`, `kpis.order_count`, `kpis.average_order_value`, `top_category.name`.
   If `dataset.synthetic` is true, include "synthetic data" in any message.
6. Turn the scenario **ON** (scheduling: *Immediately as data arrives*).

## Expected response

Make answers a custom webhook with **HTTP 200** and the body `Accepted` once
the payload is queued. If the scenario ends with a **Webhook response**
module, its status and body are returned instead; any 2xx counts as success.
FlowForge records the result on the report (`webhook.status = delivered`,
with the HTTP status) and shows it in Report History.

## Error handling

| Situation | What FlowForge does |
| --- | --- |
| `MAKE_WEBHOOK_URL` not set | The option is disabled in the UI; API returns **409** with an explanation |
| URL is not `https` | Refused before sending |
| Timeout (default 10 s, `MAKE_TIMEOUT_SECONDS`) or connection error | Retries once after 0.5 s, then records `failed` |
| HTTP 5xx | Retries once, then records `failed` |
| HTTP 4xx (e.g. 401 wrong API key, 410 webhook deleted/disabled) | Not retried; records `failed` with the status |
| Failure during report generation | The report is still created and downloadable; only the notification is marked `failed`, and a toast explains why. It can be re-sent from Report History |

Each event carries a unique `event_id`, so a scenario can ignore duplicates
if a retry delivers the same event twice.

## Security considerations

* **The webhook URL is a secret**: anyone with it can trigger the scenario.
  It is read from the environment, never sent to the browser (the API only
  reports the host name, e.g. `hook.eu1.make.com`), never logged and never
  committed. `.env` is in `.gitignore`; `.env.example` holds placeholders only.
* **API-key authentication**: enable it on the Make webhook and set
  `MAKE_WEBHOOK_API_KEY`; FlowForge sends it in the `x-make-apikey` header.
* **Data minimisation**: only aggregated KPIs and report metadata are sent.
* **Least privilege in Make**: give the scenario's Slack/Sheets connections
  access only to the channel or sheet they need.
* If the URL leaks, delete the webhook in Make, create a new one and update
  `MAKE_WEBHOOK_URL`.
