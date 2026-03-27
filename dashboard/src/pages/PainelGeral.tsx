/* Painel Geral — Premium dashboard inspired by Linear/Vercel */

import { useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarStatus } from '../services/api'
import { Users, ShieldCheck, BookOpen, Bot, Crown, ArrowUpRight } from 'lucide-react'

export default function PainelGeral() {
  const fetcher = useCallback(() => buscarStatus(), [])
  const { dados, erro, carregando } = usePolling(fetcher, 10000)

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 rounded-full sf-pulse" style={{ borderColor: 'var(--sf-border-default)', borderTopColor: 'var(--sf-accent)' }} />
      </div>
    )
  }

  if (erro) {
    return (
      <div className="sf-card p-4" style={{ borderColor: 'rgba(239,68,68,0.2)' }}>
        <p className="text-sm" style={{ color: '#ef4444' }}>Erro ao carregar: {erro}</p>
      </div>
    )
  }

  if (!dados) return null

  const metricas = [
    { label: 'Squads', valor: dados.total_squads, Icon: Users, cor: '#10b981', desc: 'Registrados' },
    { label: 'Aprovacoes', valor: dados.aprovacoes_pendentes, Icon: ShieldCheck, cor: dados.aprovacoes_pendentes > 0 ? '#f59e0b' : '#10b981', desc: 'Pendentes' },
    { label: 'Vaults RAG', valor: dados.total_vaults, Icon: BookOpen, cor: '#3b82f6', desc: 'Bases de conhecimento' },
    { label: 'PM Central', valor: 'Ativo', Icon: Bot, cor: '#8b5cf6', desc: 'Alex — Orquestrador' },
  ]

  return (
    <div className="sf-animate">
      {/* Header */}
      <div className="mb-8">
        <h1 className="sf-h1">Painel Geral</h1>
        <p className="sf-caption mt-1">{dados.data_hora} · {dados.ambiente}</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {metricas.map(m => (
          <div key={m.label} className="sf-card sf-card-interactive p-5">
            <div className="flex items-center justify-between mb-4">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${m.cor}12` }}
              >
                <m.Icon size={16} strokeWidth={1.8} style={{ color: m.cor }} />
              </div>
              <ArrowUpRight size={14} style={{ color: 'var(--sf-text-4)' }} />
            </div>
            <p className="text-2xl font-semibold sf-mono" style={{ color: 'var(--sf-text-0)' }}>{m.valor}</p>
            <p className="sf-caption mt-1">{m.label} · {m.desc}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-6">
        {/* Lideranca */}
        <div className="sf-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Crown size={14} strokeWidth={1.8} style={{ color: 'var(--sf-text-3)' }} />
            <h2 className="sf-h3">Lideranca</h2>
          </div>
          <div className="space-y-2">
            {dados.lideranca.map((u: any) => (
              <div
                key={u.id}
                className="flex items-center gap-3 p-3 rounded-lg transition-colors"
                style={{ background: 'var(--sf-bg-hover)' }}
              >
                <div
                  className="w-8 h-8 rounded-md flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0"
                  style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
                >
                  {u.nome[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>{u.nome}</p>
                  <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>{u.cargo}</p>
                </div>
                {u.pode_aprovar && (
                  <span className="sf-badge" style={{ background: 'rgba(245,158,11,0.1)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.15)' }}>
                    Aprovador
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* RAG Vaults */}
        <div className="sf-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen size={14} strokeWidth={1.8} style={{ color: 'var(--sf-text-3)' }} />
            <h2 className="sf-h3">Vaults RAG</h2>
          </div>
          <div className="space-y-2">
            {dados.rag_vaults.map((v: any) => (
              <div
                key={v.nome}
                className="flex items-center gap-3 p-3 rounded-lg"
                style={{ background: 'var(--sf-bg-hover)' }}
              >
                <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ background: 'rgba(59,130,246,0.1)' }}>
                  <BookOpen size={14} strokeWidth={1.8} style={{ color: '#3b82f6' }} />
                </div>
                <div className="min-w-0">
                  <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>{v.nome}</p>
                  <p className="text-[11px] sf-mono truncate" style={{ color: 'var(--sf-text-3)' }}>{v.caminho}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Squads */}
      <div className="sf-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Users size={14} strokeWidth={1.8} style={{ color: 'var(--sf-text-3)' }} />
          <h2 className="sf-h3">Squads</h2>
        </div>
        <div className="space-y-1">
          {dados.squads.map((s: any) => (
            <div
              key={s.nome}
              className="flex items-center justify-between py-3 px-3 rounded-lg transition-colors"
              style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
            >
              <div>
                <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>{s.nome}</p>
                <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>{s.especialidade}</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-[13px] sf-mono" style={{ color: 'var(--sf-text-1)' }}>{s.num_agentes}</p>
                  <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>agentes</p>
                </div>
                <div className="sf-dot sf-dot-green" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
