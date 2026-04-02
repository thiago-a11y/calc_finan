/* ErrorBoundary — Protege rotas contra crashes de componentes
 * Evita tela preta em caso de erro React #310 ou referências nulas. */

import { Component, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: string | null }

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
          <div className="max-w-md w-full mx-auto p-8 rounded-2xl text-center"
            style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
            <AlertTriangle className="w-12 h-12 mx-auto mb-4" style={{ color: '#f59e0b' }} />
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--sf-text)' }}>
              Erro ao carregar componente
            </h2>
            <p className="text-sm mb-6" style={{ color: 'var(--sf-text-secondary)' }}>
              Ocorreu um erro inesperado. Tente recarregar a pagina.
            </p>
            {this.state.error && (
              <p className="text-xs mb-6 p-3 rounded-lg font-mono overflow-auto max-h-24"
                style={{ background: 'var(--sf-bg)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
                {this.state.error}
              </p>
            )}
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white"
              style={{ background: 'var(--sf-accent)' }}
            >
              <RefreshCw className="w-4 h-4" />
              Recarregar Pagina
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
