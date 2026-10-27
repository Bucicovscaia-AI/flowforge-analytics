import HorizontalBarChart from '../components/charts/HorizontalBarChart'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import DemoNotice from '../components/ui/DemoNotice'
import KpiCard from '../components/ui/KpiCard'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { SAMPLE_DATASET, columnProfile, getSampleKpis, revenueByCategory } from '../data/sampleData'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'

export default function AnalysisPage() {
  const kpis = getSampleKpis()

  return (
    <>
      <PageHeader title="Data Analysis" description="Data-quality checks and the breakdowns calculated from the cleaned dataset." />
      <DemoNotice />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard label="Rows received" value={formatNumber(SAMPLE_DATASET.rowsReceived)} detail={`${SAMPLE_DATASET.columns} columns`} />
        <KpiCard label="Duplicates removed" value={formatNumber(SAMPLE_DATASET.duplicatesRemoved)} detail="Repeated order_id" />
        <KpiCard label="Invalid rows removed" value={formatNumber(SAMPLE_DATASET.invalidRowsRemoved)} detail="Bad dates or negative quantities" />
        <KpiCard label="Rows analysed" value={formatNumber(kpis.validRows)} detail={`${formatPercent(kpis.dataQualityScore)} data quality score`} />
      </div>

      <Card title="Column quality profile" subtitle="Problems found in each column and how they were handled" className="mt-6">
        <DataTable
          caption="Column quality profile"
          rowKey="column"
          rows={columnProfile}
          columns={[
            { key: 'column', header: 'Column', render: (r) => <span className="font-mono text-xs text-slate-900">{r.column}</span> },
            { key: 'type', header: 'Type' },
            { key: 'missing', header: 'Missing', align: 'right' },
            { key: 'invalid', header: 'Invalid', align: 'right' },
            {
              key: 'status',
              header: 'Status',
              render: (r) =>
                r.missing + r.invalid === 0 ? (
                  <StatusBadge variant="success">Clean</StatusBadge>
                ) : (
                  <StatusBadge variant="warning">Fixed</StatusBadge>
                ),
            },
            { key: 'action', header: 'Action taken' },
          ]}
        />
      </Card>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card title="Revenue by product category" subtitle="Ranked highest to lowest">
          <HorizontalBarChart data={revenueByCategory} label="Bar chart of revenue by product category" />
        </Card>
        <Card title="Category breakdown" subtitle="Table view of the same figures">
          <DataTable
            caption="Revenue and orders by category"
            rowKey="name"
            rows={revenueByCategory}
            columns={[
              { key: 'name', header: 'Category', render: (r) => <span className="font-medium text-slate-900">{r.name}</span> },
              { key: 'orders', header: 'Orders', align: 'right', render: (r) => formatNumber(r.orders) },
              { key: 'revenue', header: 'Revenue', align: 'right', render: (r) => formatCurrency(r.revenue) },
              { key: 'share', header: 'Share', align: 'right', render: (r) => formatPercent((r.revenue / kpis.totalRevenue) * 100) },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
