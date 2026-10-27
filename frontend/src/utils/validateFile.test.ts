import { describe, expect, it } from 'vitest'
import { validateCsvFile } from './validateFile'

const makeFile = (name: string, sizeBytes: number, type = 'text/csv') => new File([new Uint8Array(sizeBytes)], name, { type })

describe('validateCsvFile', () => {
  it('accepts a normal CSV file', () => {
    expect(validateCsvFile(makeFile('orders.csv', 2048))).toEqual([])
  })

  it('accepts an upper-case .CSV extension', () => {
    expect(validateCsvFile(makeFile('ORDERS.CSV', 10))).toEqual([])
  })

  it('rejects a missing file', () => {
    expect(validateCsvFile(null)).toEqual(['Choose a CSV file to upload.'])
  })

  it('rejects a file that is not CSV', () => {
    const errors = validateCsvFile(makeFile('orders.xlsx', 100))
    expect(errors).toHaveLength(1)
    expect(errors[0]).toMatch(/not a CSV file/)
  })

  it('rejects an empty file', () => {
    expect(validateCsvFile(makeFile('empty.csv', 0))).toEqual(['The file is empty.'])
  })

  it('rejects a file over 5 MB', () => {
    const errors = validateCsvFile(makeFile('big.csv', 5 * 1024 * 1024 + 1))
    expect(errors[0]).toMatch(/larger than 5 MB/)
  })

  it('uses the limit configured on the server', () => {
    expect(validateCsvFile(makeFile('big.csv', 2 * 1024 * 1024), 1)[0]).toMatch(/larger than 1 MB/)
  })

  it('reports every problem at once', () => {
    expect(validateCsvFile(makeFile('notes.txt', 0))).toHaveLength(2)
  })
})
