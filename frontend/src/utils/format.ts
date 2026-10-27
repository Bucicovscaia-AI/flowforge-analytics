const gbp = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 })
const gbpPrecise = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 2 })
const number = new Intl.NumberFormat('en-GB')

const NA = 'Not available'

export const formatCurrency = (value: number | null | undefined) => (value == null ? NA : gbp.format(value))
export const formatCurrencyPrecise = (value: number | null | undefined) => (value == null ? NA : gbpPrecise.format(value))
export const formatNumber = (value: number | null | undefined) => (value == null ? NA : number.format(value))
export const formatPercent = (value: number, digits = 1) => `${value.toFixed(digits)}%`

// Short axis labels: 18420 -> "£18k"
export const formatCurrencyShort = (value: number) => (value >= 1000 ? `£${Math.round(value / 1000)}k` : `£${Math.round(value)}`)

export const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

export const formatDate = (iso: string) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

export const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** "revenue_by_region" -> "Revenue by region" for column and KPI names. */
export const humanise = (key: string) => key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
