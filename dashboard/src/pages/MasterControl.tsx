/* Master Control — Feature Flags GUI (CEO Only)
 *
 * v0.59.6 — Controle visual de feature flags do sistema.
 * Flags são ligadas/desligadas pelo CEO via interface web.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Zap, Shield, Bot, Eye, Clock, Rocket, GitBranch,
  CheckCircle, XCircle, RefreshCw, History,
  AlertTriangle, Power, Loader2, Info,
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

/* Tooltips e nomes amigáveis por flag */
const FLAG_META: Record<string, {
  nomeAmigavel: string
  tooltip: string
  cor: string
  Icon: typeof Zap
}> = {
  fork_subagent: {
    nomeAmigavel: 'Fork de Subagente',
    tooltip: 'Permite que a Luna crie sub-agentes automaticamente quando você pede "inicie um sub-agente" ou "crie um fork". Essencial para squads autônomos.',
    cor: '#a78bfa',
    Icon: Bot,
  },
  worktree_isolation: {
    nomeAmigavel: 'Isolamento Worktree',
    tooltip: 'Cria uma cópia isolada do projeto (git worktree) para cada sub-agente. Evita que um agente atrapalhe o trabalho do outro.',
    cor: '#34d399',
    Icon: GitBranch,
  },
  autonomous_mode: {
    nomeAmigavel: 'Modo Autônomo',
    tooltip: 'Permite que agentes tomem decisões e executem ações sem pedir confirmação do usuário (modo autônomo).',
    cor: '#f87171',
    Icon: Shield,
  },
  brief_mode: {
    nomeAmigavel: 'Modo Breve',
    tooltip: 'Força os agentes a responderem de forma curta, estruturada e objetiva (modo breve).',
    cor: '#fbbf24',
    Icon: Eye,
  },
  continuous_factory: {
    nomeAmigavel: 'Fábrica Contínua',
    tooltip: 'Mantém a fábrica de agentes rodando 24/7, processando tarefas em segundo plano automaticamente.',
    cor: '#60a5fa',
    Icon: Clock,
  },
  visible_execution: {
    nomeAmigavel: 'Execução Visível',
    tooltip: 'Mostra em tempo real o que os agentes estão fazendo (streaming ao vivo no Mission Control).',
    cor: '#f472b6',
    Icon: Rocket,
  },
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

/* Badge de status ON/OFF */
function StatusBadge({ on }: { on: boolean }) {
  return (
    <span
      className="flex items-center gap-1 text-[11px] font-semibold"
      style={{ color: on ? '#10b981' : 'var(--sf-text-3)' }}
    >
      {on ? (
        <CheckCircle size={13} style={{ color: '#10b981' }} />
      ) : (
        <XCircle size={13} />
      )}
      {on ? 'ON' : 'OFF'}
    </span>
  )
}

/* Card individual de flag */
function FlagCard({
  flag,
  toggling,
  onToggle,
}: {
  flag: FeatureFlag
  toggling: string | null
  onToggle: (nome: string) => void
}) {
  const meta = FLAG_META[flag.nome]
  const { Icon, cor, tooltip, nomeAmigavel } = meta || {
    Icon: Zap, cor: '#6b7280', tooltip: flag.descricao, nomeAmigavel: flag.nome
  }
  const active = flag.habilitado

  return (
    <div
      className="group relative rounded-2xl p-5 transition-all duration-200"
      style={{
        background: 'var(--sf-bg-2)',
        border: `1px solid ${active ? cor + '50' : 'var(--sf-border-subtle)'}`,
      }}
    >
      {/* Badge Requires Restart */}
      {flag.requer_restart && (
        <div
          className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
          style={{
            background: 'rgba(239,68,68,0.12)',
            color: '#ef4444',
            border: '1px solid rgba(239,68,68,0.25)',
          }}
        >
          <AlertTriangle size={9} />
          Requires Restart
        </div>
      )}

      <div className="flex items-start gap-4">
        {/* Ícone */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ background: cor + '15' }}
        >
          <Icon size={18} color={cor} />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 pr-16">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-[14px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
              {nomeAmigavel}
            </h3>
          </div>
          <p className="text-[12px] mt-1 leading-relaxed" style={{ color: 'var(--sf-text-2)' }}>
            {flag.descricao}
          </p>
          <p className="text-[11px] mt-1.5" style={{ color: 'var(--sf-text-3)' }}>
            {flag.atualizado_por ? `Atualizado por ${flag.atualizado_por} • ${formatDate(flag.atualizado_em)}` : formatDate(flag.atualizado_em)}
          </p>
        </div>

        {/* Toggle */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <StatusBadge on={active} />
          <button
            onClick={() => onToggle(flag.nome)}
            disabled={toggling === flag.nome}
            className="relative w-12 h-6 rounded-full transition-all duration-300 disabled:opacity-40"
            style={{
              background: active ? '#10b981' : 'rgba(255,255,255,0.07)',
              border: `1px solid ${active ? '#10b981' : 'rgba(255,255,255,0.12)'}`,
            }}
            title={active ? 'Desativar' : 'Ativar'}
          >
            {toggling === flag.nome ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 size={12} className="animate-spin text-white" />
              </div>
            ) : (
              <div
                className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-300"
                style={{
                  background: active ? '#fff' : 'rgba(255,255,255,0.25)',
                  [active ? 'left' : 'right']: '3px',
                  boxShadow: '0 1px 4px rgba(0,0,0,0.35)',
                }}
              />
            )}
          </button>
        </div>
      </div>

      {/* Tooltip no hover */}
      <div
        className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none"
        style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          zIndex: 10,
        }}
      >
        <div
          className="rounded-xl px-4 py-3 text-[12px] leading-relaxed max-w-xs text-left"
          style={{
            background: 'var(--sf-bg-tooltip)',
            backdropFilter: 'blur(20px)',
            border: '1px solid var(--sf-border-default)',
            color: 'var(--sf-text-1)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}
        >
          <div className="flex items-start gap-2">
            <Info size={13} style={{ color: cor, flexShrink: 0, marginTop: '1px' }} />
            <span>{tooltip}</span>
          </div>
          {/* Seta */}
          <div
            style={{
              position: 'absolute',
              bottom: '-5px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '5px solid var(--sf-bg-tooltip)',
            }}
          />
        </div>
      </div>
    </div>
  )
}

