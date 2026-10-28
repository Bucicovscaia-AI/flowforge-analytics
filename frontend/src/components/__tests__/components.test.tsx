import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { request, SLOW_REQUEST_MS } from '../../api/client'
import { ChartCard } from '../charts/ChartCard'
import { ServerWakingNotice } from '../ServerWakingNotice'
import { ConfirmDialog } from '../ui/Dialog'
import { Toggle } from '../ui/Field'
import { QualityBadge } from '../ui/QualityBadge'

describe('ChartCard', () => {
  it('switches between the chart and its table view', async () => {
    render(
      <ChartCard title="Revenue" table={<table aria-label="Revenue values" />}>
        <div>chart body</div>
      </ChartCard>,
    )
    expect(screen.getByText('chart body')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: 'Table' }))
    expect(screen.queryByText('chart body')).not.toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Revenue values' })).toBeInTheDocument()
  })
})

describe('Toggle', () => {
  function Harness({ disabled = false }: { disabled?: boolean }) {
    const [on, setOn] = useState(false)
    return <Toggle label="Use AI" checked={on} onChange={setOn} disabled={disabled} />
  }

  it('toggles when clicked', async () => {
    render(<Harness />)
    const toggle = screen.getByRole('switch', { name: 'Use AI' })
    expect(toggle).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'true')
  })

  it('cannot be switched on while disabled', async () => {
    render(<Harness disabled />)
    const toggle = screen.getByRole('switch', { name: 'Use AI' })
    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'false')
  })
})

describe('QualityBadge', () => {
  it('shows the score and grade', () => {
    render(<QualityBadge score={91.25} grade="Good" />)
    expect(screen.getByText(/91\.3/)).toBeInTheDocument()
  })
})

describe('ConfirmDialog', () => {
  it('calls the handlers for confirm and cancel', async () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmDialog open title="Delete dataset?" confirmLabel="Delete dataset" onConfirm={onConfirm} onCancel={onCancel}>
        <p>This cannot be undone.</p>
      </ConfirmDialog>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Delete dataset' }))
    expect(onConfirm).toHaveBeenCalledOnce()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledOnce()
  })
})

describe('ServerWakingNotice', () => {
  it('appears only while a request is taking longer than usual', async () => {
    vi.useFakeTimers()
    let finish: (response: Response) => void = () => {}
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => (finish = resolve))))
    try {
      render(<ServerWakingNotice />)
      const pending = request('GET', '/system/status')
      expect(screen.queryByText('The server is waking up')).not.toBeInTheDocument()
      await act(() => vi.advanceTimersByTimeAsync(SLOW_REQUEST_MS))
      expect(screen.getByText('The server is waking up')).toBeInTheDocument()
      await act(async () => {
        finish(new Response('{}', { status: 200 }))
        await pending
      })
      expect(screen.queryByText('The server is waking up')).not.toBeInTheDocument()
    } finally {
      vi.unstubAllGlobals()
      vi.useRealTimers()
    }
  })
})
