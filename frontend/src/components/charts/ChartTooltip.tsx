import type { ReactNode } from 'react'

export interface TooltipRow {
  label: string
  value: ReactNode
  color?: string
}

export function TooltipBox({ title, rows, note }: { title: ReactNode; rows: TooltipRow[]; note?: ReactNode }) {
  return (
    <div className="min-w-44 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-raised">
      <p className="mb-1.5 font-semibold text-slate-900">{title}</p>
      <dl className="space-y-1">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-4">
            <dt className="flex items-center gap-1.5 text-slate-500">
              {row.color && <span className="size-2 rounded-full" style={{ backgroundColor: row.color }} aria-hidden />}
              {row.label}
            </dt>
            <dd className="tabular font-medium text-slate-900">{row.value}</dd>
          </div>
        ))}
      </dl>
      {note && <p className="mt-1.5 text-amber-700">{note}</p>}
    </div>
  )
}
