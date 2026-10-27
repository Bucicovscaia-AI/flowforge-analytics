import { useLocation } from 'react-router-dom'
import { useAnalysis } from '../../context/analysisContext'
import BackendStatus from '../ui/BackendStatus'
import Icon from '../ui/Icon'
import { NAV_ITEMS } from './navigation'

export default function TopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { pathname } = useLocation()
  const { analysis } = useAnalysis()
  const current = NAV_ITEMS.find((item) => item.to === pathname)

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        className="-ml-1 rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
        aria-label="Open navigation menu"
      >
        <Icon name="menu" className="h-6 w-6" />
      </button>
      <p className="truncate text-sm text-slate-500">
        Workspace <span className="mx-1 text-slate-300">/</span>
        <span className="font-medium text-slate-900">{current?.label ?? 'Not found'}</span>
      </p>
      <div className="ml-auto flex items-center gap-3">
        {analysis?.dataset.synthetic && (
          <span className="hidden rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900 sm:inline">Synthetic data</span>
        )}
        <BackendStatus />
      </div>
    </header>
  )
}
