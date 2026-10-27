import { type ReactNode, useCallback, useMemo, useRef, useState } from 'react'
import Icon from '../components/ui/Icon'
import { type Toast, ToastContext, type ToastVariant } from './toastContext'

const STYLES: Record<ToastVariant, { classes: string; icon: string }> = {
  success: { classes: 'border-emerald-200 text-emerald-800', icon: 'check' },
  error: { classes: 'border-rose-200 text-rose-800', icon: 'error' },
  info: { classes: 'border-sky-200 text-sky-900', icon: 'info' },
}

// Notifications appear bottom-right and disappear after a few seconds.
// Errors stay a little longer so they can be read.
export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), [])

  const notify = useCallback(
    (variant: ToastVariant, title: string, message?: string) => {
      const id = nextId.current++
      setToasts((all) => [...all.slice(-3), { id, variant, title, message }])
      setTimeout(() => dismiss(id), variant === 'error' ? 8000 : 4500)
    },
    [dismiss],
  )

  const api = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-end gap-2 sm:left-auto sm:w-96">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.variant === 'error' ? 'alert' : 'status'}
            className={`pointer-events-auto flex w-full gap-3 rounded-lg border bg-white px-4 py-3 text-sm shadow-lg ${STYLES[toast.variant].classes}`}
          >
            <Icon name={STYLES[toast.variant].icon} className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{toast.title}</p>
              {toast.message && <p className="mt-0.5 text-slate-600">{toast.message}</p>}
            </div>
            <button type="button" onClick={() => dismiss(toast.id)} className="-m-1 rounded p-1 text-slate-400 hover:text-slate-700" aria-label="Dismiss notification">
              <Icon name="close" className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
