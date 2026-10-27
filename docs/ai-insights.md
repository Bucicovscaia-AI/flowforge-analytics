# AI insights

The **AI Insights** page turns the calculated KPIs into written observations
and recommendations. It has two modes, and the interface, the PDF report and
the Make.com payload always say which one produced the text.

| Mode | When | Label |
| --- | --- | --- |
| **AI-generated** | `AI_API_KEY` is set and the API call succeeds | "AI-generated · *model name*" |
| **Rule-based** (deterministic fallback) | No key, or the call fails, times out, is rate-limited or refused | "Rule-based observations (not AI-generated)" plus the reason |

Rule-based text is never described as AI-generated.

Code: `backend/app/services/ai_insights.py` (AI) and
`backend/app/services/observations.py` (rules).

## What is sent to the AI service

Only an aggregated summary (`build_ai_summary`). The **AI Insights → View
exact payload** button and `GET /api/analyses/{id}/ai-payload` show the exact
JSON.

* Dataset name, synthetic flag, rows received and analysed
* Data-quality counts and the per-rule cleaning results
* KPI totals (revenue, orders, units, average order value, date range)
* Breakdown tables: monthly revenue, and the top 10 rows by category,
  region, channel, customer type and product
* KPIs that could not be calculated

Never sent: individual rows, order ids, the uploaded file, API keys or the
webhook URL.

## How the request is made

* Provider: Anthropic Claude API, via the official `anthropic` Python SDK.
* Model: `AI_MODEL` (default `claude-opus-5-5`).
* Structured output: `client.messages.parse(..., output_format=AIInsightResponse)`
  constrains the reply to a JSON schema (summary, 4–6 insights each with
  title / evidence / recommendation / kind, and caveats), validated with
  Pydantic before use.
* The system prompt requires every insight to quote figures from the summary,
  forbids invented figures, causes or benchmarks, and tells the model to treat
  synthetic data as a demonstration.
* Timeout `AI_TIMEOUT_SECONDS` (default 60 s), one SDK retry.

## Rule-based observations

Calculated from the KPIs with fixed thresholds, for example:

* Trend: first vs last month, and how many month-on-month changes were rises.
* Dips: any month-on-month fall of more than 5%.
* Partial month: the latest order is before the month's last day.
* Concentration: the largest category, region or channel; flagged as a risk at 40% or more of revenue.
* Average order value gap between regions above 10%.
* Best-selling product by revenue.
* Data quality: share of rows removed by cleaning.
* Each KPI that could not be calculated, and which column would unlock it.

## Enabling AI insights

1. Create an API key in the Anthropic Console.
2. Put it in `backend/.env` as `AI_API_KEY=...` (never in the frontend, never committed).
3. Restart the backend. Settings shows *AI insights: Configured*, and the
   AI Insights page button changes to **Generate AI insights**.

## Status of testing

* The fallback path, error handling (401, 429, 500, connection error, refusal)
  and the request shape are covered by `backend/tests/test_insights.py`. One
  test runs the real SDK against a mocked HTTP endpoint to check the
  structured-output request and response parsing.
* A live call to the Anthropic API was **not** made during development
  because no API key was available in the development environment.

## Limitations

* AI text can still be wrong. The page and the report tell readers to check
  the evidence against the KPI tables.
* Insights describe this dataset only; they are not compared with external
  benchmarks.
