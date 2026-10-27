import { useCallback, useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { DatasetSummary } from '../api/types'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'

/** Import the synthetic sample dataset through the normal import pipeline and select it. */
export function useLoadSample(): { loadSample: () => Promise<DatasetSummary | null>; loading: boolean } {
  const { refreshDatasets, selectDataset } = useApp()
  const { notify } = useToast()
  const [loading, setLoading] = useState(false)

  const loadSample = useCallback(async () => {
    setLoading(true)
    try {
      const dataset = await api.loadSample()
      await refreshDatasets()
      selectDataset(dataset.id)
      notify('success', 'Sample dataset loaded', `${dataset.row_count.toLocaleString('en-GB')} synthetic orders are ready to explore.`)
      return dataset
    } catch (error) {
      notify('error', 'Could not load the sample dataset', errorMessage(error))
      return null
    } finally {
      setLoading(false)
    }
  }, [notify, refreshDatasets, selectDataset])

  return { loadSample, loading }
}
