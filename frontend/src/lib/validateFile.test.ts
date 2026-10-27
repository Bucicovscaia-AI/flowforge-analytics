import { describe, expect, it } from 'vitest'

import { validateFileLocally } from './validateFile'

const file = (name: string, size: number) => new File([new Uint8Array(size)], name, { type: 'text/csv' })

describe('validateFileLocally', () => {
  it('accepts a CSV within the limit', () => {
    expect(validateFileLocally(file('orders.CSV', 100), 10)).toBeNull()
  })

  it('rejects other file types', () => {
    expect(validateFileLocally(file('orders.xlsx', 100), 10)).toMatch(/Only CSV files/)
  })

  it('rejects empty files', () => {
    expect(validateFileLocally(file('orders.csv', 0), 10)).toBe('The file is empty.')
  })

  it('rejects files over the size limit', () => {
    expect(validateFileLocally(file('orders.csv', 2 * 1024 * 1024 + 1), 2)).toMatch(/the limit is 2 MB/)
  })
})
