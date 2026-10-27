import { describe, expect, it } from 'vitest'
import { getSampleKpis, revenueByCategory, revenueByRegion } from './sampleData'

// The sample figures must be internally consistent, otherwise the demo
// dashboard would show totals that contradict its own charts.
describe('sample data consistency', () => {
  const kpis = getSampleKpis()

  it('region totals add up to total revenue', () => {
    expect(revenueByRegion.reduce((s, r) => s + r.revenue, 0)).toBe(kpis.totalRevenue)
  })

  it('category totals add up to total revenue and orders', () => {
    expect(revenueByCategory.reduce((s, c) => s + c.revenue, 0)).toBe(kpis.totalRevenue)
    expect(revenueByCategory.reduce((s, c) => s + c.orders, 0)).toBe(kpis.totalOrders)
  })

  it('rows analysed equals the number of orders', () => {
    expect(kpis.validRows).toBe(kpis.totalOrders)
  })
})
