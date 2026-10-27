import { Link } from 'react-router-dom'
import HorizontalBarChart from '../components/charts/HorizontalBarChart'
import RevenueTrendChart from '../components/charts/RevenueTrendChart'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import DemoNotice from '../components/ui/DemoNotice'
import KpiCard from '../components/ui/KpiCard'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { SAMPLE_DATASET, getSampleKpis, monthlyRevenue, reportHistory, revenueByRegion } from '../data/sampleData'
import { formatCurrency, formatCurrencyPrecise, formatDateTime, formatNumber, formatPercent } from '../utils/format'

export default function DashboardPage() {
  const kpis = getSampleKpis()
  const first = monthlyRevenue[0]
  const last = monthlyRevenue.at(-1)

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Overview of the most recent analysis: ${SAMPLE_DATASET.fileName}.`}
        actions={
          <Link to="/upload" className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500">
            Upload dataset
          </Link>
        }
      />
      <DemoNotice />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard label="Total revenue" value={formatCurrency(kpis.totalRevenue)} detail={`${first.month} to ${last.month} 2026`} />
        <KpiCard label="Orders" value={formatNumber(kpis.totalOrders)} detail="Valid orders after cleaning" />
        <KpiCard label="Average order value" value={formatCurrencyPrecise(kpis.averageOrderValue)} detail="Revenue ÷ orders" />
        <KpiCard
          label="Data quality score"
          value={formatPercent(kpis.dataQualityScore)}
          detail={`${formatNumber(kpis.validRows)} of ${formatNumber(SAMPLE_DATASET.rowsReceived)} rows passed checks`}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-5">
        <Card title="Monthly revenue" subtitle="Revenue from valid orders, by month" className="xl:col-span-3">
          <RevenueTrendChart data={monthlyRevenue} />
        </Card>
        <Card title="Revenue by region" subtitle="Ranked highest to lowest" className="xl:col-span-2">
          <HorizontalBarChart data={revenueByRegion} label="Bar chart of revenue by region" />
        </Card>
      </div>

      <Card
        title="Recent reports"
        className="mt-6"
        action={<Link to="/history" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">View all</Link>}
      >
        <DataTable
          caption="Recent reports"
          rowKey="id"
          rows={reportHistory}
          columns={[
            { key: 'title', header: 'Report', render: (r) => <span className="font-medium text-slate-900">{r.title}</span> },
            { key: 'dataset', header: 'Dataset' },
            { key: 'created', header: 'Created', render: (r) => formatDateTime(r.created) },
            {
              key: 'status',
              header: 'Status',
              render: (r) => <StatusBadge variant={r.status === 'Ready' ? 'success' : 'error'}>{r.status}</StatusBadge>,
            },
          ]}
        />
      </Card>
    </>
  )
}
