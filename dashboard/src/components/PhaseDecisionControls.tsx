/* PhaseDecisionControls — v0.58.3
 *
 * Painel de controles de decisao em tempo real durante cada fase do BMAD.
 * Recebe estado via props (NAO tem polling proprio — polling fica no pai).
 * Exibe 4 botoes: Aprovar, Revisar, Regenerar, Rejeitar.
 *
 * v0.58.3 — Corrige polling redundante que causava re-render loop
 */

import { useState, useCallback } from 'react'
import {
  CheckCircle2, Eye, RotateCcw, XCircle,
  Loader2, Bot, Pause,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

interface PhaseDecisionControlsProps {
  token: string
  sessaoId: string
  fase: number  // fase atual (1-5)
  faseLabel: string
  progresso: number
  agenteNome?: string
  onRevisar?: (fase: number) => void  // abre detalhamento
  onDecisao?: (fase: number, acao: string) => void  // callback para o pai executar a acao
}

type AcaoDecisao = 'aprovar' | 'revisar' | 'regenerar' | 'rejeitar'

export default function PhaseDecisionControls({
  token,
  sessaoId,
  fase,
  faseLabel,
  progresso,
  agenteNome = 'Agente',
  onRevisar,
  onDecisao,
}: PhaseDecisionControlsProps) {
  const [loading, setLoading] = useState<AcaoDecisao | null>(null)
  const [toast, setToast] = useState<{ tipo: 'success' | 'error' | 'info'; mensagem: string } | null>(null)

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  const showToast = useCallback((tipo: 'success' | 'error' | 'info', mensagem: string) => {
    setToast({ tipo, mensagem })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const handleDecisao = async (acao: AcaoDecisao) => {
    if (acao === 'revisar') {
      onRevisar?.(fase)
      return
    }

    if (onDecisao) {
      onDecisao(fase, acao)
      return
    }

    // Fallback: chamada direta se callback nao fornecido
    setLoading(acao)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/fase-decisao`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ fase, acao }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Erro ao enviar decisao')

      const labels: Record<string, string> = {
        aprovar: 'Aprovado — proseguindo',
        regenerar: 'Regenerando fase',
        rejeitar: 'Rejeitado — encerrando',
      }
      showToast('success', `Fase ${fase}: ${labels[acao] || acao}`)
    } catch (e) {
      showToast('error', `Erro: ${String(e)}`)
    } finally {
      setLoading(null)
    }
  }

  const faseNomes: Record<number, string> = {
    1: 'Planejamento',
    2: 'Discussao',
    3: 'Execucao',
    4: 'Review QA',
    5: 'Conclusao',
  }

  const botoes = [
    {
      id: 'aprovar' as AcaoDecisao,
      titulo: 'Aprovar',
      descricao: 'Prosseguir para proxima fase',
      icone: <CheckCircle2 className="w-5 h-5" />,
      cor: 'from-emerald-500 to-emerald-600',
      hoverCor: 'hover:from-emerald-600 hover:to-emerald-700',
    },
    {
      id: 'revisar' as AcaoDecisao,
      titulo: 'Revisar',
      descricao: 'Pausar e ver detalhamento',
      icone: <Eye className="w-5 h-5" />,
      cor: 'from-blue-500 to-blue-600',
      hoverCor: 'hover:from-blue-600 hover:to-blue-700',
    },
    {
      id: 'regenerar' as AcaoDecisao,
      titulo: 'Regenerar',
      descricao: 'Refazer esta fase',
      icone: <RotateCcw className="w-5 h-5" />,
      cor: 'from-amber-500 to-amber-600',
      hoverCor: 'hover:from-amber-600 hover:to-amber-700',
    },
    {
      id: 'rejeitar' as AcaoDecisao,
      titulo: 'Rejeitar',
      descricao: 'Cancelar e voltar',
      icone: <XCircle className="w-5 h-5" />,
      cor: 'from-red-500 to-red-600',
      hoverCor: 'hover:from-red-600 hover:to-red-700',
    },
  ]

  return (
    <div className="flex flex-col items-center gap-4 p-4 h-full">
      {/* Toast */}
      {toast && (
        <div className={`
          fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg max-w-sm
          ${toast.tipo === 'success' ? 'bg-emerald-500/90 text-white' :
            toast.tipo === 'error' ? 'bg-red-500/90 text-white' :
            'bg-blue-500/90 text-white'}
        `}>
          {toast.tipo === 'success' && <CheckCircle2 className="w-5 h-5 flex-shrink-0" />}
          {toast.tipo === 'error' && <XCircle className="w-5 h-5 flex-shrink-0" />}
          <span className="text-sm font-medium">{toast.mensagem}</span>
        </div>
      )}

      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Pause className="w-6 h-6" style={{ color: '#fbbf24' }} />
          <h3 className="text-lg font-bold" style={{ color: 'var(--sf-text)' }}>
            Fase {fase}/5 — Decisao Necessaria
          </h3>
        </div>
        <div className="flex items-center gap-2 justify-center">
          <Bot className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
          <span className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>
            {agenteNome}: {faseNomes[fase] || faseLabel}
          </span>
        </div>
        <div className="mt-2 h-2 rounded-full overflow-hidden" style={{ background: 'var(--sf-bg)', maxWidth: '300px', margin: '0 auto' }}>
          <div className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progresso}%`,
              background: 'linear-gradient(90deg, #10b981, #34d399)',
              boxShadow: '0 0 12px rgba(16,185,129,0.5)',
            }} />
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--sf-text-secondary)' }}>
          {progresso}% completo
        </p>
      </div>

      {/* Setas de progresso das fases */}
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map(f => (
          <div key={f} className="flex items-center gap-1">
            <div className={`
              w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
              ${f < fase ? 'bg-emerald-500/30 text-emerald-400' :
                f === fase ? 'bg-amber-500/30 text-amber-400 ring-2 ring-amber-500/50' :
                'bg-gray-500/20 text-gray-500'}
            `}>
              {f < fase ? <CheckCircle2 className="w-4 h-4" /> : f}
            </div>
            {f < 5 && (
              <div className={`w-6 h-0.5 ${f < fase ? 'bg-emerald-500/40' : 'bg-gray-500/20'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Botoes de decisao */}
      <div className="grid grid-cols-2 gap-3 w-full max-w-md">
        {botoes.map(botao => (
          <button
            key={botao.id}
            onClick={() => handleDecisao(botao.id)}
            disabled={loading !== null}
            className={`
              relative flex items-start gap-3 p-3 rounded-xl text-left transition-all
              bg-gradient-to-br ${botao.cor}
              ${loading === null ? botao.hoverCor + ' hover:scale-[1.02]' : 'opacity-50 cursor-not-allowed'}
            `}
            style={{ boxShadow: loading === null ? '0 4px 20px rgba(0,0,0,0.3)' : 'none' }}
          >
            <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-white/20">
              {loading === botao.id ? (
                <Loader2 className="w-5 h-5 animate-spin text-white" />
              ) : (
                <span className="text-white">{botao.icone}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <span className="font-bold text-white text-sm">{botao.titulo}</span>
              <p className="text-xs text-white/70 mt-0.5">{botao.descricao}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Indicador de "aguarde" */}
      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
        <Loader2 className="w-3 h-3 animate-spin" style={{ color: '#fbbf24' }} />
        <span>Aguardando sua decisao...</span>
      </div>
    </div>
  )
}
