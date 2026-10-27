// Service layer: every call to the backend goes through this file,
// so components never build URLs or parse responses themselves.
import type { Analysis, AnalysisListItem, AppConfig, InsightResult, Report, SampleDataset } from '../types'

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

/** An error the interface can show as-is. `problems` lists every reason. */
export class ApiError extends Error {
  status: number
  problems: string[]

  constructor(message: string, status: number, problems: string[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problems = problems.length ? problems : [message]
  }
}

// FastAPI returns `detail` as a string, as {message, problems}, or (for
// request validation errors) as a list of {msg} objects.
function readError(body: unknown, status: number): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return new ApiError(detail, status)
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const d = detail as { message: string; problems?: string[] }
    return new ApiError(d.message, status, d.problems ?? [])
  }
  if (Array.isArray(detail)) {
    const msgs = detail.map((d: { msg?: string }) => d.msg ?? 'Invalid request')
    return new ApiError(msgs[0] ?? 'Invalid request', status, msgs)
  }
  return new ApiError(`Request failed with status ${status}`, status)
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new ApiError('Cannot reach the FlowForge backend. Is it running?', 0)
  }
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) throw readError(body, response.status)
  return body as T
}

const postJson = <T>(path: string, data?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
  })

export const getHealth = () => request<{ status: string; version: string }>('/health')
export const getConfig = () => request<AppConfig>('/config')
export const getSamples = () => request<SampleDataset[]>('/samples')
export const analyseSample = (id: string) => postJson<Analysis>(`/samples/${encodeURIComponent(id)}/analyse`)

export function uploadDataset(file: File, synthetic: boolean): Promise<Analysis> {
  const form = new FormData()
  form.append('file', file)
  form.append('synthetic', String(synthetic))
  return request<Analysis>('/datasets/upload', { method: 'POST', body: form })
}

export const getAnalysis = (id: string) => request<Analysis>(`/analyses/${encodeURIComponent(id)}`)
export const listAnalyses = () => request<AnalysisListItem[]>('/analyses')
export const getAiPayload = (id: string) => request<Record<string, unknown>>(`/analyses/${encodeURIComponent(id)}/ai-payload`)
export const generateInsights = (id: string) => postJson<InsightResult>(`/analyses/${encodeURIComponent(id)}/insights`)

export interface ReportOptions {
  analysis_id: string
  title?: string
  include_insights?: boolean
  notify_make?: boolean
}
export const createReport = (options: ReportOptions) => postJson<Report>('/reports', options)
export const listReports = () => request<Report[]>('/reports')
export const deleteReport = (id: string) => request<void>(`/reports/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const notifyReport = (id: string) => postJson<{ status: string; message: string }>(`/reports/${encodeURIComponent(id)}/notify`)
export const testWebhook = () => postJson<{ delivered: boolean; status_code: number }>('/integrations/make/test')
export const reportDownloadUrl = (id: string) => `${API_BASE}/reports/${encodeURIComponent(id)}/download`
