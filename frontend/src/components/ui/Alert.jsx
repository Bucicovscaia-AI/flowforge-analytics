import Icon from './Icon'

const variants = {
  error: { classes: 'border-rose-200 bg-rose-50 text-rose-800', icon: 'error', role: 'alert' },
  info: { classes: 'border-sky-200 bg-sky-50 text-sky-900', icon: 'info', role: 'status' },
  success: { classes: 'border-emerald-200 bg-emerald-50 text-emerald-800', icon: 'check', role: 'status' },
}

export default function Alert({ variant = 'info', title, children }) {
  const { classes, icon, role } = variants[variant]
  return (
    <div role={role} className={`flex gap-3 rounded-lg border px-4 py-3 text-sm ${classes}`}>
      <Icon name={icon} className="mt-0.5 h-5 w-5 shrink-0" />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? 'mt-1' : ''}>{children}</div>
      </div>
    </div>
  )
}
