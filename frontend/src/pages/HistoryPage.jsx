import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import DemoNotice from '../components/ui/DemoNotice'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { reportHistory } from '../data/sampleData'
import { formatDateTime } from '../utils/format'

export default function HistoryPage() {
  return (
    <>
      <PageHeader title="Report History" description="Previously generated reports and the datasets they were built from." />
      <DemoNotice>These entries are sample records that show the layout. Saved history is not implemented yet.</DemoNotice>
      <Card>
        <DataTable
          caption="Report history"
          rowKey="id"
          rows={reportHistory}
          columns={[
            { key: 'id', header: 'ID', render: (r) => <span className="font-mono text-xs">{r.id}</span> },
            { key: 'title', header: 'Report', render: (r) => <span className="font-medium text-slate-900">{r.title}</span> },
            { key: 'dataset', header: 'Dataset' },
            { key: 'created', header: 'Created', render: (r) => formatDateTime(r.created) },
            {
              key: 'status',
              header: 'Status',
              render: (r) => <StatusBadge variant={r.status === 'Ready' ? 'success' : 'error'}>{r.status}</StatusBadge>,
            },
          ]}
        />
      </Card>
    </>
  )
}
