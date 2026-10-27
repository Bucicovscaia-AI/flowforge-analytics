export type ColumnType = 'numeric' | 'datetime' | 'boolean' | 'categorical' | 'text' | 'identifier' | 'empty'
export type Role = 'date' | 'quantity' | 'unit_price' | 'revenue' | 'category' | 'product' | 'region' | 'status'
export type Severity = 'error' | 'warning' | 'info'
export type Aggregation = 'sum' | 'mean' | 'median' | 'count' | 'min' | 'max'
export type Granularity = 'auto' | 'day' | 'week' | 'month' | 'quarter' | 'year'
export type ReportFormat = 'html' | 'pdf' | 'csv' | 'json'
export type EventType = 'dataset.analysed' | 'report.generated' | 'automation.test'

export interface DatasetSummary {
  id: string
  name: string
  source_filename: string | null
  is_sample: boolean
  status: string
  created_at: string
  updated_at: string
  original_row_count: number
  row_count: number
  column_count: number
  size_bytes: number
  encoding: string | null
  delimiter: string | null
  quality_score: number | null
  quality_grade: string | null
  warnings: string[]
}

export interface ColumnProfile {
  name: string
  inferred_type: ColumnType
  non_null_count: number
  missing_count: number
  missing_percent: number
  distinct_count: number
  invalid_count: number
  date_format: string | null
  sample_values: string[]
}

export interface OperationRecord {
  id: number
  operation: string
  params: Record<string, string>
  summary: string
  rows_before: number
  rows_after: number
  quality_before: number | null
  quality_after: number | null
  applied_at: string
}

export interface DatasetDetail extends DatasetSummary {
  columns: ColumnProfile[]
  roles: Record<Role, string | null>
  role_options: Record<Role, { label: string; candidates: string[] }>
  column_mapping: Partial<Record<Role, string>>
  operations: OperationRecord[]
}

export interface DatasetPreview {
  columns: { name: string; type: ColumnType }[]
  rows: (string | null)[][]
  offset: number
  limit: number
  total_rows: number
}

export interface SuggestedOperation {
  operation: string
  params: Record<string, string>
  label: string
}

export interface QualityFinding {
  id: string
  rule: string
  severity: Severity
  column: string | null
  title: string
  description: string
  impact: string
  affected_rows: number
  affected_cells: number
  affected_percent: number
  examples: string[]
  suggestion: SuggestedOperation | null
}

export interface QualityReport {
  score: number
  grade: string
  row_count: number
  column_count: number
  total_cells: number
  missing_cells: number
  duplicate_rows: number
  counts: Record<Severity, number>
  findings: QualityFinding[]
  method: string
}

export interface OperationParam {
  name: string
  label: string
  kind: 'column' | 'choice' | 'text'
  required: boolean
  choices: string[]
  default: string | null
  help: string
}

export interface OperationDescription {
  key: string
  label: string
  description: string
  consequence: string
  params: OperationParam[]
}

export interface CleaningResult {
  operation: string
  params: Record<string, string>
  rows_before: number
  rows_after: number
  rows_removed: number
  columns_before: number
  columns_after: number
  cells_changed: number
  changed: boolean
  applied: boolean
  summary: string
  warnings: string[]
  quality_before: number | null
  quality_after: number | null
  message: string | null
}

export interface Metric {
  key: string
  label: string
  value: number | null
  format: 'currency' | 'integer' | 'number' | 'percent' | 'date_range'
  description: string
  source_columns: string[]
  start?: string | null
  end?: string | null
}

export interface TimePoint {
  period: string
  start: string
  end: string
  label: string
  value: number | null
  records: number
  partial: boolean
  quantity?: number | null
}

export interface TimeSeries {
  granularity: Exclude<Granularity, 'auto'>
  aggregation: Aggregation
  points: TimePoint[]
  excluded_rows: number
  first_date: string
  last_date: string
}

