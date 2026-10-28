import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export function TableContainer({ children, className, label }: { children: ReactNode; className?: string; label?: string }) {
  return (
    <div className={cn('relative overflow-x-auto', className)} role={label ? 'region' : undefined} aria-label={label} tabIndex={label ? 0 : undefined}>
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  )
}

export function Th({ className, numeric, ...props }: ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        'border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 whitespace-nowrap',
        numeric && 'text-right',
        className,
      )}
      {...props}
    />
  )
}

export function Td({ className, numeric, ...props }: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return <td className={cn('border-b border-slate-100 px-4 py-2.5 align-top text-slate-700', numeric && 'tabular text-right', className)} {...props} />
}

export function Tr({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn('hover:bg-slate-50/60', className)} {...props} />
}
