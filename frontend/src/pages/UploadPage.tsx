import { CheckCircle2, FileSpreadsheet, FlaskConical, ShieldCheck, BarChart3, UploadCloud, X } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'

import { api, errorMessage, uploadDataset } from '../api/client'
import type { DatasetSummary } from '../api/types'
import { ColumnProfileTable, DataPreviewTable } from '../components/DatasetTables'
import { Alert } from '../components/ui/Alert'
import { Badge, SampleBadge } from '../components/ui/Badge'
import { Button, LinkButton } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { TextField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { QualityBadge } from '../components/ui/QualityBadge'
import { ErrorState, LoadingState } from '../components/ui/States'
import { StatCard } from '../components/ui/StatCard'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { useLoadSample } from '../hooks/useLoadSample'
import { cn } from '../lib/cn'
import { formatBytes, formatNumber } from '../lib/format'
import { validateFileLocally } from '../lib/validateFile'

const DEFAULT_LIMIT_MB = 10

function ImportResult({ dataset }: { dataset: DatasetSummary }) {
  const detail = useApi(`detail:${dataset.id}`, () => api.getDataset(dataset.id))
  return (
    <div className="space-y-6">
      <Alert tone="success" title="Import complete">
        {dataset.name} was validated and stored. It is now the selected dataset.
      </Alert>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Records" value={formatNumber(dataset.row_count)} />
        <StatCard label="Columns" value={formatNumber(dataset.column_count)} />
        <StatCard label="Quality score" value={dataset.quality_score?.toFixed(1) ?? '–'} hint={dataset.quality_grade} />
        <StatCard label="File" value={formatBytes(dataset.size_bytes)} hint={`${dataset.encoding?.toUpperCase()} · delimiter "${dataset.delimiter === '\t' ? 'tab' : dataset.delimiter}"`} />
      </div>
      {dataset.warnings.length > 0 && (
        <Alert tone="warning" title="Adjustments made while reading the file">
          <ul className="list-disc pl-4">
            {dataset.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Alert>
      )}
      <Card>
        <CardHeader
          title="Columns and inferred types"
          description="Types are inferred from the values. Numeric and date columns are used for calculations."
          actions={
            <>
              <LinkButton to="/quality" icon={ShieldCheck}>
                Check data quality
              </LinkButton>
              <LinkButton to="/analysis" variant="primary" icon={BarChart3}>
                Analyse
              </LinkButton>
            </>
          }
        />
        {detail.loading ? <LoadingState /> : detail.error ? <ErrorState error={detail.error} onRetry={detail.reload} /> : detail.data && <ColumnProfileTable columns={detail.data.columns} />}
      </Card>
      <Card>
        <CardHeader title="Preview" description="The first rows exactly as stored" />
        <DataPreviewTable datasetId={dataset.id} pageSize={10} />
      </Card>
    </div>
  )
}

export function UploadPage() {
  const { system, refreshDatasets, selectDataset, notifyDataChanged } = useApp()
  const { notify } = useToast()
  const { loadSample, loading: sampleLoading } = useLoadSample()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [dragging, setDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<unknown>()
  const [progress, setProgress] = useState<number | null>(null)
  const [result, setResult] = useState<DatasetSummary | null>(null)
  const maxMb = system?.limits.max_upload_mb ?? DEFAULT_LIMIT_MB

  const choose = (candidate: File | undefined) => {
    if (!candidate) return
    setResult(null)
    setUploadError(undefined)
    const problem = validateFileLocally(candidate, maxMb)
    setLocalError(problem)
    setFile(problem ? null : candidate)
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    choose(event.dataTransfer.files?.[0])
  }

  const submit = async () => {
    if (!file) return
    setProgress(0)
    setUploadError(undefined)
    try {
      const dataset = await uploadDataset(file, name.trim() || undefined, setProgress)
      await refreshDatasets()
      selectDataset(dataset.id)
      notifyDataChanged()
      setResult(dataset)
      setFile(null)
      setName('')
      notify('success', 'Dataset imported', `${formatNumber(dataset.row_count)} rows and ${dataset.column_count} columns are ready.`)
    } catch (error) {
      setUploadError(error)
      notify('error', 'Import failed', errorMessage(error))
    } finally {
      setProgress(null)
    }
  }

  const sample = async () => {
    const dataset = await loadSample()
    if (dataset) setResult(dataset)
  }

  const uploading = progress !== null

  return (
    <>
      <PageHeader
        title="Data Upload"
        description="Import a CSV file. FlowForge validates it on the server, infers column types and stores a working copy you can clean without losing the original."
      />
      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader title="Upload a CSV file" description="Drag a file onto the area below or browse for one." />
          <CardBody className="space-y-4">
            <div
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cn(
                'flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
                dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50/60',
              )}
            >
              <UploadCloud className="size-10 text-brand-600" aria-hidden />
              <p className="mt-3 text-sm font-medium text-slate-800">Drop your CSV file here</p>
              <p className="text-xs text-slate-500">or</p>
              <Button variant="secondary" className="mt-2" onClick={() => inputRef.current?.click()} disabled={uploading}>
                Choose file
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.txt,text/csv"
                className="sr-only"
                aria-label="CSV file"
                onChange={(event) => {
                  choose(event.target.files?.[0])
                  event.target.value = ''
                }}
              />
            </div>

            {localError && <Alert tone="danger" title="This file cannot be uploaded">{localError}</Alert>}

            {file && (
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-3">
                <FileSpreadsheet className="size-8 shrink-0 text-emerald-600" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">{file.name}</p>
                  <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
                </div>
                {!uploading && (
                  <button type="button" className="rounded p-1 text-slate-400 hover:text-slate-700" onClick={() => setFile(null)} aria-label="Remove selected file">
                    <X className="size-4" />
                  </button>
                )}
              </div>
            )}

            {file && (
              <TextField
                label="Dataset name (optional)"
                placeholder={file.name.replace(/\.[^.]+$/, '')}
                value={name}
                maxLength={120}
                onChange={(event) => setName(event.target.value)}
                hint="Defaults to the file name."
              />
            )}

            {uploading && (
              <div role="status" aria-live="polite">
                <div className="mb-1 flex justify-between text-xs text-slate-600">
                  <span>{progress < 1 ? 'Uploading…' : 'Validating and profiling on the server…'}</span>
                  <span>{Math.round(progress * 100)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                  <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${Math.max(4, progress * 100)}%` }} />
                </div>
              </div>
            )}

            {uploadError !== undefined && <Alert tone="danger" title="The server rejected this file">{errorMessage(uploadError)}</Alert>}

            <div className="flex flex-wrap gap-2">
              <Button icon={UploadCloud} onClick={() => void submit()} disabled={!file} loading={uploading}>
                Upload and validate
              </Button>
            </div>
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Supported files" />
            <CardBody>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />CSV files with a header row (.csv)</li>
                <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />Up to {maxMb} MB, {formatNumber(system?.limits.max_rows ?? 500000)} rows and {system?.limits.max_columns ?? 200} columns</li>
                <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />UTF-8 or Windows-1252 text</li>
                <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />Comma, semicolon, tab or pipe delimiters (detected automatically)</li>
              </ul>
              <p className="mt-4 text-xs leading-relaxed text-slate-500">
                Empty cells and values such as N/A or null are treated as missing. File contents are only parsed as text and never executed.
              </p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="No file to hand?" />
            <CardBody>
              <p className="text-sm text-slate-600">
                Load 1,200 synthetic retail orders. The sample goes through the same validation and analysis as an uploaded file, and includes a few deliberate quality problems to fix.
              </p>
              <div className="mt-3 flex items-center gap-2">
                <Button variant="secondary" icon={FlaskConical} loading={sampleLoading} onClick={() => void sample()}>
                  Load sample dataset
                </Button>
                <SampleBadge />
              </div>
            </CardBody>
          </Card>
          <Alert tone="warning" title="Protect personal data">
            Avoid uploading files with customer names, contact details or other personal information unless you are permitted to process them. Data is stored on this server until you delete it.
          </Alert>
        </div>
      </div>
      {result && (
        <section className="mt-8" aria-label="Import result">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-900">{result.name}</h2>
            {result.is_sample && <SampleBadge />}
            <QualityBadge score={result.quality_score} grade={result.quality_grade} />
            <Badge>{result.status}</Badge>
          </div>
          <ImportResult dataset={result} />
        </section>
      )}
    </>
  )
}
