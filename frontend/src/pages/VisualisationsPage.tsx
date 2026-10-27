import { Download } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/client'
import type { Aggregation, DatasetDetail, DatasetSummary, Granularity } from '../api/types'
import { BarBreakdownChart } from '../components/charts/BarBreakdownChart'
import { ChartCard } from '../components/charts/ChartCard'
import { HistogramChart } from '../components/charts/HistogramChart'
import { TrendChart } from '../components/charts/TrendChart'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { RequireDataset } from '../components/RequireDataset'
import { useValueFormatter } from '../components/useMetricFormatter'
import { Alert } from '../components/ui/Alert'
import { DownloadLink } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { SelectField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { SegmentedControl } from '../components/ui/Tabs'
import { useApp } from '../context/AppContext'
import { useApi } from '../hooks/useApi'
import { formatNumber, formatPercent } from '../lib/format'

type ChartKind = 'bar' | 'time' | 'distribution'

const AGGREGATIONS: { value: Aggregation; label: string }[] = [
  { value: 'sum', label: 'Sum' },
  { value: 'mean', label: 'Average' },
  { value: 'median', label: 'Median' },
  { value: 'min', label: 'Minimum' },
  { value: 'max', label: 'Maximum' },
  { value: 'count', label: 'Count of records' },
]

const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: 'auto', label: 'Automatic' },
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'quarter', label: 'Quarter' },
  { value: 'year', label: 'Year' },
]

function aggregationLabel(agg: Aggregation, value: string): string {
  if (agg === 'count' || !value) return 'Records'
  const name = AGGREGATIONS.find((item) => item.value === agg)?.label ?? agg
  return `${name} of ${value}`
}

function GroupedChart({ datasetId, groupBy, value, agg, topN, isCurrency }: { datasetId: string; groupBy: string; value: string; agg: Aggregation; topN: number; isCurrency: boolean }) {
  const { dataVersion } = useApp()
  const effectiveAgg = value ? agg : 'count'
  const result = useApi(`agg:${datasetId}:${dataVersion}:${groupBy}:${value}:${effectiveAgg}:${topN}`, () =>
    api.aggregate(datasetId, { group_by: groupBy, value: value || undefined, agg: effectiveAgg, top_n: topN }),
  )
  const format = useValueFormatter(isCurrency && effectiveAgg !== 'count')
  const label = aggregationLabel(effectiveAgg, value)
  const data = result.data?.rows ?? []
  return (
    <ChartCard
      title={`${label} by ${groupBy}`}
      description={result.data && result.data.total_groups > data.length ? `Top ${data.length} of ${result.data.total_groups} groups; the rest are left out` : undefined}
      actions={
        <DownloadLink href={api.aggregateCsvUrl(datasetId, { group_by: groupBy, value: value || undefined, agg: effectiveAgg })} icon={Download}>
          CSV
        </DownloadLink>
      }
      table={
        <TableContainer label={`${label} by ${groupBy}`}>
          <thead>
            <tr>
              <Th>{groupBy}</Th>
              <Th numeric>{label}</Th>
              <Th numeric>Records</Th>
              <Th numeric>Share</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <Tr key={row.group}>
                <Td>{row.group}</Td>
                <Td numeric>{format(row.value)}</Td>
                <Td numeric>{formatNumber(row.records)}</Td>
                <Td numeric>{formatPercent(row.share)}</Td>
              </Tr>
            ))}
          </tbody>
        </TableContainer>
      }
    >
      {result.loading && !result.data ? (
        <LoadingState />
      ) : result.error ? (
        <ErrorState error={result.error} onRetry={result.reload} />
      ) : data.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">There are no values to chart for this selection.</p>
      ) : (
        <BarBreakdownChart data={data} valueLabel={label} formatValue={format} />
      )}
    </ChartCard>
  )
}

