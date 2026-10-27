import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppRoutes } from './App'
import { fixtureAnalysis, fixtureConfig, fixtureReport, mockApi, withCurrentAnalysis } from './test/mockApi'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('page routing', () => {
  it.each([
    ['/', 'Dashboard'],
    ['/upload', 'Dataset Upload'],
    ['/analysis', 'Data Analysis'],
    ['/insights', 'AI Insights'],
    ['/reports', 'Reports'],
    ['/history', 'Report History'],
    ['/settings', 'Settings'],
  ])('renders %s with heading "%s"', (path, heading) => {
    renderAt(path)
    expect(screen.getByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
  })

  it('shows a not-found message for unknown pages', () => {
    renderAt('/nowhere')
    expect(screen.getByText('Page not found')).toBeInTheDocument()
  })
})

describe('empty states before any dataset is analysed', () => {
  it.each(['/analysis', '/insights', '/reports'])('%s asks the user to choose a dataset', (path) => {
    renderAt(path)
    expect(screen.getByText('No dataset analysed yet')).toBeInTheDocument()
  })

  it('dashboard offers the synthetic sample and upload', () => {
    renderAt('/')
    expect(screen.getByRole('button', { name: /try the synthetic sample/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upload a csv/i })).toBeInTheDocument()
  })
})

describe('dashboard with an analysis', () => {
  it('shows KPIs calculated by the backend and the synthetic-data notice', async () => {
    withCurrentAnalysis()
    renderAt('/')
    expect(await screen.findByText('£205')).toBeInTheDocument()
    expect(screen.getByText('£51.25')).toBeInTheDocument()
    expect(screen.getByText('Synthetic data.', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /revenue by region/i })).toBeInTheDocument()
  })

  it('loads the synthetic sample from the welcome screen', async () => {
    mockApi({ 'POST /samples/retail-2026/analyse': { status: 201, body: fixtureAnalysis }, 'GET /reports': { body: [] } })
    renderAt('/')
    fireEvent.click(screen.getByRole('button', { name: /try the synthetic sample/i }))
    expect(await screen.findByText('£205')).toBeInTheDocument()
    expect(screen.getByText('Sample dataset analysed')).toBeInTheDocument()
  })
})

