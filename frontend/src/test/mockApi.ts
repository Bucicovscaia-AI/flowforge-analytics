import { vi } from 'vitest'
import analysis from './fixtures/analysis.json'
import config from './fixtures/config.json'
import report from './fixtures/report.json'
import type { Analysis, AppConfig, Report } from '../types'

// Fixtures were produced by the real backend from a five-row CSV, so the
// frontend tests use genuine API output rather than hand-written numbers.
export const fixtureAnalysis = analysis as unknown as Analysis
export const fixtureConfig = config as unknown as AppConfig
export const fixtureReport = report as unknown as Report

type Reply = { status?: number; body?: unknown }
type Handler = Reply | ((init: RequestInit | undefined) => Reply)

/**
 * Replace fetch with a router keyed by "METHOD /path" (path without /api).
 * Unmatched requests fail like an offline backend. Returns the mock so tests
 * can inspect calls.
 */
export function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input).replace(/^\/api/, '')
    const key = `${init?.method ?? 'GET'} ${url}`
    const handler = routes[key]
    if (!handler) throw new Error(`offline in tests: ${key}`)
    const reply = typeof handler === 'function' ? handler(init) : handler
    const status = reply.status ?? 200
    return new Response(status === 204 ? null : JSON.stringify(reply.body ?? null), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Routes that every page needs: config plus the given analysis restored on start-up. */
export function withCurrentAnalysis(a: Analysis = fixtureAnalysis, extra: Record<string, Handler> = {}) {
  localStorage.setItem('flowforge.currentAnalysisId', a.id)
  return mockApi({
    'GET /config': { body: fixtureConfig },
    'GET /health': { body: { status: 'ok', version: '1.0.0' } },
    [`GET /analyses/${a.id}`]: { body: a },
    'GET /reports': { body: [] },
    ...extra,
  })
}
