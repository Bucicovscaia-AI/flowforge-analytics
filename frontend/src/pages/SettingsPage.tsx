import { Bot, Database, HardDrive, ShieldCheck, Workflow } from 'lucide-react'
import type { ReactNode } from 'react'

import { BEFORE_YOU_UPLOAD_ID } from '../components/BeforeYouUploadCard'
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
      <PageHeader title="Settings" />
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
              {system.ai.configured && (
                <dl className="mb-3 text-sm">
                  <Row label="Provider">{system.ai.provider}</Row>
                  <Row label="Model">{system.ai.model}</Row>
                </dl>
              )}
              <p className="flex gap-2 text-xs text-slate-500">
                <Bot className="size-4 shrink-0" aria-hidden />
                {system.ai.configured
                  ? system.ai.data_policy
                  : 'AI insights are not enabled for this workspace. Rule-based insights are always available.'}
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
                {system.automation_configured
                  ? 'Send analysis results and reports to your Make.com scenarios.'
                  : 'Make.com automation is not enabled for this workspace.'}
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
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="About" />
            <CardBody>
              <dl className="text-sm">
                <Row label="Application">{system.name}</Row>
                <Row label="Version">{system.version}</Row>
              </dl>
            </CardBody>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader title="Data safety" />
            <CardBody className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
              <p className="flex gap-2">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
                Three habits that keep your data and your reports safe: use demo or anonymised data, keep the webhook address private, and check before you forward.
              </p>
              <LinkButton to={`/upload#${BEFORE_YOU_UPLOAD_ID}`} size="sm">
                Read before you upload
              </LinkButton>
            </CardBody>
          </Card>
        </div>
      )}
    </>
  )
}
