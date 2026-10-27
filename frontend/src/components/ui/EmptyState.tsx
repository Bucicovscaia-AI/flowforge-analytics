import type { ReactNode } from 'react'
import Icon from './Icon'

interface EmptyStateProps {
  icon?: string
  title: string
  children?: ReactNode
  action?: ReactNode
}

export default function EmptyState({ icon = 'file', title, children, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <Icon name={icon} className="h-6 w-6" />
      </span>
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{children}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
