import { FlaskConical, Upload } from 'lucide-react'

import { useApp } from '../context/AppContext'
import { useLoadSample } from '../hooks/useLoadSample'
import { Alert } from './ui/Alert'
import { Button, LinkButton } from './ui/Button'

/** Explains that data shown earlier is no longer on the server, and offers the ways to continue. */
export function DataGoneNotice() {
  const { dataGone, dismissDataGone, system } = useApp()
  const { loadSample, loading } = useLoadSample()
  if (!dataGone) return null
  const temporary = system?.storage.persistent === false
  return (
    <Alert
      tone="warning"
      className="mb-6"
      title="Some data is no longer on the server"
      actions={
        <>
          <span onClick={dismissDataGone}>
            <LinkButton to="/upload" size="sm" icon={Upload}>
              Upload a CSV
            </LinkButton>
          </span>
          <Button size="sm" variant="secondary" icon={FlaskConical} loading={loading} onClick={() => void loadSample().then((dataset) => dataset && dismissDataGone())}>
            Load sample data
          </Button>
          <Button size="sm" variant="ghost" onClick={dismissDataGone}>
            Dismiss
          </Button>
        </>
      }
    >
      {temporary
        ? 'This server keeps uploads on temporary storage, which is cleared whenever it restarts (for example after a period without visits or a new deployment). Datasets and reports from before the restart are gone. Upload the file again to continue.'
        : 'A dataset this page was showing has been deleted. The list has been refreshed.'}
    </Alert>
  )
}
