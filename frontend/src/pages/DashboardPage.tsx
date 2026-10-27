import {
  ArrowRight,
  BarChart3,
  Database,
  FileText,
  FlaskConical,
  History,
  Layers,
  Package,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Tags,
  TrendingDown,
  TrendingUp,
  Upload,
  Workflow,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { api } from '../api/client'
import type { AnalysisResult, DatasetSummary, Metric } from '../api/types'
import { BarBreakdownChart } from '../components/charts/BarBreakdownChart'
import { ChartCard } from '../components/charts/ChartCard'
import { TrendChart } from '../components/charts/TrendChart'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, LoadingState, Skeleton } from '../components/ui/States'
import { StatCard } from '../components/ui/StatCard'
import { useValueFormatter } from '../components/useMetricFormatter'
import { useApp } from '../context/AppContext'
import { useApi } from '../hooks/useApi'
import { useLoadSample } from '../hooks/useLoadSample'
import { cn } from '../lib/cn'
import { formatDateTime, formatMetric, formatSignedPercent } from '../lib/format'

const WORKFLOW = [
  { label: 'Import', icon: Upload, to: '/upload' },
  { label: 'Check quality', icon: ShieldCheck, to: '/quality' },
  { label: 'Analyse', icon: BarChart3, to: '/analysis' },
  { label: 'Insights', icon: Sparkles, to: '/insights' },
  { label: 'Report', icon: FileText, to: '/reports' },
  { label: 'Automate', icon: Workflow, to: '/automation' },
]

const METRIC_ICONS: Record<string, typeof Database> = {
  records: Database,
  total_revenue: TrendingUp,
  average_transaction_value: ShoppingCart,
  total_quantity: Package,
  categories: Tags,
  products: Layers,
}

function Onboarding() {
  const { loadSample, loading } = useLoadSample()
  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <Badge tone="brand">Welcome</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Turn raw business data into reports you can act on</h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-600">
              FlowForge Analytics checks your data for problems, calculates the metrics your columns support, explains what it finds and
              produces downloadable reports. Start with your own CSV file or explore the synthetic sample dataset.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <LinkButton to="/upload" variant="primary" icon={Upload}>
                Upload a CSV file
              </LinkButton>
              <Button variant="secondary" icon={FlaskConical} loading={loading} onClick={() => void loadSample()}>
                Explore sample data
              </Button>
            </div>
            <p className="mt-3 text-xs text-slate-500">The sample is fabricated retail order data for demonstration only.</p>
          </div>
          <ol className="grid grid-cols-2 gap-3 self-center sm:grid-cols-3">
            {WORKFLOW.map((step, index) => (
              <li key={step.label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <step.icon className="size-5 text-brand-600" aria-hidden />
                <p className="mt-2 text-xs font-medium text-slate-500">Step {index + 1}</p>
                <p className="text-sm font-semibold text-slate-800">{step.label}</p>
              </li>
            ))}
          </ol>
        </div>
      </Card>
    </div>
  )
}

function MetricGrid({ metrics, qualityScore }: { metrics: Metric[]; qualityScore: number | null }) {
  const { currency } = useApp()
  const preferred = ['records', 'total_revenue', 'average_transaction_value', 'total_quantity', 'categories', 'products']
  const shown = preferred.map((key) => metrics.find((metric) => metric.key === key)).filter((metric): metric is Metric => Boolean(metric))
  const columns = metrics.find((metric) => metric.key === 'columns')
  if (shown.length < 4 && columns) shown.push(columns)
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      {shown.map((metric) => (
        <StatCard key={metric.key} label={metric.label} value={formatMetric(metric, currency)} hint={metric.description} icon={METRIC_ICONS[metric.key]} />
      ))}
      <StatCard
        label="Data quality"
        value={qualityScore !== null ? `${qualityScore.toFixed(1)} / 100` : '–'}
        hint={<Link to="/quality" className="text-brand-700 hover:underline">Review findings</Link>}
        icon={ShieldCheck}
      />
    </div>
  )
}

