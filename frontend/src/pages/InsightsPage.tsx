import { useState } from 'react'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Icon from '../components/ui/Icon'
import NoAnalysis from '../components/ui/NoAnalysis'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import SyntheticNotice from '../components/ui/SyntheticNotice'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { generateInsights, getAiPayload } from '../services/api'
import type { Insight } from '../types'
import { formatDateTime } from '../utils/format'

const SENT_FIELDS = ['KPI totals', 'Monthly revenue totals', 'Breakdown tables (top 10 rows each)', 'Data-quality counts']
const NEVER_SENT = ['Individual order rows', 'The original CSV file', 'Customer details', 'API keys or webhook URLs']

function InsightCard({ insight, ai }: { insight: Insight; ai: boolean }) {
  return (
    <Card>
      <div className="flex gap-4">
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${ai ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-600'}`}>
          <Icon name={ai ? 'sparkles' : 'analysis'} />
        </span>
        <div className="min-w-0">
          <h2 className="font-semibold text-slate-900">{insight.title}</h2>
          <p className="mt-2 text-sm text-slate-600">
            <span className="font-medium text-slate-900">Evidence: </span>
            {insight.evidence}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            <span className="font-medium text-slate-900">Recommendation: </span>
            {insight.recommendation}
          </p>
        </div>
      </div>
    </Card>
  )
}

export default function InsightsPage() {
  const { analysis, config, setInsights } = useAnalysis()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [payload, setPayload] = useState<string | null>(null)

  if (!analysis) {
    return (
      <>
        <PageHeader title="AI Insights" description="Evidence-based observations and recommendations from the calculated KPIs." />
        <NoAnalysis what="insights" />
      </>
    )
  }

  const aiConfigured = config?.ai.configured ?? false
  const result = analysis.insights
  const isAi = result?.source === 'ai'
  const items = result?.insights ?? analysis.observations

  async function run() {
    if (!analysis) return
    setBusy(true)
    try {
      const insights = await generateInsights(analysis.id)
      setInsights(insights)
      if (insights.source === 'ai') notify('success', 'AI insights generated', `Model: ${insights.model}`)
      else notify('info', 'Rule-based observations shown', insights.notice)
    } catch (error) {
      notify('error', 'Insights could not be generated', (error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function togglePayload() {
    if (payload || !analysis) {
      setPayload(null)
      return
    }
    try {
      setPayload(JSON.stringify(await getAiPayload(analysis.id), null, 2))
    } catch (error) {
      notify('error', 'Could not load the payload', (error as Error).message)
    }
  }

  return (
    <>
      <PageHeader
        title="AI Insights"
        description="Evidence-based observations and recommendations from the calculated KPIs."
        actions={
          <Button icon={aiConfigured ? 'sparkles' : 'refresh'} onClick={run} disabled={busy}>
            {busy ? 'Generating…' : aiConfigured ? 'Generate AI insights' : 'Refresh observations'}
          </Button>
        }
      />
      {analysis.dataset.synthetic && <SyntheticNotice fileName={analysis.dataset.file_name} />}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {isAi ? (
            <Alert variant="info" title={`AI-generated · ${result?.model}`}>
              {result?.notice} Generated {formatDateTime(result!.generated_at)}.
            </Alert>
          ) : (
            <Alert variant="warning" title="Rule-based observations (not AI-generated)">
              {result
                ? result.notice
                : `These observations are calculated by fixed rules from the KPIs, not by an AI model.${
                    aiConfigured ? ' Press "Generate AI insights" to request AI analysis.' : ' AI insights are unavailable because no AI API key is configured on the server (see Settings).'
                  }`}
            </Alert>
          )}

          {isAi && result?.summary && (
            <Card title="Summary">
              <p className="text-sm text-slate-700">{result.summary}</p>
            </Card>
          )}

          {busy ? (
            <Card>
              <div className="space-y-3" aria-hidden="true">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            </Card>
          ) : (
            items.map((insight) => <InsightCard key={insight.title} insight={insight} ai={isAi} />)
          )}

          {isAi && result!.caveats.length > 0 && (
            <Card title="Caveats from the AI response">
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
                {result!.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card title="AI service">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="text-slate-600">Status</span>
              {aiConfigured ? <StatusBadge variant="success">Configured</StatusBadge> : <StatusBadge variant="neutral">Not configured</StatusBadge>}
            </div>
            {aiConfigured && config?.ai.model && (
              <div className="mt-2 flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-600">Model</span>
                <span className="font-mono text-xs text-slate-900">{config.ai.model}</span>
              </div>
            )}
            <p className="mt-3 text-xs text-slate-500">
              If the AI service is not configured or fails, FlowForge shows rule-based observations instead and labels them as such.
            </p>
          </Card>

          <Card title="What is shared with the AI service">
            <p className="text-sm text-slate-600">Only an aggregated summary is sent. Raw rows never leave the server.</p>
            <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Sent</h3>
            <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
              {SENT_FIELDS.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <Icon name="check" className="h-4 w-4 text-emerald-600" />
                  {item}
                </li>
              ))}
            </ul>
            <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Never sent</h3>
            <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
              {NEVER_SENT.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <Icon name="close" className="h-4 w-4 text-rose-600" />
                  {item}
                </li>
              ))}
            </ul>
            <Button variant="secondary" className="mt-4 w-full" onClick={togglePayload}>
              {payload ? 'Hide exact payload' : 'View exact payload'}
            </Button>
            {payload && (
              <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100" tabIndex={0} aria-label="AI payload JSON">
                {payload}
              </pre>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
