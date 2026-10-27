import { Link } from 'react-router-dom'
import EmptyState from './EmptyState'

// Empty state for pages that need an analysed dataset.
export default function NoAnalysis({ what }: { what: string }) {
  return (
    <EmptyState
      icon="upload"
      title="No dataset analysed yet"
      action={
        <Link
          to="/upload"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
        >
          Choose a dataset
        </Link>
      }
    >
      Upload a CSV file or load a synthetic sample dataset to see {what}.
    </EmptyState>
  )
}
