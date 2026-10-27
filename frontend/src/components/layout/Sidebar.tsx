import { NavLink } from 'react-router-dom'
import { useAnalysis } from '../../context/analysisContext'
import Icon from '../ui/Icon'
import { NAV_ITEMS } from './navigation'

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { analysis } = useAnalysis()

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
          <Icon name="bolt" className="h-5 w-5" />
        </span>
        <span className="text-base font-semibold text-slate-900">FlowForge</span>
        <span className="text-base font-light text-slate-500">Analytics</span>
      </div>

      <nav aria-label="Main" className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-indigo-500 ${
                isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="m-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
        <p className="font-medium text-slate-700">Current dataset</p>
        {analysis ? (
          <>
            <p className="mt-1 truncate text-slate-900" title={analysis.dataset.file_name}>
              {analysis.dataset.file_name}
            </p>
            <p className="mt-0.5">
              {analysis.quality.rows_analysed.toLocaleString('en-GB')} rows · {analysis.dataset.synthetic ? 'synthetic' : 'user data'}
            </p>
          </>
        ) : (
          <p className="mt-1">None loaded yet.</p>
        )}
      </div>
    </div>
  )
}
