import { Bot, Calculator, FileText, Lightbulb, RefreshCw, ShieldAlert, Sparkles } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/client'
import type { DatasetSummary, Insight } from '../api/types'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { RequireDataset } from '../components/RequireDataset'
import { Alert } from '../components/ui/Alert'
import { Badge, type BadgeTone } from '../components/ui/Badge'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Toggle } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, LoadingState } from '../components/ui/States'
import { useApp } from '../context/AppContext'
import { useApi } from '../hooks/useApi'
import { formatDateTime } from '../lib/format'

const KIND: Record<Insight['kind'], { label: string; tone: BadgeTone; help: string }> = {
  fact: { label: 'Fact', tone: 'success', help: 'Calculated directly from the data' },
  interpretation: { label: 'Interpretation', tone: 'info', help: 'A reading of the facts that may not be the only explanation' },
  suggestion: { label: 'Suggestion', tone: 'violet', help: 'A possible next step to consider' },
}

function InsightCard({ insight, showSource }: { insight: Insight; showSource: boolean }) {
  const kind = KIND[insight.kind]
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span title={kind.help}>
          <Badge tone={kind.tone}>{kind.label}</Badge>
        </span>
        {showSource && (
          <Badge tone={insight.source === 'ai' ? 'brand' : 'neutral'}>
            {insight.source === 'ai' ? <Bot className="size-3" aria-hidden /> : <Calculator className="size-3" aria-hidden />}
            {insight.source === 'ai' ? 'AI-generated' : 'Rule-based'}
          </Badge>
        )}
      </div>
      <h3 className="mt-2 text-sm font-semibold text-slate-900">{insight.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-slate-700">{insight.statement}</p>
      {insight.evidence.length > 0 && (
        <dl className="mt-3 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
          {insight.evidence.map((item) => (
            <div key={`${item.label}-${item.value}`} className="flex justify-between gap-2 border-b border-dashed border-slate-100 py-1">
              <dt className="text-slate-500">{item.label}</dt>
              <dd className="text-right font-medium tabular-nums text-slate-800">{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {insight.caveat && <p className="mt-2 text-xs text-slate-500">Caveat: {insight.caveat}</p>}
    </article>
  )
}

function groupByCategory(insights: Insight[]): [string, Insight[]][] {
  const groups = new Map<string, Insight[]>()
  for (const insight of insights) {
    const list = groups.get(insight.category) ?? []
    list.push(insight)
    groups.set(insight.category, list)
  }
  return [...groups.entries()]
}

function InsightsContent({ dataset }: { dataset: DatasetSummary }) {
  const { system, dataVersion } = useApp()
  const aiConfigured = Boolean(system?.ai.configured)
  const [useAi, setUseAi] = useState(false)
  // Rule-based insights load automatically. The AI provider is only called when the user asks, and a
  // data change falls back to rule-based insights rather than calling the provider again unprompted.
  const [request, setRequest] = useState({ withAi: false, count: 0, version: dataVersion })
  const withAi = request.withAi && request.version === dataVersion
  const insights = useApi(`insights:${dataset.id}:${dataVersion}:${withAi}:${request.count}`, () => api.insights(dataset.id, withAi))
  const { loading, error } = insights
  const result = loading ? null : (insights.data ?? null)
  const generate = (ai: boolean) => setRequest((previous) => ({ withAi: ai, count: previous.count + 1, version: dataVersion }))

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <div className="min-w-0 space-y-6">
        {loading && <LoadingState label={withAi ? 'Asking the AI provider…' : 'Generating insights…'} />}
        {!loading && error !== undefined && (
          <Card>
            <ErrorState title="Insights could not be generated" error={error} onRetry={insights.reload} />
          </Card>
        )}
        {!loading && result && (
          <>
            {result.notices.map((notice) => (
              <Alert key={notice} tone={result.ai_error ? 'warning' : 'info'}>
                {notice}
              </Alert>
            ))}
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <Badge tone={result.mode === 'ai' ? 'brand' : 'neutral'}>{result.mode === 'ai' ? `AI mode · ${result.model}` : 'Rule-based mode'}</Badge>
              Generated {formatDateTime(result.generated_at)}
            </div>
            {groupByCategory(result.insights).map(([category, items]) => (
              <section key={category} aria-label={category.replace(/_/g, ' ')}>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{category.replace(/_/g, ' ')}</h2>
                <div className="grid gap-3 xl:grid-cols-2">
                  {items.map((insight) => (
                    <InsightCard key={insight.id} insight={insight} showSource={result.mode === 'ai'} />
                  ))}
                </div>
              </section>
            ))}
            {result.limitations.length > 0 && (
              <Alert tone="warning" title="Limitations">
                <ul className="list-disc pl-4">
                  {result.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </Alert>
            )}
          </>
        )}
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader title="Generate insights" />
          <CardBody className="space-y-4">
            <Toggle
              label="Use the AI provider"
              checked={useAi && aiConfigured}
              disabled={!aiConfigured || loading}
              onChange={setUseAi}
              hint={
                aiConfigured
                  ? `${system?.ai.provider} · ${system?.ai.model}`
                  : 'Not enabled for this workspace.'
              }
            />
            <Button className="w-full" icon={useAi ? Sparkles : RefreshCw} loading={loading} onClick={() => generate(useAi && aiConfigured)}>
              {useAi && aiConfigured ? 'Generate with AI' : 'Regenerate'}
            </Button>
            <p className="text-xs leading-relaxed text-slate-500">{system?.ai.data_policy}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="How to read insights" />
          <CardBody className="space-y-2 text-xs text-slate-600">
            {Object.values(KIND).map((kind) => (
              <p key={kind.label} className="flex items-start gap-2">
                <Badge tone={kind.tone}>{kind.label}</Badge>
                <span>{kind.help}.</span>
              </p>
            ))}
            {aiConfigured && (
              <p className="flex items-start gap-2 pt-1">
                <ShieldAlert className="size-4 shrink-0 text-slate-400" aria-hidden />
                Verify AI-generated figures against the Data Analysis page before acting on them.
              </p>
            )}
          </CardBody>
        </Card>
        {result && result.data_sent.length > 0 && (
          <Card>
            <CardHeader title="Data sent to the AI provider" />
            <CardBody>
              <ul className="list-disc space-y-1 pl-4 text-xs text-slate-600">
                {result.data_sent.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </CardBody>
          </Card>
        )}
        <Card>
          <CardBody className="flex items-center gap-3">
            <Lightbulb className="size-5 shrink-0 text-amber-500" aria-hidden />
            <p className="text-xs text-slate-600">Insights are included automatically when you generate a report.</p>
            <LinkButton to="/reports" size="sm" icon={FileText}>
              Report
            </LinkButton>
          </CardBody>
        </Card>
      </aside>
    </div>
  )
}

export function InsightsPage() {
  const { selected } = useApp()
  return (
    <>
      <PageHeader
        title="AI Insights"
        eyebrow={selected && <DatasetEyebrow dataset={selected} />}
      />
      <RequireDataset purpose="generate insights">{(dataset) => <InsightsContent key={dataset.id} dataset={dataset} />}</RequireDataset>
    </>
  )
}
