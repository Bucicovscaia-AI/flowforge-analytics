import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SystemStatus } from '../api/types'
import { App } from '../App'
import { AppProvider } from '../context/AppContext'
import { ToastProvider } from '../context/ToastContext'

const SYSTEM: SystemStatus = {
  name: 'FlowForge Analytics',
  version: '1.0.0',
  ai: { configured: false, provider: null, model: null, data_policy: 'Only aggregated results are sent.' },
  automation_configured: false,
  storage: { engine: 'SQLite and local files', persistent: true, description: 'Stored on the server.' },
  limits: { max_upload_mb: 10, max_rows: 500000, max_columns: 200, accepted_extensions: ['.csv'] },
}

function json(body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }))
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string) => {
      if (input.startsWith('/api/system/status')) return json(SYSTEM)
      if (input.startsWith('/api/datasets')) return json([])
      if (input.startsWith('/api/health')) return json({ status: 'ok' })
      return json([])
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ToastProvider>
        <AppProvider>
          <App />
        </AppProvider>
      </ToastProvider>
    </MemoryRouter>,
  )
}

describe('App', () => {
  it('guides a new user to import data when there are no datasets', async () => {
    renderAt('/')
    expect(await screen.findByRole('button', { name: /Explore sample data/ })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Upload a CSV file/ }).length).toBeGreaterThan(0)
  })

  it('asks for a dataset on pages that need one', async () => {
    renderAt('/analysis')
    expect(await screen.findByText('No dataset yet')).toBeInTheDocument()
  })

  it('navigates between sections from the sidebar', async () => {
    renderAt('/')
    await userEvent.click((await screen.findAllByRole('link', { name: 'Settings' }))[0])
    expect(await screen.findByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument()
    expect(await screen.findByText('Rule-based only')).toBeInTheDocument()
  })

  it('shows a not-found page for unknown addresses', async () => {
    renderAt('/does-not-exist')
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })
})
