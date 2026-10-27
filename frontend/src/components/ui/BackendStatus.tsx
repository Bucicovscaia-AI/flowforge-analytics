import { useEffect, useState } from 'react'
import { getHealth } from '../../services/api'

type State = { status: 'loading' | 'ok' | 'error'; message: string }

const COLOURS: Record<State['status'], string> = {
  loading: 'bg-slate-100 text-slate-600',
  ok: 'bg-emerald-50 text-emerald-700',
  error: 'bg-rose-50 text-rose-700',
}

// Small status pill that shows whether the backend API is reachable.
export default function BackendStatus() {
  const [state, setState] = useState<State>({ status: 'loading', message: 'Checking API…' })

  useEffect(() => {
    getHealth()
      .then((data) => setState({ status: 'ok', message: `API online · v${data.version}` }))
      .catch(() => setState({ status: 'error', message: 'API offline' }))
  }, [])

  return (
    <span
      role="status"
      title={state.status === 'error' ? 'Start the FastAPI backend on port 8000' : undefined}
      className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium ${COLOURS[state.status]}`}
    >
      <span className={`h-2 w-2 rounded-full bg-current ${state.status === 'loading' ? 'animate-pulse' : ''}`} aria-hidden="true" />
      {state.message}
    </span>
  )
}
