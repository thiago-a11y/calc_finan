/* Aprovações — Fila unificada: Aprovações gerais + Edições de código SyneriumX */

import { useState, useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import {
  buscarAprovacoes, acaoAprovacao, criarAprovacao,
  buscarPropostas, aprovarProposta, rejeitarProposta,
  buscarDeploys, aprovarDeploy, rejeitarDeploy,
  buscarSolicitacoesAgente, acaoSolicitacaoAgente,
} from '../services/api'
import {
  ShieldCheck, Plus, X, Clock, CheckCircle2, XCircle,
  Rocket, Zap, Briefcase, Megaphone, Radio, Send,
  History, DollarSign, User2, Code2, FileEdit, Eye,
  Upload, GitBranch, Bot,
} from 'lucide-react'

const tipoIcons: Record<string, { icon: typeof Rocket; cor: string; label: string }> = {
  deploy_producao: { icon: Rocket, cor: '#ef4444', label: 'Deploy Produção' },
  gasto_ia: { icon: Zap, cor: '#f59e0b', label: 'Gasto IA' },
  mudanca_arquitetura: { icon: Briefcase, cor: '#8b5cf6', label: 'Mudança Arquitetura' },
  campanha_marketing: { icon: Megaphone, cor: '#3b82f6', label: 'Campanha Marketing' },
  outreach_massa: { icon: Radio, cor: '#ec4899', label: 'Outreach Massa' },
}

type Aba = 'geral' | 'codigo' | 'deploys' | 'agentes'

export default function Aprovacoes() {
  const [aba, setAba] = useState<Aba>('codigo')
  const fetchAprovacoes = useCallback(() => buscarAprovacoes(), [])
  const fetchPropostas = useCallback(() => buscarPropostas(), [])
  const fetchDeploys = useCallback(() => buscarDeploys(), [])
  const fetchSolicitacoes = useCallback(() => buscarSolicitacoesAgente(), [])
  const { dados: aprovacoes, carregando: cAprov, recarregar: recarregarAprov } = usePolling(fetchAprovacoes, 5000)
  const { dados: propostas, carregando: cProp, recarregar: recarregarProp } = usePolling(fetchPropostas, 5000)
  const { dados: deploys, carregando: cDep, recarregar: recarregarDep } = usePolling(fetchDeploys, 5000)
  const { dados: solicitacoes, carregando: cSol, recarregar: recarregarSol } = usePolling(fetchSolicitacoes, 5000)
  const [processando, setProcessando] = useState<string | number | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [expandido, setExpandido] = useState<string | null>(null)

  const executarAcaoAprov = async (indice: number, aprovado: boolean) => {
    setProcessando(indice)
    try { await acaoAprovacao(indice, aprovado); await recarregarAprov() }
    catch (e) { alert(`Erro: ${e instanceof Error ? e.message : 'desconhecido'}`) }
    finally { setProcessando(null) }
  }

  const executarAcaoProposta = async (id: string, acao: 'aprovar' | 'rejeitar') => {
    setProcessando(id)
    try {
      if (acao === 'aprovar') await aprovarProposta(id)
      else await rejeitarProposta(id)
      await recarregarProp()
    } catch (e) { alert(`Erro: ${e instanceof Error ? e.message : 'desconhecido'}`) }
    finally { setProcessando(null) }
  }

  const enviarSolicitacao = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    try {
      await criarAprovacao({
        tipo: form.get('tipo') as string,
        descricao: form.get('descricao') as string,
        solicitante: form.get('solicitante') as string,
        valor_estimado: form.get('valor') ? Number(form.get('valor')) : undefined,
      })
      setMostrarForm(false); await recarregarAprov()
    } catch (e) { alert(`Erro: ${e instanceof Error ? e.message : 'desconhecido'}`) }
  }

  const executarAcaoDeploy = async (id: string, acao: 'aprovar' | 'rejeitar') => {
    setProcessando(id)
    try {
      if (acao === 'aprovar') await aprovarDeploy(id)
      else await rejeitarDeploy(id)
      await recarregarDep()
    } catch (e) { alert(`Erro: ${e instanceof Error ? e.message : 'desconhecido'}`) }
    finally { setProcessando(null) }
  }

  const executarAcaoSolicitacao = async (id: number, aprovado: boolean) => {
    setProcessando(id)
    try {
      await acaoSolicitacaoAgente(id, aprovado)
      await recarregarSol()
    } catch (e) { alert(`Erro: ${e instanceof Error ? e.message : 'desconhecido'}`) }
    finally { setProcessando(null) }
  }

  const carregando = cAprov || cProp || cDep || cSol
  if (carregando) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" /></div>
  }

  const pendentesAprov = (aprovacoes || []).filter((a: any) => a.aprovado === null)
  const resolvidasAprov = (aprovacoes || []).filter((a: any) => a.aprovado !== null)
  const propostasPendentes = (propostas || []).filter((p: any) => p.status === 'pendente')
  const propostasResolvidas = (propostas || []).filter((p: any) => p.status !== 'pendente')
  const deploysPendentes = (deploys || []).filter((d: any) => d.status === 'pendente')
  const deploysResolvidos = (deploys || []).filter((d: any) => d.status !== 'pendente')
  const solicitacoesPendentes = (solicitacoes || []).filter((s: any) => s.status === 'pendente')
  const solicitacoesResolvidas = (solicitacoes || []).filter((s: any) => s.status !== 'pendente')
  const totalPendentes = pendentesAprov.length + propostasPendentes.length + deploysPendentes.length + solicitacoesPendentes.length

  const inputCls = "w-full sf-glass border sf-border rounded-xl px-4 py-2.5 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"

  return (
    <div className="sf-page">
      <div className="fixed top-0 right-1/3 w-[500px] h-[300px] bg-amber-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Aprovações
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            {totalPendentes} pendente(s) no total
          </p>
        </div>
        {aba === 'geral' && (
          <button
            onClick={() => setMostrarForm(!mostrarForm)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
              mostrarForm
                ? 'bg-white/5 text-gray-400 border border-white/10'
                : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/30'
            }`}
          >
            {mostrarForm ? <><X size={14} /> Cancelar</> : <><Plus size={14} /> Nova Solicitação</>}
          </button>
        )}
      </div>

      {/* Abas */}
      <div className="flex gap-1 sf-glass border sf-border rounded-xl p-1 mb-6 w-fit">
        <button
          onClick={() => setAba('codigo')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            aba === 'codigo'
              ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
              : 'sf-text-dim hover:bg-white/5'
          }`}
        >
          <Code2 size={13} />
          Edições de Código
          {propostasPendentes.length > 0 && (
            <span className="w-5 h-5 bg-orange-500/20 text-orange-400 rounded-full text-[10px] flex items-center justify-center font-bold border border-orange-500/30">
              {propostasPendentes.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setAba('deploys')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            aba === 'deploys'
              ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
              : 'sf-text-dim hover:bg-white/5'
          }`}
        >
          <Upload size={13} />
          Deploys
          {deploysPendentes.length > 0 && (
            <span className="w-5 h-5 bg-red-500/20 text-red-400 rounded-full text-[10px] flex items-center justify-center font-bold border border-red-500/30">
              {deploysPendentes.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setAba('agentes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            aba === 'agentes'
              ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
              : 'sf-text-dim hover:bg-white/5'
          }`}
        >
          <Bot size={13} />
          Agentes
          {solicitacoesPendentes.length > 0 && (
            <span className="w-5 h-5 bg-purple-500/20 text-purple-400 rounded-full text-[10px] flex items-center justify-center font-bold border border-purple-500/30">
              {solicitacoesPendentes.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setAba('geral')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            aba === 'geral'
              ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
              : 'sf-text-dim hover:bg-white/5'
          }`}
        >
          <ShieldCheck size={13} />
          Aprovações Gerais
          {pendentesAprov.length > 0 && (
            <span className="w-5 h-5 bg-orange-500/20 text-orange-400 rounded-full text-[10px] flex items-center justify-center font-bold border border-orange-500/30">
              {pendentesAprov.length}
            </span>
          )}
        </button>
      </div>

      {/* ==================== ABA: EDIÇÕES DE CÓDIGO ==================== */}
      {aba === 'codigo' && (
        <div>
          {/* Pendentes */}
          {propostasPendentes.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-4">
                <Clock size={14} className="text-orange-400" />
                <h3 className="text-sm font-semibold text-orange-400 uppercase tracking-wider">
                  Aguardando sua aprovação
                </h3>
              </div>
              {propostasPendentes.map((p: any) => {
                const isExpand = expandido === p.id
                return (
                  <div key={p.id} className="bg-gradient-to-br from-orange-500/[0.04] to-white/[0.01] border border-orange-500/20 rounded-xl transition-all duration-300 hover:border-orange-500/30">
                    {/* Header da proposta */}
                    <div className="p-5 flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        <div className="w-9 h-9 rounded-lg flex items-center justify-center mt-0.5 bg-orange-500/10 border border-orange-500/20">
                          <FileEdit size={16} className="text-orange-400" strokeWidth={1.8} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              {p.projeto || 'SyneriumX'}
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              {p.acao === 'criar' ? 'Novo arquivo' : 'Edição'}
                            </span>
                            <span className="flex items-center gap-1 text-[10px] text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded-md border border-orange-500/20">
                              <Clock size={9} /> Pendente
                            </span>
                          </div>
                          <p className="font-medium sf-text-white text-sm">{p.descricao}</p>
                          <p className="text-xs sf-text-dim mt-1 font-mono">
                            Arquivo: {p.caminho}
                          </p>
                          <p className="text-[10px] sf-text-ghost mt-1">
                            Criado em {new Date(p.criado_em).toLocaleString('pt-BR')} · por {p.criado_por}
                          </p>
                        </div>
                      </div>

                      {/* Botões de ação */}
                      <div className="flex gap-2 ml-4 shrink-0">
                        <button
                          onClick={() => setExpandido(isExpand ? null : p.id)}
                          className="flex items-center gap-1.5 px-3 py-2 bg-white/5 border border-white/10 text-gray-400 rounded-lg text-xs font-medium hover:bg-white/10 transition-all"
                        >
                          <Eye size={12} /> {isExpand ? 'Ocultar' : 'Ver código'}
                        </button>
                        <button
                          onClick={() => executarAcaoProposta(p.id, 'aprovar')}
                          disabled={processando === p.id}
                          className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-50 transition-all"
                        >
                          <CheckCircle2 size={12} /> Aprovar
                        </button>
                        <button
                          onClick={() => executarAcaoProposta(p.id, 'rejeitar')}
                          disabled={processando === p.id}
                          className="flex items-center gap-1.5 px-4 py-2 bg-red-500/15 border border-red-500/25 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/25 disabled:opacity-50 transition-all"
                        >
                          <XCircle size={12} /> Rejeitar
                        </button>
                      </div>
                    </div>

                    {/* Código expandido */}
                    {isExpand && (
                      <div className="px-5 pb-5 border-t" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                        <div className="mt-4 grid grid-cols-2 gap-4">
                          {/* Conteúdo atual */}
                          <div>
                            <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-2 flex items-center gap-1">
                              <XCircle size={10} className="text-red-400" /> Atual
                            </p>
                            <pre className="text-xs font-mono p-3 rounded-lg overflow-auto max-h-60 sf-glass border" style={{ borderColor: 'var(--sf-border-subtle)', color: 'var(--sf-text-2)' }}>
                              {p.conteudo_atual_preview || '(arquivo novo)'}
                            </pre>
                          </div>
                          {/* Conteúdo novo */}
                          <div>
                            <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-2 flex items-center gap-1">
                              <CheckCircle2 size={10} className="text-emerald-400" /> Proposto
                            </p>
                            <pre className="text-xs font-mono p-3 rounded-lg overflow-auto max-h-60 bg-emerald-500/[0.03] border border-emerald-500/10" style={{ color: 'var(--sf-text-2)' }}>
                              {(p.conteudo_novo || '').slice(0, 3000)}
                              {(p.conteudo_novo || '').length > 3000 && '\n... (truncado)'}
                            </pre>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl sf-glass border flex items-center justify-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                <Code2 size={24} className="sf-text-ghost" strokeWidth={1.5} />
              </div>
              <p className="text-sm sf-text-dim">Nenhuma edição de código pendente.</p>
              <p className="text-xs sf-text-ghost mt-1">Quando um agente propor uma mudança no SyneriumX, ela aparece aqui.</p>
            </div>
          )}

          {/* Histórico de propostas */}
          {propostasResolvidas.length > 0 && (
            <div className="mt-8">
              <div className="flex items-center gap-2 mb-4">
                <History size={14} className="sf-text-dim" />
                <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">Histórico de edições</h3>
              </div>
              <div className="space-y-2">
                {propostasResolvidas.map((p: any) => {
                  const aprovada = p.status === 'aprovada'
                  return (
                    <div key={p.id} className="sf-glass border rounded-xl p-4 flex items-center justify-between hover:border-white/10 transition-all" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: aprovada ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' }}>
                          {aprovada ? <CheckCircle2 size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}
                        </div>
                        <div>
                          <p className="text-sm sf-text-dim">{p.descricao}</p>
                          <p className="text-[10px] sf-text-ghost font-mono">{p.caminho} · {aprovada ? `aprovado por ${p.aprovado_por}` : `rejeitado por ${p.rejeitado_por}`}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== ABA: DEPLOYS (2ª aprovação) ==================== */}
      {aba === 'deploys' && (
        <div>
          {deploysPendentes.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-4">
                <Rocket size={14} className="text-red-400" />
                <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider">
                  Deploy aguardando aprovação
                </h3>
              </div>
              {deploysPendentes.map((d: any) => (
                <div key={d.id} className="bg-gradient-to-br from-red-500/[0.04] to-white/[0.01] border border-red-500/20 rounded-xl p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center mt-0.5">
                        <Upload size={16} className="text-red-400" strokeWidth={1.8} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20">
                            git push → produção
                          </span>
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md" style={{
                            backgroundColor: d.build_ok ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                            color: d.build_ok ? '#10b981' : '#ef4444',
                          }}>
                            {d.build_ok ? <CheckCircle2 size={9} /> : <XCircle size={9} />}
                            Build {d.build_ok ? 'OK' : 'FALHOU'}
                          </span>
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md" style={{
                            backgroundColor: d.commit_ok ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                            color: d.commit_ok ? '#10b981' : '#ef4444',
                          }}>
                            <GitBranch size={9} />
                            Commit {d.commit_ok ? 'OK' : 'FALHOU'}
                          </span>
                        </div>
                        <p className="font-medium sf-text-white text-sm">{d.descricao}</p>
                        <p className="text-[10px] sf-text-dim mt-0.5">Branch → PR → Merge (squash) → GitHub Actions deploya</p>
                        <p className="text-xs sf-text-dim mt-1 font-mono">Arquivo: {d.arquivo}</p>
                        <p className="text-[10px] sf-text-ghost mt-1">
                          {new Date(d.criado_em).toLocaleString('pt-BR')} · Proposta #{d.proposta_id}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4 shrink-0">
                      <button
                        onClick={() => executarAcaoDeploy(d.id, 'aprovar')}
                        disabled={processando === d.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-red-500/15 border border-red-500/25 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/25 disabled:opacity-50 transition-all"
                      >
                        <Rocket size={12} /> Deploy Agora
                      </button>
                      <button
                        onClick={() => executarAcaoDeploy(d.id, 'rejeitar')}
                        disabled={processando === d.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-white/5 border border-white/10 text-gray-400 rounded-lg text-xs font-medium hover:bg-white/10 disabled:opacity-50 transition-all"
                      >
                        <XCircle size={12} /> Cancelar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl sf-glass border flex items-center justify-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                <Rocket size={24} className="sf-text-ghost" strokeWidth={1.5} />
              </div>
              <p className="text-sm sf-text-dim">Nenhum deploy pendente.</p>
              <p className="text-xs sf-text-ghost mt-1">Após aprovar uma edição de código, o deploy aparece aqui.</p>
            </div>
          )}

          {/* Histórico de deploys */}
          {deploysResolvidos.length > 0 && (
            <div className="mt-8">
              <div className="flex items-center gap-2 mb-4">
                <History size={14} className="sf-text-dim" />
                <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">Histórico de deploys</h3>
              </div>
              <div className="space-y-2">
                {deploysResolvidos.map((d: any) => {
                  const ok = d.status === 'deployado'
                  return (
                    <div key={d.id} className="sf-glass border rounded-xl p-4 flex items-center justify-between" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: ok ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' }}>
                          {ok ? <CheckCircle2 size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}
                        </div>
                        <div>
                          <p className="text-sm sf-text-dim">{d.descricao}</p>
                          <p className="text-[10px] sf-text-ghost font-mono">
                          {d.arquivo} · {d.status}
                          {d.push_resultado?.pr_url && ` · `}
                          {d.push_resultado?.pr_url && (
                            <a href={d.push_resultado.pr_url} target="_blank" rel="noopener" className="text-blue-400 hover:underline">
                              PR
                            </a>
                          )}
                          {d.push_resultado?.merge_ok && ' · Merged ✓'}
                          {` · ${d.aprovado_por || d.rejeitado_por || ''}`}
                        </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== ABA: SOLICITAÇÕES DE AGENTES ==================== */}
      {aba === 'agentes' && (
        <div>
          {/* Pendentes */}
          {solicitacoesPendentes.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-4">
                <Clock size={14} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-purple-400 uppercase tracking-wider">
                  Solicitações pendentes
                </h3>
              </div>
              {solicitacoesPendentes.map((s: any) => (
                <div key={s.id} className="bg-gradient-to-br from-purple-500/[0.04] to-white/[0.01] border border-purple-500/20 rounded-xl p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mt-0.5">
                        <Bot size={16} className="text-purple-400" strokeWidth={1.8} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            Solicitação de Agente
                          </span>
                          {s.nome_agente && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              {s.nome_agente}
                            </span>
                          )}
                          {s.perfil_sugerido && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-gray-500/10 sf-text-dim border border-white/10">
                              {s.perfil_sugerido}
                            </span>
                          )}
                        </div>
                        <p className="font-medium sf-text-white text-sm">{s.descricao}</p>
                        <p className="text-[10px] sf-text-ghost mt-1">
                          Solicitado por {s.usuario_nome} · {s.criado_em ? new Date(s.criado_em).toLocaleString('pt-BR') : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4 shrink-0">
                      <button
                        onClick={() => executarAcaoSolicitacao(s.id, true)}
                        disabled={processando === s.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-50 transition-all"
                      >
                        <CheckCircle2 size={12} /> Aprovar
                      </button>
                      <button
                        onClick={() => executarAcaoSolicitacao(s.id, false)}
                        disabled={processando === s.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-red-500/15 border border-red-500/25 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/25 disabled:opacity-50 transition-all"
                      >
                        <XCircle size={12} /> Rejeitar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl sf-glass border flex items-center justify-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                <Bot size={24} className="sf-text-ghost" strokeWidth={1.5} />
              </div>
              <p className="text-sm sf-text-dim">Nenhuma solicitação de agente pendente.</p>
              <p className="text-xs sf-text-ghost mt-1">Quando um usuário solicitar um agente, a solicitação aparece aqui.</p>
            </div>
          )}

          {/* Histórico de solicitações */}
          {solicitacoesResolvidas.length > 0 && (
            <div className="mt-8">
              <div className="flex items-center gap-2 mb-4">
                <History size={14} className="sf-text-dim" />
                <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">Histórico de solicitações</h3>
              </div>
              <div className="space-y-2">
                {solicitacoesResolvidas.map((s: any) => {
                  const aprovada = s.status === 'aprovado'
                  return (
                    <div key={s.id} className="sf-glass border rounded-xl p-4 flex items-center justify-between hover:border-white/10 transition-all" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: aprovada ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' }}>
                          {aprovada ? <CheckCircle2 size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}
                        </div>
                        <div>
                          <p className="text-sm sf-text-dim">{s.descricao}</p>
                          <p className="text-[10px] sf-text-ghost">
                            {s.usuario_nome} · {aprovada ? 'Aprovado' : 'Rejeitado'} por {s.aprovado_por_nome}
                            {s.comentario && ` — "${s.comentario}"`}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== ABA: APROVAÇÕES GERAIS ==================== */}
      {aba === 'geral' && (
        <div>
          {/* Formulário */}
          {mostrarForm && (
            <form onSubmit={enviarSolicitacao} className="sf-glass border sf-border rounded-2xl p-6 mb-8 space-y-4">
              <h4 className="font-semibold sf-text-white mb-2">Nova Solicitação de Aprovação</h4>
              <div className="grid grid-cols-2 gap-3">
                <select name="tipo" required className={inputCls} style={{ appearance: 'none' }}>
                  {Object.entries(tipoIcons).map(([id, cfg]) => (
                    <option key={id} value={id}>{cfg.label}</option>
                  ))}
                </select>
                <input name="solicitante" placeholder="Nome do solicitante" required className={inputCls} />
              </div>
              <input name="descricao" placeholder="Descrição da solicitação" required className={inputCls} />
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 sf-text-ghost" />
                  <input name="valor" type="number" step="0.01" placeholder="Valor estimado (R$)" className={`${inputCls} pl-9`} />
                </div>
                <button type="submit" className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-sm font-medium hover:bg-emerald-500/30 transition-all">
                  <Send size={13} /> Enviar
                </button>
              </div>
            </form>
          )}

          {/* Pendentes */}
          {pendentesAprov.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Clock size={14} className="text-orange-400" />
                <h3 className="text-sm font-semibold text-orange-400 uppercase tracking-wider">Pendentes</h3>
              </div>
              <div className="space-y-3">
                {pendentesAprov.map((a: any) => {
                  const tipo = tipoIcons[a.tipo] || tipoIcons.gasto_ia
                  const TipoIcon = tipo.icon
                  return (
                    <div key={a.indice} className="bg-gradient-to-br from-orange-500/[0.04] to-white/[0.01] border border-orange-500/20 rounded-xl p-5">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-9 h-9 rounded-lg flex items-center justify-center mt-0.5" style={{ backgroundColor: `${tipo.cor}12`, border: `1px solid ${tipo.cor}25` }}>
                            <TipoIcon size={16} style={{ color: tipo.cor }} strokeWidth={1.8} />
                          </div>
                          <div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md border" style={{ color: tipo.cor, backgroundColor: `${tipo.cor}10`, borderColor: `${tipo.cor}25` }}>
                              {tipo.label}
                            </span>
                            <p className="font-medium sf-text-white text-sm mt-1">{a.descricao}</p>
                            <div className="flex items-center gap-3 mt-1 text-xs sf-text-dim">
                              <span className="flex items-center gap-1"><User2 size={10} /> {a.solicitante}</span>
                              {a.valor_estimado != null && <span className="font-mono">R${a.valor_estimado.toFixed(2)}</span>}
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2 ml-4 shrink-0">
                          <button onClick={() => executarAcaoAprov(a.indice, true)} disabled={processando === a.indice}
                            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-50 transition-all">
                            <CheckCircle2 size={12} /> Aprovar
                          </button>
                          <button onClick={() => executarAcaoAprov(a.indice, false)} disabled={processando === a.indice}
                            className="flex items-center gap-1.5 px-4 py-2 bg-red-500/15 border border-red-500/25 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/25 disabled:opacity-50 transition-all">
                            <XCircle size={12} /> Rejeitar
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Histórico */}
          {resolvidasAprov.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <History size={14} className="sf-text-dim" />
                <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">Histórico</h3>
              </div>
              <div className="space-y-2">
                {resolvidasAprov.map((a: any) => {
                  const tipo = tipoIcons[a.tipo] || tipoIcons.gasto_ia
                  const TipoIcon = tipo.icon
                  const aprovado = a.aprovado === true
                  return (
                    <div key={a.indice} className="sf-glass border rounded-xl p-4 flex items-center justify-between" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${tipo.cor}10` }}>
                          <TipoIcon size={14} style={{ color: tipo.cor }} strokeWidth={1.8} />
                        </div>
                        <div>
                          <div className="flex items-center gap-1 mb-0.5">
                            {aprovado ? <CheckCircle2 size={10} className="text-emerald-400" /> : <XCircle size={10} className="text-red-400" />}
                            <span className={`text-[10px] ${aprovado ? 'text-emerald-400' : 'text-red-400'}`}>{aprovado ? 'Aprovada' : 'Rejeitada'}</span>
                          </div>
                          <p className="text-sm sf-text-dim">{a.descricao}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Empty */}
          {(aprovacoes || []).length === 0 && !mostrarForm && (
            <div className="text-center py-16">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl sf-glass border flex items-center justify-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                <ShieldCheck size={24} className="sf-text-ghost" strokeWidth={1.5} />
              </div>
              <p className="text-sm sf-text-dim">Nenhuma aprovação geral registrada.</p>
              <p className="text-xs sf-text-ghost mt-1">Deploy, gasto IA e mudanças de arquitetura aparecem aqui.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
