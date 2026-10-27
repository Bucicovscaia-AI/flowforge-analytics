import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(cleanup)

// jsdom has no layout engine, so provide the browser APIs that charts expect.
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Tests must not depend on a running backend: make the health check fail fast.
vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline in tests'))))

// ResponsiveContainer measures its parent, which is always 0×0 in jsdom.
// Give charts a fixed size in tests so they render without warnings.
vi.mock('recharts', async (importOriginal) => {
  const recharts = await importOriginal()
  const { cloneElement } = await import('react')
  return {
    ...recharts,
    ResponsiveContainer: ({ children }) => cloneElement(children, { width: 800, height: 300 }),
  }
})
