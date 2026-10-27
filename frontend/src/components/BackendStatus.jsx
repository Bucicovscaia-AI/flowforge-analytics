import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'

// Small status pill that shows whether the backend is reachable.
export default function BackendStatus() {
  const [state, setState] = useState({ status: 'loading', message: 'Checking backend…' })

  useEffect(() => {
    getHealth()
      .then((data) => setState({ status: 'ok', message: `Backend online (v${data.version})` }))
      .catch((error) => setState({ status: 'error', message: error.message }))
  }, [])

  const colours = {
    loading: 'bg-slate-100 text-slate-600',
    ok: 'bg-emerald-50 text-emerald-700',
    error: 'bg-rose-50 text-rose-700',
  }

  return (
    <span
      role="status"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${colours[state.status]}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
      {state.message}
    </span>
  )
}
