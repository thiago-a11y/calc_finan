/* Command Center — Centro de Comando da Fabrica */

import { useState, useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import AutonomoPanel from '../components/AutonomoPanel'
import {
  Zap, Loader2, Check, Clock, Pause,
  Send, ChevronRight, XCircle, Building2, Target,
  TrendingUp, DollarSign, Activity,
} from 'lucide-react'

interface WorkflowAtivo {
  id: string; titulo: string; fase_atual: number; fase_nome: string
  status: string; squad_nome: string; criado_em: string
  tarefa_atual: { agente_atual: string; status: string } | null
}

interface CommandCenterData {
  workflows_ativos: WorkflowAtivo[]
  historico: { id: string; titulo: string; status: string; fase_atual: number; criado_em: string }[]
  total_ativos: number
  tarefas_ativas: number
  custo_hoje_usd: number
  custo_total_usd: number
}

const FASES = ['Analise', 'Planejamento', 'Solucao', 'Implementacao']

export default function CommandCenter() {
  const { token } = useAuth()
  const [visao, setVisao] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<{ features: any[]; workflows: any[] } | null>(null)
  const [workflowAberto, setWorkflowAberto] = useState<string | null>(null)

  const fetcher = useCallback(async () => {
    const res = await fetch('/api/tarefas/command-center', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Erro')
    return res.json() as Promise<CommandCenterData>
  }, [token])

  const { dados, carregando } = usePolling(fetcher, 5000)

  const enviarEstrategia = async () => {
    if (!visao.trim() || enviando) return
    setEnviando(true)
    setResultado(null)
    try {
      const res = await fetch('/api/tarefas/command-center/estrategia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ visao: visao.trim(), squad_nome: 'CEO — Thiago', projeto_id: 0 }),
      })
      if (!res.ok) throw new Error('Erro')
      const data = await res.json()
      setResultado(data)
      setVisao('')
    } catch { /* silencioso */ }
    finally { setEnviando(false) }
  }

  return (
    <div className="sf-page">
      <div className="fixed top-0 right-1/4 w-[500px] h-[300px] bg-purple-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.2)' }}>
            <Target size={20} style={{ color: '#a855f7' }} />
          </div>
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-300 to-purple-500 bg-clip-text text-transparent">
              Command Center
            </h2>
            <p className="text-sm sf-text-dim">Centro de Comando da Fabrica — Visao e controle total</p>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="sf-glass border sf-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={14} style={{ color: '#a855f7' }} />
            <span className="text-[10px] sf-text-ghost uppercase tracking-wider">Squads Ativos</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#a855f7' }}>{dados?.total_ativos || 0}</p>
        </div>
        <div className="sf-glass border sf-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={14} style={{ color: '#10b981' }} />
            <span className="text-[10px] sf-text-ghost uppercase tracking-wider">Tarefas Ativas</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#10b981' }}>{dados?.tarefas_ativas || 0}</p>
        </div>
        <div className="sf-glass border sf-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={14} style={{ color: '#f59e0b' }} />
            <span className="text-[10px] sf-text-ghost uppercase tracking-wider">Custo Hoje</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#f59e0b' }}>${dados?.custo_hoje_usd?.toFixed(2) || '0.00'}</p>
        </div>
        <div className="sf-glass border sf-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} style={{ color: '#3b82f6' }} />
            <span className="text-[10px] sf-text-ghost uppercase tracking-wider">Custo Total</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#3b82f6' }}>${dados?.custo_total_usd?.toFixed(2) || '0.00'}</p>
        </div>
      </div>

      {/* Comando Estrategico */}
      <div className="sf-glass border sf-border rounded-2xl p-5 mb-6" style={{ borderColor: 'rgba(168,85,247,0.15)' }}>
        <div className="flex items-center gap-2 mb-3">
          <Building2 size={16} style={{ color: '#a855f7' }} />
          <h3 className="text-sm font-bold sf-text-white">Comando Estrategico</h3>
          <span className="text-[9px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(168,85,247,0.1)', color: '#a855f7' }}>CEO</span>
        </div>
        <p className="text-[11px] sf-text-dim mb-3">
          Descreva sua visao e o PM Central (Alex) vai quebrar em features e distribuir para os squads.
        </p>
        <div className="flex gap-2">
          <input
            value={visao}
            onChange={e => setVisao(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && enviarEstrategia()}
            placeholder="Ex: Lancar PlaniFactory completo em 30 dias com auth, dashboard e integracoes"
            className="flex-1 px-4 py-2.5 rounded-xl text-sm sf-glass border sf-border sf-text-white"
            style={{ background: 'var(--sf-bg-2)' }}
          />
          <button onClick={enviarEstrategia} disabled={!visao.trim() || enviando}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: '#a855f7', color: '#fff' }}>
            {enviando ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {enviando ? 'Processando...' : 'Executar'}
          </button>
        </div>

        {/* Resultado da estrategia */}
        {resultado && (
          <div className="mt-4 p-3 rounded-xl" style={{ background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.15)' }}>
            <p className="text-[11px] font-semibold mb-2" style={{ color: '#10b981' }}>
              <Check size={12} className="inline mr-1" />{resultado.workflows.length} squads criados ({resultado.features.length} features)
            </p>
            {resultado.features.map((f: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[10px] py-1">
                <ChevronRight size={10} style={{ color: '#10b981' }} />
                <span style={{ color: 'var(--sf-text-1)' }}>{f.titulo}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Squads Ativos */}
      <div className="mb-6">
        <h3 className="text-sm font-bold sf-text-white mb-3 flex items-center gap-2">
          <Activity size={14} style={{ color: '#a855f7' }} /> Squads Autonomos Ativos
        </h3>
        {(!dados?.workflows_ativos || dados.workflows_ativos.length === 0) && !carregando && (
          <div className="sf-glass border sf-border rounded-xl p-8 text-center">
            <Zap size={28} className="mx-auto mb-2" style={{ color: 'var(--sf-text-3)', opacity: 0.3 }} />
            <p className="text-[13px] sf-text-dim">Nenhum squad autonomo ativo</p>
            <p className="text-[11px] sf-text-ghost mt-1">Use o Comando Estrategico acima ou o Modo Autonomo no Escritorio Virtual</p>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {dados?.workflows_ativos?.map(wf => (
            <div key={wf.id} className="sf-glass border rounded-xl p-4 cursor-pointer transition-all hover:border-purple-500/30 group"
              style={{ borderColor: wf.status === 'aguardando_gate' ? 'rgba(245,158,11,0.3)' : 'var(--sf-border-default)' }}
              onClick={() => setWorkflowAberto(wf.id)}>

              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-[13px] font-bold sf-text-white truncate flex-1">{wf.titulo}</h4>
                <span className="text-[9px] px-2 py-0.5 rounded-full flex-shrink-0 ml-2" style={{
                  background: wf.status === 'em_execucao' ? 'rgba(168,85,247,0.1)' : wf.status === 'aguardando_gate' ? 'rgba(245,158,11,0.1)' : 'rgba(255,255,255,0.05)',
                  color: wf.status === 'em_execucao' ? '#a855f7' : wf.status === 'aguardando_gate' ? '#f59e0b' : 'var(--sf-text-3)',
                }}>
                  {wf.status === 'em_execucao' ? 'Executando' : wf.status === 'aguardando_gate' ? 'Aguardando Gate' : wf.status}
                </span>
              </div>

              {/* Barra de progresso das fases */}
              <div className="flex items-center gap-1 mb-3">
                {FASES.map((_nome, i) => {
                  const num = i + 1
                  const concluida = num < wf.fase_atual
                  const atual = num === wf.fase_atual
                  return (
                    <div key={i} className="flex items-center flex-1">
                      <div className={`h-1.5 flex-1 rounded-full ${atual ? 'animate-pulse' : ''}`}
                        style={{
                          background: concluida ? '#10b981' : atual ? '#a855f7' : 'var(--sf-border-subtle)',
                        }} />
                    </div>
                  )
                })}
              </div>

              {/* Info */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] sf-text-dim">
                  Fase {wf.fase_atual}: {wf.fase_nome}
                </span>
                {wf.tarefa_atual?.agente_atual && (
                  <span className="text-[9px]" style={{ color: '#a855f7' }}>
                    {wf.tarefa_atual.agente_atual}
                  </span>
                )}
              </div>

              {/* Botao de intervencao rapida */}
              {wf.status === 'aguardando_gate' && (
                <button
                  onClick={e => { e.stopPropagation(); setWorkflowAberto(wf.id) }}
                  className="w-full mt-3 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all hover:brightness-110"
                  style={{ background: '#f59e0b', color: '#fff' }}>
                  Aprovar Gate
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Historico */}
      {dados?.historico && dados.historico.length > 0 && (
        <div>
          <h3 className="text-sm font-bold sf-text-white mb-3 flex items-center gap-2">
            <Clock size={14} style={{ color: 'var(--sf-text-3)' }} /> Historico Recente
          </h3>
          <div className="space-y-1">
            {dados.historico.map(wf => (
              <div key={wf.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/3 cursor-pointer"
                onClick={() => setWorkflowAberto(wf.id)}>
                {wf.status === 'concluido' ? <Check size={12} style={{ color: '#10b981' }} /> :
                 wf.status === 'erro' ? <XCircle size={12} style={{ color: '#ef4444' }} /> :
                 <Pause size={12} style={{ color: 'var(--sf-text-3)' }} />}
                <span className="text-[11px] sf-text-white flex-1 truncate">{wf.titulo}</span>
                <span className="text-[9px] sf-text-ghost">
                  {new Date(wf.criado_em).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Painel do workflow aberto */}
      {workflowAberto && (
        <AutonomoPanel workflowId={workflowAberto} onFechar={() => setWorkflowAberto(null)} />
      )}
    </div>
  )
}
