import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MISSING_DATA_EVENT } from '../api/client'
import type { DatasetSummary, SystemStatus } from '../api/types'
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

  it('shows the security habits on the upload page', async () => {
    renderAt('/upload')
    expect(await screen.findByRole('heading', { name: 'Before you upload' })).toBeInTheDocument()
    expect(screen.getByText('Use demo or anonymised data only')).toBeInTheDocument()
    expect(screen.getByText('Keep the webhook address private')).toBeInTheDocument()
    expect(screen.getByText('Check before you forward')).toBeInTheDocument()
  })

  it('keeps server configuration details out of the settings page', async () => {
    renderAt('/settings')
    expect(await screen.findByRole('link', { name: 'Read before you upload' })).toHaveAttribute('href', '/upload#before-you-upload')
    expect(document.body.textContent).not.toMatch(/AI_API_KEY|MAKE_WEBHOOK|MAX_UPLOAD_MB|\.env/)
  })

  it('shows a not-found page for unknown addresses', async () => {
    renderAt('/does-not-exist')
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })
})

describe('when the server loses data', () => {
  const dataset: DatasetSummary = {
    id: 'a'.repeat(32),
    name: 'office-supplies-orders-2026',
    source_filename: 'orders.csv',
    is_sample: false,
    status: 'ready',
    created_at: '2026-10-28T10:49:00+00:00',
    updated_at: '2026-10-28T10:49:00+00:00',
    original_row_count: 455,
    row_count: 455,
    column_count: 11,
    size_bytes: 1000,
    encoding: 'utf-8',
    delimiter: ',',
    quality_score: 99.3,
    quality_grade: 'Excellent',
    warnings: [],
  }

  it('refreshes the dataset list and explains that temporary storage was cleared', async () => {
    let stored: DatasetSummary[] = [dataset]
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string) => {
        if (input.startsWith('/api/system/status')) return json({ ...SYSTEM, storage: { ...SYSTEM.storage, persistent: false } })
        if (input.startsWith('/api/datasets')) return json(stored)
        return json([])
      }),
    )
    renderAt('/analysis')
    expect((await screen.findAllByText(/office-supplies-orders-2026/)).length).toBeGreaterThan(0)

    stored = []
    act(() => {
      window.dispatchEvent(new Event(MISSING_DATA_EVENT))
    })
    expect(await screen.findByText('Some data is no longer on the server')).toBeInTheDocument()
    expect(screen.getByText(/cleared whenever it restarts/)).toBeInTheDocument()
    expect(await screen.findByText('No dataset yet')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByText('Some data is no longer on the server')).not.toBeInTheDocument()
  })
})
