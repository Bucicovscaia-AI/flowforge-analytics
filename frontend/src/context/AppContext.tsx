import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { api, MISSING_DATA_EVENT } from '../api/client'
import type { DatasetSummary, SystemStatus } from '../api/types'
import { useLocalStorage } from '../hooks/useLocalStorage'
import type { CurrencySymbol } from '../lib/format'

interface AppState {
  datasets: DatasetSummary[]
  datasetsLoaded: boolean
  datasetsError: unknown
  selected: DatasetSummary | null
  selectDataset: (id: string | null) => void
  refreshDatasets: () => Promise<DatasetSummary[]>
  /** Increments whenever the selected dataset's contents change, so pages can reload. */
  dataVersion: number
  notifyDataChanged: () => void
  /** True when data the user was working with disappeared from the server without being deleted here. */
  dataGone: boolean
  dismissDataGone: () => void
  system: SystemStatus | null
  systemError: unknown
  currency: CurrencySymbol
  setCurrency: (value: CurrencySymbol) => void
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [datasetsLoaded, setDatasetsLoaded] = useState(false)
  const [datasetsError, setDatasetsError] = useState<unknown>()
  const [selectedId, setSelectedId] = useLocalStorage<string | null>('flowforge.selectedDataset', null)
  const [currency, setCurrency] = useLocalStorage<CurrencySymbol>('flowforge.currency', '')
  const [dataVersion, setDataVersion] = useState(0)
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [systemError, setSystemError] = useState<unknown>()
  const [dataGone, setDataGone] = useState(false)
  const datasetsRef = useRef<DatasetSummary[]>([])

  useEffect(() => {
    datasetsRef.current = datasets
  }, [datasets])

  const refreshDatasets = useCallback(async () => {
    try {
      const list = await api.listDatasets()
      setDatasets(list)
      setDatasetsError(undefined)
      return list
    } catch (error) {
      setDatasetsError(error)
      return []
    } finally {
      setDatasetsLoaded(true)
    }
  }, [])

  useEffect(() => {
    let active = true
    api
      .listDatasets()
      .then(
        (list) => {
          if (active) setDatasets(list)
        },
        (error: unknown) => {
          if (active) setDatasetsError(error)
        },
      )
      .finally(() => {
        if (active) setDatasetsLoaded(true)
      })
    api
      .systemStatus()
      .then(setSystem)
      .catch(setSystemError)
    return () => {
      active = false
    }
  }, [])

  const selected = useMemo(() => {
    if (!datasets.length) return null
    return datasets.find((dataset) => dataset.id === selectedId) ?? datasets[0]
  }, [datasets, selectedId])

  // The server can lose data on its own (temporary storage is wiped on restart). When a request refers to
  // something that no longer exists, or the user comes back to the tab, reload the list and say what happened.
  const recheckDatasets = useCallback(async () => {
    const before = datasetsRef.current
    let list: DatasetSummary[]
    try {
      list = await api.listDatasets()
    } catch {
      return
    }
    const ids = new Set(list.map((dataset) => dataset.id))
    if (before.some((dataset) => !ids.has(dataset.id))) setDataGone(true)
    setDatasets(list)
    setDataVersion((value) => value + 1)
  }, [])

  useEffect(() => {
    const onMissing = () => void recheckDatasets()
    const onVisible = () => {
      if (document.visibilityState === 'visible') void recheckDatasets()
    }
    window.addEventListener(MISSING_DATA_EVENT, onMissing)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener(MISSING_DATA_EVENT, onMissing)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [recheckDatasets])

  const dismissDataGone = useCallback(() => setDataGone(false), [])

  // Refresh the list first so pages never reload data for a dataset that was just deleted.
  const notifyDataChanged = useCallback(() => {
    void refreshDatasets().then(() => setDataVersion((value) => value + 1))
  }, [refreshDatasets])

  const value = useMemo<AppState>(
    () => ({
      datasets,
      datasetsLoaded,
      datasetsError,
      selected,
      selectDataset: setSelectedId,
      refreshDatasets,
      dataVersion,
      notifyDataChanged,
      dataGone,
      dismissDataGone,
      system,
      systemError,
      currency,
      setCurrency,
    }),
    [datasets, datasetsLoaded, datasetsError, selected, setSelectedId, refreshDatasets, dataVersion, notifyDataChanged, dataGone, dismissDataGone, system, systemError, currency, setCurrency],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useApp(): AppState {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used inside AppProvider')
  return context
}
