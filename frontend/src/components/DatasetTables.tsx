import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/client'
import type { ColumnProfile, ColumnType } from '../api/types'
import { useApp } from '../context/AppContext'
import { useApi } from '../hooks/useApi'
import { formatNumber, formatPercent } from '../lib/format'
import { Badge, type BadgeTone } from './ui/Badge'
import { Button } from './ui/Button'
import { ErrorState, LoadingState } from './ui/States'
import { TableContainer, Td, Th, Tr } from './ui/Table'

const TYPE_TONES: Record<ColumnType, BadgeTone> = {
  numeric: 'brand',
  datetime: 'violet',
  boolean: 'info',
  categorical: 'success',
  text: 'neutral',
  identifier: 'neutral',
  empty: 'danger',
}

export function TypeBadge({ type }: { type: ColumnType }) {
  return <Badge tone={TYPE_TONES[type]}>{type}</Badge>
}

export function ColumnProfileTable({ columns }: { columns: ColumnProfile[] }) {
  return (
    <TableContainer label="Column profile">
      <thead>
        <tr>
          <Th>Column</Th>
          <Th>Type</Th>
          <Th numeric>Missing</Th>
          <Th numeric>Distinct</Th>
          <Th numeric>Invalid</Th>
          <Th>Example values</Th>
        </tr>
      </thead>
      <tbody>
        {columns.map((column) => (
          <Tr key={column.name}>
            <Td className="font-medium text-slate-900">{column.name}</Td>
            <Td>
              <TypeBadge type={column.inferred_type} />
              {column.date_format && <span className="ml-2 font-mono text-xs text-slate-500">{column.date_format}</span>}
            </Td>
            <Td numeric>
              {formatNumber(column.missing_count)}
              {column.missing_count > 0 && <span className="ml-1 text-xs text-slate-500">({formatPercent(column.missing_percent)})</span>}
            </Td>
            <Td numeric>{formatNumber(column.distinct_count)}</Td>
            <Td numeric className={column.invalid_count ? 'font-medium text-red-700' : undefined}>
              {formatNumber(column.invalid_count)}
            </Td>
            <Td className="max-w-xs truncate text-slate-500" title={column.sample_values.join(', ')}>
              {column.sample_values.slice(0, 3).join(', ')}
            </Td>
          </Tr>
        ))}
      </tbody>
    </TableContainer>
  )
}

export function DataPreviewTable({ datasetId, pageSize = 25 }: { datasetId: string; pageSize?: number }) {
  const { dataVersion } = useApp()
  const [offset, setOffset] = useState(0)
  const preview = useApi(`preview:${datasetId}:${offset}:${pageSize}:${dataVersion}`, () => api.preview(datasetId, offset, pageSize))

  if (preview.loading && !preview.data) return <LoadingState label="Loading rows…" />
  if (preview.error) return <ErrorState error={preview.error} onRetry={preview.reload} />
  if (!preview.data) return null
  const { columns, rows, total_rows: total } = preview.data
  const last = Math.min(offset + rows.length, total)
  return (
    <div>
      <TableContainer label="Data preview">
        <thead>
          <tr>
            <Th className="w-12 text-slate-400">#</Th>
            {columns.map((column) => (
              <Th key={column.name} numeric={column.type === 'numeric'}>
                {column.name}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <Tr key={offset + rowIndex}>
              <Td className="text-xs text-slate-400">{offset + rowIndex + 1}</Td>
              {row.map((value, index) => (
                <Td key={index} numeric={columns[index].type === 'numeric'} className="whitespace-nowrap">
                  {value === null ? <span className="text-xs italic text-slate-400">empty</span> : value}
                </Td>
              ))}
            </Tr>
          ))}
        </tbody>
      </TableContainer>
      <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm text-slate-500">
        <span>
          Rows {formatNumber(offset + 1)}–{formatNumber(last)} of {formatNumber(total)}
        </span>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" icon={ChevronLeft} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>
            Previous
          </Button>
          <Button size="sm" variant="secondary" disabled={last >= total} onClick={() => setOffset(offset + pageSize)}>
            Next
            <ChevronRight className="size-4" aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  )
}
