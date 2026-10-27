import { useId, useRef, useState } from 'react'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import PipelineSteps from '../components/ui/PipelineSteps'
import { formatFileSize } from '../utils/format'
import { MAX_FILE_SIZE_MB, validateCsvFile } from '../utils/validateFile'

const REQUIRED_COLUMNS = ['order_id', 'order_date', 'region', 'channel', 'product_category', 'quantity', 'unit_price', 'customer_type']

export default function UploadPage() {
  const inputId = useId()
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [errors, setErrors] = useState([])
  const [dragging, setDragging] = useState(false)

  function handleFile(selected) {
    const problems = validateCsvFile(selected)
    setErrors(problems)
    setFile(problems.length === 0 ? selected : null)
  }

  const steps = [
    { label: 'Upload', description: 'Choose a CSV file', state: file ? 'done' : 'current' },
    { label: 'Validate', description: 'Type, size, columns', state: file ? 'current' : 'pending' },
    { label: 'Clean', description: 'Missing and duplicate rows', state: 'pending' },
    { label: 'Analyse', description: 'Calculate KPIs', state: 'pending' },
    { label: 'Report', description: 'Generate and download', state: 'pending' },
  ]

  return (
    <>
      <PageHeader title="Dataset Upload" description="Upload a CSV export of sales orders. The file is checked before any analysis runs." />

      <Card className="mb-6">
        <PipelineSteps steps={steps} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Upload a CSV file" className="lg:col-span-2">
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
              handleFile(e.dataTransfer.files[0])
            }}
            className={`flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors focus-within:ring-2 focus-within:ring-indigo-600 ${
              dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'
            }`}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
              <Icon name="upload" className="h-6 w-6" />
            </span>
            <span className="mt-3 text-sm font-semibold text-slate-900">Drag a file here or click to browse</span>
            <span className="mt-1 text-xs text-slate-500">CSV only, up to {MAX_FILE_SIZE_MB} MB</span>
            <input
              id={inputId}
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              aria-describedby={errors.length ? `${inputId}-errors` : undefined}
              onChange={(e) => handleFile(e.target.files[0])}
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
              <>
                <div className="flex items-center gap-3 rounded-lg border border-slate-200 px-4 py-3">
                  <Icon name="file" className="h-6 w-6 text-slate-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{file.name}</p>
                    <p className="text-xs text-slate-500">{formatFileSize(file.size)} · passed browser checks</p>
                  </div>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setFile(null)
                      inputRef.current.value = ''
                    }}
                  >
                    Remove
                  </Button>
                </div>
                <Alert variant="info" title="Analysis not connected yet">
                  Server-side validation and analysis are added in the next development stages. This page currently checks
                  the file in the browser only.
                </Alert>
              </>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <Card title="Before you upload">
            <div className="flex gap-3 text-sm text-slate-600">
              <Icon name="shield" className="h-5 w-5 shrink-0 text-indigo-600" />
              <ul className="space-y-2">
                <li>Use synthetic or approved data only.</li>
                <li>Remove names, email addresses and phone numbers first.</li>
                <li>Never include passwords or API keys in a dataset.</li>
              </ul>
            </div>
          </Card>
          <Card title="Expected columns">
            <ul className="flex flex-wrap gap-2">
              {REQUIRED_COLUMNS.map((col) => (
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