function TrendPanel({ analysis }: { analysis: AnalysisResult }) {
  const series = analysis.time_series
  const isRevenue = series?.aggregation === 'sum' && analysis.revenue_source !== null
  const format = useValueFormatter(isRevenue)
  if (!series) {
    return (
      <Card>
        <CardHeader title="Trend over time" />
        <CardBody>
          <p className="text-sm text-slate-500">This dataset has no date column, so trends cannot be shown. Other metrics are still available.</p>
        </CardBody>
      </Card>
    )
  }
  const comparison = analysis.period_comparison
  const change = comparison?.change_percent ?? null
  return (
    <ChartCard
      title={isRevenue ? `Revenue by ${series.granularity}` : `Records by ${series.granularity}`}
      description={`${formatDateTimeRange(series.first_date, series.last_date)}${series.excluded_rows ? ` · ${series.excluded_rows} rows without a readable date excluded` : ''}`}
      actions={
        comparison && change !== null ? (
          <Badge tone={change >= 0 ? 'success' : 'danger'}>
            {change >= 0 ? <TrendingUp className="size-3" aria-hidden /> : <TrendingDown className="size-3" aria-hidden />}
            {formatSignedPercent(change)} {comparison.current.label} vs {comparison.previous.label}
          </Badge>
        ) : undefined
      }
      footer={comparison?.note ?? (series.points.some((point) => point.partial) ? 'Some periods contain partial data; hover a point for details.' : undefined)}
    >
      <TrendChart points={series.points} valueLabel={isRevenue ? 'Revenue' : 'Records'} formatValue={format} />
    </ChartCard>
  )
}

function formatDateTimeRange(start: string, end: string): string {
  return `${new Date(start).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })} to ${new Date(end).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`
}

function BreakdownPanel({ analysis }: { analysis: AnalysisResult }) {
  const breakdown = analysis.breakdowns.category ?? analysis.breakdowns.region ?? analysis.breakdowns.product ?? analysis.breakdowns.status
  const format = useValueFormatter(breakdown?.measure === 'revenue')
  if (!breakdown) {
    return (
      <Card>
        <CardHeader title="Group comparison" />
        <CardBody>
          <p className="text-sm text-slate-500">
            No category, region or product column was detected. Use the <Link className="text-brand-700 underline" to="/visualisations">visualisation builder</Link> to compare any column.
          </p>
        </CardBody>
      </Card>
    )
  }
  const measureLabel = breakdown.measure === 'revenue' ? 'Revenue' : 'Records'
  const data = breakdown.rows.slice(0, 8).map((row) => ({ group: row.group, value: breakdown.measure === 'revenue' ? row.revenue : row.records, records: row.records, share: row.share }))
  return (
    <ChartCard title={`${measureLabel} by ${breakdown.column}`} description={`Top ${data.length} of ${breakdown.total_groups} values`}>
      <BarBreakdownChart data={data} valueLabel={measureLabel} formatValue={format} />
    </ChartCard>
  )
}

