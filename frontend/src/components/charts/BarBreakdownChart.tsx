import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { formatCompact, formatNumber, formatPercent } from '../../lib/format'
import { CHART } from './theme'
import { TooltipBox } from './ChartTooltip'

export interface BarDatum {
  group: string
  value: number | null
  records: number
  share: number | null
}

interface BarBreakdownChartProps {
  data: BarDatum[]
  valueLabel: string
  formatValue: (value: number | null) => string
  color?: string
}

/** Horizontal bars, which keep long category names readable on every screen size. */
export function BarBreakdownChart({ data, valueLabel, formatValue, color = CHART.primary }: BarBreakdownChartProps) {
  const height = Math.max(160, data.length * 34 + 40)
  const longest = Math.max(...data.map((row) => row.group.length), 4)
  const axisWidth = Math.min(160, Math.max(64, longest * 7))
  return (
    <div style={{ height }} role="img" aria-label={`${valueLabel} by group, ${data.length} groups`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }} barCategoryGap={6}>
          <CartesianGrid stroke={CHART.grid} horizontal={false} />
          <XAxis type="number" tick={CHART.tick} tickLine={false} axisLine={false} tickFormatter={(value: number) => formatCompact(value)} />
          <YAxis
            type="category"
            dataKey="group"
            tick={CHART.tick}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            width={axisWidth}
            tickFormatter={(value: string) => (value.length > 22 ? `${value.slice(0, 21)}…` : value)}
          />
          <Tooltip
            cursor={{ fill: '#f1f5f9' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const row = payload[0].payload as BarDatum
              return (
                <TooltipBox
                  title={row.group}
                  rows={[
                    { label: valueLabel, value: formatValue(row.value), color },
                    { label: 'Records', value: formatNumber(row.records) },
                    ...(row.share !== null ? [{ label: 'Share of total', value: formatPercent(row.share) }] : []),
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} maxBarSize={22} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
