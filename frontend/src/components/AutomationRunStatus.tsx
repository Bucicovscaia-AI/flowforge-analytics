import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react'

import type { AutomationRun } from '../api/types'
import { Badge } from './ui/Badge'

/**
 * Status of one event. A webhook answering HTTP 200 only means Make.com queued the event;
 * whether the scenario sent its email is known only if the scenario calls its confirmation link.
 */
export function RunStatus({ run }: { run: AutomationRun }) {
  if (run.status === 'sending')
    return (
      <Badge tone="neutral">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Sending
      </Badge>
    )
  if (run.status === 'failed')
    return (
      <Badge tone="danger">
        <XCircle className="size-3" aria-hidden />
        Not accepted
      </Badge>
    )
  if (run.confirmation_status === 'sent')
    return (
      <Badge tone="success">
        <CheckCircle2 className="size-3" aria-hidden />
        Confirmed by Make.com
      </Badge>
    )
  if (run.confirmation_status === 'failed')
    return (
      <Badge tone="danger">
        <XCircle className="size-3" aria-hidden />
        Scenario failed
      </Badge>
    )
  return (
    <Badge tone="info">
      <Clock className="size-3" aria-hidden />
      Accepted, not confirmed
    </Badge>
  )
}
