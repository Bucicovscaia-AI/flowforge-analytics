import { FileText, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { ReportSummary } from '../api/types'
import { InsightModeBadge, ReportDownloads, ReportStatusBadge } from '../components/ReportDownloads'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardHeader } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/Dialog'
import { Toggle } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { formatDateTime, formatNumber } from '../lib/format'

export function ReportHistoryPage() {
  const { selected, datasets } = useApp()
  const { notify } = useToast()
  const [onlySelected, setOnlySelected] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<ReportSummary | null>(null)
  const [deleting, setDeleting] = useState(false)
  const datasetFilter = onlySelected ? selected?.id : undefined
  const reports = useApi(`history:${datasetFilter ?? 'all'}`, () => api.listReports(datasetFilter, 200))

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.deleteReport(pendingDelete.id)
      notify('success', 'Report deleted', pendingDelete.title)
      setPendingDelete(null)
      reports.reload()
    } catch (error) {
      notify('error', 'Could not delete the report', errorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Report History"
        description="Every report generated on this server. Report files are stored with a snapshot of the data at the time, so they stay the same even if the dataset changes or is deleted."
        actions={
          <LinkButton to="/reports" variant="primary" icon={FileText}>
            New report
          </LinkButton>
        }
      />
      <Card>
        <CardHeader
          title={reports.data ? `${formatNumber(reports.data.length)} report${reports.data.length === 1 ? '' : 's'}` : 'Reports'}
          actions={selected && <Toggle label={`Only ${selected.name}`} checked={onlySelected} onChange={setOnlySelected} />}
        />
        {reports.loading && !reports.data ? (
          <LoadingState />
        ) : reports.error ? (
          <ErrorState error={reports.error} onRetry={reports.reload} />
        ) : !reports.data?.length ? (
          <EmptyState
            icon={FileText}
            title="No reports yet"
            description={onlySelected ? 'No reports have been generated from this dataset.' : 'Reports you generate are kept here.'}
            actions={
              <LinkButton to="/reports" variant="primary" icon={FileText}>
                Generate a report
              </LinkButton>
            }
          />
        ) : (
          <TableContainer label="Report history">
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>Dataset</Th>
                <Th>Generated</Th>
                <Th numeric>Records</Th>
                <Th>Insights</Th>
                <Th>Status</Th>
                <Th>Files</Th>
                <Th className="text-right">Delete</Th>
              </tr>
            </thead>
            <tbody>
              {reports.data.map((report) => (
                <Tr key={report.id}>
                  <Td className="font-medium text-slate-800">{report.title}</Td>
                  <Td>
                    {report.dataset_name}
                    {!datasets.some((dataset) => dataset.id === report.dataset_id) && <p className="text-xs text-slate-500">dataset deleted</p>}
                  </Td>
                  <Td className="whitespace-nowrap">{formatDateTime(report.created_at)}</Td>
                  <Td numeric>{formatNumber(report.record_count)}</Td>
                  <Td>
                    <InsightModeBadge mode={report.insight_mode} />
                  </Td>
                  <Td>
                    <ReportStatusBadge report={report} />
                  </Td>
                  <Td>
                    <ReportDownloads report={report} compact />
                  </Td>
                  <Td className="text-right">
                    <Button size="sm" variant="ghost" icon={Trash2} aria-label={`Delete ${report.title}`} onClick={() => setPendingDelete(report)} />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </TableContainer>
        )}
      </Card>
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete report?"
        confirmLabel="Delete report"
        busy={deleting}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => void confirmDelete()}
      >
        <p>
          <strong>{pendingDelete?.title}</strong> and all its files will be permanently removed. Links to it, including any sent to Make.com, will
          stop working.
        </p>
      </ConfirmDialog>
    </>
  )
}
