import type { ReactNode } from 'react'
import Icon from './Icon'

interface KpiCardProps {
  label: string
  value: ReactNode
  detail?: ReactNode
  icon?: string
}

export default function KpiCard({ label, value, detail, icon }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {icon && (
          <span className="hidden h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 sm:flex">
            <Icon name={icon} className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className="mt-2 text-xl font-semibold sm:text-2xl tracking-tight text-slate-900 tabular-nums">{value}</p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </div>
  )
}
