import { type FormEvent, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import NoAnalysis from '../components/ui/NoAnalysis'
import PageHeader from '../components/ui/PageHeader'
import SyntheticNotice from '../components/ui/SyntheticNotice'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { createReport, reportDownloadUrl } from '../services/api'
import type { Analysis, AppConfig, Report } from '../types'
import { formatCurrency, formatFileSize, formatNumber, formatPercent } from '../utils/format'

const SECTIONS = [
  'Dataset overview',
  'Data-quality summary and cleaning rules',
  'Key performance indicators with charts',
  'Monthly, category, region and channel breakdowns',
  'Analytical observations and recommendations',
  'Limitations and assumptions',
]

export default function ReportsPage() {
  const { analysis, config } = useAnalysis()

  if (!analysis) {
    return (
      <>
        <PageHeader title="Reports" description="Generate a PDF business report from the current analysis." />
        <NoAnalysis what="a report preview" />
      </>
    )
  }
  // Keyed by analysis so the form starts fresh when the dataset changes.
  return <ReportBuilder key={analysis.id} analysis={analysis} config={config} />
}

function ReportBuilder({ analysis, config }: { analysis: Analysis; config: AppConfig | null }) {
  const { notify } = useToast()
  const titleId = useId()
  const [title, setTitle] = useState(`Sales performance report: ${analysis.dataset.file_name}`)
  const [notifyMake, setNotifyMake] = useState(false)
  const [busy, setBusy] = useState(false)
  const [report, setReport] = useState<Report | null>(null)

  const webhookConfigured = config?.webhook.configured ?? false
  const { summary } = analysis.kpis
  const insightSource = analysis.insights?.source

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await createReport({ analysis_id: analysis.id, title, include_insights: true, notify_make: notifyMake })
      setReport(created)
      notify('success', 'Report generated', `${created.title} (${formatFileSize(created.size_bytes)})`)
      if (created.webhook.status === 'delivered') notify('success', 'Make.com notified', created.webhook.message)
      if (created.webhook.status === 'failed') notify('error', 'Make.com webhook failed', created.webhook.message)
    } catch (error) {
      notify('error', 'Report could not be generated', (error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Reports" description="Generate a PDF business report from the current analysis and download it." />
      {analysis.dataset.synthetic && <SyntheticNotice fileName={analysis.dataset.file_name} />}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Report preview" subtitle={`Source: ${analysis.dataset.file_name}`} className="lg:col-span-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">FlowForge Analytics report</p>
            <h2 className="mt-1 text-xl font-semibold break-words text-slate-900">{title || 'Untitled report'}</h2>
            {analysis.dataset.synthetic && <p className="mt-1 text-xs text-slate-500">Synthetic data: not a real business</p>}
            <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <dt className="text-xs text-slate-500">Total revenue</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatCurrency(summary.total_revenue)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Orders</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatNumber(summary.order_count)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Units sold</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatNumber(summary.units_sold)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Data quality</dt>
                <dd className="text-lg font-semibold text-slate-900">{formatPercent(analysis.quality.quality_score)}</dd>
              </div>
            </dl>
            <h3 className="mt-6 text-sm font-semibold text-slate-900">Contents</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-600">
              {SECTIONS.map((section) => (
                <li key={section}>{section}</li>
              ))}
            </ol>
            <p className="mt-4 text-xs text-slate-500">
              Observations:{' '}
              {insightSource === 'ai'
                ? 'AI-generated insights from the AI Insights page (labelled as AI in the report).'
                : 'rule-based observations (labelled as not AI-generated in the report).'}
            </p>
          </div>
        </Card>

        <div className="space-y-6">
          <Card title="Generate PDF">
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label htmlFor={titleId} className="block text-sm font-medium text-slate-700">
                  Report title
                </label>
                <input
                  id={titleId}
                  value={title}
                  maxLength={120}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <label className={`flex items-start gap-2 text-sm ${webhookConfigured ? 'text-slate-700' : 'text-slate-400'}`}>
                <input
                  type="checkbox"
                  checked={notifyMake}
                  disabled={!webhookConfigured}
                  onChange={(e) => setNotifyMake(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                />
                <span>
                  Send a summary to the Make.com workflow
                  {!webhookConfigured && <span className="block text-xs">Unavailable: no webhook is configured on the server.</span>}
                </span>
              </label>
              <Button type="submit" icon="report" className="w-full" disabled={busy}>
                {busy ? 'Generating PDF…' : 'Generate report'}
              </Button>
            </form>
          </Card>

          {report && (
            <Alert variant="success" title="Report ready">
              <p>{report.title}</p>
              <a
                href={reportDownloadUrl(report.id)}
                className="mt-3 inline-flex items-center rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-600"
                download
              >
                Download PDF ({formatFileSize(report.size_bytes)})
              </a>
              <p className="mt-2 text-xs">
                Saved to <Link to="/history" className="underline">Report History</Link>.
                {report.webhook.status === 'delivered' && ' Make.com workflow notified.'}
                {report.webhook.status === 'failed' && ` Make.com notification failed: ${report.webhook.message}`}
              </p>
            </Alert>
          )}
        </div>
      </div>
    </>
  )
}
