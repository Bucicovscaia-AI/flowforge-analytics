import { CheckCircle2, Database, Download, HardDrive, Pencil, Trash2, Upload } from 'lucide-react'
import { useState } from 'react'

import { api, errorMessage } from '../api/client'
import type { DatasetSummary } from '../api/types'
import { ColumnProfileTable, DataPreviewTable } from '../components/DatasetTables'
import { Badge, SampleBadge } from '../components/ui/Badge'
import { Button, DownloadLink, LinkButton } from '../components/ui/Button'
import { Card, CardHeader } from '../components/ui/Card'
import { ConfirmDialog, Dialog } from '../components/ui/Dialog'
import { TextField } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { QualityBadge } from '../components/ui/QualityBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { TableContainer, Td, Th, Tr } from '../components/ui/Table'
import { useApp } from '../context/AppContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { formatBytes, formatDateTime, formatNumber } from '../lib/format'

function SelectedDatasetDetail({ dataset }: { dataset: DatasetSummary }) {
  const { dataVersion } = useApp()
  const detail = useApi(`detail:${dataset.id}:${dataVersion}`, () => api.getDataset(dataset.id))
  return (
    <div className="mt-6 space-y-6">
      <Card>
        <CardHeader
          title={`Columns in ${dataset.name}`}
          description={`Encoding ${dataset.encoding?.toUpperCase() ?? 'unknown'} · ${formatBytes(dataset.size_bytes)} original size`}
        />
        {detail.loading && !detail.data ? (
          <LoadingState />
        ) : detail.error ? (
          <ErrorState error={detail.error} onRetry={detail.reload} />
        ) : (
          detail.data && <ColumnProfileTable columns={detail.data.columns} />
        )}
      </Card>
      <Card>
        <CardHeader title="Data preview" description="Working copy, including any cleaning applied" />
        <DataPreviewTable datasetId={dataset.id} />
      </Card>
    </div>
  )
}

export function DatasetsPage() {
  const { datasets, datasetsLoaded, datasetsError, selected, selectDataset, refreshDatasets, notifyDataChanged } = useApp()
  const { notify } = useToast()
  const [pendingDelete, setPendingDelete] = useState<DatasetSummary | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [renaming, setRenaming] = useState<DatasetSummary | null>(null)
  const [newName, setNewName] = useState('')
  const [saving, setSaving] = useState(false)

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.deleteDataset(pendingDelete.id)
      notify('success', 'Dataset deleted', `${pendingDelete.name} and its stored files were removed.`)
      setPendingDelete(null)
      notifyDataChanged()
    } catch (error) {
      notify('error', 'Could not delete the dataset', errorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  const saveName = async () => {
    if (!renaming) return
    setSaving(true)
    try {
      await api.renameDataset(renaming.id, newName)
      await refreshDatasets()
      notify('success', 'Dataset renamed')
      setRenaming(null)
    } catch (error) {
      notify('error', 'Could not rename the dataset', errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Datasets"
        actions={
          <LinkButton to="/upload" variant="primary" icon={Upload}>
            Import data
          </LinkButton>
        }
      />
      <Card>
        {!datasetsLoaded ? (
          <LoadingState />
        ) : datasetsError ? (
          <ErrorState error={datasetsError} onRetry={() => void refreshDatasets()} />
        ) : datasets.length === 0 ? (
          <EmptyState
            icon={Database}
            title="No datasets"
            description="Imported datasets will appear here."
            actions={
              <LinkButton to="/upload" variant="primary" icon={Upload}>
                Import data
              </LinkButton>
            }
          />
        ) : (
          <TableContainer label="Datasets">
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Imported</Th>
                <Th numeric>Records</Th>
                <Th numeric>Columns</Th>
                <Th>Quality</Th>
                <Th>Status</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((dataset) => {
                const isSelected = selected?.id === dataset.id
                return (
                  <Tr key={dataset.id} className={isSelected ? 'bg-brand-50/50' : undefined}>
                    <Td>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-900">{dataset.name}</span>
                        {dataset.is_sample && <SampleBadge />}
                      </div>
                      {dataset.source_filename && <p className="text-xs text-slate-500">from {dataset.source_filename}</p>}
                    </Td>
                    <Td className="whitespace-nowrap">{formatDateTime(dataset.created_at)}</Td>
                    <Td numeric>
                      {formatNumber(dataset.row_count)}
                      {dataset.row_count !== dataset.original_row_count && (
                        <p className="text-xs text-slate-500">of {formatNumber(dataset.original_row_count)} imported</p>
                      )}
                    </Td>
                    <Td numeric>{dataset.column_count}</Td>
                    <Td>
                      <QualityBadge score={dataset.quality_score} grade={dataset.quality_grade} />
                    </Td>
                    <Td>
                      <Badge tone="success" className="capitalize">{dataset.status}</Badge>
                    </Td>
                    <Td>
                      <div className="flex justify-end gap-1.5">
                        {isSelected ? (
                          <Badge tone="brand">
                            <CheckCircle2 className="size-3" aria-hidden />
                            Selected
                          </Badge>
                        ) : (
                          <Button size="sm" variant="secondary" onClick={() => selectDataset(dataset.id)}>
                            Select
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={Pencil}
                          aria-label={`Rename ${dataset.name}`}
                          onClick={() => {
                            setRenaming(dataset)
                            setNewName(dataset.name)
                          }}
                        />
                        <DownloadLink href={api.exportDatasetUrl(dataset.id)} variant="ghost" icon={Download}>
                          <span className="sr-only">Download {dataset.name} as CSV</span>
                        </DownloadLink>
                        <Button size="sm" variant="ghost" icon={Trash2} aria-label={`Delete ${dataset.name}`} onClick={() => setPendingDelete(dataset)} />
                      </div>
                    </Td>
                  </Tr>
                )
              })}
            </tbody>
          </TableContainer>
        )}
      </Card>

      {selected && <SelectedDatasetDetail dataset={selected} />}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete dataset?"
        confirmLabel="Delete dataset"
        busy={deleting}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => void confirmDelete()}
      >
        <p>
          <strong>{pendingDelete?.name}</strong> will be permanently removed from this server, including the original file, the working copy
          and its cleaning history. This cannot be undone.
        </p>
        <p className="mt-2 flex items-center gap-2 text-xs text-slate-500">
          <HardDrive className="size-3.5" aria-hidden />
          Reports already generated from this dataset are kept in report history.
        </p>
      </ConfirmDialog>

      <Dialog
        open={renaming !== null}
        title="Rename dataset"
        onClose={() => setRenaming(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRenaming(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void saveName()} loading={saving} disabled={!newName.trim()}>
              Save name
            </Button>
          </>
        }
      >
        <TextField label="Dataset name" value={newName} maxLength={120} onChange={(event) => setNewName(event.target.value)} />
      </Dialog>
    </>
  )
}
