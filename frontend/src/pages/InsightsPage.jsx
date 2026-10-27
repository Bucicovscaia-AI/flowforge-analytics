import Card from '../components/ui/Card'
import DemoNotice from '../components/ui/DemoNotice'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { sampleInsights } from '../data/sampleData'

const SENT_FIELDS = ['KPI totals', 'Monthly revenue totals', 'Revenue by region and category', 'Data-quality counts']
const NEVER_SENT = ['Individual order rows', 'Customer details', 'The original CSV file', 'API keys']

export default function InsightsPage() {
  return (
    <>
      <PageHeader
        title="AI Insights"
        description="Plain-language observations and recommendations based on the calculated KPIs."
        actions={<StatusBadge variant="prototype">Documented prototype</StatusBadge>}
      />
      <DemoNotice>
        The insights below are example output written for the interface. No AI service is connected in this version.
      </DemoNotice>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {sampleInsights.map((insight) => (
            <Card key={insight.title}>
              <div className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <Icon name="sparkles" />
                </span>
                <div>
                  <h2 className="font-semibold text-slate-900">{insight.title}</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    <span className="font-medium text-slate-900">Evidence: </span>
                    {insight.evidence}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    <span className="font-medium text-slate-900">Recommendation: </span>
                    {insight.recommendation}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <Card title="What would be shared with the AI service">
          <p className="text-sm text-slate-600">Only an aggregated summary would be sent. Raw rows never leave the server.</p>
          <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Sent</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
            {SENT_FIELDS.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <Icon name="check" className="h-4 w-4 text-emerald-600" />
                {item}
              </li>
            ))}
          </ul>
          <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Never sent</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
            {NEVER_SENT.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <Icon name="close" className="h-4 w-4 text-rose-600" />
                {item}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
