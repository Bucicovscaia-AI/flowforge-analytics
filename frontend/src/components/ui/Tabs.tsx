import { cn } from '../../lib/cn'

interface TabsProps<T extends string> {
  value: T
  onChange: (value: T) => void
  options: { value: T; label: string }[]
  label: string
}

export function SegmentedControl<T extends string>({ value, onChange, options, label }: TabsProps<T>) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-md px-3 py-1 text-sm font-medium transition-colors',
            option.value === value ? 'bg-white text-slate-900 shadow-card' : 'text-slate-600 hover:text-slate-900',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
