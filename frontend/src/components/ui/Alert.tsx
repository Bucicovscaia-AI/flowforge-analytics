import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const STYLES: Record<Tone, { box: string; icon: typeof Info }> = {
  info: { box: 'border-sky-200 bg-sky-50 text-sky-900', icon: Info },
  success: { box: 'border-emerald-200 bg-emerald-50 text-emerald-900', icon: CheckCircle2 },
  warning: { box: 'border-amber-200 bg-amber-50 text-amber-900', icon: AlertTriangle },
  danger: { box: 'border-red-200 bg-red-50 text-red-900', icon: XCircle },
}

interface AlertProps {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
  actions?: ReactNode
  className?: string
}

export function Alert({ tone = 'info', title, children, actions, className }: AlertProps) {
  const { box, icon: Icon } = STYLES[tone]
  return (
    <div role={tone === 'danger' ? 'alert' : 'note'} className={cn('flex gap-3 rounded-lg border px-4 py-3 text-sm', box, className)}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cn(title ? 'mt-0.5' : '', 'leading-relaxed [&_a]:font-medium [&_a]:underline')}>{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  )
}
