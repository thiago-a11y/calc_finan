/* Relatórios — Histórico premium dark-mode (zero emojis) */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarHistoricoTarefas, continuarReuniao, reabrirReuniao, encerrarReuniao } from '../services/api'
import type { TarefaResultado } from '../types'
import {
  CheckCircle2, XCircle, Clock, Loader2, Hand, MessageSquare,
  Users, Bot, ChevronDown, ChevronUp, Pin, User2, RefreshCw,
  Timer, Hash, Send, RotateCcw, Square, FileText, ListFilter,
} from 'lucide-react'

const statusConfig: Record<string, { icon: typeof CheckCircle2; cor: string; label: string; bg: string }> = {
  pendente: { icon: Clock, cor: '#f59e0b', label: 'Pendente', bg: 'rgba(245,158,11,0.1)' },
  executando: { icon: Loader2, cor: '#3b82f6', label: 'Executando', bg: 'rgba(59,130,246,0.1)' },
  concluida: { icon: CheckCircle2, cor: '#10b981', label: 'Concluída', bg: 'rgba(16,185,129,0.1)' },
  aguardando_feedback: { icon: Hand, cor: '#f97316', label: 'Sua vez!', bg: 'rgba(249,115,22,0.1)' },
  erro: { icon: XCircle, cor: '#ef4444', label: 'Erro', bg: 'rgba(239,68,68,0.1)' },
}