function TimeChart({ datasetId, dateColumn, value, agg, granularity, isCurrency, title }: { datasetId: string; dateColumn: string; value: string; agg: Aggregation; granularity: Granularity; isCurrency: boolean; title?: string }) {
  const { dataVersion } = useApp()
  const effectiveAgg = value ? agg : 'count'
  const result = useApi(`ts:${datasetId}:${dataVersion}:${dateColumn}:${value}:${effectiveAgg}:${granularity}`, () =>
    api.timeSeries(datasetId, { date_column: dateColumn || undefined, value: value || undefined, agg: effectiveAgg, granularity }),
  )
  const format = useValueFormatter(isCurrency && effectiveAgg !== 'count')
  const label = aggregationLabel(effectiveAgg, value)
  const points = result.data?.points ?? []
  const partial = points.filter((point) => point.partial).length
  return (
    <ChartCard
      title={title ?? `${label} per ${result.data?.granularity ?? 'period'}`}
      description={result.data ? `${formatNumber(points.length)} ${result.data.granularity}s from ${dateColumn || 'the date column'}` : undefined}
      footer={
        result.data && (partial > 0 || result.data.excluded_rows > 0)
          ? [
              partial > 0 ? `${partial} partial period${partial === 1 ? '' : 's'} at the edges cover only part of the ${result.data.granularity}.` : '',
              result.data.excluded_rows > 0 ? `${formatNumber(result.data.excluded_rows)} rows without a valid date are left out.` : '',
            ]
              .filter(Boolean)
              .join(' ')
          : undefined
      }
      table={
        <TableContainer label={label}>
          <thead>
            <tr>
              <Th>Period</Th>
              <Th numeric>{label}</Th>
              <Th numeric>Records</Th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => (
              <Tr key={point.period}>
                <Td>
                  {point.label}
                  {point.partial && <span className="text-xs text-slate-500"> (partial)</span>}
                </Td>
                <Td numeric>{format(point.value)}</Td>
                <Td numeric>{formatNumber(point.records)}</Td>
              </Tr>
            ))}
          </tbody>
        </TableContainer>
      }
    >
      {result.loading && !result.data ? (
        <LoadingState />
      ) : result.error ? (
        <ErrorState error={result.error} onRetry={result.reload} />
      ) : points.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">There are no dated values to chart.</p>
      ) : (
        <TrendChart points={points} valueLabel={label} formatValue={format} />
      )}
    </ChartCard>
  )
}

function DistributionChart({ datasetId, column }: { datasetId: string; column: string }) {
  const { dataVersion } = useApp()
  const result = useApi(`dist:${datasetId}:${dataVersion}:${column}`, () => api.distribution(datasetId, column))
  const data = result.data
  return (
    <ChartCard
      title={`Distribution of ${column}`}
      description={data ? `${formatNumber(data.count)} values · median ${formatNumber(data.median)} · mean ${formatNumber(data.mean)}` : undefined}
      footer={data && data.excluded_rows > 0 ? `${formatNumber(data.excluded_rows)} rows without a valid number are left out.` : undefined}
      table={
        data && (
          <TableContainer label={`Distribution of ${column}`}>
            <thead>
              <tr>
                <Th>Range</Th>
                <Th numeric>Records</Th>
              </tr>
            </thead>
            <tbody>
              {data.bins.map((bin, index) => (
                <Tr key={index}>
                  <Td>
                    {formatNumber(bin.start)} to {formatNumber(bin.end)}
                  </Td>
                  <Td numeric>{formatNumber(bin.count)}</Td>
                </Tr>
              ))}
            </tbody>
          </TableContainer>
        )
      }
    >
      {result.loading && !data ? <LoadingState /> : result.error ? <ErrorState error={result.error} onRetry={result.reload} /> : data && <HistogramChart bins={data.bins} valueLabel={column} />}
    </ChartCard>
  )
}

