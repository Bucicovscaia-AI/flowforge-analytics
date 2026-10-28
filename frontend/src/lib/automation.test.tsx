import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { AutomationRun } from '../api/types'
import { RunStatus } from '../components/AutomationRunStatus'
import { runDetail } from './automation'

const accepted: AutomationRun = {
  id: 'a'.repeat(32),
  event_type: 'report.generated',
  trigger: 'manual',
  dataset_id: null,
  report_id: 'b'.repeat(32),
  status: 'delivered',
  http_status: 200,
  message: 'The webhook accepted the event (HTTP 200).',
  duration_ms: 120,
  payload: {},
  created_at: '2026-10-28T10:00:00+00:00',
  pdf_downloaded_at: null,
  confirmation_status: 'pending',
  confirmation_message: null,
  confirmed_at: null,
}

describe('automation run status', () => {
  it('does not present an accepted webhook call as a delivered email', () => {
    render(<RunStatus run={accepted} />)
    expect(screen.getByText('Accepted, not confirmed')).toBeInTheDocument()
    expect(runDetail(accepted)).toContain('No confirmation from the scenario yet.')
  })

  it('shows the outcome the scenario reported', () => {
    const { rerender } = render(<RunStatus run={{ ...accepted, confirmation_status: 'sent' }} />)
    expect(screen.getByText('Confirmed by Make.com')).toBeInTheDocument()
    rerender(<RunStatus run={{ ...accepted, confirmation_status: 'failed' }} />)
    expect(screen.getByText('Scenario failed')).toBeInTheDocument()
    expect(runDetail({ ...accepted, confirmation_status: 'failed', confirmation_message: 'Gmail quota exceeded' })).toContain(
      'Scenario reported a failure: Gmail quota exceeded',
    )
  })

  it('shows a rejected webhook call as not accepted', () => {
    render(<RunStatus run={{ ...accepted, status: 'failed', confirmation_status: null }} />)
    expect(screen.getByText('Not accepted')).toBeInTheDocument()
  })
})