export default function Relatorios() {
  const fetcher = useCallback(() => buscarHistoricoTarefas(50), [])
  const { dados, erro, carregando, recarregar } = usePolling(fetcher, 5000)
  const [expandido, setExpandido] = useState<string | null>(null)
  const [filtro, setFiltro] = useState<'todos' | 'tarefa' | 'reuniao'>('todos')
  const [feedback, setFeedback] = useState<Record<string, string>>({})
  const [enviando, setEnviando] = useState<string | null>(null)

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (erro) {
    return <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">Erro: {erro}</div>
  }

  const tarefas = ((dados || []) as TarefaResultado[]).filter(
    t => filtro === 'todos' || t.tipo === filtro
  )

  const handleContinuar = async (id: string) => {
    const fb = feedback[id]?.trim()
    if (!fb) return
    setEnviando(id)
    try { await continuarReuniao(id, fb); setFeedback(prev => ({ ...prev, [id]: '' })); recarregar() }
    catch {} finally { setEnviando(null) }
  }

  const handleReabrir = async (id: string) => {
    setEnviando(id)
    try { await reabrirReuniao(id); recarregar() } catch {} finally { setEnviando(null) }
  }

  const handleEncerrar = async (id: string) => {
    setEnviando(id)
    try { await encerrarReuniao(id); recarregar() } catch {} finally { setEnviando(null) }
  }

  const filtros: { id: typeof filtro; label: string; icon: typeof ListFilter }[] = [
    { id: 'todos', label: 'Todos', icon: ListFilter },
    { id: 'tarefa', label: 'Tarefas', icon: MessageSquare },
    { id: 'reuniao', label: 'Reuniões', icon: Users },
  ]

  return (
    <div className="sf-page">
      <div className="fixed top-0 right-1/3 w-[500px] h-[300px] bg-orange-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Relatórios
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            {tarefas.length} execução(ões) registrada(s)
          </p>
        </div>
        <div className="flex gap-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-1">
          {filtros.map(f => {
            const Icon = f.icon
            return (
              <button
                key={f.id}
                onClick={() => setFiltro(f.id)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-300 ${
                  filtro === f.id
                    ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                    : 'sf-text-dim hover:text-gray-300 hover:bg-white/5'
                }`}
              >
                <Icon size={13} strokeWidth={2} />
                {f.label}
              </button>
            )
          })}
        </div>
      </div>

      {tarefas.length === 0 && (
        <div className="text-center py-16">
          <FileText size={40} className="sf-text-faint mx-auto mb-4" strokeWidth={1.5} />
          <p className="text-sm sf-text-dim">Nenhum relatório ainda.</p>
          <p className="text-xs sf-text-ghost mt-1">Envie tarefas para os agentes na página Squads.</p>
        </div>
      )}

      <div className="space-y-3">
        {tarefas.map(tarefa => {
          const isExpandido = expandido === tarefa.id
          const isReuniao = tarefa.tipo === 'reuniao'
          const status = statusConfig[tarefa.status] || statusConfig.pendente
          const StatusIcon = status.icon
          const isUrgent = tarefa.status === 'aguardando_feedback'

          return (
            <div
              key={tarefa.id}
              className={`group sf-glass backdrop-blur-sm border rounded-xl overflow-hidden transition-all duration-300 hover:-translate-y-0.5 ${
                isUrgent ? 'border-orange-500/30 ring-1 ring-orange-500/10' :
                isReuniao ? 'border-purple-500/15' : 'sf-border'
              } hover:border-white/15`}
            >
              {/* Header */}
              <div
                className="px-5 py-4 cursor-pointer flex items-center gap-3"
                onClick={() => setExpandido(isExpandido ? null : tarefa.id)}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: isReuniao ? 'rgba(168,85,247,0.1)' : 'rgba(59,130,246,0.1)' }}>
                  {isReuniao
                    ? <Users size={16} className="text-purple-400" strokeWidth={1.8} />
                    : <Bot size={16} className="text-blue-400" strokeWidth={1.8} />
                  }
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium sf-text-white text-sm truncate">
                      {isReuniao ? 'Reunião' : tarefa.agente_nome}
                    </h3>
                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-md border"
                      style={{ backgroundColor: status.bg, borderColor: `${status.cor}30` }}>
                      <StatusIcon size={11} style={{ color: status.cor }}
                        className={tarefa.status === 'executando' ? 'animate-spin' : ''} strokeWidth={2} />
                      <span className="text-[10px] font-medium" style={{ color: status.cor }}>
                        {status.label}
                      </span>
                    </div>
                    {tarefa.status === 'executando' && tarefa.agente_atual && (
                      <span className="text-[10px] text-blue-400 animate-pulse font-mono">
                        {tarefa.agente_atual}
                      </span>
                    )}
                  </div>
                  <p className="text-xs sf-text-dim truncate mt-0.5">{tarefa.descricao}</p>
                </div>

                <div className="text-right shrink-0">
                  <p className="text-[11px] sf-text-dim font-mono">
                    {new Date(tarefa.criado_em).toLocaleDateString('pt-BR')}
                  </p>
                  <p className="text-[11px] sf-text-ghost font-mono">
                    {new Date(tarefa.criado_em).toLocaleTimeString('pt-BR')}
                  </p>
                </div>

                {isExpandido
                  ? <ChevronUp size={14} className="sf-text-ghost shrink-0" />
                  : <ChevronDown size={14} className="sf-text-ghost shrink-0" />
                }
              </div>

              {/* Expandido */}
              {isExpandido && (
                <div className="px-5 pb-5 border-t" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                  {/* Metadados */}
                  <div className="flex flex-wrap gap-4 py-3 text-xs sf-text-dim">
                    <span className="flex items-center gap-1"><Pin size={11} /> Squad: <strong className="sf-text-dim">{tarefa.squad_nome}</strong></span>
                    <span className="flex items-center gap-1"><User2 size={11} /> Por: <strong className="sf-text-dim">{tarefa.usuario_nome}</strong></span>
                    {isReuniao && <span className="flex items-center gap-1"><RefreshCw size={11} /> Rodada: <strong className="sf-text-dim">{tarefa.rodada_atual}</strong></span>}
                    {tarefa.concluido_em && <span className="flex items-center gap-1"><Timer size={11} /> {calcularDuracao(tarefa.criado_em, tarefa.concluido_em)}</span>}
                    <span className="flex items-center gap-1 font-mono"><Hash size={11} /> {tarefa.id.slice(0, 8)}</span>
                  </div>

                  {/* Participantes */}
                  {isReuniao && tarefa.participantes && (
                    <div className="mb-3">
                      <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-1.5">Participantes</p>
                      <div className="flex flex-wrap gap-1.5">
                        {tarefa.participantes.map(p => (
                          <span key={p} className="text-[11px] text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2.5 py-0.5 rounded-md">{p}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Rodadas */}
                  {isReuniao && tarefa.rodadas && tarefa.rodadas.length > 0 && (
                    <div className="mb-3">
                      <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-2">Rodadas</p>
                      <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                        {tarefa.rodadas.map((r: any, i: number) => {
                          const isCeo = r.agente.includes('CEO') || r.agente.includes('Feedback')
                          const isSofia = r.agente.includes('Sofia') || r.agente.includes('ATA')
                          return (
                            <div key={i} className={`rounded-xl p-3 border ${
                              isCeo ? 'bg-emerald-500/5 border-emerald-500/15' :
                              isSofia ? 'bg-purple-500/5 border-purple-500/15' :
                              'sf-glass'
                            }`}>
                              <div className="flex items-center justify-between mb-1.5">
                                <span className={`text-xs font-medium flex items-center gap-1.5 ${
                                  isCeo ? 'text-emerald-400' : isSofia ? 'text-purple-400' : 'sf-text-dim'
                                }`}>
                                  {isCeo ? <User2 size={11} /> : <Bot size={11} />}
                                  {r.agente}
                                </span>
                                <span className="text-[10px] sf-text-ghost font-mono">
                                  R{r.rodada} · {new Date(r.timestamp).toLocaleTimeString('pt-BR')}
                                </span>
                              </div>
                              <p className="text-sm sf-text-dim whitespace-pre-wrap leading-relaxed">{r.resposta}</p>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Resultado tarefa simples */}
                  {!isReuniao && tarefa.status === 'concluida' && tarefa.resultado && (
                    <div className="mb-3">
                      <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-1.5">Resultado</p>
                      <div className="sf-glass border rounded-xl p-4 text-sm sf-text-dim whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                        {tarefa.resultado}
                      </div>
                    </div>
                  )}

                  {/* Executando */}
                  {tarefa.status === 'executando' && (
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 flex items-center gap-2 mb-3">
                      <Loader2 size={14} className="text-blue-400 animate-spin" />
                      <span className="text-sm text-blue-300">{tarefa.agente_atual || 'Processando...'}</span>
                    </div>
                  )}

                  {/* Erro */}
                  {tarefa.status === 'erro' && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-center gap-2 mb-3">
                      <XCircle size={14} className="text-red-400" />
                      <span className="text-sm text-red-300">{tarefa.erro}</span>
                    </div>
                  )}

                  {/* Aguardando feedback */}
                  {tarefa.status === 'aguardando_feedback' && isReuniao && (
                    <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        <Hand size={14} className="text-orange-400" />
                        <p className="text-sm text-orange-300 font-medium">Rodada {tarefa.rodada_atual} concluída — é sua vez!</p>
                      </div>
                      <div className="flex gap-2">
                        <input
                          value={feedback[tarefa.id] || ''}
                          onChange={e => setFeedback(prev => ({ ...prev, [tarefa.id]: e.target.value }))}
                          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleContinuar(tarefa.id)}
                          placeholder="Feedback, direcionamento ou nova pergunta..."
                          disabled={enviando === tarefa.id}
                          className="flex-1 sf-glass border sf-border rounded-lg px-4 py-2.5 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"
                        />
                        <button
                          onClick={() => handleContinuar(tarefa.id)}
                          disabled={enviando === tarefa.id || !(feedback[tarefa.id]?.trim())}
                          className="flex items-center gap-1.5 px-4 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-40 transition-all"
                        >
                          <Send size={13} />
                          {enviando === tarefa.id ? '...' : 'Continuar'}
                        </button>
                      </div>
                      <button
                        onClick={() => handleEncerrar(tarefa.id)}
                        disabled={enviando === tarefa.id}
                        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 sf-glass border sf-text-dim rounded-lg text-xs transition-all" style={{ borderColor: 'var(--sf-border-subtle)' }}
                      >
                        <Square size={11} />
                        Encerrar Reunião
                      </button>
                    </div>
                  )}

                  {/* Reunião concluída → reabrir */}
                  {tarefa.status === 'concluida' && isReuniao && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleReabrir(tarefa.id)}
                        disabled={enviando === tarefa.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg text-sm hover:bg-purple-500/20 disabled:opacity-50 transition-all"
                      >
                        <RotateCcw size={13} />
                        {enviando === tarefa.id ? '...' : 'Reabrir Reunião'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function calcularDuracao(inicio: string, fim: string): string {
  const ms = new Date(fim).getTime() - new Date(inicio).getTime()
  const seg = Math.floor(ms / 1000)
  if (seg < 60) return `${seg}s`
  const min = Math.floor(seg / 60)
  return `${min}min ${seg % 60}s`
}
