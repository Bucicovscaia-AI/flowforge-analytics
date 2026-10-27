import { Compass, LayoutDashboard } from 'lucide-react'

import { LinkButton } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/States'

export function NotFoundPage() {
  return (
    <Card>
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="The page you were looking for does not exist or has moved."
        actions={
          <LinkButton to="/" variant="primary" icon={LayoutDashboard}>
            Go to the dashboard
          </LinkButton>
        }
      />
    </Card>
  )
}
