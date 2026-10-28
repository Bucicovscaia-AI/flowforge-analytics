import { CheckCircle2, FileText, History, Send, Workflow } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { DatasetSummary, ReportCreated } from '../api/types'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { InsightModeBadge, ReportDownloads, ReportStatusBadge } from '../components/ReportDownloads'
import { RequireDataset } from '../components/RequireDataset'
import { Alert } from '../components/ui/Alert'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { TextField, Toggle } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { useAutomationSender } from '../hooks/useAutomationSender'
import { formatDateTime, formatNumber } from '../lib/format'

const CONTENTS = [
  'Dataset summary and data quality score',
  'Key business metrics',
  'Trend chart and period comparison',
  'Top groups by category, product and region',
  'Rule-based or AI insights, labelled by source',
  'Quality findings and cleaning steps applied',
  'Limitations and assumptions',
]

function GeneratedReport({ report, onSent }: { report: ReportCreated; onSent: () => void }) {
  const { system } = useApp()
  const [sent, setSent] = useState(report.automation_run?.status === 'delivered')
  const sender = useAutomationSender((run) => {
    if (run.status === 'delivered') setSent(true)
    onSent()
  })

  return (
    <Card>
      <CardHeader
        title={report.title}
        description={`Generated ${formatDateTime(report.created_at)} from ${report.dataset_name}`}
        actions={<ReportStatusBadge report={report} />}
      />
      <CardBody className="space-y-4">
        {report.status === 'partial' && report.error && <Alert tone="warning" title="Some outputs could not be produced">{report.error}</Alert>}
        {report.automation_run && (
          <Alert tone={report.automation_run.status === 'delivered' ? 'success' : 'warning'} title="Automation rule">
            The configured rule sent this report to Make.com: {report.automation_run.message} The Automation page shows whether the scenario
            confirms the email.
          </Alert>
        )}
        <ReportDownloads report={report} />
        {system?.automation_configured && (
          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
            <Button
              variant="secondary"
              icon={sent ? CheckCircle2 : Send}
              loading={sender.sending}
              disabled={sent}
              onClick={() => void sender.send('report.generated', undefined, report.id)}
            >
              {sent ? 'Accepted by Make.com' : 'Send to Make.com'}
            </Button>
            <p className="text-xs text-slate-500">
              Sends the report's KPIs and a temporary link to its PDF to your Make.com scenario, which can email it as an attachment.
            </p>
            {sender.dialog}
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function ReportsContent({ dataset }: { dataset: DatasetSummary }) {
  const { system } = useApp()
  const { notify } = useToast()
  const aiConfigured = Boolean(system?.ai.configured)
  const [title, setTitle] = useState('')
  const [useAi, setUseAi] = useState(aiConfigured)
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState<ReportCreated | null>(null)
  const [version, setVersion] = useState(0)
  const recent = useApi(`reports:${dataset.id}:${version}`, () => api.listReports(dataset.id, 5))

  const generate = async () => {
    setGenerating(true)
    try {
      const report = await api.createReport(dataset.id, title.trim() || undefined, useAi && aiConfigured)
      setGenerated(report)
      setVersion((value) => value + 1)
      notify(report.status === 'completed' ? 'success' : 'error', report.status === 'completed' ? 'Report generated' : 'Report generated with problems', report.title)
    } catch (error) {
      notify('error', 'The report could not be generated', errorMessage(error))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title="New report" description={`From ${dataset.name}, using the working copy with all cleaning applied`} />
          <CardBody className="space-y-4">
            <TextField
              label="Report title (optional)"
              placeholder={`${dataset.name} analysis report`}
              value={title}
              maxLength={150}
              onChange={(event) => setTitle(event.target.value)}
            />
            <Toggle
              label="Include AI insights"
              checked={useAi && aiConfigured}
              onChange={setUseAi}
              disabled={!aiConfigured}
              hint={aiConfigured ? 'Rule-based insights are included either way.' : 'No AI provider is configured, so the report uses rule-based insights.'}
            />
            <Button icon={FileText} loading={generating} onClick={() => void generate()}>
              Generate report
            </Button>
            {system?.automation_configured && (
              <p className="flex items-center gap-1.5 text-xs text-slate-500">
                <Workflow className="size-3.5" aria-hidden />
                Make.com is connected. A report is sent only when you choose to send it, or automatically if the server's report rule is switched
                on (see Automation).
              </p>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="What a report contains" />
          <CardBody>
            <ul className="space-y-1.5 text-sm text-slate-600">
              {CONTENTS.map((item) => (
                <li key={item} className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-500">Download as HTML or PDF to share, CSV for the figures, or JSON for other systems.</p>
          </CardBody>
        </Card>
      </div>

      {generated && <GeneratedReport report={generated} onSent={() => setVersion((value) => value + 1)} />}

      <Card>
        <CardHeader
          title="Recent reports for this dataset"
          actions={
            <LinkButton to="/reports/history" size="sm" icon={History}>
              All reports
            </LinkButton>
          }
        />
        {recent.loading && !recent.data ? (
          <LoadingState />
        ) : recent.error ? (
          <ErrorState error={recent.error} onRetry={recent.reload} />
        ) : !recent.data?.length ? (
          <EmptyState icon={FileText} title="No reports yet" description="Generated reports for this dataset will be listed here." />
        ) : (
          <TableContainer label="Recent reports">
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>Generated</Th>
                <Th numeric>Records</Th>
                <Th>Insights</Th>
                <Th>Status</Th>
                <Th>Files</Th>
              </tr>
            </thead>
            <tbody>
              {recent.data.map((report) => (
                <Tr key={report.id}>
                  <Td className="font-medium text-slate-800">{report.title}</Td>
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
                </Tr>
              ))}
            </tbody>
          </TableContainer>
        )}
      </Card>
    </div>
  )
}

export function ReportsPage() {
  const { selected } = useApp()
  return (
    <>
      <PageHeader
        title="Reports"
        description="Generate a shareable report of the selected dataset with metrics, charts, insights and data quality notes."
        eyebrow={selected && <DatasetEyebrow dataset={selected} />}
      />
      <RequireDataset purpose="generate a report">{(dataset) => <ReportsContent key={dataset.id} dataset={dataset} />}</RequireDataset>
    </>
  )
}
