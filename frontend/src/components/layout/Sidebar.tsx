import { NavLink } from 'react-router-dom'

import { cn } from '../../lib/cn'
import { Wordmark } from './Logo'
import { NAVIGATION } from './navigation'

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-ink-950 text-slate-300">
      <div className="flex h-16 items-center px-5">
        <Wordmark inverted />
      </div>
      <nav aria-label="Main navigation" className="flex-1 overflow-y-auto px-3 pb-6">
        {NAVIGATION.map((group) => (
          <div key={group.label} className="mt-5 first:mt-2">
            <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">{group.label}</p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === '/' || item.to === '/reports'}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive ? 'bg-ink-800 text-white' : 'text-slate-300 hover:bg-ink-900 hover:text-white',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon className={cn('size-4', isActive ? 'text-brand-300' : 'text-slate-500')} aria-hidden />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="border-t border-ink-800 px-5 py-4 text-xs text-slate-500">Local workspace · data stays on this server</div>
    </div>
  )
}