describe('upload page', () => {
  const chooseFile = (file: File) => fireEvent.change(screen.getByLabelText(/drag a file here/i), { target: { files: [file] } })

  it('shows a validation error for a non-CSV file', () => {
    renderAt('/upload')
    chooseFile(new File(['x'], 'report.pdf', { type: 'application/pdf' }))
    expect(screen.getByRole('alert')).toHaveTextContent('"report.pdf" is not a CSV file')
  })

  it('uploads a CSV file and shows the server analysis summary', async () => {
    const fetchMock = mockApi({ 'POST /datasets/upload': { status: 201, body: fixtureAnalysis }, 'GET /samples': { body: [] } })
    renderAt('/upload')
    chooseFile(new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' }))
    expect(screen.getByText('orders.csv')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /validate and analyse/i }))
    expect(await screen.findByText('orders.csv analysed')).toBeInTheDocument()
    expect(screen.getByText(/5 rows received/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/datasets/upload', expect.objectContaining({ method: 'POST' }))
  })

  it('lists every problem the server reports', async () => {
    mockApi({
      'GET /samples': { body: [] },
      'POST /datasets/upload': {
        status: 422,
        body: { detail: { message: 'Required columns are missing: quantity.', problems: ['Required columns are missing: quantity.', 'One or more columns have no header name.'] } },
      },
    })
    renderAt('/upload')
    chooseFile(new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' }))
    fireEvent.click(screen.getByRole('button', { name: /validate and analyse/i }))
    const alert = await screen.findByText("This file can't be used")
    const box = alert.closest('[role="alert"]') as HTMLElement
    expect(within(box).getByText('Required columns are missing: quantity.')).toBeInTheDocument()
    expect(within(box).getByText('One or more columns have no header name.')).toBeInTheDocument()
  })

  it('lists the synthetic sample datasets from the API', async () => {
    mockApi({
      'GET /samples': { body: [{ id: 'retail-2026', file: 'r.csv', name: 'Retail sales', description: 'Fabricated', size_bytes: 1000, synthetic: true }] },
    })
    renderAt('/upload')
    expect(await screen.findByText('Retail sales')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyse sample' })).toBeInTheDocument()
  })
})

describe('analysis page', () => {
  it('shows cleaning rules, column profile and breakdowns', async () => {
    withCurrentAnalysis()
    renderAt('/analysis')
    expect(await screen.findByRole('heading', { name: 'Cleaning rules applied' })).toBeInTheDocument()
    expect(screen.getByText('C7')).toBeInTheDocument()
    expect(screen.getAllByText('Clothing').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Region' }))
    expect(screen.getByRole('button', { name: 'Region' })).toHaveAttribute('aria-pressed', 'true')
  })
})

describe('insights page', () => {
  it('labels rule-based observations as not AI-generated', async () => {
    withCurrentAnalysis()
    renderAt('/insights')
    expect(await screen.findByText('Rule-based observations (not AI-generated)')).toBeInTheDocument()
    expect(screen.getByText('Clothing is the largest category')).toBeInTheDocument()
  })

  it('labels AI output with the model name', async () => {
    const ai = {
      source: 'ai',
      model: 'claude-opus-5-5',
      generated_at: '2026-10-27T10:00:00Z',
      summary: 'Revenue grew.',
      insights: [{ title: 'Jackets lead', evidence: '£150 of £205', recommendation: 'Stock up', kind: 'mix' }],
      caveats: [],
      notice: 'AI-generated from the aggregated summary only.',
    }
    withCurrentAnalysis(fixtureAnalysis, {
      'GET /config': { body: { ...fixtureConfig, ai: { configured: true, model: 'claude-opus-5-5' } } },
      [`POST /analyses/${fixtureAnalysis.id}/insights`]: { body: ai },
    })
    renderAt('/insights')
    fireEvent.click(await screen.findByRole('button', { name: /generate ai insights/i }))
    expect(await screen.findByText('AI-generated · claude-opus-5-5')).toBeInTheDocument()
    expect(screen.getByText('Jackets lead')).toBeInTheDocument()
  })
})

describe('reports', () => {
  it('generates a report and offers the PDF download', async () => {
    const fetchMock = withCurrentAnalysis(fixtureAnalysis, { 'POST /reports': { status: 201, body: fixtureReport } })
    renderAt('/reports')
    fireEvent.click(await screen.findByRole('button', { name: /generate report/i }))
    const link = await screen.findByRole('link', { name: /download pdf/i })
    expect(link).toHaveAttribute('href', `/api/reports/${fixtureReport.id}/download`)
    const sent = JSON.parse(String(fetchMock.mock.calls.find((c) => String(c[0]) === '/api/reports' && c[1]?.method === 'POST')?.[1]?.body))
    expect(sent).toMatchObject({ analysis_id: fixtureAnalysis.id, notify_make: false })
  })

  it('disables the Make.com option when no webhook is configured', async () => {
    withCurrentAnalysis()
    renderAt('/reports')
    expect(await screen.findByRole('checkbox', { name: /make\.com/i })).toBeDisabled()
  })

  it('lists report history and deletes a report after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockApi({
      'GET /config': { body: fixtureConfig },
      'GET /reports': { body: [fixtureReport] },
      [`DELETE /reports/${fixtureReport.id}`]: { status: 204 },
    })
    renderAt('/history')
    expect(await screen.findByText('Q1 review')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete Q1 review' }))
    await waitFor(() => expect(screen.queryByText('Q1 review')).not.toBeInTheDocument())
  })
})

describe('settings page', () => {
  it('shows integration status from the server without secrets', async () => {
    mockApi({ 'GET /config': { body: fixtureConfig } })
    renderAt('/settings')
    expect(await screen.findByText(/Set AI_API_KEY on the server/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send test event/i })).toBeDisabled()
    expect(screen.getByText('C1')).toBeInTheDocument()
  })
})
