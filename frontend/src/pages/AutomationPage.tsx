import { Eye, Send, Workflow } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { AutomationRun, EventType } from '../api/types'
import { RunStatus } from '../components/AutomationRunStatus'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Dialog } from '../components/ui/Dialog'
import { SelectField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { useAutomationSender } from '../hooks/useAutomationSender'
import { runDetail } from '../lib/automation'
import { formatDateTime, formatNumber } from '../lib/format'

const EVENT_LABELS: Record<EventType, string> = {
  'dataset.analysed': 'Dataset analysed',
  'report.generated': 'Report generated',
  'automation.test': 'Connection test',
}

const EVENT_CONTENTS: Record<EventType, string> = {
  'automation.test': 'No dataset or report data: only the event details and a confirmation link. Safe for checking the connection.',
  'dataset.analysed': 'Dataset name, size and quality score, and the calculated KPIs. No rows from the dataset.',
  'report.generated':
    'Dataset and report details, the KPIs exactly as they appear in the report, and a temporary signed link to the report PDF. No rows from the dataset.',
}

export function AutomationPage() {
  const { datasets, selected, dataVersion } = useApp()
  const { notify } = useToast()
  const status = useApi('automation-status', () => api.automationStatus())
  const [runsVersion, setRunsVersion] = useState(0)
  const runs = useApi(`automation-runs:${runsVersion}:${dataVersion}`, () => api.automationRuns(50))
  const [eventType, setEventType] = useState<EventType>('dataset.analysed')
  const [datasetId, setDatasetId] = useState('')
  const [reportId, setReportId] = useState('')
  const reports = useApi(eventType === 'report.generated' ? `automation-reports:${dataVersion}` : null, () => api.listReports(undefined, 50))
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [viewRun, setViewRun] = useState<AutomationRun | null>(null)

  // Default to the selected dataset and the newest report until the user picks another.
  const chosenDatasetId = datasetId || selected?.id || ''
  const chosenReportId = reportId || reports.data?.[0]?.id || ''

  const target = (): [string | undefined, string | undefined] => {
    if (eventType === 'dataset.analysed') return [chosenDatasetId || undefined, undefined]
    if (eventType === 'report.generated') return [undefined, chosenReportId || undefined]
    return [undefined, undefined]
  }
  const missingTarget = (eventType === 'dataset.analysed' && !chosenDatasetId) || (eventType === 'report.generated' && !chosenReportId)

  const showPreview = async () => {
    setPreviewing(true)
    try {
      setPreview(await api.previewAutomation(eventType, ...target()))
    } catch (error) {
      notify('error', 'Could not build the preview', errorMessage(error))
    } finally {
      setPreviewing(false)
    }
  }

  const sender = useAutomationSender(() => setRunsVersion((value) => value + 1))

  const configured = Boolean(status.data?.configured)

  return (
    <>
      <PageHeader title="Automation" />

      {status.loading && !status.data ? (
        <LoadingState />
      ) : status.error ? (
        <Card>
          <ErrorState error={status.error} onRetry={status.reload} />
        </Card>
      ) : (
        status.data && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Send an event" />
              <CardBody className="max-w-3xl space-y-4">
                <SelectField
                  label="Event"
                  value={eventType}
                  onChange={(event) => {
                    setEventType(event.target.value as EventType)
                    setPreview(null)
                  }}
                  hint={EVENT_CONTENTS[eventType]}
                >
                  {status.data.event_types.map((item) => (
                    <option key={item.type} value={item.type}>
                      {EVENT_LABELS[item.type]}
                    </option>
                  ))}
                </SelectField>
                {eventType === 'dataset.analysed' && (
                  <SelectField
                    label="Dataset"
                    value={chosenDatasetId}
                    onChange={(event) => {
                      setDatasetId(event.target.value)
                      setPreview(null)
                    }}
                  >
                    {datasets.length === 0 && <option value="">No datasets</option>}
                    {datasets.map((dataset) => (
                      <option key={dataset.id} value={dataset.id}>
                        {dataset.name}
                      </option>
                    ))}
                  </SelectField>
                )}
                {eventType === 'report.generated' && (
                  <SelectField
                    label="Report"
                    value={chosenReportId}
                    onChange={(event) => {
                      setReportId(event.target.value)
                      setPreview(null)
                    }}
                  >
                    {!reports.data?.length && <option value="">No reports</option>}
                    {reports.data?.map((report) => (
                      <option key={report.id} value={report.id}>
                        {report.title} · {formatDateTime(report.created_at)}
                      </option>
                    ))}
                  </SelectField>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" icon={Eye} loading={previewing} disabled={missingTarget} onClick={() => void showPreview()}>
                    Preview data
                  </Button>
                  <Button icon={Send} loading={sender.sending} disabled={!configured || missingTarget} onClick={() => void sender.send(eventType, ...target())}>
                    Send to Make.com
                  </Button>
                </div>
                <p className="text-xs text-slate-500">
                  {configured
                    ? 'Check the quality score and date range before you send, and forward the PDF file rather than its link.'
                    : 'Sending is not enabled for this workspace. You can still preview what would be sent.'}
                </p>
                {preview && (
                  <pre className="max-h-80 overflow-auto rounded-lg bg-ink-950 p-4 text-xs leading-relaxed text-slate-100" aria-label="Data preview">
                    {JSON.stringify(preview, null, 2)}
                  </pre>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Delivery history" />
              {runs.loading && !runs.data ? (
                <LoadingState />
              ) : runs.error ? (
                <ErrorState error={runs.error} onRetry={runs.reload} />
              ) : !runs.data?.length ? (
                <EmptyState icon={Workflow} title="No events sent yet" description="Events you send to Make.com are recorded here with their result." />
              ) : (
                <TableContainer label="Delivery history">
                  <thead>
                    <tr>
                      <Th>Sent</Th>
                      <Th>Event</Th>
                      <Th>Trigger</Th>
                      <Th>Result</Th>
                      <Th numeric>Time</Th>
                      <Th>Message</Th>
                      <Th className="text-right">Data sent</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data.map((run) => (
                      <Tr key={run.id}>
                        <Td className="whitespace-nowrap">{formatDateTime(run.created_at)}</Td>
                        <Td>{EVENT_LABELS[run.event_type]}</Td>
                        <Td>{run.trigger === 'rule' ? 'Rule' : 'Manual'}</Td>
                        <Td>
                          <RunStatus run={run} />
                        </Td>
                        <Td numeric>{run.duration_ms !== null ? `${formatNumber(run.duration_ms)} ms` : '–'}</Td>
                        <Td className="max-w-xs text-xs text-slate-600">{runDetail(run)}</Td>
                        <Td className="text-right">
                          <Button size="sm" variant="ghost" onClick={() => setViewRun(run)}>
                            View
                          </Button>
                        </Td>
                      </Tr>
                    ))}
                  </tbody>
                </TableContainer>
              )}
            </Card>
          </div>
        )
      )}

      <Dialog open={viewRun !== null} title="Data sent" onClose={() => setViewRun(null)}>
        <pre className="max-h-96 overflow-auto rounded-lg bg-ink-950 p-4 text-xs text-slate-100">{JSON.stringify(viewRun?.payload, null, 2)}</pre>
      </Dialog>
      {sender.dialog}
    </>
  )
}
