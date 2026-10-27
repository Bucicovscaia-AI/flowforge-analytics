import Icon from './Icon'

// Shows where a dataset is in the processing pipeline.
// Each step has a state: 'done', 'current' or 'pending'.
export default function PipelineSteps({ steps }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-5">
      {steps.map((step, index) => (
        <li key={step.label} className="flex items-center gap-3 sm:flex-col sm:items-start">
          <span
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
              step.state === 'done'
                ? 'bg-indigo-600 text-white'
                : step.state === 'current'
                  ? 'bg-indigo-50 text-indigo-700 ring-2 ring-indigo-600'
                  : 'bg-slate-100 text-slate-500'
            }`}
          >
            {step.state === 'done' ? <Icon name="check" className="h-4 w-4" /> : index + 1}
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
