import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import PipelineSteps, { type PipelineStep } from '../components/ui/PipelineSteps'
import { useAnalysis } from '../context/analysisContext'
import { useToast } from '../context/toastContext'
import { ApiError, analyseSample, getSamples, uploadDataset } from '../services/api'
import type { Analysis, SampleDataset } from '../types'
import { formatFileSize, formatNumber, formatPercent } from '../utils/format'
import { MAX_FILE_SIZE_MB, validateCsvFile } from '../utils/validateFile'

type Phase = 'idle' | 'ready' | 'working' | 'done' | 'failed'

function pipelineFor(phase: Phase): PipelineStep[] {
  const state = (index: number): PipelineStep['state'] => {
    if (phase === 'done') return 'done'
    if (phase === 'failed') return index === 1 ? 'error' : index === 0 ? 'done' : 'pending'
    if (phase === 'working') return index === 0 ? 'done' : index === 1 ? 'current' : 'pending'
    if (phase === 'ready') return index === 0 ? 'done' : index === 1 ? 'current' : 'pending'
    return index === 0 ? 'current' : 'pending'
  }
  return [
    { label: 'Upload', description: 'Choose a CSV file', state: state(0) },
    { label: 'Validate', description: 'Type, size, columns', state: state(1) },
    { label: 'Clean', description: 'Duplicates, blanks, bad values', state: state(2) },
    { label: 'Analyse', description: 'Calculate KPIs', state: state(3) },
    { label: 'Report', description: 'Generate a PDF', state: phase === 'done' ? 'current' : 'pending' },
  ]
}

function ResultSummary({ analysis }: { analysis: Analysis }) {
  const q = analysis.quality
  return (
    <Alert variant="success" title={`${analysis.dataset.file_name} analysed`}>
      <p>
        {formatNumber(q.rows_received)} rows received, {formatNumber(q.duplicate_rows)} duplicates and {formatNumber(q.missing_cells)} missing
        cells found. {formatNumber(q.rows_removed)} rows removed by the cleaning rules, leaving {formatNumber(q.rows_analysed)} (
        {formatPercent(q.quality_score)}).
      </p>
      <div className="mt-3 flex flex-wrap gap-3">
        <Link to="/" className="font-semibold underline">View dashboard</Link>
        <Link to="/analysis" className="font-semibold underline">Inspect data quality</Link>
        <Link to="/reports" className="font-semibold underline">Generate report</Link>
      </div>
    </Alert>
  )
}

