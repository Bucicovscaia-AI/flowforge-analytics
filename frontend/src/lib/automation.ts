import type { AutomationRun } from '../api/types'
import { formatDateTime } from './format'

/** One line describing what is known about an event, including what happened after the webhook accepted it. */
export function runDetail(run: AutomationRun): string {
  if (run.status !== 'delivered') return run.message
  const parts = [run.message]
  if (run.pdf_downloaded_at) parts.push(`PDF downloaded ${formatDateTime(run.pdf_downloaded_at)}.`)
  const note = run.confirmation_message ? `: ${run.confirmation_message}` : '.'
  if (run.confirmation_status === 'sent') parts.push(`Scenario reported success${note}`)
  else if (run.confirmation_status === 'failed') parts.push(`Scenario reported a failure${note}`)
  else parts.push('No confirmation from the scenario yet.')
  return parts.join(' ')
}
