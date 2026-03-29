/* Projetos — Gestão premium dark-mode (zero emojis) */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import {
  FolderKanban, Crown, Wrench, Users, X, Plus, Send,
  Clock, CheckCircle2, XCircle, Loader2, ShieldCheck,
  GitPullRequest, Bug, RefreshCw, Rocket, Lock, MessageSquare,
  ChevronRight, GitBranch, Plug, Trash2,
} from 'lucide-react'
import { buscarVCS, salvarVCS, testarVCS, removerVCS } from '../services/api'

interface Membro { id: number; nome: string; papel: string }
interface Solicitacao {
  id: number; titulo: string; descricao: string; tipo_mudanca: string
  categoria: string; status: string; aprovador_necessario: string
  solicitante_nome: string; aprovado_por_nome: string
  comentario_aprovador: string; criado_em: string; aprovado_em: string | null
}
interface Projeto {
  id: number; nome: string; descricao: string; caminho: string
  repositorio: string; stack: string; icone: string
  proprietario_id: number; proprietario_nome: string
  lider_tecnico_id: number | null; lider_tecnico_nome: string
  membros: Membro[]; fase_atual: string; criado_em: string
}
interface ProjetoDetalhado extends Projeto {
  eh_proprietario: boolean; eh_lider: boolean; eh_ceo: boolean
  solicitacoes: Solicitacao[]
}

const tipoConfig: Record<string, { cor: string; label: string }> = {
  pequena: { cor: '#10b981', label: 'Pequena' },
  grande: { cor: '#f59e0b', label: 'Grande' },
  critica: { cor: '#ef4444', label: 'Crítica' },
}

const statusConfig: Record<string, { cor: string; label: string; icon: typeof Clock }> = {
  pendente: { cor: '#f97316', label: 'Pendente', icon: Clock },
  aprovada: { cor: '#10b981', label: 'Aprovada', icon: CheckCircle2 },
  rejeitada: { cor: '#ef4444', label: 'Rejeitada', icon: XCircle },
  em_execucao: { cor: '#3b82f6', label: 'Executando', icon: Loader2 },
  concluida: { cor: '#10b981', label: 'Concluída', icon: CheckCircle2 },
}

const catIcons: Record<string, typeof GitPullRequest> = {
  feature: GitPullRequest, bugfix: Bug, refactor: RefreshCw,
  deploy: Rocket, seguranca: Lock,
}

