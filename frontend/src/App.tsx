import { lazy, Suspense, type ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'

import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { LoadingState } from './components/ui/States'

// The dashboard loads with the shell; other sections are fetched when first opened.
const AnalysisPage = lazy(() => import('./pages/AnalysisPage').then((module) => ({ default: module.AnalysisPage })))
const AutomationPage = lazy(() => import('./pages/AutomationPage').then((module) => ({ default: module.AutomationPage })))
const DatasetsPage = lazy(() => import('./pages/DatasetsPage').then((module) => ({ default: module.DatasetsPage })))
const InsightsPage = lazy(() => import('./pages/InsightsPage').then((module) => ({ default: module.InsightsPage })))
const QualityPage = lazy(() => import('./pages/QualityPage').then((module) => ({ default: module.QualityPage })))
const ReportHistoryPage = lazy(() => import('./pages/ReportHistoryPage').then((module) => ({ default: module.ReportHistoryPage })))
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })))
const UploadPage = lazy(() => import('./pages/UploadPage').then((module) => ({ default: module.UploadPage })))
const VisualisationsPage = lazy(() => import('./pages/VisualisationsPage').then((module) => ({ default: module.VisualisationsPage })))

function page(element: ReactNode) {
  return <Suspense fallback={<LoadingState />}>{element}</Suspense>
}

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={page(<UploadPage />)} />
        <Route path="datasets" element={page(<DatasetsPage />)} />
        <Route path="quality" element={page(<QualityPage />)} />
        <Route path="analysis" element={page(<AnalysisPage />)} />
        <Route path="visualisations" element={page(<VisualisationsPage />)} />
        <Route path="insights" element={page(<InsightsPage />)} />
        <Route path="reports" element={page(<ReportsPage />)} />
        <Route path="reports/history" element={page(<ReportHistoryPage />)} />
        <Route path="automation" element={page(<AutomationPage />)} />
        <Route path="settings" element={page(<SettingsPage />)} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
