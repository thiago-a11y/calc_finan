/* Theme Components — Componentes premium reutilizáveis com tema dinâmico */

import type { ReactNode, CSSProperties } from 'react'

/* Card premium */
export function Card({ children, className = '', hover = true, style }: {
  children: ReactNode; className?: string; hover?: boolean; style?: CSSProperties
}) {
  return (
    <div
      className={`sf-card p-5 ${hover ? '' : ''} ${className}`}
      style={style}
    >
      {children}
    </div>
  )
}

/* Page wrapper — aplica fundo e padding padrão */
export function Page({ children, title, subtitle }: {
  children: ReactNode; title?: string; subtitle?: string
}) {
  return (
    <div className="sf-animate-in">
      {title && (
        <div className="mb-6">
          <h2 className="text-2xl font-bold sf-text">{title}</h2>
          {subtitle && <p className="text-sm sf-text-muted mt-1">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  )
}

/* Stat Card — card de métrica grande */
export function StatCard({ label, value, sub, icon, cor }: {
  label: string; value: string | number; sub?: string; icon?: string; cor?: string
}) {
  return (
    <div className="sf-card p-5 group">
      <div className="flex items-center gap-2 mb-3">
        {icon && (
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: `${cor || 'var(--sf-accent)'}15` }}
          >
            {icon}
          </div>
        )}
        <p className="text-xs sf-text-muted uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-3xl font-bold sf-text font-mono tracking-tight">{value}</p>
      {sub && <p className="text-sm sf-text-muted mt-1">{sub}</p>}
    </div>
  )
}

/* Table wrapper */
export function Table({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`sf-card overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm sf-text">
          {children}
        </table>
      </div>
    </div>
  )
}

/* Badge */
export function Badge({ children, cor = 'emerald' }: { children: ReactNode; cor?: string }) {
  const cores: Record<string, string> = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    gray: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${cores[cor] || cores.gray}`}>
      {children}
    </span>
  )
}

/* Empty State */
export function EmptyState({ icon = '📭', message = 'Nenhum dado encontrado' }: {
  icon?: string; message?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 sf-text-muted">
      <span className="text-4xl mb-3">{icon}</span>
      <p className="text-sm">{message}</p>
    </div>
  )
}

/* Loading spinner */
export function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
    </div>
  )
}

/* Error state */
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="sf-card p-4 border-red-500/20">
      <p className="text-sm text-red-400">Erro: {message}</p>
    </div>
  )
}
