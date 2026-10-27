import Icon from './Icon'

// Shows where a dataset is in the processing pipeline.
// Each step has a state: 'done', 'current', 'pending' or 'error'.
export interface PipelineStep {
  label: string
  description: string
  state: 'done' | 'current' | 'pending' | 'error'
}

const CIRCLE: Record<PipelineStep['state'], string> = {
  done: 'bg-indigo-600 text-white',
  error: 'bg-rose-600 text-white',
  current: 'bg-indigo-50 text-indigo-700 ring-2 ring-indigo-600',
  pending: 'bg-slate-100 text-slate-500',
}

export default function PipelineSteps({ steps }: { steps: PipelineStep[] }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-5">
      {steps.map((step, index) => (
        <li key={step.label} className="flex items-center gap-3 sm:flex-col sm:items-start">
          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${CIRCLE[step.state]}`}>
            {step.state === 'done' ? (
              <Icon name="check" className="h-4 w-4" />
            ) : step.state === 'error' ? (
              <Icon name="close" className="h-4 w-4" />
            ) : (
              index + 1
            )}
            <span className="sr-only">{` (${step.state})`}</span>
          </span>
          <div>
            <p className="text-sm font-medium text-slate-900">{step.label}</p>
            <p className="text-xs text-slate-500">{step.description}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
