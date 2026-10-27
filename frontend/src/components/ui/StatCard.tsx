import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: LucideIcon
  className?: string
}

export function StatCard({ label, value, hint, icon: Icon, className }: StatCardProps) {
  return (
    <div className={cn('rounded-xl border border-slate-200 bg-white p-4 shadow-card', className)}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        {Icon && <Icon className="size-4 text-slate-400" aria-hidden />}
      </div>
      <p className={cn('tabular mt-2 font-semibold tracking-tight text-slate-900', String(value).length > 16 ? 'text-lg leading-tight' : 'truncate text-2xl')}>{value}</p>
      {hint && <p className="mt-1 text-xs leading-snug text-slate-500">{hint}</p>}
    </div>
  )
}
