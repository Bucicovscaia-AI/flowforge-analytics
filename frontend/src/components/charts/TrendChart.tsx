import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { TimePoint } from '../../api/types'
import { formatCompact, formatNumber } from '../../lib/format'
import { CHART } from './theme'
import { TooltipBox } from './ChartTooltip'

interface TrendChartProps {
  points: TimePoint[]
  valueLabel: string
  formatValue: (value: number | null) => string
  height?: number
}

function shortLabel(label: string): string {
  return label.replace('Week of ', '')
}

export function TrendChart({ points, valueLabel, formatValue, height = 280 }: TrendChartProps) {
  const data = points.map((point) => ({ ...point, short: shortLabel(point.label) }))
  return (
    <div style={{ height }} role="img" aria-label={`${valueLabel} over time, ${points.length} periods`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART.primary} stopOpacity={0.18} />
              <stop offset="100%" stopColor={CHART.primary} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="short" tick={CHART.tick} tickLine={false} axisLine={{ stroke: CHART.grid }} minTickGap={24} />
          <YAxis
            tick={CHART.tick}
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={(value: number) => formatCompact(value)}
            label={{ value: valueLabel, angle: -90, position: 'insideLeft', offset: 10, style: { fill: '#64748b', fontSize: 12, textAnchor: 'middle' } }}
          />
          <Tooltip
            cursor={{ stroke: CHART.axis, strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const point = payload[0].payload as TimePoint
              return (
                <TooltipBox
                  title={point.label}
                  rows={[
                    { label: valueLabel, value: formatValue(point.value), color: CHART.primary },
                    { label: 'Records', value: formatNumber(point.records) },
                  ]}
                  note={point.partial ? 'Partial period: data does not cover the whole period.' : undefined}
                />
              )
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART.primary}
            strokeWidth={2}
            fill="url(#trendFill)"
            dot={{ r: 3, fill: CHART.primary, strokeWidth: 0 }}
            activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
