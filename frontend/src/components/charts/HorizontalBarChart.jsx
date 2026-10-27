import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatCurrency, formatCurrencyShort } from '../../utils/format'
import { SERIES_COLOURS, axisProps, gridProps, tooltipProps } from './chartTheme'

// Ranked horizontal bars: easier to read than a pie chart when comparing
// a handful of categories, and long labels fit on the left.
export default function HorizontalBarChart({ data, valueKey = 'revenue', label, colour = SERIES_COLOURS[0] }) {
  const height = Math.max(160, data.length * 44)
  return (
    <div className="w-full" style={{ height }} role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 56, left: 0, bottom: 0 }} barCategoryGap={10}>
          <CartesianGrid {...gridProps} vertical horizontal={false} />
          <XAxis type="number" tickFormatter={formatCurrencyShort} {...axisProps} />
          <YAxis type="category" dataKey="name" width={104} {...axisProps} />
          <Tooltip {...tooltipProps} formatter={(value) => [formatCurrency(value), 'Revenue']} />
          <Bar dataKey={valueKey} fill={colour} radius={[0, 4, 4, 0]} maxBarSize={24}>
            <LabelList dataKey={valueKey} position="right" formatter={formatCurrencyShort} style={{ fill: '#475569', fontSize: 12 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
