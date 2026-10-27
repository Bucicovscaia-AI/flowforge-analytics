import { describe, expect, it } from 'vitest'

import type { Metric } from '../api/types'
import { formatBytes, formatCurrency, formatMetric, formatNumber, formatPercent, formatSignedPercent, pluralise } from './format'

describe('number formatting', () => {
  it('shows a dash for missing values', () => {
    expect(formatNumber(null)).toBe('–')
    expect(formatNumber(Number.NaN)).toBe('–')
    expect(formatCurrency(undefined)).toBe('–')
    expect(formatPercent(null)).toBe('–')
  })

  it('keeps integers whole and rounds other values to two places', () => {
    expect(formatNumber(1234)).toBe('1,234')
    expect(formatNumber(12.345)).toBe('12.35')
    expect(formatNumber(3, 1)).toBe('3.0')
  })

  it('formats currency with the chosen symbol and a true minus sign', () => {
    expect(formatCurrency(1234.5, '£')).toBe('£1,234.50')
    expect(formatCurrency(-20, '$')).toBe('−$20.00')
    expect(formatCurrency(5)).toBe('5.00')
  })

  it('signs percentage changes', () => {
    expect(formatSignedPercent(12.34)).toBe('+12.3%')
    expect(formatSignedPercent(-4)).toBe('−4.0%')
    expect(formatSignedPercent(0)).toBe('0.0%')
  })

  it('formats file sizes', () => {
    expect(formatBytes(500)).toBe('500 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(3 * 1024 * 1024)).toBe('3.0 MB')
  })

  it('pluralises counts', () => {
    expect(pluralise(1, 'row')).toBe('1 row')
    expect(pluralise(2500, 'row')).toBe('2,500 rows')
  })
})

describe('formatMetric', () => {
  const base: Metric = { key: 'k', label: 'K', value: 1500, format: 'number', description: '', source_columns: [] }

  it('uses the metric format', () => {
    expect(formatMetric({ ...base, format: 'currency' }, '€')).toBe('€1,500.00')
    expect(formatMetric({ ...base, format: 'integer' })).toBe('1,500')
    expect(formatMetric({ ...base, format: 'percent', value: 12.5 })).toBe('12.5%')
  })

  it('formats date ranges from start and end', () => {
    expect(formatMetric({ ...base, format: 'date_range', value: null, start: '2025-01-05', end: '2025-03-31' })).toBe('5 Jan 2025 – 31 Mar 2025')
  })
})
