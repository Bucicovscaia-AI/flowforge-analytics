import { useState } from 'react'
import BackendStatus from '../components/ui/BackendStatus'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { testWebhook } from '../services/api'
import { formatNumber } from '../utils/format'

const SECURITY_HABITS = [
  { title: 'Upload synthetic or approved data only', text: 'Real customer data must not be used in this demo workspace.' },
  { title: 'Strip personal details first', text: 'Delete names, emails and phone numbers before exporting the CSV.' },
  { title: 'Keep keys out of the browser', text: 'API keys and the webhook URL live in the server .env file. Never paste them into a form or a dataset.' },
  { title: 'Check a report before sharing it', text: 'Read the data notice and limitations section before sending a report on.' },
]

// Configuration is read-only here on purpose: secrets are set on the server,
// never typed into the browser.
export default function SettingsPage() {
  const { config, refreshConfig } = useAnalysis()
  const { notify } = useToast()
  const [testing, setTesting] = useState(false)

  async function sendTest() {
    setTesting(true)
    try {
      const result = await testWebhook()
      notify('success', 'Test event delivered', `Make.com answered HTTP ${result.status_code}.`)
    } catch (error) {
      notify('error', 'Test event failed', (error as Error).message)
    } finally {
      setTesting(false)
    }
  }

  const rules: [string, string][] = [
    ['Accepted format', 'CSV (.csv), comma, semicolon or tab separated'],
    ['Maximum file size', config ? `${config.max_upload_mb} MB` : '…'],
    ['Maximum rows', config ? formatNumber(config.max_rows) : '…'],
    ['Checks', 'Type, size, encoding, row shape, required columns'],
    ['Data retention', 'Uploaded file is not stored; results and PDFs are kept on the server'],
  ]

  return (
    <>
      <PageHeader
        title="Settings"
        description="Upload limits, integrations and data-handling guidance. Integrations are configured with environment variables on the server."
        actions={
          <Button variant="secondary" icon="refresh" onClick={refreshConfig}>
            Recheck
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Upload rules">
          <dl className="divide-y divide-slate-100 text-sm">
            {rules.map(([term, value]) => (
              <div key={term} className="flex justify-between gap-4 py-2.5">
                <dt className="text-slate-500">{term}</dt>
                <dd className="text-right font-medium text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card title="Integrations">
          <ul className="divide-y divide-slate-100">
            <li className="flex flex-col gap-2 py-3 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-900">FlowForge API</p>
                <p className="text-xs text-slate-500">FastAPI backend that validates and analyses datasets.</p>
              </div>
              <BackendStatus />
            </li>
            <li className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-900">AI insights (Anthropic API)</p>
                <p className="text-xs text-slate-500">
                  {config?.ai.configured ? `Model ${config.ai.model}.` : 'Set AI_API_KEY on the server to enable. Rule-based observations are used until then.'}
                </p>
              </div>
              {config?.ai.configured ? <StatusBadge variant="success">Configured</StatusBadge> : <StatusBadge>Not configured</StatusBadge>}
            </li>
            <li className="flex flex-col gap-2 py-3 last:pb-0">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">Make.com webhook</p>
                  <p className="text-xs text-slate-500">
                    {config?.webhook.configured
                      ? `Sends a KPI summary to ${config.webhook.target_host} when a report is generated${config.webhook.api_key_set ? ' (API key set)' : ''}.`
                      : 'Set MAKE_WEBHOOK_URL on the server to enable. See docs/make-integration.md.'}
                  </p>
                </div>
                {config?.webhook.configured ? <StatusBadge variant="success">Configured</StatusBadge> : <StatusBadge>Not configured</StatusBadge>}
              </div>
              <Button variant="secondary" icon="send" className="self-start" onClick={sendTest} disabled={!config?.webhook.configured || testing}>
                {testing ? 'Sending…' : 'Send test event'}
              </Button>
            </li>
          </ul>
        </Card>
      </div>

      {config && (
        <Card title="Cleaning rules" subtitle="Applied to every dataset, in this order" className="mt-6">
          <ol className="grid gap-2 text-sm sm:grid-cols-2">
            {config.cleaning_rules.map((r) => (
              <li key={r.rule} className="flex gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <span className="font-mono text-xs font-semibold text-indigo-700">{r.rule}</span>
                <span className="text-slate-700">{r.description}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      <Card title="Data and security habits" subtitle="Four habits that keep data safe when using FlowForge" className="mt-6">
        <ul className="grid gap-4 sm:grid-cols-2">
          {SECURITY_HABITS.map((habit) => (
            <li key={habit.title} className="flex gap-3 rounded-lg bg-slate-50 p-4">
              <Icon name="shield" className="h-5 w-5 shrink-0 text-indigo-600" />
              <div>
                <p className="text-sm font-semibold text-slate-900">{habit.title}</p>
                <p className="mt-1 text-sm text-slate-600">{habit.text}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </>
  )
}
