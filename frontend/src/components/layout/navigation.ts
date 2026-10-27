import {
  BarChart3,
  Database,
  FileText,
  History,
  LayoutDashboard,
  type LucideIcon,
  LineChart,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  Workflow,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/** Navigation follows the product workflow: bring data in, understand it, then deliver results. */
export const NAVIGATION: NavGroup[] = [
  { label: 'Overview', items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard }] },
  {
    label: 'Data',
    items: [
      { to: '/upload', label: 'Data Upload', icon: Upload },
      { to: '/datasets', label: 'Datasets', icon: Database },
      { to: '/quality', label: 'Data Quality', icon: ShieldCheck },
    ],
  },
  {
    label: 'Analyse',
    items: [
      { to: '/analysis', label: 'Data Analysis', icon: BarChart3 },
      { to: '/visualisations', label: 'Visualisations', icon: LineChart },
      { to: '/insights', label: 'AI Insights', icon: Sparkles },
    ],
  },
  {
    label: 'Deliver',
    items: [
      { to: '/reports', label: 'Reports', icon: FileText },
      { to: '/reports/history', label: 'Report History', icon: History },
      { to: '/automation', label: 'Automation', icon: Workflow },
    ],
  },
  { label: 'System', items: [{ to: '/settings', label: 'Settings', icon: Settings }] },
]
