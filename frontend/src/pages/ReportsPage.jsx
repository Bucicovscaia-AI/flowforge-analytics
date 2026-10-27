import { Link } from 'react-router-dom'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DemoNotice from '../components/ui/DemoNotice'
import EmptyState from '../components/ui/EmptyState'
import PageHeader from '../components/ui/PageHeader'
import { SAMPLE_DATASET, getSampleKpis } from '../data/sampleData'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'

const SECTIONS = [
  'Executive summary',
  'Dataset and data-quality checks',
  'Key performance indicators',
  'Monthly revenue trend',
  'Regional and category breakdown',
  'Observations and recommendations',
  'Method, limitations and data notice',
]

export default function ReportsPage() {
  const kpis = getSampleKpis()

  return (
    <>
      <PageHeader
        title="Reports"
        description="Generate a structured report from the latest analysis and download it."
        actions={
          <Button icon="download" disabled title="Report download is added in a later stage">
            Download report
          </Button>
        }
      />
      <DemoNotice />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Report preview" subtitle={`Source: ${SAMPLE_DATASET.fileName}`} className="lg:col-span-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">FlowForge Analytics report</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">Sales performance, January to June 2026</h2>
            <p className="mt-1 text-xs text-slate-500">Demonstration data: not a real business</p>
            <dl className="mt-5 grid gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-slate-500">Total revenue</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatCurrency(kpis.totalRevenue)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Orders</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatNumber(kpis.totalOrders)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Data quality</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatPercent(kpis.dataQualityScore)}</dd>
              </div>
            </dl>
            <h3 className="mt-6 text-sm font-semibold text-slate-900">Contents</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-600">
              {SECTIONS.map((section) => (
                <li key={section}>{section}</li>
              ))}
            </ol>
          </div>
        </Card>

        <Card title="Your reports">
          <EmptyState
            icon="report"
            title="No reports generated yet"
            action={
              <Link to="/upload" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
                Upload a dataset
              </Link>
            }
          >
            Reports appear here after you upload a dataset and run the analysis.
          </EmptyState>
        </Card>
      </div>
    </>
  )
}
