import { useSyncExternalStore } from 'react'

import { isServerSlow, subscribeServerSlow } from '../api/client'
import { Alert } from './ui/Alert'

/** Tells the visitor why the page is still loading when the server is starting up after a quiet period. */
export function ServerWakingNotice() {
  const slow = useSyncExternalStore(subscribeServerSlow, isServerSlow)
  if (!slow) return null
  return (
    <Alert tone="info" className="mb-6" title="The server is waking up">
      FlowForge runs on a free hosting plan that pauses after a period without visits. Starting it again can take up to a minute. The page
      will continue on its own as soon as it is ready.
    </Alert>
  )
}