/* Dialog de confirmação de restart */
function RestartConfirmDialog({
  flagNome,
  flagDescricao,
  onConfirm,
  onCancel,
  restarting,
}: {
  flagNome: string
  flagDescricao: string
  onConfirm: () => void
  onCancel: () => void
  restarting: boolean
}) {
  const meta = FLAG_META[flagNome]
  const nomeAmigavel = meta?.nomeAmigavel || flagNome

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(6px)' }}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-lg rounded-2xl overflow-hidden"
        style={{
          background: 'var(--sf-bg-1)',
          border: '1px solid var(--sf-border-default)',
          boxShadow: '0 32px 64px rgba(0,0,0,0.6)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <div className="flex items-start gap-4">
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
            >
              <Rocket size={20} style={{ color: '#ef4444' }} />
            </div>
            <div className="flex-1">
              <h2 className="text-[16px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
                Reiniciar o Serviço
              </h2>
              <p className="text-[13px] mt-1 leading-relaxed" style={{ color: 'var(--sf-text-2)' }}>
                A flag <strong style={{ color: 'var(--sf-text-1)' }}>{nomeAmigavel}</strong> foi alterada e precisa de um restart para entrar em vigor.
              </p>
            </div>
          </div>
        </div>

        {/* Aviso */}
        <div
          className="mx-6 mb-5 rounded-xl px-4 py-3"
          style={{
            background: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.15)',
          }}
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle size={14} style={{ color: '#ef4444', flexShrink: 0, marginTop: '1px' }} />
            <div>
              <p className="text-[12px] font-medium" style={{ color: '#fca5a5' }}>
                Esta ação vai reiniciar a API e desconectar usuários temporariamente.
              </p>
              <p className="text-[11px] mt-1" style={{ color: '#f87171' }}>
                O serviço vai voltar automaticamente em ~10 segundos.
              </p>
            </div>
          </div>
        </div>

        {/* Flag afetada */}
        <div
          className="mx-6 mb-5 rounded-xl px-4 py-3 flex items-center gap-3"
          style={{
            background: 'var(--sf-bg-2)',
            border: '1px solid var(--sf-border-subtle)',
          }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(139,92,246,0.1)' }}
          >
            <Zap size={14} style={{ color: '#8b5cf6' }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
              {nomeAmigavel}
            </p>
            <p className="text-[11px] truncate" style={{ color: 'var(--sf-text-3)' }}>
              {flagDescricao}
            </p>
          </div>
        </div>

        {/* Botões */}
        <div
          className="flex items-center justify-end gap-3 px-6 pb-6"
          style={{ borderTop: '1px solid var(--sf-border-subtle)', paddingTop: '16px' }}
        >
          <button
            onClick={onCancel}
            disabled={restarting}
            className="px-4 py-2 rounded-lg text-[13px] font-medium transition-all disabled:opacity-40"
            style={{
              background: 'var(--sf-bg-2)',
              border: '1px solid var(--sf-border-default)',
              color: 'var(--sf-text-1)',
            }}
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={restarting}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-[13px] font-semibold transition-all disabled:opacity-50"
            style={{
              background: '#dc2626',
              color: '#fff',
              boxShadow: '0 4px 12px rgba(220,38,38,0.3)',
            }}
          >
            {restarting ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Reiniciando...
              </>
            ) : (
              <>
                <Rocket size={14} />
                Reiniciar Serviço
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

/* Linha de histórico */
function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const meta = FLAG_META[entry.flag_nome]
  const nomeAmigavel = meta?.nomeAmigavel || entry.flag_nome

  return (
    <tr
      className="transition-colors"
      style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--sf-bg-2)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <td className="px-5 py-3.5">
        <div className="flex items-center gap-2">
          {meta && (
            <div
              className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
              style={{ background: meta.cor + '15' }}
            >
              <meta.Icon size={11} color={meta.cor} />
            </div>
          )}
          <div>
            <p className="text-[12px] font-medium" style={{ color: 'var(--sf-text-1)' }}>
              {nomeAmigavel}
            </p>
            <p className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
              {entry.flag_nome}
            </p>
          </div>
        </div>
      </td>
      <td className="px-5 py-3.5">
        <div className="flex items-center gap-1.5">
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded-md"
            style={{
              background: entry.valor_anterior ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
              color: entry.valor_anterior ? '#fca5a5' : '#6ee7b7',
            }}
          >
            {entry.valor_anterior ? 'ON' : 'OFF'}
          </span>
          <span className="text-[11px]" style={{ color: 'var(--sf-text-4)' }}>→</span>
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded-md"
            style={{
              background: entry.valor_novo ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              color: entry.valor_novo ? '#6ee7b7' : '#fca5a5',
            }}
          >
            {entry.valor_novo ? 'ON' : 'OFF'}
          </span>
        </div>
      </td>
      <td className="px-5 py-3.5">
        <p className="text-[12px]" style={{ color: 'var(--sf-text-2)' }}>
          {entry.usuario_email}
        </p>
      </td>
      <td className="px-5 py-3.5">
        <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
          {formatDate(entry.criado_em)}
        </p>
      </td>
    </tr>
  )
}

export default function MasterControl() {
  const { token, usuario } = useAuth()
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [carregando, setCarregando] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [tab, setTab] = useState<'flags' | 'history'>('flags')

  // Dialog de restart
  const [confirmingRestart, setConfirmingRestart] = useState(false)
  const [restartTarget, setRestartTarget] = useState<{ nome: string; descricao: string } | null>(null)
  const [restarting, setRestarting] = useState(false)

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

  // Carregar dados na montagem
  useEffect(() => {
    fetchFlags()
    fetchHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-dismiss success message
  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(null), 6000)
      return () => clearTimeout(t)
    }
  }, [successMsg])

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
            ? { ...f, habilitado: result.habilitado, requer_restart: result.requer_restart }
            : f
        )
      )
      fetchHistory()
    } catch (e) {
      console.error(e)
      setErro(`Erro ao alterar '${nome}': ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setToggling(null)
    }
  }

  const openRestartDialog = (nome: string, descricao: string) => {
    setRestartTarget({ nome, descricao })
    setConfirmingRestart(true)
  }

  const handleRestartConfirm = async () => {
    if (!restartTarget) return
    setRestarting(true)
    try {
      const res = await fetch(`/api/master-control/flags/${restartTarget.nome}/restart`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erro ao reiniciar')
      }
      setConfirmingRestart(false)
      setRestartTarget(null)
      setSuccessMsg('Serviço reiniciado com sucesso! A página vai recarregar em instantes.')
      setTimeout(() => window.location.reload(), 3000)
    } catch (e) {
      setErro(`Erro ao reiniciar: ${e instanceof Error ? e.message : String(e)}`)
      setConfirmingRestart(false)
    } finally {
      setRestarting(false)
    }
  }

  const handleRestartCancel = () => {
    if (!restarting) {
      setConfirmingRestart(false)
      setRestartTarget(null)
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
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Dialog de confirmação de restart */}
      {confirmingRestart && restartTarget && (
        <RestartConfirmDialog
          flagNome={restartTarget.nome}
          flagDescricao={restartTarget.descricao}
          onConfirm={handleRestartConfirm}
          onCancel={handleRestartCancel}
          restarting={restarting}
        />
      )}

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
        <div className="flex items-center gap-2">
          <button
            onClick={recarregar}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] transition-all"
            style={{
              background: 'var(--sf-bg-2)',
              border: '1px solid var(--sf-border-subtle)',
              color: 'var(--sf-text-2)',
            }}
            title="Recarregar dados"
          >
            <RefreshCw size={12} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Aviso de restart pendente */}
      {flagsComRestart.length > 0 && (
        <div
          className="flex items-center gap-3 px-5 py-4 rounded-2xl"
          style={{
            background: 'rgba(239,68,68,0.07)',
            border: '1px solid rgba(239,68,68,0.2)',
          }}
        >
          <AlertTriangle size={17} style={{ color: '#ef4444', flexShrink: 0 }} />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold" style={{ color: '#fca5a5' }}>
              {flagsComRestart.length} flag(s) precisa(m) de restart para funcionar
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: '#f87171' }}>
              {flagsComRestart.map(f => {
                const meta = FLAG_META[f.nome]
                return meta?.nomeAmigavel || f.nome
              }).join(', ')}
            </p>
          </div>
          {flagsComRestart.map(f => (
            <button
              key={f.nome}
              onClick={() => openRestartDialog(f.nome, f.descricao)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all flex-shrink-0"
              style={{
                background: 'rgba(239,68,68,0.15)',
                border: '1px solid rgba(239,68,68,0.3)',
                color: '#fca5a5',
              }}
            >
              <Rocket size={11} />
              Reiniciar
            </button>
          ))}
        </div>
      )}

      {/* Sucesso */}
      {successMsg && (
        <div
          className="flex items-center gap-3 px-4 py-3.5 rounded-xl"
          style={{
            background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.2)',
          }}
        >
          <CheckCircle size={16} style={{ color: '#10b981', flexShrink: 0 }} />
          <p className="text-[13px]" style={{ color: '#6ee7b7' }}>{successMsg}</p>
        </div>
      )}

      {/* Erro */}
      {erro && (
        <div
          className="flex items-center gap-3 px-4 py-3.5 rounded-xl"
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
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-[13px] font-medium transition-all"
          style={{
            background: tab === 'flags' ? 'var(--sf-bg-1)' : 'transparent',
            color: tab === 'flags' ? 'var(--sf-text-0)' : 'var(--sf-text-2)',
            boxShadow: tab === 'flags' ? '0 1px 4px rgba(0,0,0,0.1)' : 'none',
          }}
        >
          <Power size={14} />
          Feature Flags
          {!carregando && (
            <span
              className="ml-1 text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
              style={{
                background: tab === 'flags' ? 'var(--sf-accent-dim)' : 'rgba(255,255,255,0.06)',
                color: tab === 'flags' ? 'var(--sf-accent-text)' : 'var(--sf-text-3)',
              }}
            >
              {flags.length}
            </span>
          )}
        </button>
        <button
          onClick={() => { setTab('history'); fetchHistory() }}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-[13px] font-medium transition-all"
          style={{
            background: tab === 'history' ? 'var(--sf-bg-1)' : 'transparent',
            color: tab === 'history' ? 'var(--sf-text-0)' : 'var(--sf-text-2)',
            boxShadow: tab === 'history' ? '0 1px 4px rgba(0,0,0,0.1)' : 'none',
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
            <div className="flex items-center justify-center py-20">
              <Loader2 size={28} className="animate-spin" style={{ color: 'var(--sf-text-3)' }} />
            </div>
          ) : flags.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-[14px]" style={{ color: 'var(--sf-text-3)' }}>
                Nenhuma flag encontrada. Execute o script de migração primeiro.
              </p>
            </div>
          ) : (
            flags.map(flag => (
              <div key={flag.id} className="relative">
                <FlagCard
                  flag={flag}
                  toggling={toggling}
                  onToggle={toggleFlag}
                />
                {/* Botão de restart inline no card quando requer restart */}
                {flag.requer_restart && flag.habilitado && (
                  <button
                    onClick={() => openRestartDialog(flag.nome, flag.descricao)}
                    className="absolute bottom-4 right-20 flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                    style={{
                      background: 'rgba(239,68,68,0.1)',
                      border: '1px solid rgba(239,68,68,0.25)',
                      color: '#ef4444',
                    }}
                  >
                    <Rocket size={10} />
                    Reiniciar
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      ) : (
        /* Histórico */
        <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--sf-border-subtle)' }}>
          <table className="w-full">
            <thead>
              <tr style={{ background: 'var(--sf-bg-2)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
                <th className="text-left px-5 py-3.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--sf-text-3)' }}>Flag</th>
                <th className="text-left px-5 py-3.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--sf-text-3)' }}>Alteração</th>
                <th className="text-left px-5 py-3.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--sf-text-3)' }}>Usuário</th>
                <th className="text-left px-5 py-3.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--sf-text-3)' }}>Quando</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-16 text-[13px]" style={{ color: 'var(--sf-text-3)' }}>
                    Nenhuma alteração registrada ainda.
                  </td>
                </tr>
              ) : (
                history.map(entry => (
                  <HistoryRow key={entry.id} entry={entry} />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
