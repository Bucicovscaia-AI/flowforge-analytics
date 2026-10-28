import { describe, expect, it } from 'vitest'

import { categoryVariantNote, categoryVariants } from './categories'

describe('category variants', () => {
  it('finds labels that differ only in case or spacing', () => {
    expect(categoryVariants(['Electronics', 'Furniture', 'electronics', 'East', 'east '])).toEqual([
      ['Electronics', 'electronics'],
      ['East', 'east '],
    ])
  })

  it('ignores distinct labels', () => {
    expect(categoryVariants(['Electronics', 'Furniture', 'Accessories'])).toEqual([])
    expect(categoryVariantNote(['Electronics', 'Furniture'])).toBeUndefined()
  })

  it('describes the variants without changing them', () => {
    expect(categoryVariantNote(['Electronics', 'electronics'])).toMatch(/^'Electronics' and 'electronics' differ only/)
  })
})
