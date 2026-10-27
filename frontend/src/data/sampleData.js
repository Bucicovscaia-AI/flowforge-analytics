// DEMONSTRATION DATA ONLY.
// Every figure in this file is fabricated for interface development (Stage 2).
// It does not describe any real business. From Stage 5 the pages read real
// results from the backend instead of this file.

export const SAMPLE_DATASET = {
  fileName: 'demo_retail_orders.csv',
  description: 'Fabricated retail sales orders, January to June 2026',
  rowsReceived: 1512,
  duplicatesRemoved: 14,
  invalidRowsRemoved: 13,
  columns: 8,
}

export const monthlyRevenue = [
  { month: 'Jan', revenue: 18420, orders: 212 },
  { month: 'Feb', revenue: 19875, orders: 228 },
  { month: 'Mar', revenue: 22310, orders: 251 },
  { month: 'Apr', revenue: 21040, orders: 239 },
  { month: 'May', revenue: 24680, orders: 268 },
  { month: 'Jun', revenue: 26915, orders: 287 },
]

export const revenueByRegion = [
  { name: 'North', revenue: 38910 },
  { name: 'East', revenue: 34120 },
  { name: 'West', revenue: 30760 },
  { name: 'South', revenue: 29450 },
]

export const revenueByCategory = [
  { name: 'Electronics', revenue: 45300, orders: 402 },
  { name: 'Home & Garden', revenue: 31820, orders: 371 },
  { name: 'Clothing', revenue: 27640, orders: 356 },
  { name: 'Sports', revenue: 17250, orders: 214 },
  { name: 'Books', revenue: 11230, orders: 142 },
]

// Column profile: what the data-quality step found in each column.
export const columnProfile = [
  { column: 'order_id', type: 'Text', missing: 0, invalid: 0, action: 'Duplicates removed (14)' },
  { column: 'order_date', type: 'Date', missing: 0, invalid: 9, action: 'Unparseable dates removed' },
  { column: 'region', type: 'Category', missing: 0, invalid: 0, action: 'None needed' },
  { column: 'channel', type: 'Category', missing: 8, invalid: 0, action: 'Filled with "Unknown"' },
  { column: 'product_category', type: 'Category', missing: 0, invalid: 0, action: 'None needed' },
  { column: 'quantity', type: 'Integer', missing: 0, invalid: 4, action: 'Negative values removed' },
  { column: 'unit_price', type: 'Decimal', missing: 0, invalid: 0, action: 'None needed' },
  { column: 'customer_type', type: 'Category', missing: 21, invalid: 0, action: 'Filled with "Unknown"' },
]

export const reportHistory = [
  { id: 'RPT-003', title: 'Q2 sales performance', dataset: 'demo_retail_orders.csv', created: '2026-10-26T14:20:00', status: 'Ready' },
  { id: 'RPT-002', title: 'Regional revenue review', dataset: 'demo_retail_orders.csv', created: '2026-10-24T09:05:00', status: 'Ready' },
  { id: 'RPT-001', title: 'Data quality check', dataset: 'demo_orders_with_errors.csv', created: '2026-10-22T16:45:00', status: 'Failed validation' },
]

// Example of the kind of output the AI prototype (Stage 7) would produce.
export const sampleInsights = [
  {
    title: 'Revenue grew across the period',
    evidence: 'Revenue rose in 4 of the 5 month-on-month changes, from £18,420 in January to £26,915 in June (+46%).',
    recommendation: 'Check whether the April dip repeats in other years before planning stock for spring.',
  },
  {
    title: 'Electronics is the largest category',
    evidence: 'Electronics produced £45,300, about 34% of total revenue.',
    recommendation: 'Monitor supplier risk for this category, as a large share of revenue depends on it.',
  },
  {
    title: 'Revenue is spread evenly across regions',
    evidence: 'No region contributes more than 30% of revenue (North is highest at 29%).',
    recommendation: 'Regional performance is balanced; compare average order value by region next.',
  },
]

// KPIs are derived from the rows above so the numbers always agree.
export function getSampleKpis() {
  const totalRevenue = monthlyRevenue.reduce((sum, m) => sum + m.revenue, 0)
  const totalOrders = monthlyRevenue.reduce((sum, m) => sum + m.orders, 0)
  const validRows = SAMPLE_DATASET.rowsReceived - SAMPLE_DATASET.duplicatesRemoved - SAMPLE_DATASET.invalidRowsRemoved
  return {
    totalRevenue,
    totalOrders,
    averageOrderValue: totalRevenue / totalOrders,
    dataQualityScore: (validRows / SAMPLE_DATASET.rowsReceived) * 100,
    validRows,
  }
}
