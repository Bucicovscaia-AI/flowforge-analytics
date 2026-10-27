const gbp = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 })
const gbpPrecise = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 2 })
const number = new Intl.NumberFormat('en-GB')

export const formatCurrency = (value) => gbp.format(value)
export const formatCurrencyPrecise = (value) => gbpPrecise.format(value)
export const formatNumber = (value) => number.format(value)
export const formatPercent = (value, digits = 1) => `${value.toFixed(digits)}%`

// Short axis labels: 18420 -> "£18k"
export const formatCurrencyShort = (value) => (value >= 1000 ? `£${Math.round(value / 1000)}k` : `£${value}`)

export const formatDateTime = (iso) =>
  new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

export const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
