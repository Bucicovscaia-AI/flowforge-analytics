import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes, ComponentType, ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { cn } from '../../lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 shadow-card disabled:bg-brand-300',
  secondary: 'bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 hover:border-slate-400 shadow-card disabled:text-slate-400 disabled:bg-slate-50',
  ghost: 'text-slate-700 hover:bg-slate-100 disabled:text-slate-400',
  danger: 'bg-red-600 text-white hover:bg-red-700 shadow-card disabled:bg-red-300',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
}

// eslint-disable-next-line react-refresh/only-export-components
export function buttonClasses(variant: Variant = 'primary', size: Size = 'md', className?: string): string {
  return cn(
    'inline-flex items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors disabled:cursor-not-allowed',
    VARIANTS[variant],
    SIZES[size],
    className,
  )
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  icon?: ComponentType<{ className?: string }>
  loading?: boolean
}

export function Button({ variant = 'primary', size = 'md', icon: Icon, loading, className, children, disabled, type = 'button', ...props }: ButtonProps) {
  return (
    <button type={type} className={buttonClasses(variant, size, className)} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : Icon ? <Icon className="size-4" aria-hidden /> : null}
      {children}
    </button>
  )
}

interface LinkButtonProps {
  to: string
  variant?: Variant
  size?: Size
  icon?: ComponentType<{ className?: string }>
  className?: string
  children: ReactNode
}

export function LinkButton({ to, variant = 'secondary', size = 'md', icon: Icon, className, children }: LinkButtonProps) {
  return (
    <Link to={to} className={buttonClasses(variant, size, className)}>
      {Icon && <Icon className="size-4" aria-hidden />}
      {children}
    </Link>
  )
}

interface DownloadLinkProps {
  href: string
  variant?: Variant
  size?: Size
  icon?: ComponentType<{ className?: string }>
  children: ReactNode
  newTab?: boolean
}

export function DownloadLink({ href, variant = 'secondary', size = 'sm', icon: Icon, children, newTab }: DownloadLinkProps) {
  return (
    <a href={href} className={buttonClasses(variant, size)} {...(newTab ? { target: '_blank', rel: 'noopener noreferrer' } : { download: true })}>
      {Icon && <Icon className="size-4" aria-hidden />}
      {children}
    </a>
  )
}
