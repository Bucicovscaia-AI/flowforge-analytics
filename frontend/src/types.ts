// Shapes of the JSON returned by the FastAPI backend (see docs/api.md).

export interface ColumnProfile {
  name: string
  type: 'date' | 'number' | 'category' | 'text'
  role: 'required' | 'optional' | 'extra'
  missing: number
  missing_pct: number
  invalid: number
  unique: number
  examples: string[]
}

export interface CleaningStep {
  rule: string
  description: string
  rows_removed: number
  cells_changed: number
  detail: string
}

export interface BreakdownRow {
  name: string
  revenue: number
  orders: number
  units: number
  share_pct: number
  average_order_value: number
}

export interface MonthRow {
  period: string
  label: string
  revenue: number
  units: number
  orders: number | null
}

export interface KpiSummary {
  total_revenue: number | null
  order_count: number | null
  units_sold: number | null
  average_order_value: number | null
  order_lines: number
  average_units_per_order: number | null
  currency: string
  date_from?: string
  date_to?: string
}

export type BreakdownKey =
  | 'revenue_by_category'
  | 'revenue_by_region'
  | 'revenue_by_channel'
  | 'revenue_by_customer_type'
  | 'top_products'

export interface Kpis {
  summary: KpiSummary
  breakdowns: Partial<Record<BreakdownKey, BreakdownRow[]>> & { revenue_over_time?: MonthRow[] }
  unavailable: { kpi: string; label: string; missing_columns: string[] }[]
}

export interface Insight {
  title: string
  evidence: string
  recommendation: string
  kind: string
}

export interface InsightResult {
  source: 'ai' | 'rule-based'
  model: string | null
  generated_at: string
  summary: string | null
  insights: Insight[]
  caveats: string[]
  notice: string
}

export interface Analysis {
  id: string
  created_at: string
  dataset: {
    file_name: string
    size_bytes: number
    encoding: string
    columns: string[]
    original_columns: string[]
    renamed_columns: Record<string, string>
    synthetic: boolean
    sample_id: string | null
  }
  profile: {
    rows: number
    columns: number
    column_names: string[]
    duplicate_rows: number
    missing_cells: number
    completeness_pct: number
    column_profile: ColumnProfile[]
  }
  quality: {
    rows_received: number
    rows_analysed: number
    rows_removed: number
    duplicate_rows: number
    missing_cells: number
    completeness_pct: number
    quality_score: number
  }
  cleaning_steps: CleaningStep[]
  kpis: Kpis
  observations: Insight[]
  preview: { columns: string[]; rows: Record<string, string | number | null>[] }
  insights: InsightResult | null
}

export interface AnalysisListItem {
  id: string
  created_at: string
  file_name: string
  synthetic: boolean
  rows_analysed: number
  total_revenue: number | null
}

export interface SampleDataset {
  id: string
  file: string
  name: string
  description: string
  size_bytes: number
  synthetic: boolean
}

export interface WebhookStatus {
  status: 'not_configured' | 'not_requested' | 'delivered' | 'failed'
  message?: string
  at?: string
  event_id?: string
}

export interface Report {
  id: string
  analysis_id: string
  title: string
  dataset: string
  synthetic: boolean
  created_at: string
  size_bytes: number
  insight_source: 'ai' | 'rule-based'
  total_revenue: number | null
  webhook: WebhookStatus
}

export interface AppConfig {
  version: string
  max_upload_mb: number
  max_rows: number
  required_columns: string[]
  optional_columns: string[]
  cleaning_rules: { rule: string; description: string }[]
  ai: { configured: boolean; model: string | null }
  webhook: { configured: boolean; target_host: string | null; api_key_set: boolean }
}
