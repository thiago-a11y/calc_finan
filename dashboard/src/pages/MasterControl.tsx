/* Master Control — Feature Flags GUI (CEO Only)
 *
 * v0.59.4 — Controle visual de feature flags do sistema.
 * Flags são ligadas/desligadas pelo CEO via interface web.
 * Altera o banco de dados (não variáveis de ambiente em produção).
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Zap, Shield, Bot, Eye, Clock, Rocket, GitBranch,
  CheckCircle, XCircle, RefreshCw, History,
  AlertTriangle, Power, Loader2,
} from 'lucide-react'

interface FeatureFlag {
  id: number
  nome: string
  habilitado: boolean
  descricao: string
  requer_restart: boolean
  atualizado_por: string
  atualizado_em: string | null
}

interface HistoryEntry {
  id: number
  flag_nome: string
  usuario_email: string
  valor_anterior: boolean
  valor_novo: boolean
  criado_em: string
}

/* Mapeamento de ícones e cores por flag */
const flagConfig: Record<string, {
  Icon: typeof Zap; cor: string; badge: string
}> = {
  fork_subagent:     { Icon: Bot,        cor: '#a78bfa', badge: 'Fork' },
  worktree_isolation: { Icon: GitBranch,  cor: '#34d399', badge: 'Isol.' },
  autonomous_mode:   { Icon: Shield,     cor: '#f87171', badge: 'Auto' },
  brief_mode:        { Icon: Eye,        cor: '#fbbf24', badge: 'Brief' },
  continuous_factory: { Icon: Clock,      cor: '#60a5fa', badge: '24/7' },
  visible_execution:  { Icon: Rocket,     cor: '#f472b6', badge: 'Live' },
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function MasterControl() {
  const { token, usuario } = useAuth()
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [carregando, setCarregando] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [tab, setTab] = useState<'flags' | 'history'>('flags')

  const fetchFlags = useCallback(async () => {
    try {
      const res = await fetch('/api/master-control/flags', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) {
        setErro('Acesso negado. Apenas o CEO pode acessar esta página.')
        return
      }
      if (!res.ok) throw new Error('Erro ao carregar flags')
      const data = await res.json()
      setFlags(data)
      setErro(null)
    } catch (e) {
      setErro('Erro ao carregar feature flags. Verifique se a API está rodando.')
      console.error(e)
    } finally {
      setCarregando(false)
    }
  }, [token])

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch('/api/master-control/flags/history', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Erro')
      const data = await res.json()
      setHistory(data)
    } catch (e) {
      console.error(e)
    }
  }, [token])

  // Carregar dados uma vez na montagem
  useEffect(() => {
    fetchFlags()
    fetchHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const toggleFlag = async (nome: string) => {
    setToggling(nome)
    try {
      const res = await fetch(`/api/master-control/flags/${nome}/toggle`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) {
        setErro('Acesso negado. Apenas o CEO pode alterar flags.')
        return
      }
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erro')
      }
      const result = await res.json()
      setFlags(prev =>
        prev.map(f =>
          f.nome === nome
            ? { ...f, habilitado: result.habilitado }
            : f
        )
      )
      fetchHistory()
    } catch (e) {
      console.error(e)
      setErro(`Erro ao toggle '${nome}': ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setToggling(null)
    }
  }

  const restartFlag = async (nome: string) => {
    try {
      const res = await fetch(`/api/master-control/flags/${nome}/restart`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Erro no restart')
      setErro(null)
    } catch (e) {
      setErro(`Erro ao solicitar restart: ${e}`)
    }
  }

  const recarregar = () => {
    setCarregando(true)
    setFlags([])
    fetchFlags()
    fetchHistory()
  }

  const flagsComRestart = flags.filter(f => f.requer_restart && f.habilitado)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' }}
          >
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-[20px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
              Master Control
            </h1>
            <div className="flex items-center gap-2 mt-0.5">
              <Shield size={12} style={{ color: '#8b5cf6' }} />
              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(139,92,246,0.12)', color: '#8b5cf6' }}>
                CEO Only
              </span>
              <span className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
                {usuario?.email}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={recarregar}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] transition-all"
          style={{
            background: 'var(--sf-bg-2)',
            border: '1px solid var(--sf-border-subtle)',
            color: 'var(--sf-text-2)',
          }}
        >
          <RefreshCw size={12} />
          Atualizar
        </button>
      </div>

      {/* Aviso de restart pendente */}
      {flagsComRestart.length > 0 && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl"
          style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.2)',
          }}
        >
          <AlertTriangle size={16} style={{ color: '#ef4444', flexShrink: 0 }} />
          <div className="flex-1">
            <p className="text-[13px] font-medium" style={{ color: '#fca5a5' }}>
              {flagsComRestart.length} flag(s) requer(em) restart do serviço
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: '#f87171' }}>
              {flagsComRestart.map(f => f.nome).join(', ')}
            </p>
          </div>
          <button
            onClick={() => flagsComRestart.forEach(f => restartFlag(f.nome))}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
            style={{
              background: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.3)',
              color: '#fca5a5',
            }}
          >
            <Rocket size={12} />
            Restart
          </button>
        </div>
      )}

      {/* Erro */}
      {erro && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl"
          style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.2)',
          }}
        >
          <XCircle size={16} style={{ color: '#ef4444', flexShrink: 0 }} />
          <p className="text-[13px]" style={{ color: '#fca5a5' }}>{erro}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-xl"
        style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-subtle)' }}>
        <button
          onClick={() => setTab('flags')}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[13px] font-medium transition-all"
          style={{
            background: tab === 'flags' ? 'var(--sf-bg-1)' : 'transparent',
            color: tab === 'flags' ? 'var(--sf-text-0)' : 'var(--sf-text-2)',
            boxShadow: tab === 'flags' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
          }}
        >
          <Power size={14} />
          Feature Flags
        </button>
        <button
          onClick={() => { setTab('history'); fetchHistory() }}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[13px] font-medium transition-all"
          style={{
            background: tab === 'history' ? 'var(--sf-bg-1)' : 'transparent',
            color: tab === 'history' ? 'var(--sf-text-0)' : 'var(--sf-text-2)',
            boxShadow: tab === 'history' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
          }}
        >
          <History size={14} />
          Histórico
        </button>
      </div>

      {/* Conteúdo */}
      {tab === 'flags' ? (
        <div className="space-y-3">
          {carregando ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin" style={{ color: 'var(--sf-text-3)' }} />
            </div>
          ) : flags.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[14px]" style={{ color: 'var(--sf-text-3)' }}>
                Nenhuma flag encontrada. Execute o script de migração primeiro.
              </p>
            </div>
          ) : (
            flags.map(flag => {
              const cfg = flagConfig[flag.nome] || { Icon: Zap, cor: '#6b7280', badge: flag.nome }
              const active = flag.habilitado
              return (
                <div
                  key={flag.id}
                  className="flex items-center gap-4 px-5 py-4 rounded-xl transition-all"
                  style={{
                    background: 'var(--sf-bg-2)',
                    border: `1px solid ${active ? cfg.cor + '40' : 'var(--sf-border-subtle)'}`,
                  }}
                >
                  {/* Ícone */}
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: cfg.cor + '18' }}
                  >
                    <cfg.Icon size={16} color={cfg.cor} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <code className="text-[13px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
                        {flag.nome}
                      </code>
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-md font-bold"
                        style={{ background: cfg.cor + '20', color: cfg.cor }}
                      >
                        {cfg.badge}
                      </span>
                      {flag.requer_restart && (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded-md font-medium flex items-center gap-0.5"
                          style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
                        >
                          <RefreshCw size={8} />
                          restart
                        </span>
                      )}
                    </div>
                    <p className="text-[12px] mt-1" style={{ color: 'var(--sf-text-2)' }}>
                      {flag.descricao}
                    </p>
                    <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
                      Atualizado por {flag.atualizado_por || '—'} • {formatDate(flag.atualizado_em)}
                    </p>
                  </div>

                  {/* Status + Toggle */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span
                      className="flex items-center gap-1 text-[11px] font-semibold"
                      style={{ color: active ? '#10b981' : 'var(--sf-text-3)' }}
                    >
                      {active ? (
                        <CheckCircle size={13} style={{ color: '#10b981' }} />
                      ) : (
                        <XCircle size={13} />
                      )}
                      {active ? 'ON' : 'OFF'}
                    </span>

                    <button
                      onClick={() => toggleFlag(flag.nome)}
                      disabled={toggling === flag.nome}
                      className="relative w-12 h-6 rounded-full transition-all duration-300 disabled:opacity-50"
                      style={{
                        background: active ? '#10b981' : 'rgba(255,255,255,0.08)',
                        border: `1px solid ${active ? '#10b981' : 'rgba(255,255,255,0.12)'}`,
                      }}
                    >
                      <div
                        className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-300"
                        style={{
                          background: active ? '#fff' : 'rgba(255,255,255,0.3)',
                          [active ? 'left' : 'right']: '3px',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                        }}
                      />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      ) : (
        /* Histórico */
        <div className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--sf-border-subtle)' }}>
          <table className="w-full">
            <thead>
              <tr style={{ background: 'var(--sf-bg-2)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
                <th className="text-left px-4 py-3 text-[11px] font-semibold" style={{ color: 'var(--sf-text-3)' }}>FLAG</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold" style={{ color: 'var(--sf-text-3)' }}>ALTERAÇÃO</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold" style={{ color: 'var(--sf-text-3)' }}>USUÁRIO</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold" style={{ color: 'var(--sf-text-3)' }}>QUANDO</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-[13px]" style={{ color: 'var(--sf-text-3)' }}>
                    Nenhuma alteração registrada ainda.
                  </td>
                </tr>
              ) : (
                history.map(entry => (
                  <tr key={entry.id}
                    className="transition-colors"
                    style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--sf-bg-2)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td className="px-4 py-3">
                      <code className="text-[12px]" style={{ color: 'var(--sf-text-1)' }}>
                        {entry.flag_nome}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="text-[11px] font-medium px-2 py-0.5 rounded-md"
                        style={{
                          background: entry.valor_anterior ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                          color: entry.valor_anterior ? '#fca5a5' : '#6ee7b7',
                        }}
                      >
                        {entry.valor_anterior ? 'ON' : 'OFF'}
                      </span>
                      <span className="mx-1.5 text-[11px]" style={{ color: 'var(--sf-text-4)' }}>→</span>
                      <span
                        className="text-[11px] font-medium px-2 py-0.5 rounded-md"
                        style={{
                          background: entry.valor_novo ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                          color: entry.valor_novo ? '#6ee7b7' : '#fca5a5',
                        }}
                      >
                        {entry.valor_novo ? 'ON' : 'OFF'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[12px]" style={{ color: 'var(--sf-text-2)' }}>
                        {entry.usuario_email}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
                        {formatDate(entry.criado_em)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
