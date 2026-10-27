import { Database, FlaskConical, Upload } from 'lucide-react'
import type { ReactNode } from 'react'

import type { DatasetSummary } from '../api/types'
import { useApp } from '../context/AppContext'
import { useLoadSample } from '../hooks/useLoadSample'
import { Button, LinkButton } from './ui/Button'
import { Card } from './ui/Card'
import { EmptyState, ErrorState, LoadingState } from './ui/States'

/** Render children for the selected dataset, or guide the user to import one. */
export function RequireDataset({ children, purpose }: { children: (dataset: DatasetSummary) => ReactNode; purpose: string }) {
  const { datasetsLoaded, datasetsError, selected, refreshDatasets } = useApp()
  const { loadSample, loading } = useLoadSample()

  if (!datasetsLoaded) return <LoadingState label="Loading datasets…" />
  if (datasetsError) {
    return (
      <Card>
        <ErrorState title="Datasets could not be loaded" error={datasetsError} onRetry={() => void refreshDatasets()} />
      </Card>
    )
  }
  if (!selected) {
    return (
      <Card>
        <EmptyState
          icon={Database}
          title="No dataset yet"
          description={`Import a CSV file or load the synthetic sample dataset to ${purpose}.`}
          actions={
            <>
              <LinkButton to="/upload" variant="primary" icon={Upload}>
                Upload a CSV
              </LinkButton>
              <Button variant="secondary" icon={FlaskConical} loading={loading} onClick={() => void loadSample()}>
                Load sample data
              </Button>
            </>
          }
        />
      </Card>
    )
  }
  return <>{children(selected)}</>
}
