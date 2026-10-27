import { NavLink } from 'react-router-dom'
import Icon from '../ui/Icon'
import { NAV_ITEMS } from './navigation'

export default function Sidebar({ onNavigate }) {
  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-300">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-white">
          <Icon name="bolt" className="h-5 w-5" />
        </span>
        <span className="text-base font-semibold text-white">FlowForge</span>
        <span className="text-base font-light text-slate-400">Analytics</span>
      </div>

      <nav aria-label="Main" className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400 ${
                isActive ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="m-3 rounded-lg bg-slate-800/70 p-3 text-xs text-slate-400">
        <p className="font-medium text-slate-200">Demo workspace</p>
        <p className="mt-1">Uses fabricated sample data only.</p>
      </div>
    </div>
  )
}