export interface PeriodComparison {
  granularity: string
  aggregation: string
  current: { label: string; value: number; records: number }
  previous: { label: string; value: number; records: number }
  change: number
  change_percent: number | null
  note: string | null
}

export interface Trend {
  direction: 'upward' | 'downward' | 'flat'
  slope_per_period: number
  relative_slope_percent: number
  periods: number
  first_label: string
  last_label: string
}

export interface BreakdownRow {
  group: string
  records: number
  revenue: number | null
  average_revenue: number | null
  quantity: number | null
  share: number | null
}

export interface Breakdown {
  role: Role
  column: string
  measure: 'revenue' | 'records'
  rows: BreakdownRow[]
  total_groups: number
}

export interface HistogramBin {
  start: number | null
  end: number | null
  count: number
}

export interface Distribution {
  column?: string
  bins: HistogramBin[]
  count: number
  excluded_rows: number
  mean: number | null
  median: number | null
  std: number | null
  min: number | null
  max: number | null
}

export interface ColumnSummary {
  name: string
  type: ColumnType
  non_null: number
  missing: number
  missing_percent: number
  distinct: number
  invalid: number
  stats?: Record<string, number | string | null>
  top_values?: { value: string; count: number }[]
}

export interface Correlation {
  column_a: string
  column_b: string
  coefficient: number
  strength: 'strong' | 'moderate'
  expected: boolean
}

export interface AnalysisResult {
  roles: Record<Role, string | null>
  revenue_source: 'column' | 'derived' | null
  metrics: Metric[]
  columns: ColumnSummary[]
  time_series: TimeSeries | null
  period_comparison: PeriodComparison | null
  trend: Trend | null
  breakdowns: Partial<Record<Role, Breakdown>>
  distributions: Record<string, Distribution>
  correlations: Correlation[]
  limitations: string[]
}

export interface AggregateResult {
  group_by: string
  aggregation: Aggregation
  rows: { group: string; value: number | null; records: number; share: number | null }[]
  total_groups: number
}

export interface Insight {
  id: string
  category: string
  kind: 'fact' | 'interpretation' | 'suggestion'
  title: string
  statement: string
  evidence: { label: string; value: string }[]
  caveat: string | null
  source: 'ai' | 'rule_based'
}

export interface InsightResult {
  mode: 'ai' | 'rule_based'
  provider: string | null
  model: string | null
  generated_at: string
  insights: Insight[]
  notices: string[]
  limitations: string[]
  data_sent: string[]
  ai_error: string | null
}

export interface AutomationRun {
  id: string
  event_type: EventType
  trigger: 'manual' | 'rule'
  dataset_id: string | null
  report_id: string | null
  status: 'delivered' | 'failed'
  http_status: number | null
  message: string
  duration_ms: number | null
  payload: Record<string, unknown>
  created_at: string
}

export interface ReportSummary {
  id: string
  title: string
  dataset_id: string | null
  dataset_name: string
  created_at: string
  status: 'completed' | 'partial' | 'failed'
  insight_mode: 'ai' | 'rule_based' | null
  record_count: number | null
  formats: ReportFormat[]
  error: string | null
}

export interface ReportCreated extends ReportSummary {
  automation_run: AutomationRun | null
}

export interface AutomationStatus {
  provider: string
  configured: boolean
  configuration_problem: string | null
  signing_enabled: boolean
  trigger_on_report: boolean
  timeout_seconds: number
  event_types: { type: EventType; description: string }[]
}

export interface SystemStatus {
  name: string
  version: string
  ai: { configured: boolean; provider: string | null; model: string | null; data_policy: string }
  automation_configured: boolean
  storage: { engine: string; persistent: boolean; description: string }
  limits: { max_upload_mb: number; max_rows: number; max_columns: number; accepted_extensions: string[] }
}

export interface ActivityItem {
  id: number
  kind: string
  message: string
  dataset_id: string | null
  report_id: string | null
  created_at: string
}
