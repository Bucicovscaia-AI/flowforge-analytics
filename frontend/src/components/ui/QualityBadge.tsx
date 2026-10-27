import { Badge, type BadgeTone } from './Badge'

// eslint-disable-next-line react-refresh/only-export-components
export function qualityTone(score: number | null | undefined): BadgeTone {
  if (score === null || score === undefined) return 'neutral'
  if (score >= 95) return 'success'
  if (score >= 85) return 'brand'
  if (score >= 70) return 'warning'
  return 'danger'
}

export function QualityBadge({ score, grade }: { score: number | null | undefined; grade?: string | null }) {
  if (score === null || score === undefined) return <Badge>Not assessed</Badge>
  return (
    <Badge tone={qualityTone(score)}>
      {score.toFixed(1)}
      {grade ? ` · ${grade}` : ''}
    </Badge>
  )
}

const SEVERITY_TONES = { error: 'danger', warning: 'warning', info: 'info' } as const
const SEVERITY_LABELS = { error: 'Error', warning: 'Warning', info: 'Info' } as const

export function SeverityBadge({ severity }: { severity: 'error' | 'warning' | 'info' }) {
  return <Badge tone={SEVERITY_TONES[severity]}>{SEVERITY_LABELS[severity]}</Badge>
}
