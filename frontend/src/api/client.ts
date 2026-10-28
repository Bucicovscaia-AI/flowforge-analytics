import type {
  ActivityItem,
  AggregateResult,
  Aggregation,
  AnalysisResult,
  AutomationRun,
  AutomationStatus,
  CleaningResult,
  DatasetDetail,
  DatasetPreview,
  DatasetSummary,
  Distribution,
  EventType,
  Granularity,
  InsightResult,
  OperationDescription,
  QualityReport,
  ReportCreated,
  ReportFormat,
  ReportSummary,
  Role,
  SystemStatus,
  TimeSeries,
} from './types'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '/api'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

const NETWORK_MESSAGE = 'The FlowForge server could not be reached. Check that the backend is running and try again.'

export async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json()
    if (body && typeof body === 'object' && 'error' in body) {
      const { code, message, details } = body.error as { code: string; message: string; details?: Record<string, unknown> }
      return new ApiError(response.status, code, message, details ?? {})
    }
  } catch {
    // Not JSON: fall through to a generic message.
  }
  return new ApiError(response.status, 'http_error', `The server returned an error (HTTP ${response.status}).`)
}

type Query = Record<string, string | number | boolean | null | undefined>

function buildUrl(path: string, query?: Query): string {
  const url = `${API_BASE}${path}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
  }
  const search = params.toString()
  return search ? `${url}?${search}` : url
}

export async function request<T>(method: string, path: string, options: { query?: Query; body?: unknown } = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers: options.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'network_error', NETWORK_MESSAGE)
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Upload with progress reporting; fetch() cannot report upload progress. */
export function uploadDataset(file: File, name: string | undefined, onProgress: (fraction: number) => void): Promise<DatasetSummary> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', buildUrl('/datasets/upload'))
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    xhr.onerror = () => reject(new ApiError(0, 'network_error', NETWORK_MESSAGE))
    xhr.onload = async () => {
      const response = new Response(xhr.responseText, { status: xhr.status, headers: { 'Content-Type': 'application/json' } })
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText) as DatasetSummary)
      else reject(await parseError(response))
    }
    xhr.send(form)
  })
}

export const api = {
  systemStatus: () => request<SystemStatus>('GET', '/system/status'),
  activity: (datasetId?: string, limit = 10) => request<ActivityItem[]>('GET', '/activity', { query: { dataset_id: datasetId, limit } }),

  listDatasets: () => request<DatasetSummary[]>('GET', '/datasets'),
  getDataset: (id: string) => request<DatasetDetail>('GET', `/datasets/${id}`),
  loadSample: () => request<DatasetSummary>('POST', '/datasets/sample'),
  renameDataset: (id: string, name: string) => request<DatasetSummary>('PATCH', `/datasets/${id}`, { body: { name } }),
  deleteDataset: (id: string) => request<void>('DELETE', `/datasets/${id}`),
  updateMapping: (id: string, mapping: Partial<Record<Role, string | null>>) =>
    request<DatasetDetail>('PUT', `/datasets/${id}/column-mapping`, { body: { mapping } }),
  preview: (id: string, offset = 0, limit = 25) => request<DatasetPreview>('GET', `/datasets/${id}/preview`, { query: { offset, limit } }),
  exportDatasetUrl: (id: string) => buildUrl(`/datasets/${id}/export.csv`),

  quality: (id: string) => request<QualityReport>('GET', `/datasets/${id}/quality`),
  cleaningOperations: () => request<OperationDescription[]>('GET', '/cleaning/operations'),
  previewCleaning: (id: string, operation: string, params: Record<string, string>) =>
    request<CleaningResult>('POST', `/datasets/${id}/cleaning/preview`, { body: { operation, params } }),
  applyCleaning: (id: string, operation: string, params: Record<string, string>) =>
    request<CleaningResult>('POST', `/datasets/${id}/cleaning/apply`, { body: { operation, params } }),
  resetCleaning: (id: string) => request<DatasetDetail>('POST', `/datasets/${id}/cleaning/reset`),

  analysis: (id: string) => request<AnalysisResult>('GET', `/datasets/${id}/analysis`),
  aggregate: (id: string, query: { group_by: string; value?: string; agg: Aggregation; top_n?: number }) =>
    request<AggregateResult>('GET', `/datasets/${id}/charts/aggregate`, { query }),
  aggregateCsvUrl: (id: string, query: { group_by: string; value?: string; agg: Aggregation }) =>
    buildUrl(`/datasets/${id}/charts/aggregate.csv`, query),
  timeSeries: (id: string, query: { date_column?: string; value?: string; agg: Aggregation; granularity: Granularity }) =>
    request<TimeSeries>('GET', `/datasets/${id}/charts/timeseries`, { query }),
  distribution: (id: string, column: string, bins = 20) =>
    request<Distribution>('GET', `/datasets/${id}/charts/distribution`, { query: { column, bins } }),
  insights: (id: string, useAi: boolean) => request<InsightResult>('POST', `/datasets/${id}/insights`, { body: { use_ai: useAi } }),

  createReport: (datasetId: string, title: string | undefined, useAi: boolean) =>
    request<ReportCreated>('POST', '/reports', { body: { dataset_id: datasetId, title: title || null, use_ai: useAi } }),
  listReports: (datasetId?: string, limit = 100) => request<ReportSummary[]>('GET', '/reports', { query: { dataset_id: datasetId, limit } }),
  deleteReport: (id: string) => request<void>('DELETE', `/reports/${id}`),
  reportUrl: (id: string, format: ReportFormat, inline = false) =>
    buildUrl(`/reports/${id}/download`, { format, inline: inline || undefined }),

  automationStatus: () => request<AutomationStatus>('GET', '/automation/status'),
  automationRuns: (limit = 50) => request<AutomationRun[]>('GET', '/automation/runs', { query: { limit } }),
  previewAutomation: (eventType: EventType, datasetId?: string, reportId?: string) =>
    request<Record<string, unknown>>('POST', '/automation/preview', {
      body: { event_type: eventType, dataset_id: datasetId ?? null, report_id: reportId ?? null },
    }),
  triggerAutomation: (eventType: EventType, datasetId?: string, reportId?: string, resend = false) =>
    request<AutomationRun>('POST', '/automation/trigger', {
      body: { event_type: eventType, dataset_id: datasetId ?? null, report_id: reportId ?? null, resend },
    }),
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}
