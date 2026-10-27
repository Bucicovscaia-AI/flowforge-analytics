import { useCallback } from 'react'

import { useApp } from '../context/AppContext'
import { formatCurrency, formatNumber } from '../lib/format'

/** Format chart and table values: currency for revenue measures, plain numbers otherwise. */
export function useValueFormatter(isCurrency: boolean): (value: number | null) => string {
  const { currency } = useApp()
  return useCallback((value: number | null) => (isCurrency ? formatCurrency(value, currency) : formatNumber(value)), [currency, isCurrency])
}
