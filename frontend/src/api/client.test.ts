import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, errorMessage, parseError, request } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('parseError', () => {
  it('reads the API error envelope', async () => {
    const response = new Response(JSON.stringify({ error: { code: 'file_too_large', message: 'Too big', details: { limit_mb: 10 } } }), { status: 413 })
    const error = await parseError(response)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(413)
    expect(error.code).toBe('file_too_large')
    expect(error.message).toBe('Too big')
    expect(error.details).toEqual({ limit_mb: 10 })
  })

  it('falls back to a generic message when the body is not JSON', async () => {
    const error = await parseError(new Response('<html>Bad gateway</html>', { status: 502 }))
    expect(error.code).toBe('http_error')
    expect(error.message).toContain('HTTP 502')
  })
})

describe('request', () => {
  it('sends JSON and returns the parsed body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(request('POST', '/things', { body: { a: 1 }, query: { limit: 5, empty: '' } })).resolves.toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/things?limit=5')
    expect(init.method).toBe('POST')
    expect(init.body).toBe('{"a":1}')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(request('DELETE', '/things/1')).resolves.toBeUndefined()
  })

  it('turns a network failure into a readable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const error = await request('GET', '/things').catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect(errorMessage(error)).toMatch(/could not be reached/)
  })
})

describe('URL builders', () => {
  it('builds report download links', () => {
    expect(api.reportUrl('abc', 'pdf')).toBe('/api/reports/abc/download?format=pdf')
    expect(api.reportUrl('abc', 'html', true)).toBe('/api/reports/abc/download?format=html&inline=true')
  })

  it('omits empty query values', () => {
    expect(api.aggregateCsvUrl('d1', { group_by: 'region', agg: 'count' })).toBe('/api/datasets/d1/charts/aggregate.csv?group_by=region&agg=count')
  })
})