export default function Projetos() {
  const { token } = useAuth()
  const [projetoAberto, setProjetoAberto] = useState<ProjetoDetalhado | null>(null)
  const [novaSolicitacao, setNovaSolicitacao] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [tipoMudanca, setTipoMudanca] = useState('grande')
  const [categoria, setCategoria] = useState('feature')
  const [mensagem, setMensagem] = useState('')

  const fetcher = useCallback(async () => {
    const res = await fetch('/api/projetos', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error('Erro')
    return res.json()
  }, [token])

  const { dados, erro, carregando } = usePolling(fetcher, 15000)
  const projetos = (dados || []) as Projeto[]

  const abrirProjeto = async (id: number) => {
    const res = await fetch(`/api/projetos/${id}`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) setProjetoAberto(await res.json())
  }

  const criarSolicitacao = async (projetoId: number) => {
    setMensagem('')
    const res = await fetch(`/api/projetos/${projetoId}/solicitacoes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ titulo, descricao, tipo_mudanca: tipoMudanca, categoria }),
    })
    const data = await res.json()
    setMensagem(res.ok ? data.mensagem : (data.detail || 'Erro'))
    if (res.ok) { setNovaSolicitacao(false); setTitulo(''); setDescricao(''); abrirProjeto(projetoId) }
  }

  const acaoSolicitacao = async (solId: number, acao: 'aprovar' | 'rejeitar') => {
    const comentario = acao === 'rejeitar' ? prompt('Motivo da rejeição:') || '' : ''
    const res = await fetch(`/api/solicitacoes/${solId}/${acao}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ comentario }),
    })
    const data = await res.json()
    setMensagem(data.mensagem || data.detail)
    if (projetoAberto) abrirProjeto(projetoAberto.id)
  }

  if (carregando) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" /></div>
  }
  if (erro) return <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">Erro: {erro}</div>

  const inputCls = "w-full sf-glass border sf-border rounded-xl px-4 py-2.5 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"
  const selectCls = "sf-glass border sf-border rounded-xl px-4 py-2.5 text-sm sf-text-dim focus:outline-none focus:border-emerald-500/50"

  return (
    <div className="sf-page">
      <div className="fixed top-0 right-1/4 w-[500px] h-[300px] bg-indigo-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">Projetos</h2>
        <p className="text-sm sf-text-dim mt-1">{projetos.length} projeto(s) registrado(s)</p>
      </div>

      {mensagem && (
        <div className={`mb-6 px-4 py-3 rounded-xl text-sm flex items-center gap-2 ${
          mensagem.includes('sucesso') || mensagem.includes('Aprovada')
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {mensagem.includes('sucesso') ? <CheckCircle2 size={14} /> : <XCircle size={14} />} {mensagem}
        </div>
      )}

      {/* Lista de Projetos */}
      <div className="space-y-4">
        {projetos.map(p => (
          <div key={p.id}
            className="group sf-glass border sf-border rounded-2xl p-6 cursor-pointer transition-all duration-300 hover:border-white/15 hover:-translate-y-0.5"
            onClick={() => abrirProjeto(p.id)}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <FolderKanban size={22} className="text-indigo-400" strokeWidth={1.5} />
                </div>
                <div>
                  <h3 className="text-lg font-bold sf-text-white">{p.nome}</h3>
                  <p className="text-xs sf-text-dim font-mono">{p.stack}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {p.fase_atual && (
                  <span className="text-[10px] font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 px-3 py-1 rounded-lg">
                    {p.fase_atual}
                  </span>
                )}
                <ChevronRight size={16} className="sf-text-ghost group-hover:sf-text-dim transition-colors" />
              </div>
            </div>
            <p className="text-sm sf-text-dim mb-4">{p.descricao}</p>
            <div className="flex gap-6 text-xs">
              <span className="flex items-center gap-1.5"><Crown size={12} className="text-emerald-400" /> <span className="sf-text-dim">{p.proprietario_nome}</span></span>
              {p.lider_tecnico_nome && <span className="flex items-center gap-1.5"><Wrench size={12} className="text-blue-400" /> <span className="sf-text-dim">{p.lider_tecnico_nome}</span></span>}
              <span className="flex items-center gap-1.5"><Users size={12} className="sf-text-dim" /> <span className="sf-text-dim">{p.membros.length} membro(s)</span></span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {projetoAberto && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setProjetoAberto(null)}>
          <div className="border sf-border rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" style={{ background: 'var(--sf-bg-tooltip)' }} onClick={e => e.stopPropagation()}>
            {/* Modal header */}
            <div className="p-6 border-b flex items-center justify-between" style={{ borderColor: 'var(--sf-border-subtle)' }}>
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <FolderKanban size={20} className="text-indigo-400" strokeWidth={1.5} />
                </div>
                <div>
                  <h3 className="text-xl font-bold sf-text-white">{projetoAberto.nome}</h3>
                  <p className="text-xs sf-text-dim font-mono">{projetoAberto.stack}</p>
                </div>
              </div>
              <button onClick={() => setProjetoAberto(null)} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors">
                <X size={16} className="sf-text-dim" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Hierarquia */}
              <div>
                <p className="text-[10px] sf-text-ghost uppercase tracking-wider mb-3">Hierarquia</p>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { icon: Crown, label: 'Proprietário', nome: projetoAberto.proprietario_nome, cor: '#10b981' },
                    { icon: Wrench, label: 'Líder Técnico', nome: projetoAberto.lider_tecnico_nome || '—', cor: '#3b82f6' },
                    { icon: Users, label: 'Membros', nome: projetoAberto.membros.map(m => m.nome).join(', ') || '—', cor: '#8b5cf6' },
                  ].map(h => {
                    const Icon = h.icon
                    return (
                      <div key={h.label} className="sf-glass border rounded-xl p-4 text-center">
                        <div className="w-9 h-9 rounded-lg mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: `${h.cor}15` }}>
                          <Icon size={16} style={{ color: h.cor }} strokeWidth={1.8} />
                        </div>
                        <p className="text-[10px] sf-text-ghost uppercase tracking-wider">{h.label}</p>
                        <p className="text-sm font-medium sf-text-white mt-1">{h.nome}</p>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Regras de Aprovação */}
              <div className="sf-glass border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck size={14} className="sf-text-dim" />
                  <p className="text-xs sf-text-dim font-semibold uppercase tracking-wider">Regras de Aprovação</p>
                </div>
                <div className="space-y-2.5">
                  {[
                    { tipo: 'Pequena', desc: 'Bug fix, UI tweak', quem: 'Líder Técnico', cor: '#10b981' },
                    { tipo: 'Grande', desc: 'Feature, arquitetura', quem: 'Proprietário', cor: '#f59e0b' },
                    { tipo: 'Crítica', desc: 'Deploy, banco, segurança', quem: 'Proprietário + Líder', cor: '#ef4444' },
                  ].map(r => (
                    <div key={r.tipo} className="flex items-center gap-3">
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-md border" style={{ color: r.cor, backgroundColor: `${r.cor}10`, borderColor: `${r.cor}25` }}>{r.tipo}</span>
                      <span className="text-xs sf-text-dim flex-1">{r.desc}</span>
                      <span className="text-xs sf-text-dim font-medium">{r.quem}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Version Control */}
              {(projetoAberto.eh_proprietario || projetoAberto.eh_ceo) && (
                <SecaoVCS projetoId={projetoAberto.id} />
              )}

              {/* Solicitações */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[10px] sf-text-ghost uppercase tracking-wider">
                    Solicitações ({projetoAberto.solicitacoes.length})
                  </p>
                  <button onClick={() => setNovaSolicitacao(!novaSolicitacao)}
                    className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                      novaSolicitacao
                        ? 'bg-white/5 text-gray-400 border border-white/10'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/30'
                    }`}>
                    {novaSolicitacao ? <><X size={12} /> Cancelar</> : <><Plus size={12} /> Nova</>}
                  </button>
                </div>

                {novaSolicitacao && (
                  <div className="sf-glass border rounded-xl p-4 mb-4 space-y-3">
                    <input value={titulo} onChange={e => setTitulo(e.target.value)} placeholder="Título da mudança" className={inputCls} />
                    <textarea value={descricao} onChange={e => setDescricao(e.target.value)} placeholder="Descreva em detalhes..." rows={3} className={inputCls} />
                    <div className="flex gap-3">
                      <select value={tipoMudanca} onChange={e => setTipoMudanca(e.target.value)} className={selectCls}>
                        <option value="pequena">Pequena</option>
                        <option value="grande">Grande</option>
                        <option value="critica">Crítica</option>
                      </select>
                      <select value={categoria} onChange={e => setCategoria(e.target.value)} className={selectCls}>
                        <option value="feature">Feature</option>
                        <option value="bugfix">Bug Fix</option>
                        <option value="refactor">Refatoração</option>
                        <option value="deploy">Deploy</option>
                        <option value="seguranca">Segurança</option>
                      </select>
                      <button onClick={() => criarSolicitacao(projetoAberto.id)} disabled={!titulo || !descricao}
                        className="flex items-center gap-1.5 px-4 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-xs font-medium hover:bg-emerald-500/30 disabled:opacity-40">
                        <Send size={12} /> Enviar
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  {projetoAberto.solicitacoes.map(sol => {
                    const tipo = tipoConfig[sol.tipo_mudanca] || tipoConfig.grande
                    const st = statusConfig[sol.status] || statusConfig.pendente
                    const StIcon = st.icon
                    const CatIcon = catIcons[sol.categoria] || GitPullRequest
                    return (
                      <div key={sol.id} className="sf-glass border rounded-xl p-4 hover:border-white/10 transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <CatIcon size={13} className="sf-text-dim" />
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-md border" style={{ color: tipo.cor, backgroundColor: `${tipo.cor}10`, borderColor: `${tipo.cor}25` }}>{tipo.label}</span>
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded-md" style={{ backgroundColor: `${st.cor}10` }}>
                              <StIcon size={10} style={{ color: st.cor }} strokeWidth={2} />
                              <span className="text-[10px] font-medium" style={{ color: st.cor }}>{st.label}</span>
                            </div>
                            <h5 className="font-medium sf-text-white text-sm">{sol.titulo}</h5>
                          </div>
                          <span className="text-[10px] sf-text-ghost font-mono">{sol.criado_em?.split('T')[0]}</span>
                        </div>
                        <p className="text-xs sf-text-dim mb-2">{sol.descricao}</p>
                        <div className="flex items-center justify-between text-[10px] sf-text-ghost">
                          <span>Por: {sol.solicitante_nome} · Requer: {sol.aprovador_necessario}</span>
                          {sol.status === 'pendente' && (projetoAberto.eh_proprietario || projetoAberto.eh_lider || projetoAberto.eh_ceo) && (
                            <div className="flex gap-2">
                              <button onClick={() => acaoSolicitacao(sol.id, 'aprovar')}
                                className="flex items-center gap-1 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-[10px] font-medium hover:bg-emerald-500/20">
                                <CheckCircle2 size={10} /> Aprovar
                              </button>
                              <button onClick={() => acaoSolicitacao(sol.id, 'rejeitar')}
                                className="flex items-center gap-1 px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-[10px] font-medium hover:bg-red-500/20">
                                <XCircle size={10} /> Rejeitar
                              </button>
                            </div>
                          )}
                        </div>
                        {sol.comentario_aprovador && (
                          <div className="mt-2 sf-glass border rounded-lg px-3 py-2 flex items-start gap-2" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                            <MessageSquare size={11} className="sf-text-ghost mt-0.5 shrink-0" />
                            <span className="text-[11px] sf-text-dim">{sol.aprovado_por_nome}: {sol.comentario_aprovador}</span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {projetoAberto.solicitacoes.length === 0 && (
                    <p className="text-sm sf-text-ghost text-center py-6">Nenhuma solicitação.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


/* ================================================================ */
/* Seção Version Control (VCS)                                       */
/* ================================================================ */

function SecaoVCS({ projetoId }: { projetoId: number }) {
  const [vcs, setVcs] = useState<{ configurado: boolean; vcs_tipo?: string; repo_url?: string; branch_padrao?: string } | null>(null)
  const [editando, setEditando] = useState(false)
  const [vcsTipo, setVcsTipo] = useState('github')
  const [repoUrl, setRepoUrl] = useState('')
  const [token, setToken] = useState('')
  const [branch, setBranch] = useState('main')
  const [salvando, setSalvando] = useState(false)
  const [testando, setTestando] = useState(false)
  const [resultadoTeste, setResultadoTeste] = useState<{ sucesso: boolean; mensagem: string } | null>(null)
  const [erro, setErro] = useState('')

  const inputCls = 'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm sf-text-white outline-none focus:border-emerald-500/50'

  // Carregar config ao montar
  useState(() => {
    buscarVCS(projetoId).then(data => {
      setVcs(data)
      if (data.configurado) {
        setVcsTipo(data.vcs_tipo || 'github')
        setRepoUrl(data.repo_url || '')
        setBranch(data.branch_padrao || 'main')
      }
    }).catch(() => {})
  })

  const handleSalvar = async () => {
    if (!repoUrl || !token) { setErro('Preencha URL e Token'); return }
    setSalvando(true); setErro('')
    try {
      await salvarVCS(projetoId, { vcs_tipo: vcsTipo, repo_url: repoUrl, api_token: token, branch_padrao: branch })
      setVcs({ configurado: true, vcs_tipo: vcsTipo, repo_url: repoUrl, branch_padrao: branch })
      setEditando(false); setToken('')
    } catch (e) { setErro(e instanceof Error ? e.message : 'Erro ao salvar') }
    finally { setSalvando(false) }
  }

  const handleTestar = async () => {
    setTestando(true); setResultadoTeste(null)
    try {
      const r = await testarVCS(projetoId)
      setResultadoTeste(r)
    } catch (e) { setResultadoTeste({ sucesso: false, mensagem: e instanceof Error ? e.message : 'Erro' }) }
    finally { setTestando(false) }
  }

  const handleRemover = async () => {
    if (!confirm('Remover configuração VCS deste projeto?')) return
    try {
      await removerVCS(projetoId)
      setVcs({ configurado: false }); setRepoUrl(''); setToken(''); setBranch('main')
    } catch { /* ignore */ }
  }

  return (
    <div className="sf-glass border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch size={14} className="sf-text-dim" />
          <p className="text-xs sf-text-dim font-semibold uppercase tracking-wider">Version Control</p>
        </div>
        {vcs?.configurado && !editando && (
          <div className="flex gap-1.5">
            <button onClick={() => setEditando(true)}
              className="text-[10px] px-2 py-1 rounded bg-white/5 hover:bg-white/10 sf-text-dim transition-colors">
              Editar
            </button>
            <button onClick={handleTestar} disabled={testando}
              className="text-[10px] px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors disabled:opacity-50">
              {testando ? <Loader2 size={10} className="animate-spin inline" /> : <Plug size={10} className="inline" />}
              {' '}Testar
            </button>
            <button onClick={handleRemover}
              className="text-[10px] px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors">
              <Trash2 size={10} className="inline" />
            </button>
          </div>
        )}
      </div>

      {/* Resultado do teste */}
      {resultadoTeste && (
        <div className={`mb-3 px-3 py-2 rounded-lg text-[11px] font-medium ${resultadoTeste.sucesso ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
          {resultadoTeste.sucesso ? <CheckCircle2 size={12} className="inline mr-1" /> : <XCircle size={12} className="inline mr-1" />}
          {resultadoTeste.mensagem}
        </div>
      )}

      {vcs?.configurado && !editando ? (
        /* VCS configurado — mostrar info */
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded"
              style={{ background: vcs.vcs_tipo === 'github' ? 'rgba(36,41,47,0.3)' : 'rgba(139,92,246,0.1)', color: vcs.vcs_tipo === 'github' ? '#e6edf3' : '#a78bfa' }}>
              {vcs.vcs_tipo === 'github' ? 'GitHub' : 'GitBucket'}
            </span>
            <span className="text-xs sf-text-dim font-mono truncate">{vcs.repo_url}</span>
          </div>
          <p className="text-[10px] sf-text-ghost">Branch: <span className="sf-text-dim font-mono">{vcs.branch_padrao}</span> · Token: <span className="text-emerald-400">***configurado***</span></p>
        </div>
      ) : (
        /* Formulário de configuração */
        <div className="space-y-3">
          <div>
            <p className="text-[10px] sf-text-ghost mb-1">Tipo</p>
            <div className="flex gap-2">
              {(['github', 'gitbucket'] as const).map(t => (
                <button key={t} onClick={() => setVcsTipo(t)}
                  className={`flex-1 px-3 py-2 rounded-lg text-[11px] font-medium border transition-all ${vcsTipo === t ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' : 'border-white/10 bg-white/5 sf-text-dim hover:bg-white/8'}`}>
                  {t === 'github' ? 'GitHub' : 'GitBucket'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-[10px] sf-text-ghost mb-1">URL do Repositório</p>
            <input value={repoUrl} onChange={e => setRepoUrl(e.target.value)}
              placeholder={vcsTipo === 'github' ? 'https://github.com/owner/repo' : 'http://gitbucket.empresa.com/git/owner/repo'}
              className={inputCls} />
          </div>
          <div>
            <p className="text-[10px] sf-text-ghost mb-1">{vcsTipo === 'github' ? 'Personal Access Token' : 'Token de API'}</p>
            <input type="password" value={token} onChange={e => setToken(e.target.value)}
              placeholder="ghp_xxxxx..." className={inputCls} />
          </div>
          <div>
            <p className="text-[10px] sf-text-ghost mb-1">Branch Padrão</p>
            <input value={branch} onChange={e => setBranch(e.target.value)}
              placeholder="main" className={inputCls} />
          </div>
          {erro && <p className="text-[11px] text-red-400">{erro}</p>}
          <div className="flex gap-2">
            <button onClick={handleSalvar} disabled={salvando}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-all disabled:opacity-50">
              {salvando ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
              {salvando ? 'Salvando...' : 'Salvar VCS'}
            </button>
            {vcs?.configurado && (
              <button onClick={() => setEditando(false)}
                className="px-3 py-2 rounded-lg text-[11px] sf-text-dim bg-white/5 hover:bg-white/10 transition-colors">
                Cancelar
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
