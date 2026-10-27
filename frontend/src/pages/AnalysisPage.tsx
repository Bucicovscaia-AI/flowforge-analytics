import { ArrowDownRight, ArrowRight, ArrowUpRight, Info, LineChart, Settings2, Sparkles } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { AnalysisResult, Breakdown, ColumnSummary, DatasetDetail, DatasetSummary, Role } from '../api/types'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { RequireDataset } from '../components/RequireDataset'
import { TypeBadge } from '../components/DatasetTables'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { SelectField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, LoadingState } from '../components/ui/States'
import { StatCard } from '../components/ui/StatCard'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { formatCurrency, formatDate, formatMetric, formatNumber, formatPercent, formatSignedPercent } from '../lib/format'

const ROLE_ORDER: Role[] = ['date', 'revenue', 'quantity', 'unit_price', 'category', 'product', 'region', 'status']

function MappingEditor({ detail, onSaved }: { detail: DatasetDetail; onSaved: () => void }) {
  const { notify } = useToast()
  const [draft, setDraft] = useState<Record<Role, string>>(() => toDraft(detail))
  const [saving, setSaving] = useState(false)

  const dirty = ROLE_ORDER.some((role) => draft[role] !== (detail.roles[role] ?? ''))

  const save = async () => {
    setSaving(true)
    try {
      const mapping: Partial<Record<Role, string | null>> = {}
      for (const role of ROLE_ORDER) mapping[role] = draft[role]
      await api.updateMapping(detail.id, mapping)
      notify('success', 'Column mapping saved', 'Metrics and charts now use the columns you chose.')
      onSaved()
    } catch (error) {
      notify('error', 'Could not save the mapping', errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader
        title="Column mapping"
        description="FlowForge detects which column holds each business field from its name and type. Change a mapping if the guess is wrong, or choose None to switch a field off."
        actions={
          <>
            <Button variant="ghost" size="sm" disabled={!dirty || saving} onClick={() => setDraft(toDraft(detail))}>
              Discard
            </Button>
            <Button size="sm" icon={Settings2} disabled={!dirty} loading={saving} onClick={() => void save()}>
              Save mapping
            </Button>
          </>
        }
      />
      <CardBody className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {ROLE_ORDER.map((role) => {
          const option = detail.role_options[role]
          const candidates = option.candidates
          const current = draft[role]
          const choices = current && !candidates.includes(current) ? [current, ...candidates] : candidates
          return (
            <SelectField
              key={role}
              label={option.label}
              value={current}
              onChange={(event) => setDraft((previous) => ({ ...previous, [role]: event.target.value }))}
              hint={detail.column_mapping[role] !== undefined ? 'Set manually' : current ? 'Detected automatically' : 'Not detected'}
            >
              <option value="">None</option>
              {choices.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </SelectField>
          )
        })}
      </CardBody>
    </Card>
  )
}

function toDraft(detail: DatasetDetail): Record<Role, string> {
  return Object.fromEntries(ROLE_ORDER.map((role) => [role, detail.roles[role] ?? ''])) as Record<Role, string>
}

function ComparisonCard({ analysis }: { analysis: AnalysisResult }) {
  const { currency } = useApp()
  const comparison = analysis.period_comparison
  const trend = analysis.trend
  if (!comparison && !trend) return null
  const isRevenue = analysis.revenue_source !== null
  const format = (value: number) => (isRevenue ? formatCurrency(value, currency) : formatNumber(value))
  const TrendIcon = trend?.direction === 'upward' ? ArrowUpRight : trend?.direction === 'downward' ? ArrowDownRight : ArrowRight
  return (
    <Card>
      <CardHeader title="Change over time" description={isRevenue ? 'Based on revenue' : 'Based on the number of records'} />
      <CardBody className="grid gap-4 md:grid-cols-2">
        {comparison && (
          <div>
            <p className="text-sm text-slate-500">
              {comparison.current.label} compared with {comparison.previous.label}
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{formatSignedPercent(comparison.change_percent)}</p>
            <p className="text-sm text-slate-600">
              {format(comparison.current.value)} against {format(comparison.previous.value)} ({formatNumber(comparison.current.records)} and{' '}
              {formatNumber(comparison.previous.records)} records)
            </p>
            {comparison.note && <p className="mt-2 text-xs text-slate-500">{comparison.note}</p>}
          </div>
        )}
        {trend && (
          <div>
            <p className="text-sm text-slate-500">
              Trend from {trend.first_label} to {trend.last_label} ({trend.periods} periods)
            </p>
            <p className="mt-1 flex items-center gap-1.5 text-2xl font-semibold capitalize text-slate-900">
              <TrendIcon className="size-6 text-brand-600" aria-hidden />
              {trend.direction}
            </p>
            <p className="text-sm text-slate-600">
              Fitted slope of {formatSignedPercent(trend.relative_slope_percent)} of the average per {analysis.time_series?.granularity ?? 'period'}.
            </p>
            <p className="mt-2 text-xs text-slate-500">A straight-line fit over complete periods. It describes the past and is not a forecast.</p>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function BreakdownTable({ breakdown }: { breakdown: Breakdown }) {
  const { currency } = useApp()
  const hasRevenue = breakdown.measure === 'revenue'
  return (
    <Card>
      <CardHeader
        title={`By ${breakdown.column}`}
        description={breakdown.total_groups > breakdown.rows.length ? `Top ${breakdown.rows.length} of ${breakdown.total_groups} groups` : `${breakdown.total_groups} groups`}
      />
      <TableContainer label={`Breakdown by ${breakdown.column}`}>
        <thead>
          <tr>
            <Th>{breakdown.column}</Th>
            <Th numeric>Records</Th>
            {hasRevenue && <Th numeric>Revenue</Th>}
            {hasRevenue && <Th numeric>Average</Th>}
            <Th numeric>Share</Th>
          </tr>
        </thead>
        <tbody>
          {breakdown.rows.map((row) => (
            <Tr key={row.group}>
              <Td className="font-medium text-slate-800">{row.group}</Td>
              <Td numeric>{formatNumber(row.records)}</Td>
              {hasRevenue && <Td numeric>{formatCurrency(row.revenue, currency)}</Td>}
              {hasRevenue && <Td numeric>{formatCurrency(row.average_revenue, currency)}</Td>}
              <Td numeric>{formatPercent(row.share)}</Td>
            </Tr>
          ))}
        </tbody>
      </TableContainer>
    </Card>
  )
}

function statText(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '–'
  return typeof value === 'number' ? formatNumber(value) : value
}

function ColumnSummaryDetail({ column }: { column: ColumnSummary }) {
  if (column.type === 'numeric' && column.stats) {
    const { mean, median, min, max, std } = column.stats
    return (
      <span>
        mean {statText(mean)} · median {statText(median)} · range {statText(min)} to {statText(max)}
        {std !== null && std !== undefined ? ` · std ${statText(std)}` : ''}
      </span>
    )
  }
  if (column.type === 'datetime' && column.stats) {
    return (
      <span>
        {formatDate(String(column.stats.min))} to {formatDate(String(column.stats.max))} ({statText(column.stats.span_days)} days)
      </span>
    )
  }
  if (column.top_values?.length) {
    return <span>{column.top_values.map((item) => `${item.value} (${formatNumber(item.count)})`).join(', ')}</span>
  }
  return <span className="text-slate-400">–</span>
}

function AnalysisContent({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion, currency, notifyDataChanged } = useApp()
  const detail = useApi(`detail:${dataset.id}:${dataVersion}`, () => api.getDataset(dataset.id))
  const analysis = useApi(`analysis:${dataset.id}:${dataVersion}`, () => api.analysis(dataset.id))

  return (
    <div className="space-y-6">
      {detail.data && <MappingEditor key={`${detail.data.id}:${detail.data.updated_at}:${JSON.stringify(detail.data.roles)}`} detail={detail.data} onSaved={notifyDataChanged} />}
      {detail.error !== undefined && !detail.data && <ErrorState error={detail.error} onRetry={detail.reload} />}

      {analysis.loading && !analysis.data ? (
        <LoadingState label="Calculating metrics…" />
      ) : analysis.error ? (
        <Card>
          <ErrorState title="The analysis could not be calculated" error={analysis.error} onRetry={analysis.reload} />
        </Card>
      ) : analysis.data ? (
        <>
          {analysis.data.revenue_source === 'derived' && (
            <Alert tone="info" title="Revenue is calculated">
              There is no revenue column, so revenue is calculated as {analysis.data.roles.quantity} × {analysis.data.roles.unit_price} for each row.
            </Alert>
          )}
          <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {analysis.data.metrics.map((metric) => (
              <StatCard
                key={metric.key}
                label={metric.label}
                value={formatMetric(metric, currency)}
                hint={
                  <span title={metric.source_columns.length ? `Columns used: ${metric.source_columns.join(', ')}` : undefined}>{metric.description}</span>
                }
              />
            ))}
          </section>

          <ComparisonCard analysis={analysis.data} />

          {Object.values(analysis.data.breakdowns).length > 0 && (
            <div className="grid gap-6 xl:grid-cols-2">
              {Object.values(analysis.data.breakdowns).map((breakdown) => breakdown && <BreakdownTable key={breakdown.role} breakdown={breakdown} />)}
            </div>
          )}

          <Card>
            <CardHeader title="Column summaries" description="Descriptive statistics for every column, calculated from valid values only" />
            <TableContainer label="Column summaries">
              <thead>
                <tr>
                  <Th>Column</Th>
                  <Th>Type</Th>
                  <Th numeric>Values</Th>
                  <Th numeric>Missing</Th>
                  <Th numeric>Distinct</Th>
                  <Th>Summary</Th>
                </tr>
              </thead>
              <tbody>
                {analysis.data.columns.map((column) => (
                  <Tr key={column.name}>
                    <Td className="font-medium text-slate-800">{column.name}</Td>
                    <Td>
                      <TypeBadge type={column.type} />
                    </Td>
                    <Td numeric>{formatNumber(column.non_null)}</Td>
                    <Td numeric>
                      {formatNumber(column.missing)}
                      {column.missing > 0 && <span className="text-xs text-slate-500"> ({formatPercent(column.missing_percent)})</span>}
                    </Td>
                    <Td numeric>{formatNumber(column.distinct)}</Td>
                    <Td className="max-w-md text-xs text-slate-600">
                      <ColumnSummaryDetail column={column} />
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </TableContainer>
          </Card>

          <Card>
            <CardHeader title="Relationships between numeric columns" description="Pearson correlations with a strength of at least 0.5" />
            <CardBody>
              {analysis.data.correlations.length === 0 ? (
                <p className="text-sm text-slate-500">No moderate or strong correlations were found between numeric columns.</p>
              ) : (
                <ul className="space-y-2">
                  {analysis.data.correlations.map((item) => (
                    <li key={`${item.column_a}-${item.column_b}`} className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                      <span className="font-medium">{item.column_a}</span>
                      <span className="text-slate-400">and</span>
                      <span className="font-medium">{item.column_b}</span>
                      <Badge tone={item.strength === 'strong' ? 'brand' : 'neutral'}>
                        {item.strength} {item.coefficient > 0 ? 'positive' : 'negative'} ({item.coefficient.toFixed(2)})
                      </Badge>
                      {item.expected && <span className="text-xs text-slate-500">Expected, as one column is calculated from the other.</span>}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-3 flex items-start gap-1.5 text-xs text-slate-500">
                <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                Correlation shows that two columns move together. It does not show that one causes the other.
              </p>
            </CardBody>
          </Card>

          {analysis.data.limitations.length > 0 && (
            <Alert tone="warning" title="Limitations of this analysis">
              <ul className="list-disc pl-4">
                {analysis.data.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Alert>
          )}
        </>
      ) : null}
    </div>
  )
}

export function AnalysisPage() {
  const { selected } = useApp()
  return (
    <>
      <PageHeader
        title="Data Analysis"
        description="Business metrics, comparisons and descriptive statistics calculated from the selected dataset. Every figure comes directly from your data."
        eyebrow={selected && <DatasetEyebrow dataset={selected} />}
        actions={
          selected && (
            <>
              <LinkButton to="/visualisations" icon={LineChart}>
                Charts
              </LinkButton>
              <LinkButton to="/insights" variant="primary" icon={Sparkles}>
                Insights
              </LinkButton>
            </>
          )
        }
      />
      <RequireDataset purpose="analyse it">{(dataset) => <AnalysisContent dataset={dataset} />}</RequireDataset>
    </>
  )
}
