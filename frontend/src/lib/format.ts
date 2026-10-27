import type { Metric } from '../api/types'

export type CurrencySymbol = '' | '£' | '$' | '€'

const numberFormat = (decimals: number) =>
  new Intl.NumberFormat('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })

export function formatNumber(value: number | null | undefined, decimals?: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  const places = decimals ?? (Number.isInteger(value) ? 0 : 2)
  return numberFormat(places).format(value)
}

export function formatCurrency(value: number | null | undefined, symbol: CurrencySymbol = ''): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  const formatted = numberFormat(2).format(Math.abs(value))
  return `${value < 0 ? '−' : ''}${symbol}${formatted}`
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return ''
  if (Math.abs(value) < 1000) return formatNumber(value, Number.isInteger(value) ? 0 : 1)
  return new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  return `${numberFormat(decimals).format(value)}%`
}

export function formatSignedPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '–'
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${numberFormat(1).format(Math.abs(value))}%`
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '–'
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '–'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatMetric(metric: Metric, currency: CurrencySymbol = ''): string {
  switch (metric.format) {
    case 'currency':
      return formatCurrency(metric.value, currency)
    case 'integer':
      return formatNumber(metric.value, 0)
    case 'percent':
      return formatPercent(metric.value)
    case 'date_range':
      return `${formatDate(metric.start)} – ${formatDate(metric.end)}`
    default:
      return formatNumber(metric.value)
  }
}

export function pluralise(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count, 0)} ${count === 1 ? singular : plural}`
}
