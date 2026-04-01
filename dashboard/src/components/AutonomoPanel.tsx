/* AutonomoPanel — Painel de progresso do Workflow Autonomo BMAD */

import { useState, useEffect, useCallback } from 'react'
import { Zap, Loader2, Check, X, AlertCircle, ChevronDown, ChevronRight, Clock, Pause, RefreshCw } from 'lucide-react'
import { buscarAutonomo, aprovarGate, cancelarAutonomo, reiniciarAutonomo, type WorkflowAutonomo } from '../services/api'

interface Props {
  workflowId: string
  onFechar: () => void
}

const FASES = [
  { num: 1, nome: 'Analise', icone: '🔍' },
  { num: 2, nome: 'Planejamento', icone: '📋' },
  { num: 3, nome: 'Solucao', icone: '🏗️' },
  { num: 4, nome: 'Implementacao', icone: '⚡' },
]

function tempoRelativo(dataStr: string): string {
  if (!dataStr) return ''
  const diff = Date.now() - new Date(dataStr).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return 'agora'
  if (min < 60) return `${min}min`
  return `${Math.floor(min / 60)}h${min % 60}min`
}

export default function AutonomoPanel({ workflowId, onFechar }: Props) {
  const [workflow, setWorkflow] = useState<WorkflowAutonomo | null>(null)
  const [erro, setErro] = useState('')
  const [feedback, setFeedback] = useState('')
  const [aprovando, setAprovando] = useState(false)
  const [faseExpandida, setFaseExpandida] = useState<number | null>(null)

  // Polling a cada 3s
  const atualizar = useCallback(async () => {
    try {
      const wf = await buscarAutonomo(workflowId)
      setWorkflow(wf)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao buscar workflow')
    }
  }, [workflowId])

  useEffect(() => {
    atualizar()
    const intervalo = setInterval(atualizar, 3000)
    return () => clearInterval(intervalo)
  }, [atualizar])

  const handleAprovar = async (decisao: string) => {
    setAprovando(true)
    try {
      await aprovarGate(workflowId, decisao, feedback)
      setFeedback('')
      atualizar()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro')
    } finally {
      setAprovando(false)
    }
  }

  const handleCancelar = async () => {
    if (!confirm('Cancelar workflow autonomo?')) return
    try {
      await cancelarAutonomo(workflowId)
      atualizar()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro')
    }
  }

  if (!workflow) {
    return (
      <div className="fixed bottom-4 right-4 z-40 w-96 rounded-2xl shadow-2xl p-4"
        style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>
        <div className="flex items-center gap-2">
          <Loader2 size={16} className="animate-spin" style={{ color: '#a855f7' }} />
          <span className="text-[12px]" style={{ color: 'var(--sf-text-2)' }}>Carregando workflow...</span>
        </div>
      </div>
    )
  }

  const ehAtivo = ['em_execucao', 'aguardando_gate', 'montando_time'].includes(workflow.status)

  return (
    <div className="fixed bottom-4 right-4 z-40 w-[420px] max-h-[70vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      style={{ background: 'var(--sf-bg-1)', border: '1px solid rgba(168,85,247,0.2)', boxShadow: '0 8px 40px rgba(168,85,247,0.1)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)', background: 'rgba(168,85,247,0.05)' }}>
        <div className="flex items-center gap-2">
          <Zap size={16} style={{ color: '#a855f7' }} />
          <div>
            <h3 className="text-[13px] font-bold" style={{ color: 'var(--sf-text-0)' }}>Modo Autonomo</h3>
            <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
              {workflow.titulo.slice(0, 40)}{workflow.titulo.length > 40 ? '...' : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {ehAtivo && (
            <button onClick={handleCancelar} className="p-1.5 rounded hover:bg-red-500/10" style={{ color: '#ef4444' }} title="Cancelar">
              <Pause size={12} />
            </button>
          )}
          <button onClick={onFechar} className="p-1.5 rounded hover:bg-white/5" style={{ color: 'var(--sf-text-3)' }}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Barra de progresso das 4 fases */}
      <div className="flex items-center px-4 py-3 gap-1" style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
        {FASES.map((f, i) => {
          const gate = workflow.gates[`fase_${f.num}`]
          const ehAtual = workflow.fase_atual === f.num && ehAtivo
          const concluida = gate?.status === 'aprovado' || gate?.status === 'auto_pass' || gate?.status === 'pulado' || f.num < workflow.fase_atual
          const aguardando = workflow.status === 'aguardando_gate' && workflow.fase_atual === f.num

          return (
            <div key={f.num} className="flex items-center flex-1">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full text-[12px] font-bold transition-all ${ehAtual ? 'animate-pulse' : ''}`}
                style={{
                  background: concluida ? 'rgba(16,185,129,0.15)' : aguardando ? 'rgba(245,158,11,0.15)' : ehAtual ? 'rgba(168,85,247,0.15)' : 'rgba(255,255,255,0.03)',
                  color: concluida ? '#10b981' : aguardando ? '#f59e0b' : ehAtual ? '#a855f7' : 'var(--sf-text-3)',
                  border: `2px solid ${concluida ? '#10b98140' : aguardando ? '#f59e0b40' : ehAtual ? '#a855f740' : 'transparent'}`,
                }}
                title={f.nome}
              >
                {concluida ? <Check size={14} /> : f.icone}
              </div>
              {i < 3 && (
                <div className="flex-1 h-0.5 mx-1 rounded" style={{
                  background: concluida ? '#10b981' : 'var(--sf-border-subtle)',
                }} />
              )}
            </div>
          )
        })}
      </div>

      {/* Status atual */}
      <div className="px-4 py-2" style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <div className="flex items-center gap-2">
          {workflow.status === 'em_execucao' && <Loader2 size={12} className="animate-spin" style={{ color: '#a855f7' }} />}
          {workflow.status === 'aguardando_gate' && <AlertCircle size={12} style={{ color: '#f59e0b' }} />}
          {workflow.status === 'concluido' && <Check size={12} style={{ color: '#10b981' }} />}
          {workflow.status === 'erro' && <AlertCircle size={12} style={{ color: '#ef4444' }} />}
          <span className="text-[11px] font-medium" style={{
            color: workflow.status === 'em_execucao' ? '#a855f7' :
                   workflow.status === 'aguardando_gate' ? '#f59e0b' :
                   workflow.status === 'concluido' ? '#10b981' : '#ef4444'
          }}>
            {workflow.status === 'em_execucao' && `Fase ${workflow.fase_atual}: ${workflow.fase_nome} em andamento...`}
            {workflow.status === 'aguardando_gate' && `Fase ${workflow.fase_atual}: Aguardando sua aprovacao`}
            {workflow.status === 'concluido' && 'Workflow concluido com sucesso!'}
            {workflow.status === 'erro' && 'Erro no workflow'}
            {workflow.status === 'cancelado' && 'Workflow cancelado'}
          </span>
          <span className="ml-auto text-[9px]" style={{ color: 'var(--sf-text-3)' }}>
            <Clock size={8} className="inline mr-0.5" />{tempoRelativo(workflow.criado_em)}
          </span>
        </div>

        {/* Agente atual trabalhando */}
        {workflow.tarefa_atual?.agente_atual && workflow.status === 'em_execucao' && (
          <p className="text-[10px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
            {workflow.tarefa_atual.agente_atual}
          </p>
        )}
      </div>

      {/* Conteudo scrollavel */}
      <div className="flex-1 overflow-auto px-4 py-3 space-y-2" style={{ scrollbarWidth: 'thin', maxHeight: '40vh' }}>
        {/* Outputs das fases */}
        {FASES.map(f => {
          const output = workflow.outputs[`fase_${f.num}`]
          if (!output) return null
          const expandida = faseExpandida === f.num
          return (
            <div key={f.num} className="rounded-lg overflow-hidden"
              style={{ border: '1px solid var(--sf-border-subtle)' }}>
              <button onClick={() => setFaseExpandida(expandida ? null : f.num)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/3"
                style={{ background: 'rgba(255,255,255,0.02)' }}>
                {expandida ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span className="text-[11px] font-medium" style={{ color: 'var(--sf-text-1)' }}>
                  {f.icone} Fase {f.num}: {f.nome}
                </span>
                <Check size={10} className="ml-auto" style={{ color: '#10b981' }} />
              </button>
              {expandida && (
                <div className="px-3 py-2 text-[10px] whitespace-pre-wrap max-h-48 overflow-auto"
                  style={{ color: 'var(--sf-text-2)', borderTop: '1px solid var(--sf-border-subtle)', scrollbarWidth: 'thin' }}>
                  {output.slice(0, 2000)}{output.length > 2000 ? '\n\n[... truncado ...]' : ''}
                </div>
              )}
            </div>
          )
        })}

        {/* Erro */}
        {(erro || workflow.outputs?.erro) && (
          <div className="px-3 py-2 rounded-lg text-[10px]"
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}>
            {erro || workflow.outputs.erro}
          </div>
        )}
      </div>

      {/* Footer — Aprovacao do gate */}
      {workflow.status === 'aguardando_gate' && (
        <div className="px-4 py-3" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
          <p className="text-[10px] font-semibold mb-2" style={{ color: '#f59e0b' }}>
            Gate da Fase {workflow.fase_atual} — Aprovacao necessaria
          </p>
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="Feedback opcional (ajustes, correcoes...)"
            rows={2}
            className="w-full px-3 py-1.5 rounded-lg text-[10px] resize-none mb-2"
            style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-1)' }}
          />
          <div className="flex items-center gap-2">
            <button onClick={() => handleAprovar('rejeitar')} disabled={aprovando}
              className="flex-1 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all disabled:opacity-40"
              style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.15)' }}>
              Refazer
            </button>
            <button onClick={() => handleAprovar('aprovar')} disabled={aprovando}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all hover:brightness-110 disabled:opacity-40"
              style={{ background: '#10b981', color: '#fff' }}>
              {aprovando ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
              Aprovar e Continuar
            </button>
          </div>
        </div>
      )}

      {/* Footer — Concluido */}
      {workflow.status === 'concluido' && (
        <div className="px-4 py-3 text-center" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
          <button onClick={onFechar}
            className="px-4 py-1.5 rounded-lg text-[11px] font-medium"
            style={{ background: 'var(--sf-accent)', color: '#fff' }}>
            Fechar
          </button>
        </div>
      )}

      {/* Footer — Erro: mostrar causa + botão reiniciar */}
      {workflow.status === 'erro' && (
        <div className="px-4 py-3" style={{ borderTop: '1px solid rgba(239,68,68,0.3)' }}>
          {workflow.outputs?.erro && (
            <div className="mb-3 px-3 py-2 rounded-lg text-[10px] font-mono overflow-auto max-h-28"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#fca5a5' }}>
              <span className="font-bold text-red-400 block mb-1">Causa do erro:</span>
              {workflow.outputs.erro}
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={async () => {
              try { await reiniciarAutonomo(workflow.id); atualizar() }
              catch (e) { setErro(e instanceof Error ? e.message : 'Erro ao reiniciar') }
            }}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all hover:brightness-110"
              style={{ background: '#f59e0b', color: '#000' }}>
              <RefreshCw size={11} />
              Reiniciar da Fase {workflow.fase_atual}
            </button>
            <button onClick={onFechar}
              className="px-3 py-1.5 rounded-lg text-[11px]"
              style={{ background: 'var(--sf-bg-2)', color: 'var(--sf-text-2)', border: '1px solid var(--sf-border-subtle)' }}>
              Fechar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
