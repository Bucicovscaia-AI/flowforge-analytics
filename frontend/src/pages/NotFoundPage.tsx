import { Link } from 'react-router-dom'
import EmptyState from '../components/ui/EmptyState'

export default function NotFoundPage() {
  return (
    <EmptyState
      icon="warning"
      title="Page not found"
      action={
        <Link to="/" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
          Back to dashboard
        </Link>
      }
    >
      The page you asked for does not exist.
    </EmptyState>
  )
}
