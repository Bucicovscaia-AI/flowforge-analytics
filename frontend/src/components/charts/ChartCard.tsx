import { useState, type ReactNode } from 'react'

import { Card, CardBody, CardHeader } from '../ui/Card'
import { SegmentedControl } from '../ui/Tabs'

interface ChartCardProps {
  title: string
  description?: ReactNode
  actions?: ReactNode
  table?: ReactNode
  footer?: ReactNode
  children: ReactNode
  className?: string
}

/** A chart with an optional accessible table view of the same data. */
export function ChartCard({ title, description, actions, table, footer, children, className }: ChartCardProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  return (
    <Card className={className}>
      <CardHeader
        title={title}
        description={description}
        actions={
          <>
            {actions}
            {table && (
              <SegmentedControl
                label={`${title} view`}
                value={view}
                onChange={setView}
                options={[
                  { value: 'chart', label: 'Chart' },
                  { value: 'table', label: 'Table' },
                ]}
              />
            )}
          </>
        }
      />
      <CardBody>{view === 'table' && table ? <div className="max-h-96 overflow-auto">{table}</div> : children}</CardBody>
      {footer && <div className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">{footer}</div>}
    </Card>
  )
}
