import { CheckCircle2, Eye, KeyRound, Send, Workflow, XCircle } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { AutomationRun, EventType } from '../api/types'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
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
import { formatDateTime, formatNumber } from '../lib/format'

const SETUP_STEPS = [
  'In Make.com, create a scenario that starts with the Webhooks › Custom webhook module and copy its URL.',
  'On the FlowForge server, set MAKE_WEBHOOK_URL to that URL in the backend .env file. It is never sent to the browser.',
  'Optionally set MAKE_WEBHOOK_SECRET so each request carries an X-FlowForge-Signature HMAC header your scenario can verify.',
  'Restart the backend, then send a test event from this page and use it in Make.com to define the data structure.',
]

function RunStatus({ run }: { run: AutomationRun }) {
  return run.status === 'delivered' ? (
    <Badge tone="success">
      <CheckCircle2 className="size-3" aria-hidden />
      Delivered
    </Badge>
  ) : (
    <Badge tone="danger">
      <XCircle className="size-3" aria-hidden />
      Failed
    </Badge>
  )
}

export function AutomationPage() {
  const { datasets, selected } = useApp()
  const { notify } = useToast()
  const status = useApi('automation-status', () => api.automationStatus())
  const [runsVersion, setRunsVersion] = useState(0)
  const runs = useApi(`automation-runs:${runsVersion}`, () => api.automationRuns(50))
  const [eventType, setEventType] = useState<EventType>('dataset.analysed')
  const [datasetId, setDatasetId] = useState('')
  const [reportId, setReportId] = useState('')
  const reports = useApi(eventType === 'report.generated' ? 'automation-reports' : null, () => api.listReports(undefined, 50))
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [sending, setSending] = useState(false)
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
      notify('error', 'Could not build the payload', errorMessage(error))
    } finally {
      setPreviewing(false)
    }
  }

  const send = async () => {
    setSending(true)
    try {
      const run = await api.triggerAutomation(eventType, ...target())
      if (run.status === 'delivered') notify('success', 'Event delivered to Make.com', run.message)
      else notify('error', 'Delivery failed', run.message)
      setRunsVersion((value) => value + 1)
    } catch (error) {
      notify('error', 'Could not send the event', errorMessage(error))
    } finally {
      setSending(false)
    }
  }

  const configured = Boolean(status.data?.configured)

  return (
    <>
      <PageHeader
        title="Automation"
        description="Send analysis and report events to a Make.com scenario, for example to email a report, post to a team channel or update a spreadsheet. Events are only sent when you press Send or when a rule you configured on the server applies."
      />

      {status.loading && !status.data ? (
        <LoadingState />
      ) : status.error ? (
        <Card>
          <ErrorState error={status.error} onRetry={status.reload} />
        </Card>
      ) : (
        status.data && (
          <div className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
              <Card>
                <CardHeader
                  title="Make.com connection"
                  actions={configured ? <Badge tone="success">Configured</Badge> : <Badge tone="warning">Not configured</Badge>}
                />
                <CardBody className="space-y-3 text-sm text-slate-600">
                  {status.data.configuration_problem && <Alert tone={status.data.configuration_problem.includes('not set') ? 'info' : 'warning'}>{status.data.configuration_problem}</Alert>}
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                    <dt className="text-slate-500">Webhook URL</dt>
                    <dd>{configured ? 'Set on the server (hidden)' : 'Not set'}</dd>
                    <dt className="text-slate-500">Request signing</dt>
                    <dd className="flex items-center gap-1.5">
                      <KeyRound className="size-3.5 text-slate-400" aria-hidden />
                      {status.data.signing_enabled ? 'HMAC-SHA256 signature header' : 'Off'}
                    </dd>
                    <dt className="text-slate-500">Timeout</dt>
                    <dd>{status.data.timeout_seconds} seconds</dd>
                    <dt className="text-slate-500">Report rule</dt>
                    <dd>{status.data.trigger_on_report ? 'Every new report is sent automatically' : 'Off: reports are sent only on request'}</dd>
                  </dl>
                  {!configured && (
                    <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-xs leading-relaxed">
                      {SETUP_STEPS.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                  )}
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Send an event" description="Preview exactly what will be sent before sending it." />
                <CardBody className="space-y-4">
                  <SelectField
                    label="Event"
                    value={eventType}
                    onChange={(event) => {
                      setEventType(event.target.value as EventType)
                      setPreview(null)
                    }}
                    hint={status.data.event_types.find((item) => item.type === eventType)?.description}
                  >
                    {status.data.event_types.map((item) => (
                      <option key={item.type} value={item.type}>
                        {item.type}
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
                      Preview payload
                    </Button>
                    <Button icon={Send} loading={sending} disabled={!configured || missingTarget} onClick={() => void send()}>
                      Send to Make.com
                    </Button>
                  </div>
                  {!configured && <p className="text-xs text-slate-500">Sending is disabled until a webhook URL is configured on the server. Previews still work.</p>}
                  {preview && (
                    <pre className="max-h-80 overflow-auto rounded-lg bg-ink-950 p-4 text-xs leading-relaxed text-slate-100" aria-label="Payload preview">
                      {JSON.stringify(preview, null, 2)}
                    </pre>
                  )}
                </CardBody>
              </Card>
            </div>

            <Card>
              <CardHeader title="Delivery history" description="Every attempt to send an event, including failures" />
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
                      <Th numeric>HTTP</Th>
                      <Th numeric>Time</Th>
                      <Th>Message</Th>
                      <Th className="text-right">Payload</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data.map((run) => (
                      <Tr key={run.id}>
                        <Td className="whitespace-nowrap">{formatDateTime(run.created_at)}</Td>
                        <Td className="font-mono text-xs">{run.event_type}</Td>
                        <Td>{run.trigger === 'rule' ? 'Rule' : 'Manual'}</Td>
                        <Td>
                          <RunStatus run={run} />
                        </Td>
                        <Td numeric>{run.http_status ?? '–'}</Td>
                        <Td numeric>{run.duration_ms !== null ? `${formatNumber(run.duration_ms)} ms` : '–'}</Td>
                        <Td className="max-w-xs text-xs text-slate-600">{run.message}</Td>
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

      <Dialog open={viewRun !== null} title="Payload sent" onClose={() => setViewRun(null)}>
        <pre className="max-h-96 overflow-auto rounded-lg bg-ink-950 p-4 text-xs text-slate-100">{JSON.stringify(viewRun?.payload, null, 2)}</pre>
      </Dialog>
    </>
  )
}
