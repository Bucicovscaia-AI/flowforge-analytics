// Shared chart styling. Series colours come from a colour-blind-checked
// palette; axes and gridlines stay light so the data stands out.
export const SERIES_COLOURS = ['#2a78d6', '#eb6834', '#1baf7a']

export const axisProps = {
  stroke: '#94a3b8',
  tick: { fill: '#64748b', fontSize: 12 },
  tickLine: false,
  axisLine: false,
}

export const gridProps = { stroke: '#e2e8f0', strokeDasharray: '0', vertical: false }

export const tooltipProps = {
  cursor: { stroke: '#cbd5e1', fill: 'rgba(148, 163, 184, 0.12)' },
  contentStyle: { borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(15, 23, 42, 0.08)', fontSize: 13 },
  labelStyle: { color: '#0f172a', fontWeight: 600 },
}