export default function UploadPage() {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const { config, setAnalysis } = useAnalysis()
  const { notify } = useToast()
  const [file, setFile] = useState<File | null>(null)
  const [synthetic, setSynthetic] = useState(true)
  const [errors, setErrors] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<Analysis | null>(null)
  const [samples, setSamples] = useState<SampleDataset[] | null>(null)
  const [busySample, setBusySample] = useState<string | null>(null)

  const maxMb = config?.max_upload_mb ?? MAX_FILE_SIZE_MB
  const requiredColumns = config?.required_columns ?? ['order_id', 'order_date', 'quantity', 'unit_price']
  const optionalColumns = config?.optional_columns ?? ['product', 'product_category', 'region', 'channel', 'customer_type']

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch(() => setSamples([]))
  }, [])

  function chooseFile(selected: File | null | undefined) {
    const problems = validateCsvFile(selected, maxMb)
    setErrors(problems)
    setResult(null)
    setFile(problems.length === 0 && selected ? selected : null)
    setPhase(problems.length === 0 ? 'ready' : 'failed')
  }

  function clearFile() {
    setFile(null)
    setErrors([])
    setPhase('idle')
    if (inputRef.current) inputRef.current.value = ''
  }

  function finish(analysis: Analysis) {
    setAnalysis(analysis)
    setResult(analysis)
    setPhase('done')
    notify('success', 'Analysis complete', `${analysis.dataset.file_name}: ${formatNumber(analysis.quality.rows_analysed)} rows analysed.`)
  }

  function fail(error: unknown) {
    const problems = error instanceof ApiError ? error.problems : [(error as Error).message]
    setErrors(problems)
    setPhase('failed')
    notify('error', 'The dataset could not be analysed', problems[0])
  }

  async function analyseFile() {
    if (!file) return
    setPhase('working')
    setErrors([])
    try {
      finish(await uploadDataset(file, synthetic))
    } catch (error) {
      fail(error)
    }
  }

  async function analyseSampleById(id: string) {
    setBusySample(id)
    setErrors([])
    setPhase('working')
    try {
      finish(await analyseSample(id))
    } catch (error) {
      fail(error)
    } finally {
      setBusySample(null)
    }
  }

  return (
    <>
      <PageHeader title="Dataset Upload" description="Upload a CSV export of sales order lines, or start from a synthetic sample. The file is validated on the server before any analysis runs." />

      <Card className="mb-6">
        <PipelineSteps steps={pipelineFor(phase)} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Upload a CSV file">
            <label
              htmlFor={inputId}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragging(false)
                chooseFile(e.dataTransfer.files[0])
              }}
              className={`flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors focus-within:ring-2 focus-within:ring-indigo-600 ${
                dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'
              }`}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                <Icon name="upload" className="h-6 w-6" />
              </span>
              <span className="mt-3 text-sm font-semibold text-slate-900">Drag a file here or click to browse</span>
              <span className="mt-1 text-xs text-slate-500">CSV only, up to {maxMb} MB</span>
              <input
                id={inputId}
                ref={inputRef}
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                aria-describedby={errors.length ? `${inputId}-errors` : undefined}
                onChange={(e) => chooseFile(e.target.files?.[0])}
              />
            </label>

            <div className="mt-4 space-y-4" id={`${inputId}-errors`}>
              {errors.length > 0 && (
                <Alert variant="error" title="This file can't be used">
                  <ul className="list-disc space-y-1 pl-4">
                    {errors.map((error) => (
                      <li key={error}>{error}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              {file && (
                <div className="rounded-lg border border-slate-200 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <Icon name="file" className="h-6 w-6 text-slate-400" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{file.name}</p>
                      <p className="text-xs text-slate-500">{formatFileSize(file.size)} · passed browser checks</p>
                    </div>
                    <Button variant="secondary" onClick={clearFile} disabled={phase === 'working'}>
                      Remove
                    </Button>
                    <Button icon="bolt" onClick={analyseFile} disabled={phase === 'working'}>
                      {phase === 'working' ? 'Analysing…' : 'Validate and analyse'}
                    </Button>
                  </div>
                  <label className="mt-3 flex items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={synthetic}
                      onChange={(e) => setSynthetic(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                    />
                    <span>This file contains synthetic or demonstration data (adds a synthetic-data notice to the dashboard and report).</span>
                  </label>
                </div>
              )}

              {result && <ResultSummary analysis={result} />}
            </div>
          </Card>

          <Card title="Synthetic sample datasets" subtitle="Fabricated data for trying FlowForge. Results are not real business findings.">
            {samples === null ? (
              <p className="text-sm text-slate-500">Loading samples…</p>
            ) : samples.length === 0 ? (
              <p className="text-sm text-slate-500">Sample datasets are unavailable. Check that the backend is running.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {samples.map((sample) => (
                  <li key={sample.id} className="flex flex-col gap-3 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900">
                        {sample.name} <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">Synthetic</span>
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">{sample.description}</p>
                      <p className="mt-0.5 font-mono text-xs text-slate-400">
                        {sample.file} · {formatFileSize(sample.size_bytes)}
                      </p>
                    </div>
                    <Button variant="secondary" onClick={() => analyseSampleById(sample.id)} disabled={busySample !== null || phase === 'working'}>
                      {busySample === sample.id ? 'Analysing…' : 'Analyse sample'}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Before you upload">
            <div className="flex gap-3 text-sm text-slate-600">
              <Icon name="shield" className="h-5 w-5 shrink-0 text-indigo-600" />
              <ul className="space-y-2">
                <li>Use synthetic or approved data only.</li>
                <li>Remove names, email addresses and phone numbers first.</li>
                <li>Never include passwords or API keys in a dataset.</li>
                <li>The original file is not stored; only the results are.</li>
              </ul>
            </div>
          </Card>
          <Card title="Expected columns" subtitle="Header names are matched case-insensitively; common alternatives such as Qty or Date are recognised.">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Required</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {requiredColumns.map((col) => (
                <li key={col} className="rounded-md bg-indigo-50 px-2 py-1 font-mono text-xs text-indigo-800">
                  {col}
                </li>
              ))}
            </ul>
            <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Optional (unlock breakdowns)</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {optionalColumns.map((col) => (
                <li key={col} className="rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
                  {col}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
