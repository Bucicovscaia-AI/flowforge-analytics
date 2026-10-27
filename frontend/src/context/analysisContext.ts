import { createContext, useContext } from 'react'
import type { Analysis, AppConfig, InsightResult } from '../types'

export interface AnalysisState {
  /** The analysis the pages are showing, or null before any dataset is loaded. */
  analysis: Analysis | null
  /** True while the stored analysis is being fetched on start-up. */
  loading: boolean
  config: AppConfig | null
  setAnalysis: (analysis: Analysis | null) => void
  setInsights: (insights: InsightResult) => void
  refreshConfig: () => void
}

export const AnalysisContext = createContext<AnalysisState | null>(null)

export function useAnalysis(): AnalysisState {
  const value = useContext(AnalysisContext)
  if (!value) throw new Error('useAnalysis must be used inside AnalysisProvider')
  return value
}
