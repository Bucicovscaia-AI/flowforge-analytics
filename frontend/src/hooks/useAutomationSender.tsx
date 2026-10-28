import { useState, type ReactNode } from 'react'

import { api, ApiError, errorMessage } from '../api/client'
import type { AutomationRun, EventType } from '../api/types'
import { ConfirmDialog } from '../components/ui/Dialog'
import { useToast } from '../context/ToastContext'

type Target = [EventType, string | undefined, string | undefined]

/** Sends an event and, when the server reports the report was already sent, asks before sending it again. */
export function useAutomationSender(onSent: (run: AutomationRun) => void) {
  const { notify } = useToast()
  const [sending, setSending] = useState(false)
  const [duplicate, setDuplicate] = useState<{ message: string; target: Target } | null>(null)

  const run = async (target: Target, resend: boolean) => {
    setSending(true)
    try {
      const result = await api.triggerAutomation(...target, resend)
      if (result.status === 'delivered')
        notify('success', 'Accepted by Make.com', 'The scenario received the event. Delivery history shows whether it confirms the email.')
      else notify('error', 'Make.com did not accept the event', result.message)
      setDuplicate(null)
      onSent(result)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'already_sent') setDuplicate({ message: error.message, target })
      else notify('error', 'Could not send the event', errorMessage(error))
    } finally {
      setSending(false)
    }
  }

  const dialog: ReactNode = (
    <ConfirmDialog
      open={duplicate !== null}
      title="Send this report again?"
      confirmLabel="Send again"
      tone="primary"
      busy={sending}
      onCancel={() => setDuplicate(null)}
      onConfirm={() => duplicate && void run(duplicate.target, true)}
    >
      <p>{duplicate?.message}</p>
      <p className="mt-2">Sending again starts the scenario again, so recipients may receive a second email.</p>
    </ConfirmDialog>
  )

  return {
    sending,
    send: (eventType: EventType, datasetId?: string, reportId?: string) => run([eventType, datasetId, reportId], false),
    dialog,
  }
}
