/* TaskTray — Bandeja global de tarefas em andamento.
 * Fica fixa no canto inferior direito em TODAS as paginas.
 * Mostra tarefas/reunioes ativas com progresso em tempo real.
 * Clique para navegar ate o Escritorio Virtual. */

import { useState, useEffect, useCallback } from 'react'
import { Loader2, X, ChevronUp, ChevronDown, Zap, Users } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface TarefaAtiva {
  id: string
  agente_nome: string
  agente_atual: string | null
  descricao: string
  status: string
  tipo: string
  squad_nome: string
}

const API = ''

function getStoredToken(): string {
  try {
    return localStorage.getItem('sf_token') || ''
  } catch {
    return ''
  }
}

function headers() {
  const t = getStoredToken()
  return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' }
}

export default function TaskTray() {
  const { autenticado } = useAuth()
  const [tarefas, setTarefas] = useState<TarefaAtiva[]>([])
  const [expandido, setExpandido] = useState(false)
  const [minimizado, setMinimizado] = useState(false)

  const buscar = useCallback(async () => {
    if (!autenticado) return
    try {
      const res = await fetch(`${API}/api/tarefas/historico?limite=10`, { headers: headers() })
      if (!res.ok) return
      const data: TarefaAtiva[] = await res.json()
      const ativas = data.filter(t => t.status === 'executando' || t.status === 'pendente' || t.status === 'aguardando_feedback')
      setTarefas(ativas)
    } catch { /* silencioso */ }
  }, [autenticado])

  // Polling a cada 4s
  useEffect(() => {
    if (!autenticado) return
    buscar()
    const intervalo = setInterval(buscar, 4000)
    return () => clearInterval(intervalo)
  }, [buscar, autenticado])

  // Nada ativo = nao mostrar
  if (tarefas.length === 0) return null

  // Minimizado = bolinha flutuante
  if (minimizado) {
    return (
      <div
        className="fixed bottom-6 right-6 z-[60] cursor-pointer"
        onClick={() => setMinimizado(false)}
      >
        <div className="relative flex items-center justify-center w-12 h-12 rounded-full shadow-lg"
          style={{
            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
            boxShadow: '0 4px 20px rgba(59,130,246,0.4), 0 0 0 3px rgba(59,130,246,0.15)',
          }}>
          <Zap size={18} className="text-white" />
          {/* Badge com contagem */}
          <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
            style={{ background: '#ef4444' }}>
            {tarefas.length}
          </div>
          {/* Pulse ring */}
          <div className="absolute inset-0 rounded-full animate-ping"
            style={{ background: 'rgba(59,130,246,0.2)' }} />
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-[60] w-72 rounded-xl overflow-hidden shadow-2xl"
      style={{
        background: 'var(--sf-bg-1, #18181b)',
        border: '1px solid var(--sf-border-default, #27272a)',
        boxShadow: '0 8px 40px rgba(0,0,0,0.3), 0 0 0 1px rgba(59,130,246,0.1)',
      }}>

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2"
        style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1))', borderBottom: '1px solid var(--sf-border-subtle, #27272a)' }}>
        <div className="flex items-center gap-2">
          <Zap size={13} style={{ color: '#3b82f6' }} />
          <span className="text-[11px] font-bold" style={{ color: 'var(--sf-text-0, #fafafa)' }}>
            {tarefas.length} tarefa{tarefas.length > 1 ? 's' : ''} ativa{tarefas.length > 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setExpandido(!expandido)}
            className="w-5 h-5 rounded flex items-center justify-center hover:bg-white/10 transition-colors"
            style={{ color: 'var(--sf-text-3, #71717a)' }}>
            {expandido ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          </button>
          <button onClick={() => setMinimizado(true)}
            className="w-5 h-5 rounded flex items-center justify-center hover:bg-white/10 transition-colors"
            style={{ color: 'var(--sf-text-3, #71717a)' }}
            title="Minimizar">
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Lista de tarefas */}
      <div className="max-h-48 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        {tarefas.map(t => (
          <div key={t.id} className="px-3 py-2 flex items-start gap-2"
            style={{ borderBottom: '1px solid var(--sf-border-subtle, #1f1f23)' }}>
            {/* Icone animado */}
            <div className="mt-0.5 flex-shrink-0">
              {t.status === 'executando' ? (
                <Loader2 size={12} className="animate-spin" style={{ color: '#3b82f6' }} />
              ) : t.status === 'aguardando_feedback' ? (
                <Users size={12} style={{ color: '#f59e0b' }} />
              ) : (
                <div className="w-3 h-3 rounded-full animate-pulse" style={{ background: '#f59e0b' }} />
              )}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-semibold truncate" style={{ color: 'var(--sf-text-0, #fafafa)' }}>
                {t.agente_nome}
              </p>
              {t.agente_atual ? (
                <p className="text-[9px] truncate" style={{ color: '#60a5fa' }}>
                  {t.agente_atual}
                </p>
              ) : t.status === 'aguardando_feedback' ? (
                <p className="text-[9px] font-medium" style={{ color: '#f59e0b' }}>
                  Aguardando seu feedback
                </p>
              ) : (
                <p className="text-[9px] truncate" style={{ color: 'var(--sf-text-3, #71717a)' }}>
                  {t.descricao?.slice(0, 50)}
                </p>
              )}

              {/* Barra shimmer */}
              {t.status === 'executando' && (
                <div className="w-full h-0.5 rounded-full mt-1 overflow-hidden" style={{ background: 'rgba(59,130,246,0.15)' }}>
                  <div className="h-full rounded-full" style={{
                    background: 'linear-gradient(90deg, #3b82f6, #8b5cf6, #3b82f6)',
                    backgroundSize: '200% 100%',
                    animation: 'shimmer 2s ease-in-out infinite',
                    width: '70%',
                  }} />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer expandido: navegar ao escritorio */}
      {expandido && (
        <div className="px-3 py-2" style={{ borderTop: '1px solid var(--sf-border-subtle, #1f1f23)' }}>
          <a href="/escritorio"
            className="flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg text-[10px] font-semibold transition-all hover:brightness-110"
            style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.15)' }}>
            Ir para o Escritorio Virtual
          </a>
        </div>
      )}
    </div>
  )
}
