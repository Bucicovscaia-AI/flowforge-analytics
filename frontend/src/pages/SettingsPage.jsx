import BackendStatus from '../components/ui/BackendStatus'
import Card from '../components/ui/Card'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { MAX_FILE_SIZE_MB } from '../utils/validateFile'

const INTEGRATIONS = [
  { name: 'FlowForge API', description: 'Python FastAPI backend that validates and analyses datasets.', status: <BackendStatus /> },
  { name: 'AI insights service', description: 'External AI API for written observations. Key read from the server environment.', status: <StatusBadge variant="prototype">Documented prototype</StatusBadge> },
  { name: 'Make.com webhook', description: 'Sends a KPI summary to an automation scenario after each report.', status: <StatusBadge variant="prototype">Documented prototype</StatusBadge> },
]

const SECURITY_HABITS = [
  { title: 'Upload synthetic or approved data only', text: 'Real customer data must not be used in this demo workspace.' },
  { title: 'Strip personal details first', text: 'Delete names, emails and phone numbers before exporting the CSV.' },
  { title: 'Keep keys out of the browser', text: 'API keys live in the server .env file. Never paste them into a form or a dataset.' },
  { title: 'Check a report before sharing it', text: 'Read the data notice and limitations section before sending a report on.' },
]

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Upload limits, integrations and data-handling guidance." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Upload rules">
          <dl className="divide-y divide-slate-100 text-sm">
            {[
              ['Accepted format', 'CSV (.csv)'],
              ['Maximum file size', `${MAX_FILE_SIZE_MB} MB`],
              ['Checks', 'File type, size, required columns, data types'],
              ['Data retention', 'Not stored after the session (planned)'],
            ].map(([term, value]) => (
              <div key={term} className="flex justify-between gap-4 py-2.5">
                <dt className="text-slate-500">{term}</dt>
                <dd className="text-right font-medium text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card title="Integrations">
          <ul className="divide-y divide-slate-100">
            {INTEGRATIONS.map((item) => (
              <li key={item.name} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">{item.name}</p>
                  <p className="text-xs text-slate-500">{item.description}</p>
                </div>
                {item.status}
              </li>
            ))}
          </ul>
        </Card>
      </div>

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
