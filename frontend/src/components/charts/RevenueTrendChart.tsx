import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { MonthRow } from '../../types'
import { formatCurrency, formatCurrencyShort } from '../../utils/format'
import { SERIES_COLOURS, axisProps, gridProps, tooltipProps } from './chartTheme'

export default function RevenueTrendChart({ data }: { data: MonthRow[] }) {
  return (
    <div className="h-72 w-full" role="img" aria-label="Line chart of monthly revenue">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis tickFormatter={formatCurrencyShort} width={52} {...axisProps} />
          <Tooltip {...tooltipProps} formatter={(value) => [formatCurrency(Number(value)), 'Revenue']} />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke={SERIES_COLOURS[0]}
            strokeWidth={2}
            isAnimationActive={false}
            dot={{ r: 4, fill: SERIES_COLOURS[0], stroke: '#fff', strokeWidth: 2 }}
            activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
