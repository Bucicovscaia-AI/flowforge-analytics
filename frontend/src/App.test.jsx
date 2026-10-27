import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppRoutes } from './App'

function renderAt(path) {
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

describe('demo data labelling', () => {
  it('labels dashboard figures as demonstration data', () => {
    renderAt('/')
    expect(screen.getByText('Demonstration data.')).toBeInTheDocument()
    expect(screen.getByText('£133,240')).toBeInTheDocument()
  })
})

describe('upload page', () => {
  it('shows a validation error for a non-CSV file', () => {
    renderAt('/upload')
    const input = screen.getByLabelText(/drag a file here/i)
    fireEvent.change(input, { target: { files: [new File(['x'], 'report.pdf', { type: 'application/pdf' })] } })
    expect(screen.getByRole('alert')).toHaveTextContent('"report.pdf" is not a CSV file')
  })

  it('accepts a CSV file and shows its name', () => {
    renderAt('/upload')
    const input = screen.getByLabelText(/drag a file here/i)
    fireEvent.change(input, { target: { files: [new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' })] } })
    expect(screen.getByText('orders.csv')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
