import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { HistogramBin } from '../../api/types'
import { formatCompact, formatNumber } from '../../lib/format'
import { CHART } from './theme'
import { TooltipBox } from './ChartTooltip'

export function HistogramChart({ bins, valueLabel }: { bins: HistogramBin[]; valueLabel: string }) {
  const data = bins.map((bin) => ({ ...bin, label: `${formatCompact(bin.start)}–${formatCompact(bin.end)}` }))
  return (
    <div style={{ height: 280 }} role="img" aria-label={`Distribution of ${valueLabel} in ${bins.length} ranges`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 24, left: 0 }} barCategoryGap={2}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="label"
            tick={CHART.tick}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            interval="preserveStartEnd"
            minTickGap={16}
            label={{ value: valueLabel, position: 'insideBottom', offset: -16, style: { fill: '#64748b', fontSize: 12 } }}
          />
          <YAxis
            tick={CHART.tick}
            tickLine={false}
            axisLine={false}
            width={48}
            allowDecimals={false}
            label={{ value: 'Records', angle: -90, position: 'insideLeft', offset: 12, style: { fill: '#64748b', fontSize: 12, textAnchor: 'middle' } }}
          />
          <Tooltip
            cursor={{ fill: '#f1f5f9' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const bin = payload[0].payload as HistogramBin
              return (
                <TooltipBox
                  title={`${formatNumber(bin.start)} to ${formatNumber(bin.end)}`}
                  rows={[{ label: 'Records', value: formatNumber(bin.count), color: CHART.primary }]}
                />
              )
            }}
          />
          <Bar dataKey="count" fill={CHART.primary} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