function ChartBuilder({ detail }: { detail: DatasetDetail }) {
  const numeric = detail.columns.filter((column) => column.inferred_type === 'numeric').map((column) => column.name)
  const dates = detail.columns.filter((column) => column.inferred_type === 'datetime').map((column) => column.name)
  const groupable = detail.columns
    .filter((column) => ['categorical', 'boolean', 'text'].includes(column.inferred_type) || (column.inferred_type === 'numeric' && column.distinct_count <= 30))
    .map((column) => column.name)

  const kinds: { value: ChartKind; label: string }[] = [
    ...(groupable.length ? [{ value: 'bar' as const, label: 'Bar by group' }] : []),
    ...(dates.length ? [{ value: 'time' as const, label: 'Over time' }] : []),
    ...(numeric.length ? [{ value: 'distribution' as const, label: 'Distribution' }] : []),
  ]

  const [kind, setKind] = useState<ChartKind>(kinds[0]?.value ?? 'bar')
  const [groupBy, setGroupBy] = useState(detail.roles.category ?? groupable[0] ?? '')
  const [dateColumn, setDateColumn] = useState(detail.roles.date ?? dates[0] ?? '')
  const [value, setValue] = useState(detail.roles.revenue ?? numeric[0] ?? '')
  const [agg, setAgg] = useState<Aggregation>('sum')
  const [granularity, setGranularity] = useState<Granularity>('auto')
  const [topN, setTopN] = useState(10)
  const [distColumn, setDistColumn] = useState(detail.roles.revenue ?? numeric[0] ?? '')

  if (kinds.length === 0) {
    return <Alert tone="info">This dataset has no columns that can be charted. Charts need a categorical, date or numeric column.</Alert>
  }

  const isCurrency = value !== '' && value === detail.roles.revenue

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Build a chart" description="Choose what to plot. Values are calculated on the server from the current working copy." />
        <CardBody className="space-y-4">
          <SegmentedControl label="Chart type" value={kind} onChange={setKind} options={kinds} />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kind === 'bar' && (
              <SelectField label="Group by" value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>
                {groupable.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </SelectField>
            )}
            {kind === 'time' && (
              <SelectField label="Date column" value={dateColumn} onChange={(event) => setDateColumn(event.target.value)}>
                {dates.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </SelectField>
            )}
            {kind !== 'distribution' && (
              <>
                <SelectField label="Value" value={value} onChange={(event) => setValue(event.target.value)}>
                  <option value="">Number of records</option>
                  {numeric.map((column) => (
                    <option key={column}>{column}</option>
                  ))}
                </SelectField>
                <SelectField label="Calculation" value={value ? agg : 'count'} disabled={!value} onChange={(event) => setAgg(event.target.value as Aggregation)}>
                  {AGGREGATIONS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </SelectField>
              </>
            )}
            {kind === 'bar' && (
              <SelectField label="Groups shown" value={topN} onChange={(event) => setTopN(Number(event.target.value))}>
                {[5, 10, 15, 25].map((count) => (
                  <option key={count} value={count}>
                    Top {count}
                  </option>
                ))}
              </SelectField>
            )}
            {kind === 'time' && (
              <SelectField label="Period" value={granularity} onChange={(event) => setGranularity(event.target.value as Granularity)}>
                {GRANULARITIES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>
            )}
            {kind === 'distribution' && (
              <SelectField label="Numeric column" value={distColumn} onChange={(event) => setDistColumn(event.target.value)}>
                {numeric.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </SelectField>
            )}
          </div>
        </CardBody>
      </Card>
      {kind === 'bar' && groupBy && <GroupedChart datasetId={detail.id} groupBy={groupBy} value={value} agg={agg} topN={topN} isCurrency={isCurrency} />}
      {kind === 'time' && dateColumn && (
        <TimeChart datasetId={detail.id} dateColumn={dateColumn} value={value} agg={agg} granularity={granularity} isCurrency={isCurrency} />
      )}
      {kind === 'distribution' && distColumn && <DistributionChart datasetId={detail.id} column={distColumn} />}
    </div>
  )
}

function DefaultCharts({ detail }: { detail: DatasetDetail }) {
  const [granularity, setGranularity] = useState<Granularity>('auto')
  const { date, revenue, category, region } = detail.roles
  const value = revenue ?? ''
  const group = category ?? region
  if (!date && !group) return null
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      {date && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <SegmentedControl
              label="Trend period"
              value={granularity}
              onChange={setGranularity}
              options={GRANULARITIES.filter((item) => ['auto', 'week', 'month', 'quarter'].includes(item.value))}
            />
          </div>
          <TimeChart
            datasetId={detail.id}
            dateColumn={date}
            value={value}
            agg="sum"
            granularity={granularity}
            isCurrency={Boolean(revenue)}
            title={revenue ? 'Revenue over time' : 'Records over time'}
          />
        </div>
      )}
      {group && <GroupedChart datasetId={detail.id} groupBy={group} value={value} agg="sum" topN={10} isCurrency={Boolean(revenue)} />}
    </div>
  )
}

function VisualisationsContent({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion } = useApp()
  const detail = useApi(`detail:${dataset.id}:${dataVersion}`, () => api.getDataset(dataset.id))
  if (detail.loading && !detail.data) return <LoadingState />
  if (detail.error || !detail.data) return <ErrorState error={detail.error} onRetry={detail.reload} />
  return (
    <div className="space-y-8">
      <DefaultCharts detail={detail.data} />
      <ChartBuilder key={detail.data.id} detail={detail.data} />
    </div>
  )
}

export function VisualisationsPage() {
  const { selected } = useApp()
  return (
    <>
      <PageHeader
        title="Visualisations"
        description="Charts of the selected dataset. Every chart has a table view with the exact values, and grouped results can be downloaded as CSV."
        eyebrow={selected && <DatasetEyebrow dataset={selected} />}
      />
      <RequireDataset purpose="chart it">{(dataset) => <VisualisationsContent dataset={dataset} />}</RequireDataset>
    </>
  )
}
