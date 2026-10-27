import { Download, ExternalLink } from 'lucide-react'

import { api } from '../api/client'
import type { ReportFormat, ReportSummary } from '../api/types'
import { cn } from '../lib/cn'
import { Badge, type BadgeTone } from './ui/Badge'
import { DownloadLink } from './ui/Button'

const FORMAT_LABELS: Record<ReportFormat, string> = { html: 'HTML', pdf: 'PDF', csv: 'CSV', json: 'JSON' }
const FORMAT_ORDER: ReportFormat[] = ['html', 'pdf', 'csv', 'json']

export function ReportDownloads({ report, showOpen = true, compact = false }: { report: ReportSummary; showOpen?: boolean; compact?: boolean }) {
  return (
    <div className={cn('flex flex-wrap gap-1.5', compact && 'w-56')}>
      {showOpen && report.formats.includes('html') && (
        <DownloadLink href={api.reportUrl(report.id, 'html', true)} icon={ExternalLink} newTab>
          Open
        </DownloadLink>
      )}
      {FORMAT_ORDER.filter((format) => report.formats.includes(format)).map((format) => (
        <DownloadLink key={format} href={api.reportUrl(report.id, format)} variant="ghost" icon={Download}>
          {FORMAT_LABELS[format]}
        </DownloadLink>
      ))}
    </div>
  )
}

const STATUS_TONE: Record<ReportSummary['status'], BadgeTone> = { completed: 'success', partial: 'warning', failed: 'danger' }

export function ReportStatusBadge({ report }: { report: ReportSummary }) {
  return (
    <span title={report.error ?? undefined}>
      <Badge tone={STATUS_TONE[report.status]}>{report.status}</Badge>
    </span>
  )
}

export function InsightModeBadge({ mode }: { mode: ReportSummary['insight_mode'] }) {
  if (!mode) return <span className="text-slate-400">–</span>
  return <Badge tone={mode === 'ai' ? 'brand' : 'neutral'}>{mode === 'ai' ? 'AI' : 'Rule-based'}</Badge>
}
