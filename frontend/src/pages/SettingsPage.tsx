import { BookOpen, Bot, Database, Gauge, HardDrive, Workflow } from 'lucide-react'
import type { ReactNode } from 'react'

import { API_BASE } from '../api/client'
import { LinkButton } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { SelectField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, LoadingState } from '../components/ui/States'
import { useApp } from '../context/AppContext'
import type { CurrencySymbol } from '../lib/format'
import { formatNumber } from '../lib/format'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-2 border-b border-slate-100 py-2 last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{children}</dd>
    </div>
  )
}

export function SettingsPage() {
  const { system, systemError, currency, setCurrency, datasets } = useApp()

  return (
    <>
      <PageHeader
        title="Settings"
        description="How this FlowForge server is configured. Integrations and limits are set with environment variables on the backend, so secrets never reach the browser."
      />
      {systemError !== undefined && !system ? (
        <Card>
          <ErrorState title="Server settings could not be loaded" error={systemError} />
        </Card>
      ) : !system ? (
        <LoadingState />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader title="Display" description="Saved in this browser only" />
            <CardBody>
              <SelectField
                label="Currency symbol for revenue"
                value={currency}
                onChange={(event) => setCurrency(event.target.value as CurrencySymbol)}
                hint="FlowForge does not convert currencies; this only changes how values are labelled."
              >
                <option value="">None</option>
                <option value="£">£ Pound sterling</option>
                <option value="€">€ Euro</option>
                <option value="$">$ Dollar</option>
              </SelectField>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="AI insights"
              actions={system.ai.configured ? <Badge tone="success">Configured</Badge> : <Badge tone="neutral">Rule-based only</Badge>}
            />
            <CardBody>
              <dl className="text-sm">
                <Row label="Provider">{system.ai.provider ?? 'None'}</Row>
                <Row label="Model">{system.ai.model ?? '–'}</Row>
              </dl>
              <p className="mt-3 flex gap-2 text-xs text-slate-500">
                <Bot className="size-4 shrink-0" aria-hidden />
                {system.ai.configured
                  ? system.ai.data_policy
                  : 'Set AI_API_KEY (and optionally AI_MODEL) in the backend .env file and restart the server to enable AI insights. Rule-based insights work without it.'}
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Make.com automation"
              actions={system.automation_configured ? <Badge tone="success">Configured</Badge> : <Badge tone="neutral">Not configured</Badge>}
            />
            <CardBody className="space-y-3 text-sm text-slate-600">
              <p className="flex gap-2">
                <Workflow className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
                The webhook URL and signing secret are read from MAKE_WEBHOOK_URL and MAKE_WEBHOOK_SECRET on the server.
              </p>
              <LinkButton to="/automation" size="sm">
                Open Automation
              </LinkButton>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Storage" actions={<Badge tone={system.storage.persistent ? 'success' : 'warning'}>{system.storage.persistent ? 'Persistent' : 'Temporary'}</Badge>} />
            <CardBody>
              <dl className="text-sm">
                <Row label="Engine">{system.storage.engine}</Row>
                <Row label="Datasets stored">{formatNumber(datasets.length)}</Row>
              </dl>
              <p className="mt-3 flex gap-2 text-xs text-slate-500">
                <HardDrive className="size-4 shrink-0" aria-hidden />
                {system.storage.description}
              </p>
              <div className="mt-3">
                <LinkButton to="/datasets" size="sm" icon={Database}>
                  Manage datasets
                </LinkButton>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Upload limits" />
            <CardBody>
              <dl className="text-sm">
                <Row label="Maximum file size">{system.limits.max_upload_mb} MB</Row>
                <Row label="Maximum rows">{formatNumber(system.limits.max_rows)}</Row>
                <Row label="Maximum columns">{formatNumber(system.limits.max_columns)}</Row>
                <Row label="Accepted files">{system.limits.accepted_extensions.join(', ')}</Row>
              </dl>
              <p className="mt-3 flex gap-2 text-xs text-slate-500">
                <Gauge className="size-4 shrink-0" aria-hidden />
                Change with MAX_UPLOAD_MB, MAX_ROWS and MAX_COLUMNS on the server.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="About" />
            <CardBody>
              <dl className="text-sm">
                <Row label="Application">{system.name}</Row>
                <Row label="Version">{system.version}</Row>
              </dl>
              <a
                href={`${API_BASE}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline"
              >
                <BookOpen className="size-4" aria-hidden />
                API documentation
              </a>
            </CardBody>
          </Card>
        </div>
      )}
    </>
  )
}
