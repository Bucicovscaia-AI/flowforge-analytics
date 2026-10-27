import { useState } from 'react'
import HorizontalBarChart from '../components/charts/HorizontalBarChart'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import KpiCard from '../components/ui/KpiCard'
import NoAnalysis from '../components/ui/NoAnalysis'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import SyntheticNotice from '../components/ui/SyntheticNotice'
import { useAnalysis } from '../context/analysisContext'
import type { BreakdownKey, BreakdownRow, CleaningStep, ColumnProfile, MonthRow } from '../types'
import { formatCurrency, formatCurrencyPrecise, formatNumber, formatPercent } from '../utils/format'

const BREAKDOWNS: { key: BreakdownKey; label: string; noun: string }[] = [
  { key: 'revenue_by_category', label: 'Category', noun: 'Category' },
  { key: 'revenue_by_region', label: 'Region', noun: 'Region' },
  { key: 'revenue_by_channel', label: 'Channel', noun: 'Channel' },
  { key: 'revenue_by_customer_type', label: 'Customer type', noun: 'Customer type' },
  { key: 'top_products', label: 'Top products', noun: 'Product' },
]

export default function AnalysisPage() {
  const { analysis } = useAnalysis()
  const [selected, setSelected] = useState<BreakdownKey>('revenue_by_category')

  if (!analysis) {
    return (
      <>
        <PageHeader title="Data Analysis" description="Data-quality checks, cleaning results and KPI breakdowns." />
        <NoAnalysis what="data-quality checks and breakdowns" />
      </>
    )
  }

  const { quality, profile, kpis } = analysis
  const available = BREAKDOWNS.filter((b) => kpis.breakdowns[b.key])
  const active = available.find((b) => b.key === selected) ?? available[0]
  const rows = active ? (kpis.breakdowns[active.key] ?? []) : []

  return (
    <>
      <PageHeader title="Data Analysis" description={`Data-quality checks, cleaning results and KPI breakdowns for ${analysis.dataset.file_name}.`} />
      {analysis.dataset.synthetic && <SyntheticNotice fileName={analysis.dataset.file_name} />}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard label="Rows received" value={formatNumber(quality.rows_received)} detail={`${profile.columns} columns`} />
        <KpiCard label="Duplicate rows" value={formatNumber(quality.duplicate_rows)} detail="Exact copies of another row" />
        <KpiCard label="Missing cells" value={formatNumber(quality.missing_cells)} detail={`${formatPercent(quality.completeness_pct)} complete`} />
        <KpiCard label="Rows analysed" value={formatNumber(quality.rows_analysed)} detail={`${formatNumber(quality.rows_removed)} removed · ${formatPercent(quality.quality_score)} kept`} />
      </div>

      <Card title="Cleaning rules applied" subtitle="Applied in order; every KPI is calculated after these rules. See docs/data-cleaning-rules.md." className="mt-6">
        <DataTable<CleaningStep>
          caption="Cleaning rules applied"
          rowKey={(r) => r.rule}
          rows={analysis.cleaning_steps}
          columns={[
            { key: 'rule', header: 'Rule', render: (r) => <span className="font-mono text-xs text-slate-900">{r.rule}</span> },
            { key: 'description', header: 'What it does', render: (r) => <span className="whitespace-normal">{r.description}</span> },
            { key: 'rows_removed', header: 'Rows removed', align: 'right', render: (r) => formatNumber(r.rows_removed) },
            { key: 'cells_changed', header: 'Cells changed', align: 'right', render: (r) => formatNumber(r.cells_changed) },
            {
              key: 'status',
              header: 'Result',
              render: (r) =>
                r.rows_removed + r.cells_changed === 0 ? <StatusBadge variant="success">No issues</StatusBadge> : <StatusBadge variant="warning">Applied</StatusBadge>,
            },
          ]}
        />
      </Card>

      <Card title="Column profile" subtitle="The file as received, before cleaning" className="mt-6">
        <DataTable<ColumnProfile>
          caption="Column profile"
          rowKey={(r) => r.name}
          rows={profile.column_profile}
          columns={[
            { key: 'name', header: 'Column', render: (r) => <span className="font-mono text-xs text-slate-900">{r.name}</span> },
            { key: 'role', header: 'Role', render: (r) => <span className="capitalize">{r.role}</span> },
            { key: 'type', header: 'Type', render: (r) => <span className="capitalize">{r.type}</span> },
            { key: 'missing', header: 'Missing', align: 'right', render: (r) => `${formatNumber(r.missing)} (${formatPercent(r.missing_pct)})` },
            { key: 'invalid', header: 'Invalid', align: 'right', render: (r) => formatNumber(r.invalid) },
            { key: 'unique', header: 'Unique', align: 'right', render: (r) => formatNumber(r.unique) },
            { key: 'examples', header: 'Examples', render: (r) => <span className="text-xs text-slate-500">{r.examples.join(' · ')}</span> },
          ]}
        />
      </Card>

      <Card
        title="Revenue breakdown"
        subtitle="Ranked highest to lowest, with a table of the same figures"
        className="mt-6"
        action={
          available.length > 0 && (
            <div role="group" aria-label="Choose breakdown" className="flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
              {available.map((b) => (
                <button
                  key={b.key}
                  type="button"
                  aria-pressed={active?.key === b.key}
                  onClick={() => setSelected(b.key)}
                  className={`rounded-md px-3 py-1 text-xs font-medium focus-visible:outline-2 focus-visible:outline-indigo-600 ${
                    active?.key === b.key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          )
        }
      >
        {active ? (
          <div className="grid gap-6 xl:grid-cols-2">
            <HorizontalBarChart data={rows} label={`Bar chart of revenue by ${active.label.toLowerCase()}`} />
            <DataTable<BreakdownRow>
              caption={`Revenue by ${active.label.toLowerCase()}`}
              rowKey={(r) => r.name}
              rows={rows}
              columns={[
                { key: 'name', header: active.noun, render: (r) => <span className="font-medium text-slate-900">{r.name}</span> },
                { key: 'revenue', header: 'Revenue', align: 'right', render: (r) => formatCurrency(r.revenue) },
                { key: 'share', header: 'Share', align: 'right', render: (r) => formatPercent(r.share_pct) },
                { key: 'orders', header: 'Orders', align: 'right', render: (r) => formatNumber(r.orders) },
                { key: 'aov', header: 'Avg order', align: 'right', render: (r) => formatCurrencyPrecise(r.average_order_value) },
              ]}
            />
          </div>
        ) : (
          <p className="text-sm text-slate-500">No breakdowns are available: the dataset has none of the optional columns.</p>
        )}
        {kpis.unavailable.length > 0 && (
          <p className="mt-4 text-xs text-slate-500">
            Not available: {kpis.unavailable.map((u) => `${u.label} (needs ${u.missing_columns.join(', ')})`).join('; ')}.
          </p>
        )}
      </Card>

      {kpis.breakdowns.revenue_over_time && (
        <Card title="Monthly figures" className="mt-6">
          <DataTable<MonthRow>
            caption="Monthly revenue, orders and units"
            rowKey={(r) => r.period}
            rows={kpis.breakdowns.revenue_over_time}
            columns={[
              { key: 'label', header: 'Month' },
              { key: 'revenue', header: 'Revenue', align: 'right', render: (r) => formatCurrency(r.revenue) },
              { key: 'orders', header: 'Orders', align: 'right', render: (r) => formatNumber(r.orders) },
              { key: 'units', header: 'Units', align: 'right', render: (r) => formatNumber(r.units) },
            ]}
          />
        </Card>
      )}

      <Card title="Cleaned data preview" subtitle={`First ${analysis.preview.rows.length} rows after cleaning (revenue = quantity × unit price)`} className="mt-6">
        <DataTable<Record<string, string | number | null>>
          caption="Cleaned data preview"
          rowKey={(_, i) => String(i)}
          rows={analysis.preview.rows}
          columns={analysis.preview.columns.map((c) => ({
            key: c,
            header: c,
            align: ['quantity', 'unit_price', 'revenue'].includes(c) ? 'right' : 'left',
            render: (r) => (c === 'unit_price' || c === 'revenue' ? formatCurrencyPrecise(Number(r[c])) : String(r[c] ?? '')),
          }))}
        />
      </Card>
    </>
  )
}
