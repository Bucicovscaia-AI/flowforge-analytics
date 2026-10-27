import { cn } from '../../lib/cn'

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('size-8', className)} aria-hidden>
      <rect width="32" height="32" rx="8" fill="#2a78d6" />
      <path d="M9 21.5 15 15.5l3.5 3.5L24 12" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="24" cy="12" r="2.2" fill="#fff" />
    </svg>
  )
}

export function Wordmark({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="leading-none">
        <span className={cn('block text-[15px] font-semibold tracking-tight', inverted ? 'text-white' : 'text-slate-900')}>
          Flow<span className={inverted ? 'text-brand-300' : 'text-brand-600'}>Forge</span>
        </span>
        <span className={cn('mt-1 block text-[10px] font-medium uppercase tracking-[0.18em]', inverted ? 'text-slate-400' : 'text-slate-500')}>
          Analytics
        </span>
      </span>
    </span>
  )
}
