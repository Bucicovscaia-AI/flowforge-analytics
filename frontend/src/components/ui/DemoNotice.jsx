import Icon from './Icon'

// Shown on every page that displays sample figures, so they are never
// mistaken for genuine business findings.
export default function DemoNotice({ children }) {
  return (
    <div role="note" className="mb-6 flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <Icon name="info" className="mt-0.5 h-5 w-5 shrink-0" />
      <p>
        <strong className="font-semibold">Demonstration data.</strong>{' '}
        {children ?? 'All figures on this page come from a fabricated dataset and are not real business results.'}
      </p>
    </div>
  )
}
