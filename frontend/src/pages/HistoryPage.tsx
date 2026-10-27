import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import EmptyState from '../components/ui/EmptyState'
import PageHeader from '../components/ui/PageHeader'
import Spinner from '../components/ui/Spinner'
import StatusBadge from '../components/ui/StatusBadge'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { deleteReport, listReports, notifyReport, reportDownloadUrl } from '../services/api'
import type { Report, WebhookStatus } from '../types'
import { formatCurrency, formatDateTime, formatFileSize } from '../utils/format'

function WebhookBadge({ webhook }: { webhook: WebhookStatus }) {
  switch (webhook.status) {
    case 'delivered':
      return <StatusBadge variant="success">Sent</StatusBadge>
    case 'failed':
      return <StatusBadge variant="error">Failed</StatusBadge>
    case 'not_requested':
      return <StatusBadge>Not sent</StatusBadge>
    default:
      return <StatusBadge>Not configured</StatusBadge>
  }
}

export default function HistoryPage() {
  const { config } = useAnalysis()
  const { notify } = useToast()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const webhookConfigured = config?.webhook.configured ?? false

  const load = useCallback(() => {
    listReports()
      .then((items) => {
        setReports(items)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

  async function remove(report: Report) {
    if (!window.confirm(`Delete "${report.title}"? The PDF will be removed permanently.`)) return
    setBusyId(report.id)
    try {
      await deleteReport(report.id)
      setReports((all) => all?.filter((r) => r.id !== report.id) ?? null)
      notify('success', 'Report deleted')
    } catch (e) {
      notify('error', 'Could not delete the report', (e as Error).message)
    } finally {
      setBusyId(null)
    }
  }

  async function send(report: Report) {
    setBusyId(report.id)
    try {
      const status = await notifyReport(report.id)
      notify('success', 'Sent to Make.com', status.message)
    } catch (e) {
      notify('error', 'Make.com webhook failed', (e as Error).message)
    } finally {
      setBusyId(null)
      load()
    }
  }

  return (
    <>
      <PageHeader
        title="Report History"
        description="Every report generated on this server, newest first."
        actions={
          <Button variant="secondary" icon="refresh" onClick={load}>
            Refresh
          </Button>
        }
      />
      <Card>
        {error ? (
          <Alert variant="error" title="Report history could not be loaded">
            {error}
          </Alert>
        ) : reports === null ? (
          <Spinner label="Loading reports…" />
        ) : reports.length === 0 ? (
          <EmptyState
            icon="history"
            title="No reports generated yet"
            action={
              <Link to="/reports" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
                Go to Reports
              </Link>
            }
          >
            Reports appear here after you generate one from an analysed dataset.
          </EmptyState>
        ) : (
          <DataTable<Report>
            caption="Report history"
            rowKey={(r) => r.id}
            rows={reports}
            columns={[
              {
                key: 'title',
                header: 'Report',
                render: (r) => (
                  <div className="max-w-xs whitespace-normal">
                    <p className="font-medium text-slate-900">{r.title}</p>
                    <p className="text-xs text-slate-500">
                      {r.dataset}
                      {r.synthetic && ' · synthetic'}
                    </p>
                  </div>
                ),
              },
              { key: 'created', header: 'Created', render: (r) => formatDateTime(r.created_at) },
              { key: 'revenue', header: 'Revenue', align: 'right', render: (r) => formatCurrency(r.total_revenue) },
              {
                key: 'source',
                header: 'Insights',
                render: (r) => (r.insight_source === 'ai' ? <StatusBadge variant="ai">AI</StatusBadge> : <StatusBadge>Rule-based</StatusBadge>),
              },
              { key: 'webhook', header: 'Make.com', render: (r) => <WebhookBadge webhook={r.webhook} /> },
              {
                key: 'actions',
                header: <span className="sr-only">Actions</span>,
                render: (r) => (
                  <div className="flex justify-end gap-2">
                    <a
                      href={reportDownloadUrl(r.id)}
                      download
                      className="inline-flex items-center rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-300 ring-inset hover:bg-slate-50"
                      aria-label={`Download ${r.title} (${formatFileSize(r.size_bytes)})`}
                    >
                      Download
                    </a>
                    {webhookConfigured && (
                      <Button variant="secondary" className="!px-3 !py-1.5 text-xs" disabled={busyId === r.id} onClick={() => send(r)} aria-label={`Send ${r.title} to Make.com`}>
                        Send
                      </Button>
                    )}
                    <Button variant="danger" className="!px-3 !py-1.5 text-xs" disabled={busyId === r.id} onClick={() => remove(r)} aria-label={`Delete ${r.title}`}>
                      Delete
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>
    </>
  )
}