function ActivityPanel({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion } = useApp()
  const reports = useApi(`reports:${dataset.id}:${dataVersion}`, () => api.listReports(dataset.id, 5))
  const activity = useApi(`activity:${dataset.id}:${dataVersion}`, () => api.activity(dataset.id, 6))
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader title="Recent reports" actions={<LinkButton to="/reports/history" size="sm" variant="ghost" icon={History}>All reports</LinkButton>} />
        <CardBody className="p-0">
          {reports.loading ? (
            <LoadingState />
          ) : reports.error ? (
            <ErrorState error={reports.error} onRetry={reports.reload} />
          ) : reports.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {reports.data.map((report) => (
                <li key={report.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-800">{report.title}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(report.created_at)}</p>
                  </div>
                  <a className="text-sm font-medium text-brand-700 hover:underline" href={api.reportUrl(report.id, 'html', true)} target="_blank" rel="noopener noreferrer">
                    Open
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-5 py-6 text-sm text-slate-500">
              No reports yet for this dataset. <Link className="text-brand-700 underline" to="/reports">Generate one</Link>.
            </p>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Recent activity" description="Imports, cleaning, reports and automation for this dataset" />
        <CardBody className="p-0">
          {activity.loading ? (
            <LoadingState />
          ) : activity.error ? (
            <ErrorState error={activity.error} onRetry={activity.reload} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {activity.data?.map((item) => (
                <li key={item.id} className="flex items-start gap-3 px-5 py-3">
                  <span
                    className={cn(
                      'mt-1.5 size-2 shrink-0 rounded-full',
                      item.kind.startsWith('automation.failed') ? 'bg-red-500' : item.kind.startsWith('report') ? 'bg-brand-500' : item.kind.startsWith('automation') ? 'bg-emerald-500' : 'bg-slate-400',
                    )}
                    aria-hidden
                  />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700">{item.message}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(item.created_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

function DatasetDashboard({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion } = useApp()
  const analysis = useApi(`analysis:${dataset.id}:${dataVersion}`, () => api.analysis(dataset.id))

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="A summary of the selected dataset. Every figure is calculated from the data itself."
        eyebrow={<DatasetEyebrow dataset={dataset} />}
        actions={
          <>
            <LinkButton to="/quality" icon={ShieldCheck}>
              Check quality
            </LinkButton>
            <LinkButton to="/reports" variant="primary" icon={FileText}>
              Generate report
            </LinkButton>
          </>
        }
      />
      {dataset.is_sample && (
        <Alert tone="info" className="mb-6" title="You are viewing demonstration data">
          This is a synthetic retail dataset created for FlowForge. It does not describe a real business.
        </Alert>
      )}
      {analysis.loading && !analysis.data ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      ) : analysis.error ? (
        <Card>
          <ErrorState title="The analysis could not be loaded" error={analysis.error} onRetry={analysis.reload} />
        </Card>
      ) : analysis.data ? (
        <div className="space-y-6">
          <MetricGrid metrics={analysis.data.metrics} qualityScore={dataset.quality_score} />
          <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <TrendPanel analysis={analysis.data} />
            <BreakdownPanel analysis={analysis.data} />
          </div>
          {analysis.data.limitations.length > 0 && (
            <Alert tone="warning" title="Things to keep in mind">
              <ul className="list-disc space-y-0.5 pl-4">
                {analysis.data.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Alert>
          )}
          <Card>
            <CardHeader title="Next steps" description="Continue the workflow for this dataset" />
            <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { to: '/quality', title: 'Improve data quality', text: 'Review findings and apply cleaning operations.', icon: ShieldCheck },
                { to: '/visualisations', title: 'Explore charts', text: 'Compare any column and change groupings.', icon: BarChart3 },
                { to: '/insights', title: 'Read insights', text: 'Measured facts and clearly labelled interpretations.', icon: Sparkles },
                { to: '/automation', title: 'Automate delivery', text: 'Send summaries to a Make.com scenario.', icon: Workflow },
              ].map((item) => (
                <Link key={item.to} to={item.to} className="group rounded-lg border border-slate-200 p-4 transition-colors hover:border-brand-300 hover:bg-brand-50/40">
                  <item.icon className="size-5 text-brand-600" aria-hidden />
                  <p className="mt-2 flex items-center gap-1 text-sm font-semibold text-slate-800">
                    {item.title}
                    <ArrowRight className="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">{item.text}</p>
                </Link>
              ))}
            </CardBody>
          </Card>
          <ActivityPanel dataset={dataset} />
        </div>
      ) : null}
    </>
  )
}

export function DashboardPage() {
  const { datasetsLoaded, datasetsError, selected, refreshDatasets } = useApp()
  if (!datasetsLoaded) return <LoadingState label="Loading workspace…" />
  if (datasetsError) {
    return (
      <Card>
        <ErrorState title="FlowForge could not load your workspace" error={datasetsError} onRetry={() => void refreshDatasets()} />
      </Card>
    )
  }
  if (!selected) return <Onboarding />
  return <DatasetDashboard dataset={selected} />
}
