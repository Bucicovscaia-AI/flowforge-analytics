import { ArrowRight, Eye, RotateCcw, ShieldCheck, Wand2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { CleaningResult, DatasetDetail, DatasetSummary, OperationDescription, QualityFinding, QualityReport, SuggestedOperation } from '../api/types'
import { DatasetEyebrow } from '../components/DatasetHeading'
import { RequireDataset } from '../components/RequireDataset'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/Dialog'
import { SelectField, TextField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { qualityTone, SeverityBadge } from '../components/ui/QualityBadge'
import type { BadgeTone } from '../components/ui/Badge'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { cn } from '../lib/cn'
import { formatDateTime, formatNumber, formatPercent } from '../lib/format'

const SCORE_COLOURS: Record<BadgeTone, string> = {
  success: 'text-emerald-600',
  brand: 'text-brand-600',
  warning: 'text-amber-600',
  danger: 'text-red-600',
  info: 'text-sky-600',
  violet: 'text-violet-600',
  neutral: 'text-slate-500',
}

function ScoreSummary({ report }: { report: QualityReport }) {
  const tone = qualityTone(report.score)
  return (
    <Card>
      <CardBody className="grid gap-6 md:grid-cols-[auto_1fr]">
        <div className="flex items-center gap-4">
          <div className="relative size-24">
            <svg viewBox="0 0 36 36" className="size-24 -rotate-90" aria-hidden>
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e2e8f0" strokeWidth="3" />
              <circle
                cx="18"
                cy="18"
                r="15.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={`${(report.score / 100) * 97.4} 97.4`}
                className={SCORE_COLOURS[tone]}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="tabular text-xl font-semibold text-slate-900">{report.score.toFixed(1)}</span>
              <span className="text-[10px] uppercase tracking-wide text-slate-500">of 100</span>
            </div>
          </div>
          <div>
            <p className="text-sm text-slate-500">Quality score</p>
            <p className="text-xl font-semibold text-slate-900">{report.grade}</p>
          </div>
        </div>
        <div>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {[
              ['Errors', report.counts.error],
              ['Warnings', report.counts.warning],
              ['Information', report.counts.info],
              ['Missing cells', report.missing_cells],
              ['Duplicate rows', report.duplicate_rows],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="tabular text-lg font-semibold text-slate-900">{formatNumber(value as number)}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">{report.method} The score summarises known problems; it does not prove the data is correct.</p>
        </div>
      </CardBody>
    </Card>
  )
}

function FindingItem({ finding, onFix }: { finding: QualityFinding; onFix: (suggestion: SuggestedOperation) => void }) {
  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <h3 className="text-sm font-semibold text-slate-900">{finding.title}</h3>
          </div>
          <p className="mt-1 text-sm text-slate-700">{finding.description}</p>
          <p className="mt-1 text-sm text-slate-500">
            <span className="font-medium text-slate-600">Effect on analysis: </span>
            {finding.impact}
          </p>
          {finding.examples.length > 0 && (
            <p className="mt-1.5 text-xs text-slate-500">
              Examples:{' '}
              {finding.examples.map((example) => (
                <code key={example} className="mr-1 rounded bg-slate-100 px-1 py-0.5 text-slate-700">
                  {example}
                </code>
              ))}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="tabular text-sm text-slate-600">
            {formatNumber(finding.affected_rows)} rows ({formatPercent(finding.affected_percent)})
          </span>
          {finding.suggestion && (
            <Button size="sm" variant="secondary" icon={Wand2} onClick={() => onFix(finding.suggestion as SuggestedOperation)}>
              {finding.suggestion.label}
            </Button>
          )}
        </div>
      </div>
    </li>
  )
}

function operationDefaults(operations: OperationDescription[], key: string): Record<string, string> {
  const definition = operations.find((item) => item.key === key)
  return Object.fromEntries((definition?.params ?? []).filter((param) => param.default).map((param) => [param.name, param.default as string]))
}

interface CleaningPanelProps {
  detail: DatasetDetail
  operations: OperationDescription[]
  preset: { suggestion: SuggestedOperation; nonce: number } | null
  onApplied: () => void
}

function CleaningPanel({ detail, operations, preset, onApplied }: CleaningPanelProps) {
  const { notify } = useToast()
  const defaultsFor = (key: string) => operationDefaults(operations, key)
  const [operationKey, setOperationKey] = useState(preset?.suggestion.operation ?? operations[0]?.key ?? '')
  const [params, setParams] = useState<Record<string, string>>(() =>
    preset ? { ...defaultsFor(preset.suggestion.operation), ...preset.suggestion.params } : defaultsFor(operations[0]?.key ?? ''),
  )
  const [preview, setPreview] = useState<CleaningResult | null>(null)
  const [busy, setBusy] = useState<'preview' | 'apply' | null>(null)
  const [error, setError] = useState<unknown>()
  const [confirming, setConfirming] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const operation = operations.find((item) => item.key === operationKey)

  // The panel is remounted with a new key when a finding's suggested fix is chosen, so only scrolling is needed here.
  useEffect(() => {
    if (preset) panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [preset])

  const changeOperation = (key: string) => {
    setOperationKey(key)
    setParams(defaultsFor(key))
    setPreview(null)
    setError(undefined)
  }

  const missingRequired = operation?.params.some((param) => {
    if (param.name === 'value') return params.strategy === 'constant' && !params.value?.trim()
    return param.required && !params[param.name]
  })

  const runPreview = async () => {
    setBusy('preview')
    setError(undefined)
    try {
      setPreview(await api.previewCleaning(detail.id, operationKey, params))
    } catch (reason) {
      setError(reason)
      setPreview(null)
    } finally {
      setBusy(null)
    }
  }

  const apply = async () => {
    setConfirming(false)
    setBusy('apply')
    setError(undefined)
    try {
      const result = await api.applyCleaning(detail.id, operationKey, params)
      if (result.applied) {
        notify('success', 'Cleaning applied', result.summary)
        onApplied()
      } else {
        notify('info', 'No changes needed', result.message ?? result.summary)
      }
      setPreview(null)
    } catch (reason) {
      setError(reason)
      notify('error', 'Cleaning failed', errorMessage(reason))
    } finally {
      setBusy(null)
    }
  }

  const removesRows = preview ? preview.rows_removed > 0 || preview.columns_after < preview.columns_before : false

  return (
    <Card>
      <div ref={panelRef} className="scroll-mt-20" />
      <CardHeader title="Clean the data" description="Preview an operation, then apply it to the working copy. The original import is always kept." />
      <CardBody className="space-y-4">
        <SelectField label="Operation" value={operationKey} onChange={(event) => changeOperation(event.target.value)}>
          {operations.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </SelectField>
        {operation && (
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            <p className="text-slate-700">{operation.description}</p>
            <p className="mt-1 text-slate-500">
              <span className="font-medium text-slate-600">Consequence: </span>
              {operation.consequence}
            </p>
          </div>
        )}
        {operation?.params.map((param) => {
          if (param.name === 'value' && params.strategy !== 'constant') return null
          const value = params[param.name] ?? ''
          const update = (next: string) => {
            setParams((current) => ({ ...current, [param.name]: next }))
            setPreview(null)
          }
          if (param.kind === 'column') {
            return (
              <SelectField key={param.name} label={param.label} value={value} onChange={(event) => update(event.target.value)} hint={param.help || undefined}>
                <option value="">Choose a column…</option>
                {detail.columns.map((column) => (
                  <option key={column.name} value={column.name}>
                    {column.name} ({column.inferred_type})
                  </option>
                ))}
              </SelectField>
            )
          }
          if (param.kind === 'choice') {
            return (
              <SelectField key={param.name} label={param.label} value={value} onChange={(event) => update(event.target.value)} hint={param.help || undefined}>
                {param.choices.map((choice) => (
                  <option key={choice} value={choice}>
                    {choice}
                  </option>
                ))}
              </SelectField>
            )
          }
          return <TextField key={param.name} label={param.label} value={value} onChange={(event) => update(event.target.value)} hint={param.help || undefined} />
        })}

        {error !== undefined && <Alert tone="danger">{errorMessage(error)}</Alert>}

        {preview && (
          <div role="status" className={cn('rounded-lg border p-4 text-sm', preview.changed ? 'border-brand-200 bg-brand-50/60' : 'border-slate-200 bg-slate-50')}>
            <p className="font-semibold text-slate-900">Preview: {preview.changed ? preview.summary : 'This operation would not change anything.'}</p>
            <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <dt className="text-xs text-slate-500">Rows</dt>
                <dd className="tabular font-medium">
                  {formatNumber(preview.rows_before)} <ArrowRight className="inline size-3" aria-label="to" /> {formatNumber(preview.rows_after)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Columns</dt>
                <dd className="tabular font-medium">
                  {preview.columns_before} <ArrowRight className="inline size-3" aria-label="to" /> {preview.columns_after}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Cells changed</dt>
                <dd className="tabular font-medium">{formatNumber(preview.cells_changed)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Quality score</dt>
                <dd className="tabular font-medium">
                  {preview.quality_before?.toFixed(1)} <ArrowRight className="inline size-3" aria-label="to" /> {preview.quality_after?.toFixed(1)}
                </dd>
              </div>
            </dl>
            {preview.warnings.map((warning) => (
              <p key={warning} className="mt-2 text-amber-800">
                {warning}
              </p>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={Eye} onClick={() => void runPreview()} loading={busy === 'preview'} disabled={!operation || missingRequired || busy !== null}>
            Preview
          </Button>
          <Button
            icon={Wand2}
            onClick={() => (removesRows ? setConfirming(true) : void apply())}
            loading={busy === 'apply'}
            disabled={!preview || !preview.changed || busy !== null}
          >
            Apply to working copy
          </Button>
        </div>
        {!preview && <p className="text-xs text-slate-500">Preview the operation first; applying is enabled once a preview shows a change.</p>}
      </CardBody>
      <ConfirmDialog
        open={confirming}
        title="Remove data from the working copy?"
        confirmLabel="Apply and remove"
        onCancel={() => setConfirming(false)}
        onConfirm={() => void apply()}
      >
        <p>{preview?.summary}</p>
        <p className="mt-2">Removed rows or columns are excluded from all analysis and reports. You can restore them later with “Reset to original”.</p>
      </ConfirmDialog>
    </Card>
  )
}

function CleaningHistory({ detail, onReset }: { detail: DatasetDetail; onReset: () => void }) {
  const { notify } = useToast()
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const reset = async () => {
    setBusy(true)
    try {
      await api.resetCleaning(detail.id)
      notify('success', 'Original data restored', `${formatNumber(detail.original_row_count)} rows from the original import are back in the working copy.`)
      setConfirming(false)
      onReset()
    } catch (error) {
      notify('error', 'Reset failed', errorMessage(error))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card>
      <CardHeader
        title="Cleaning history"
        description="Operations applied to the working copy, in order"
        actions={
          <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => setConfirming(true)} disabled={detail.operations.length === 0}>
            Reset to original
          </Button>
        }
      />
      {detail.operations.length === 0 ? (
        <CardBody>
          <p className="text-sm text-slate-500">No cleaning has been applied. The working copy matches the original import.</p>
        </CardBody>
      ) : (
        <TableContainer label="Cleaning history">
          <thead>
            <tr>
              <Th>When</Th>
              <Th>Change</Th>
              <Th numeric>Rows</Th>
              <Th numeric>Quality</Th>
            </tr>
          </thead>
          <tbody>
            {detail.operations.map((operation) => (
              <Tr key={operation.id}>
                <Td className="whitespace-nowrap text-xs">{formatDateTime(operation.applied_at)}</Td>
                <Td>{operation.summary}</Td>
                <Td numeric className="whitespace-nowrap">
                  {formatNumber(operation.rows_before)} → {formatNumber(operation.rows_after)}
                </Td>
                <Td numeric className="whitespace-nowrap">
                  {operation.quality_before?.toFixed(1)} → {operation.quality_after?.toFixed(1)}
                </Td>
              </Tr>
            ))}
          </tbody>
        </TableContainer>
      )}
      <ConfirmDialog
        open={confirming}
        title="Reset to the original import?"
        confirmLabel="Reset data"
        tone="primary"
        busy={busy}
        onCancel={() => setConfirming(false)}
        onConfirm={() => void reset()}
      >
        All cleaning operations will be undone and the working copy will match the file as originally imported.
      </ConfirmDialog>
    </Card>
  )
}

function QualityWorkspace({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion, notifyDataChanged } = useApp()
  const quality = useApi(`quality:${dataset.id}:${dataVersion}`, () => api.quality(dataset.id))
  const detail = useApi(`detail:${dataset.id}:${dataVersion}`, () => api.getDataset(dataset.id))
  const operations = useApi('operations', () => api.cleaningOperations())
  const [preset, setPreset] = useState<{ suggestion: SuggestedOperation; nonce: number } | null>(null)
  const [severity, setSeverity] = useState<'all' | 'error' | 'warning' | 'info'>('all')

  const findings = useMemo(
    () => (quality.data?.findings ?? []).filter((finding) => severity === 'all' || finding.severity === severity),
    [quality.data, severity],
  )

  return (
    <>
      <PageHeader
        title="Data Quality"
        description="Automated checks for missing values, duplicates, invalid numbers and dates, inconsistent categories and suspicious values, with operations to fix them."
        eyebrow={<DatasetEyebrow dataset={dataset} />}
      />
      {quality.loading && !quality.data ? (
        <LoadingState label="Running quality checks…" />
      ) : quality.error ? (
        <Card>
          <ErrorState error={quality.error} onRetry={quality.reload} />
        </Card>
      ) : quality.data ? (
        <div className="space-y-6">
          <ScoreSummary report={quality.data} />
          <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <Card className="self-start">
              <CardHeader
                title="Findings"
                description="Sorted by severity, then by the number of rows affected"
                actions={
                  <SelectField label="Show" className="w-40 [&_label]:sr-only" value={severity} onChange={(event) => setSeverity(event.target.value as typeof severity)}>
                    <option value="all">All findings</option>
                    <option value="error">Errors</option>
                    <option value="warning">Warnings</option>
                    <option value="info">Information</option>
                  </SelectField>
                }
              />
              {quality.data.findings.length === 0 ? (
                <EmptyState icon={ShieldCheck} title="No problems found" description="None of the configured checks found an issue in this dataset." />
              ) : findings.length === 0 ? (
                <CardBody>
                  <p className="text-sm text-slate-500">No findings at this severity.</p>
                </CardBody>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {findings.map((finding) => (
                    <FindingItem key={finding.id} finding={finding} onFix={(suggestion) => setPreset({ suggestion, nonce: Date.now() })} />
                  ))}
                </ul>
              )}
            </Card>
            <div className="space-y-6">
              {detail.data && operations.data ? (
                <CleaningPanel key={preset?.nonce ?? 0} detail={detail.data} operations={operations.data} preset={preset} onApplied={notifyDataChanged} />
              ) : detail.error || operations.error ? (
                <Card>
                  <ErrorState error={detail.error ?? operations.error} onRetry={() => (detail.reload(), operations.reload())} />
                </Card>
              ) : (
                <LoadingState />
              )}
              {detail.data && <CleaningHistory detail={detail.data} onReset={notifyDataChanged} />}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

export function QualityPage() {
  return <RequireDataset purpose="check its quality">{(dataset) => <QualityWorkspace dataset={dataset} />}</RequireDataset>
}
