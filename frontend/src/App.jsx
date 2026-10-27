import BackendStatus from './components/BackendStatus'

// Stage 1 placeholder. Stage 2 replaces this with the full dashboard layout
// (sidebar, top bar and the seven pages).
export default function App() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-4">
      <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600">Stage 1 scaffold</p>
      <h1 className="text-4xl font-bold tracking-tight">FlowForge Analytics</h1>
      <p className="text-lg text-slate-600">
        An automation platform that turns a business CSV dataset into KPIs, charts and a downloadable report.
      </p>
      <div>
        <BackendStatus />
      </div>
    </main>
  )
}
