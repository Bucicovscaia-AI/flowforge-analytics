import Icon from './Icon'

// Shown whenever the figures on a page come from a dataset marked as
// synthetic, so they are never mistaken for genuine business findings.
export default function SyntheticNotice({ fileName }: { fileName: string }) {
  return (
    <div role="note" className="mb-6 flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <Icon name="info" className="mt-0.5 h-5 w-5 shrink-0" />
      <p>
        <strong className="font-semibold">Synthetic data.</strong> {fileName} is a fabricated demonstration dataset. The figures
        below were calculated from it by FlowForge, but they do not describe a real business.
      </p>
    </div>
  )
}
