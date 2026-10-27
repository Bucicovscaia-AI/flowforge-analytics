import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import { getAnalysis, getConfig } from '../services/api'
import type { Analysis, AppConfig, InsightResult } from '../types'
import { AnalysisContext } from './analysisContext'

const STORAGE_KEY = 'flowforge.currentAnalysisId'

// Only the analysis id is kept in the browser; the results themselves are
// always fetched from the backend.
function readStoredId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function storeId(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Private browsing: the current analysis just won't survive a reload.
  }
}

export default function AnalysisProvider({ children }: { children: ReactNode }) {
  const [analysis, setAnalysisState] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(() => readStoredId() !== null)
  const [config, setConfig] = useState<AppConfig | null>(null)

  const refreshConfig = useCallback(() => {
    getConfig()
      .then(setConfig)
      .catch(() => setConfig(null))
  }, [])

  useEffect(() => {
    refreshConfig()
    const id = readStoredId()
    if (!id) return
    getAnalysis(id)
      .then(setAnalysisState)
      .catch(() => storeId(null))
      .finally(() => setLoading(false))
  }, [refreshConfig])

  const setAnalysis = useCallback((next: Analysis | null) => {
    setAnalysisState(next)
    storeId(next?.id ?? null)
  }, [])

  const setInsights = useCallback((insights: InsightResult) => {
    setAnalysisState((current) => (current ? { ...current, insights } : current))
  }, [])

  const value = useMemo(
    () => ({ analysis, loading, config, setAnalysis, setInsights, refreshConfig }),
    [analysis, loading, config, setAnalysis, setInsights, refreshConfig],
  )
  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>
}
