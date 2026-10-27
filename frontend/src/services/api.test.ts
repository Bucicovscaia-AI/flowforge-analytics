import { describe, expect, it } from 'vitest'
import { mockApi } from '../test/mockApi'
import { ApiError, createReport, getHealth, uploadDataset } from './api'

describe('api service', () => {
  it('returns parsed JSON on success', async () => {
    mockApi({ 'GET /health': { body: { status: 'ok', version: '1.0.0' } } })
    await expect(getHealth()).resolves.toEqual({ status: 'ok', version: '1.0.0' })
  })

  it('explains when the backend cannot be reached', async () => {
    await expect(getHealth()).rejects.toThrow('Cannot reach the FlowForge backend')
  })

  it('keeps every validation problem from the backend', async () => {
    mockApi({
      'POST /datasets/upload': { status: 422, body: { detail: { message: 'Required columns are missing: quantity.', problems: ['Required columns are missing: quantity.', 'Duplicate column'] } } },
    })
    const error = await uploadDataset(new File(['x'], 'a.csv'), true).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
    expect(error.problems).toHaveLength(2)
  })

  it('reads string and list error details', async () => {
    mockApi({ 'POST /reports': { status: 404, body: { detail: 'Analysis not found.' } } })
    await expect(createReport({ analysis_id: 'x' })).rejects.toThrow('Analysis not found.')
    mockApi({ 'POST /reports': { status: 422, body: { detail: [{ msg: 'Field required' }] } } })
    await expect(createReport({ analysis_id: 'x' })).rejects.toThrow('Field required')
  })

  it('sends the file and synthetic flag as form data', async () => {
    const fetchMock = mockApi({ 'POST /datasets/upload': { status: 201, body: { id: 'ana_1' } } })
    await uploadDataset(new File(['a,b'], 'orders.csv'), false)
    const body = fetchMock.mock.calls[0][1]?.body as FormData
    expect((body.get('file') as File).name).toBe('orders.csv')
    expect(body.get('synthetic')).toBe('false')
  })
})
