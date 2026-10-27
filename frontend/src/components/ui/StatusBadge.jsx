import Icon from './Icon'

// Status is shown with colour, an icon and a text label, so it is never
// communicated by colour alone (accessibility).
const variants = {
  success: { classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', icon: 'check' },
  warning: { classes: 'bg-amber-50 text-amber-800 ring-amber-600/20', icon: 'warning' },
  error: { classes: 'bg-rose-50 text-rose-700 ring-rose-600/20', icon: 'error' },
  neutral: { classes: 'bg-slate-100 text-slate-700 ring-slate-500/20', icon: 'info' },
  prototype: { classes: 'bg-violet-50 text-violet-700 ring-violet-600/20', icon: 'info' },
}

export default function StatusBadge({ variant = 'neutral', children }) {
  const { classes, icon } = variants[variant]
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${classes}`}>
      <Icon name={icon} className="h-3.5 w-3.5" />
      {children}
    </span>
  )
}
