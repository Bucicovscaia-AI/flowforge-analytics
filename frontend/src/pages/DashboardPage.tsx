import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import HorizontalBarChart from '../components/charts/HorizontalBarChart'
import RevenueTrendChart from '../components/charts/RevenueTrendChart'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import EmptyState from '../components/ui/EmptyState'
import KpiCard from '../components/ui/KpiCard'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import SyntheticNotice from '../components/ui/SyntheticNotice'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { analyseSample, listReports } from '../services/api'
import type { Report } from '../types'
import { formatCurrency, formatCurrencyPrecise, formatDate, formatDateTime, formatNumber, formatPercent } from '../utils/format'

function Welcome() {
  const { setAnalysis } = useAnalysis()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  async function loadSample() {
    setBusy(true)
    try {
      const analysis = await analyseSample('retail-2026')
      setAnalysis(analysis)
      notify('success', 'Sample dataset analysed', `${formatNumber(analysis.quality.rows_analysed)} rows passed the cleaning rules.`)
    } catch (error) {
      notify('error', 'Could not load the sample', (error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Dashboard" description="Business performance from your most recent analysis." />
      <Card>
        <EmptyState
          icon="analysis"
          title="Start by analysing a dataset"
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button icon="bolt" onClick={loadSample} disabled={busy}>
                {busy ? 'Analysing…' : 'Try the synthetic sample'}
              </Button>
              <Button variant="secondary" icon="upload" onClick={() => navigate('/upload')}>
                Upload a CSV
              </Button>
            </div>
          }
        >
          FlowForge validates and cleans the file, calculates KPIs and builds a downloadable report. The sample is fabricated
          retail data with deliberate quality problems for the cleaning rules to find.
        </EmptyState>
      </Card>
    </>
  )
}

export default function DashboardPage() {
  const { analysis } = useAnalysis()
  const [reports, setReports] = useState<Report[] | null>(null)

  useEffect(() => {
    listReports()
      .then(setReports)
      .catch(() => setReports([]))
  }, [])

  if (!analysis) return <Welcome />

  const { summary, breakdowns, unavailable } = analysis.kpis
  const months = breakdowns.revenue_over_time ?? []
  const period = summary.date_from && summary.date_to ? `${formatDate(summary.date_from)} – ${formatDate(summary.date_to)}` : undefined

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Overview of ${analysis.dataset.file_name}, analysed ${formatDateTime(analysis.created_at)}.`}
        actions={
          <>
            <Link to="/upload" className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
              Change dataset
            </Link>
            <Link to="/reports" className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500">
              Generate report
            </Link>
          </>
        }
      />
      {analysis.dataset.synthetic && <SyntheticNotice fileName={analysis.dataset.file_name} />}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard label="Total revenue" icon="report" value={formatCurrency(summary.total_revenue)} detail={period} />
        <KpiCard label="Orders" icon="file" value={formatNumber(summary.order_count)} detail={`${formatNumber(summary.units_sold)} units sold`} />
        <KpiCard label="Average order value" icon="analysis" value={formatCurrencyPrecise(summary.average_order_value)} detail="Revenue ÷ distinct orders" />
        <KpiCard
          label="Data quality score"
          icon="shield"
          value={formatPercent(analysis.quality.quality_score)}
          detail={`${formatNumber(analysis.quality.rows_analysed)} of ${formatNumber(analysis.quality.rows_received)} rows kept`}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-5">
        <Card title="Monthly revenue" subtitle="Revenue from cleaned order lines, by order month" className="xl:col-span-3">
          {months.length > 0 ? <RevenueTrendChart data={months} /> : <p className="text-sm text-slate-500">Not available: the dataset has no usable order dates.</p>}
        </Card>
        <Card title="Revenue by region" subtitle="Ranked highest to lowest" className="xl:col-span-2">
          {breakdowns.revenue_by_region ? (
            <HorizontalBarChart data={breakdowns.revenue_by_region} label="Bar chart of revenue by region" />
          ) : (
            <p className="text-sm text-slate-500">Not available: the dataset has no region column.</p>
          )}
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card title="Revenue by category" subtitle="Ranked highest to lowest">
          {breakdowns.revenue_by_category ? (
            <HorizontalBarChart data={breakdowns.revenue_by_category} label="Bar chart of revenue by product category" />
          ) : (
            <p className="text-sm text-slate-500">Not available: the dataset has no product_category column.</p>
          )}
        </Card>
        <Card
          title="Recent reports"
          action={
            <Link to="/history" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
              View all
            </Link>
          }
        >
          {reports === null ? (
            <p className="text-sm text-slate-500">Loading reports…</p>
          ) : reports.length === 0 ? (
            <EmptyState icon="report" title="No reports yet">
              Generate a PDF report from the Reports page.
            </EmptyState>
          ) : (
            <DataTable<Report>
              caption="Recent reports"
              rowKey={(r) => r.id}
              rows={reports.slice(0, 5)}
              columns={[
                { key: 'title', header: 'Report', render: (r) => <span className="block min-w-48 whitespace-normal font-medium text-slate-900">{r.title}</span> },
                { key: 'created', header: 'Created', render: (r) => formatDateTime(r.created_at) },
                {
                  key: 'source',
                  header: 'Insights',
                  render: (r) => (r.insight_source === 'ai' ? <StatusBadge variant="ai">AI</StatusBadge> : <StatusBadge>Rule-based</StatusBadge>),
                },
              ]}
            />
          )}
        </Card>
      </div>

      {unavailable.length > 0 && (
        <Card title="KPIs not available for this dataset" className="mt-6">
          <ul className="space-y-1 text-sm text-slate-600">
            {unavailable.map((u) => (
              <li key={u.kpi}>
                <span className="font-medium text-slate-900">{u.label}</span>: needs the {u.missing_columns.join(', ')} column.
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
