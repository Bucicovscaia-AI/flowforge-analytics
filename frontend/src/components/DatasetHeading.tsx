import type { DatasetSummary } from '../api/types'
import { formatDateTime, formatNumber } from '../lib/format'
import { Badge, SampleBadge } from './ui/Badge'
import { QualityBadge } from './ui/QualityBadge'

export function DatasetEyebrow({ dataset }: { dataset: DatasetSummary }) {
  return (
    <>
      <Badge tone="brand">{dataset.name}</Badge>
      {dataset.is_sample && <SampleBadge />}
      <span className="text-xs text-slate-500">
        {formatNumber(dataset.row_count)} rows · {dataset.column_count} columns · imported {formatDateTime(dataset.created_at)}
      </span>
      <QualityBadge score={dataset.quality_score} grade={dataset.quality_grade} />
    </>
  )
}
