import { Menu } from 'lucide-react'
import { useId } from 'react'

import { useApp } from '../../context/AppContext'
import { formatNumber } from '../../lib/format'
import { Badge } from '../ui/Badge'

function ConnectionStatus() {
  const { system, systemError } = useApp()
  if (systemError) return <Badge tone="danger">API unreachable</Badge>
  if (!system) return <Badge>Connecting…</Badge>
  return (
    <Badge tone="success">
      <span className="size-1.5 rounded-full bg-emerald-500" aria-hidden />
      API connected
    </Badge>
  )
}

function DatasetSwitcher() {
  const { datasets, selected, selectDataset } = useApp()
  const id = useId()
  if (!datasets.length || !selected) {
    return <span className="text-sm text-slate-500">No dataset selected</span>
  }
  return (
    <div className="flex min-w-0 items-center gap-2">
      <label htmlFor={id} className="hidden text-sm font-medium text-slate-500 md:block">
        Dataset
      </label>
      <select
        id={id}
        value={selected.id}
        onChange={(event) => selectDataset(event.target.value)}
        className="h-9 min-w-0 max-w-[16rem] truncate rounded-lg border border-slate-300 bg-white pl-3 pr-8 text-sm font-medium text-slate-800 shadow-card focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 sm:max-w-xs"
      >
        {datasets.map((dataset) => (
          <option key={dataset.id} value={dataset.id}>
            {dataset.name} ({formatNumber(dataset.row_count)} rows)
          </option>
        ))}
      </select>
    </div>
  )
}

export function TopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  return (
    <div className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        className="-ml-1 rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="size-5" />
      </button>
      <DatasetSwitcher />
      <div className="ml-auto hidden sm:block">
        <ConnectionStatus />
      </div>
    </div>
  )
}
