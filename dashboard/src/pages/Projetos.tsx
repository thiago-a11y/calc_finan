/* Projetos — Gestao premium dark-mode com hierarquia e regras editaveis */

import { useCallback, useState, useEffect } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import {
  FolderKanban, Crown, Wrench, Users, X, Plus, Send,
  Clock, CheckCircle2, XCircle, Loader2, ShieldCheck,
  GitPullRequest, Bug, RefreshCw, Rocket, Lock, MessageSquare,
  ChevronRight, GitBranch, Plug, Trash2, Edit3, UserPlus, UserMinus,
  Save, ChevronDown,
} from 'lucide-react'
import {
  buscarVCS, salvarVCS, testarVCS, removerVCS,
  buscarUsuarios, nomearProprietario, nomearLider,
  gerenciarMembro, atualizarRegrasAprovacao, criarProjeto,
} from '../services/api'

interface Membro { id: number; nome: string; papel: string }
interface RegraAprovacao { aprovador: string; descricao: string }
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
  membros: Membro[]; regras_aprovacao: Record<string, RegraAprovacao>
  fase_atual: string; criado_em: string
}
interface ProjetoDetalhado extends Projeto {
  eh_proprietario: boolean; eh_lider: boolean; eh_ceo: boolean
  solicitacoes: Solicitacao[]
}
interface UsuarioSimples { id: string; nome: string; email: string; cargo: string; ativo: boolean }

const tipoConfig: Record<string, { cor: string; label: string }> = {
  pequena: { cor: '#10b981', label: 'Pequena' },
  grande: { cor: '#f59e0b', label: 'Grande' },
  critica: { cor: '#ef4444', label: 'Critica' },
}

const statusConfig: Record<string, { cor: string; label: string; icon: typeof Clock }> = {
  pendente: { cor: '#f97316', label: 'Pendente', icon: Clock },
  aprovada: { cor: '#10b981', label: 'Aprovada', icon: CheckCircle2 },
  rejeitada: { cor: '#ef4444', label: 'Rejeitada', icon: XCircle },
  em_execucao: { cor: '#3b82f6', label: 'Executando', icon: Loader2 },
  concluida: { cor: '#10b981', label: 'Concluida', icon: CheckCircle2 },
}

const catIcons: Record<string, typeof GitPullRequest> = {
  feature: GitPullRequest, bugfix: Bug, refactor: RefreshCw,
  deploy: Rocket, seguranca: Lock,
}

const aprovadorLabels: Record<string, string> = {
  lider_tecnico: 'Lider Tecnico',
  proprietario: 'Proprietario',
  ambos: 'Proprietario + Lider',
  nenhum: 'Auto-aprovacao',
}

const regras_padrao: Record<string, RegraAprovacao> = {
  pequena: { aprovador: 'lider_tecnico', descricao: 'Bug fix, UI tweak' },
  grande: { aprovador: 'proprietario', descricao: 'Feature, arquitetura' },
  critica: { aprovador: 'ambos', descricao: 'Deploy, banco, seguranca' },
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
  const [modalNovoProjeto, setModalNovoProjeto] = useState(false)
  const [novoProjeto, setNovoProjeto] = useState({ nome: '', descricao: '', stack: '', repositorio: '', fase_atual: '' })
  const [criandoProjeto, setCriandoProjeto] = useState(false)

  const handleCriarProjeto = async () => {
    if (!novoProjeto.nome.trim()) return
    setCriandoProjeto(true)
    try {
      await criarProjeto(novoProjeto)
      setMensagem('Projeto criado com sucesso!')
      setModalNovoProjeto(false)
      setNovoProjeto({ nome: '', descricao: '', stack: '', repositorio: '', fase_atual: '' })
    } catch (e) {
      setMensagem(e instanceof Error ? e.message : 'Erro ao criar projeto')
    } finally {
      setCriandoProjeto(false)
    }
  }

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
    const comentario = acao === 'rejeitar' ? prompt('Motivo da rejeicao:') || '' : ''
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

      <div className="relative mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">Projetos</h2>
          <p className="text-sm sf-text-dim mt-1">{projetos.length} projeto(s) registrado(s)</p>
        </div>
        <button
          onClick={() => setModalNovoProjeto(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all hover:brightness-110"
          style={{ background: '#10b981', color: '#fff' }}>
          <Plus size={16} /> Novo Projeto
        </button>
      </div>

      {mensagem && (
        <div className={`mb-6 px-4 py-3 rounded-xl text-sm flex items-center gap-2 ${
          mensagem.includes('sucesso') || mensagem.includes('Aprovada') || mensagem.includes('atualizada')
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {mensagem.includes('sucesso') || mensagem.includes('atualizada') ? <CheckCircle2 size={14} /> : <XCircle size={14} />} {mensagem}
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
              {/* Hierarquia Editavel */}
              <SecaoHierarquia
                projeto={projetoAberto}
                onAtualizar={() => abrirProjeto(projetoAberto.id)}
                onMensagem={setMensagem}
              />

              {/* Regras de Aprovacao Editaveis */}
              <SecaoRegras
                projeto={projetoAberto}
                onAtualizar={() => abrirProjeto(projetoAberto.id)}
                onMensagem={setMensagem}
              />

              {/* Version Control */}
              {(projetoAberto.eh_proprietario || projetoAberto.eh_ceo) && (
                <SecaoVCS projetoId={projetoAberto.id} />
              )}

              {/* Solicitacoes */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[10px] sf-text-ghost uppercase tracking-wider">
                    Solicitacoes ({projetoAberto.solicitacoes.length})
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
                    <input value={titulo} onChange={e => setTitulo(e.target.value)} placeholder="Titulo da mudanca" className={inputCls} />
                    <textarea value={descricao} onChange={e => setDescricao(e.target.value)} placeholder="Descreva em detalhes..." rows={3} className={inputCls} />
                    <div className="flex gap-3">
                      <select value={tipoMudanca} onChange={e => setTipoMudanca(e.target.value)} className={selectCls}>
                        <option value="pequena">Pequena</option>
                        <option value="grande">Grande</option>
                        <option value="critica">Critica</option>
                      </select>
                      <select value={categoria} onChange={e => setCategoria(e.target.value)} className={selectCls}>
                        <option value="feature">Feature</option>
                        <option value="bugfix">Bug Fix</option>
                        <option value="refactor">Refatoracao</option>
                        <option value="deploy">Deploy</option>
                        <option value="seguranca">Seguranca</option>
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
                          <span>Por: {sol.solicitante_nome} | Requer: {sol.aprovador_necessario}</span>
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
                    <p className="text-sm sf-text-ghost text-center py-6">Nenhuma solicitacao.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Novo Projeto */}
      {modalNovoProjeto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <div className="rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6"
            style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <FolderKanban size={18} style={{ color: '#10b981' }} />
                <h3 className="text-[16px] font-bold" style={{ color: 'var(--sf-text-0)' }}>Novo Projeto</h3>
              </div>
              <button onClick={() => setModalNovoProjeto(false)} className="p-1 rounded hover:bg-white/5" style={{ color: 'var(--sf-text-3)' }}>
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-medium uppercase tracking-wider mb-1 block" style={{ color: 'var(--sf-text-3)' }}>Nome *</label>
                <input value={novoProjeto.nome} onChange={e => setNovoProjeto(p => ({ ...p, nome: e.target.value }))}
                  placeholder="Ex: SyneriumX, PlaniFactory..." className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-medium uppercase tracking-wider mb-1 block" style={{ color: 'var(--sf-text-3)' }}>Descricao</label>
                <input value={novoProjeto.descricao} onChange={e => setNovoProjeto(p => ({ ...p, descricao: e.target.value }))}
                  placeholder="Breve descricao do projeto" className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-medium uppercase tracking-wider mb-1 block" style={{ color: 'var(--sf-text-3)' }}>Stack</label>
                <input value={novoProjeto.stack} onChange={e => setNovoProjeto(p => ({ ...p, stack: e.target.value }))}
                  placeholder="Ex: PHP 7.4 + React 18 + MySQL" className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-medium uppercase tracking-wider mb-1 block" style={{ color: 'var(--sf-text-3)' }}>Repositorio (URL)</label>
                <input value={novoProjeto.repositorio} onChange={e => setNovoProjeto(p => ({ ...p, repositorio: e.target.value }))}
                  placeholder="https://github.com/org/repo" className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-medium uppercase tracking-wider mb-1 block" style={{ color: 'var(--sf-text-3)' }}>Fase Atual</label>
                <input value={novoProjeto.fase_atual} onChange={e => setNovoProjeto(p => ({ ...p, fase_atual: e.target.value }))}
                  placeholder="Ex: Fase 3 — Solucao" className={inputCls} />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 mt-5">
              <button onClick={() => setModalNovoProjeto(false)}
                className="px-4 py-2 rounded-lg text-[11px] font-medium hover:bg-white/5"
                style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
                Cancelar
              </button>
              <button onClick={handleCriarProjeto} disabled={!novoProjeto.nome.trim() || criandoProjeto}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[11px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
                style={{ background: '#10b981', color: '#fff' }}>
                {criandoProjeto ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
                {criandoProjeto ? 'Criando...' : 'Criar Projeto'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


/* ================================================================ */
/* Secao Hierarquia Editavel                                         */
/* ================================================================ */

function SecaoHierarquia({
  projeto, onAtualizar, onMensagem,
}: {
  projeto: ProjetoDetalhado
  onAtualizar: () => void
  onMensagem: (msg: string) => void
}) {
  const [editando, setEditando] = useState(false)
  const [usuarios, setUsuarios] = useState<UsuarioSimples[]>([])
  const [carregandoUsuarios, setCarregandoUsuarios] = useState(false)
  const [salvando, setSalvando] = useState(false)

  // Dropdowns abertos
  const [dropProp, setDropProp] = useState(false)
  const [dropLider, setDropLider] = useState(false)
  const [dropNovoMembro, setDropNovoMembro] = useState(false)
  const [papelNovoMembro, setPapelNovoMembro] = useState('dev')

  const podeEditar = projeto.eh_proprietario || projeto.eh_ceo

  const carregarUsuarios = async () => {
    setCarregandoUsuarios(true)
    try {
      const lista = await buscarUsuarios(false)
      setUsuarios(lista)
    } catch { /* ignore */ }
    setCarregandoUsuarios(false)
  }

  const handleEditar = () => {
    setEditando(true)
    carregarUsuarios()
  }

  const handleMudarProprietario = async (userId: string | number) => {
    setSalvando(true)
    try {
      const r = await nomearProprietario(projeto.id, Number(userId))
      onMensagem(r.mensagem)
      onAtualizar()
    } catch (e) {
      onMensagem(e instanceof Error ? e.message : 'Erro')
    }
    setSalvando(false)
    setDropProp(false)
  }

  const handleMudarLider = async (userId: string | number) => {
    setSalvando(true)
    try {
      const r = await nomearLider(projeto.id, Number(userId))
      onMensagem(r.mensagem)
      onAtualizar()
    } catch (e) {
      onMensagem(e instanceof Error ? e.message : 'Erro')
    }
    setSalvando(false)
    setDropLider(false)
  }

  const handleAdicionarMembro = async (userId: string | number) => {
    setSalvando(true)
    try {
      const r = await gerenciarMembro(projeto.id, 'adicionar', Number(userId), papelNovoMembro)
      onMensagem(r.mensagem)
      onAtualizar()
    } catch (e) {
      onMensagem(e instanceof Error ? e.message : 'Erro')
    }
    setSalvando(false)
    setDropNovoMembro(false)
  }

  const handleRemoverMembro = async (userId: string | number) => {
    setSalvando(true)
    try {
      const r = await gerenciarMembro(projeto.id, 'remover', Number(userId))
      onMensagem(r.mensagem)
      onAtualizar()
    } catch (e) {
      onMensagem(e instanceof Error ? e.message : 'Erro')
    }
    setSalvando(false)
  }

  // Filtrar usuarios que nao sao membros (comparar como number)
  const membrosIds = new Set((projeto.membros || []).map(m => Number(m.id)))
  const usuariosDisponiveis = usuarios.filter(u =>
    Number(u.id) !== projeto.proprietario_id &&
    Number(u.id) !== projeto.lider_tecnico_id &&
    !membrosIds.has(Number(u.id))
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] sf-text-ghost uppercase tracking-wider">Hierarquia</p>
        {podeEditar && !editando && (
          <button onClick={handleEditar}
            className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 sf-text-dim transition-colors">
            <Edit3 size={10} /> Editar
          </button>
        )}
        {editando && (
          <button onClick={() => setEditando(false)}
            className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 transition-colors">
            <CheckCircle2 size={10} /> Concluir
          </button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 relative" style={{ zIndex: 10 }}>
        {/* Proprietario */}
        <div className="sf-glass border rounded-xl p-4 text-center relative overflow-visible">
          <div className="w-9 h-9 rounded-lg mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: '#10b98115' }}>
            <Crown size={16} className="text-emerald-400" strokeWidth={1.8} />
          </div>
          <p className="text-[10px] sf-text-ghost uppercase tracking-wider">Proprietario</p>
          <p className="text-sm font-medium sf-text-white mt-1">{projeto.proprietario_nome}</p>

          {editando && projeto.eh_ceo && (
            <div className="mt-2 relative">
              <button onClick={() => { setDropProp(!dropProp); setDropLider(false); setDropNovoMembro(false) }}
                className="text-[10px] px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors w-full flex items-center justify-center gap-1">
                <Edit3 size={9} /> Alterar <ChevronDown size={9} />
              </button>
              {dropProp && (
                <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-white/10 shadow-xl max-h-40 overflow-y-auto z-50" style={{ background: 'var(--sf-bg-tooltip)' }}>
                  {carregandoUsuarios ? (
                    <div className="p-2 text-center"><Loader2 size={12} className="animate-spin inline sf-text-dim" /></div>
                  ) : usuarios.filter(u => Number(u.id) !== projeto.proprietario_id).map(u => (
                    <button key={u.id} onClick={() => handleMudarProprietario(u.id)} disabled={salvando}
                      className="w-full text-left px-3 py-2 text-[11px] sf-text-dim hover:bg-white/5 transition-colors truncate">
                      {u.nome} <span className="sf-text-ghost">({u.cargo})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Lider Tecnico */}
        <div className="sf-glass border rounded-xl p-4 text-center relative overflow-visible">
          <div className="w-9 h-9 rounded-lg mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: '#3b82f615' }}>
            <Wrench size={16} className="text-blue-400" strokeWidth={1.8} />
          </div>
          <p className="text-[10px] sf-text-ghost uppercase tracking-wider">Lider Tecnico</p>
          <p className="text-sm font-medium sf-text-white mt-1">{projeto.lider_tecnico_nome || '(nenhum)'}</p>

          {editando && (
            <div className="mt-2 relative">
              <button onClick={() => { setDropLider(!dropLider); setDropProp(false); setDropNovoMembro(false) }}
                className="text-[10px] px-2 py-1 rounded bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors w-full flex items-center justify-center gap-1">
                <Edit3 size={9} /> Alterar <ChevronDown size={9} />
              </button>
              {dropLider && (
                <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-white/10 shadow-xl max-h-40 overflow-y-auto z-50" style={{ background: 'var(--sf-bg-tooltip)' }}>
                  {carregandoUsuarios ? (
                    <div className="p-2 text-center"><Loader2 size={12} className="animate-spin inline sf-text-dim" /></div>
                  ) : usuarios.filter(u => Number(u.id) !== projeto.lider_tecnico_id).map(u => (
                    <button key={u.id} onClick={() => handleMudarLider(u.id)} disabled={salvando}
                      className="w-full text-left px-3 py-2 text-[11px] sf-text-dim hover:bg-white/5 transition-colors truncate">
                      {u.nome} <span className="sf-text-ghost">({u.cargo})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Membros */}
        <div className="sf-glass border rounded-xl p-4 text-center relative overflow-visible">
          <div className="w-9 h-9 rounded-lg mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: '#8b5cf615' }}>
            <Users size={16} className="text-purple-400" strokeWidth={1.8} />
          </div>
          <p className="text-[10px] sf-text-ghost uppercase tracking-wider">Membros ({(projeto.membros || []).length})</p>

          {(projeto.membros || []).length > 0 ? (
            <div className="mt-1 space-y-1">
              {(projeto.membros || []).map(m => (
                <div key={m.id} className="flex items-center justify-center gap-1">
                  <span className="text-[11px] sf-text-dim">{m.nome}</span>
                  <span className="text-[9px] sf-text-ghost">({m.papel})</span>
                  {editando && (
                    <button onClick={() => handleRemoverMembro(m.id)} disabled={salvando}
                      className="text-red-400/60 hover:text-red-400 transition-colors ml-0.5">
                      <UserMinus size={10} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] sf-text-ghost mt-1">(nenhum)</p>
          )}

          {editando && (
            <div className="mt-2 relative">
              <button onClick={() => { setDropNovoMembro(!dropNovoMembro); setDropProp(false); setDropLider(false) }}
                className="text-[10px] px-2 py-1 rounded bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors w-full flex items-center justify-center gap-1">
                <UserPlus size={9} /> Adicionar <ChevronDown size={9} />
              </button>
              {dropNovoMembro && (
                <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-white/10 shadow-xl max-h-48 overflow-y-auto z-20" style={{ background: 'var(--sf-bg-tooltip)' }}>
                  {/* Seletor de papel */}
                  <div className="p-2 border-b border-white/5">
                    <select value={papelNovoMembro} onChange={e => setPapelNovoMembro(e.target.value)}
                      className="w-full text-[10px] bg-white/5 border border-white/10 rounded px-2 py-1 sf-text-dim outline-none">
                      <option value="dev">Desenvolvedor</option>
                      <option value="designer">Designer</option>
                      <option value="qa">QA</option>
                      <option value="membro">Membro</option>
                      <option value="analista">Analista</option>
                    </select>
                  </div>
                  {carregandoUsuarios ? (
                    <div className="p-2 text-center"><Loader2 size={12} className="animate-spin inline sf-text-dim" /></div>
                  ) : usuariosDisponiveis.length === 0 ? (
                    <p className="p-2 text-[10px] sf-text-ghost text-center">Nenhum usuario disponivel</p>
                  ) : usuariosDisponiveis.map(u => (
                    <button key={u.id} onClick={() => handleAdicionarMembro(u.id)} disabled={salvando}
                      className="w-full text-left px-3 py-2 text-[11px] sf-text-dim hover:bg-white/5 transition-colors truncate">
                      {u.nome} <span className="sf-text-ghost">({u.cargo})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


/* ================================================================ */
/* Secao Regras de Aprovacao Editaveis                               */
/* ================================================================ */

function SecaoRegras({
  projeto, onAtualizar, onMensagem,
}: {
  projeto: ProjetoDetalhado
  onAtualizar: () => void
  onMensagem: (msg: string) => void
}) {
  const regras = projeto.regras_aprovacao && Object.keys(projeto.regras_aprovacao).length > 0
    ? projeto.regras_aprovacao
    : regras_padrao

  const [editando, setEditando] = useState(false)
  const [regraLocal, setRegraLocal] = useState<Record<string, RegraAprovacao>>({ ...regras })
  const [salvando, setSalvando] = useState(false)

  const podeEditar = projeto.eh_proprietario || projeto.eh_ceo

  useEffect(() => {
    const r = projeto.regras_aprovacao && Object.keys(projeto.regras_aprovacao).length > 0
      ? projeto.regras_aprovacao
      : regras_padrao
    setRegraLocal({ ...r })
  }, [projeto.regras_aprovacao])

  const handleSalvar = async () => {
    setSalvando(true)
    try {
      const r = await atualizarRegrasAprovacao(projeto.id, regraLocal)
      onMensagem(r.mensagem)
      onAtualizar()
      setEditando(false)
    } catch (e) {
      onMensagem(e instanceof Error ? e.message : 'Erro ao salvar regras')
    }
    setSalvando(false)
  }

  const tipos = [
    { key: 'pequena', label: 'Pequena', cor: '#10b981' },
    { key: 'grande', label: 'Grande', cor: '#f59e0b' },
    { key: 'critica', label: 'Critica', cor: '#ef4444' },
  ]

  return (
    <div className="sf-glass border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="sf-text-dim" />
          <p className="text-xs sf-text-dim font-semibold uppercase tracking-wider">Regras de Aprovacao</p>
        </div>
        {podeEditar && !editando && (
          <button onClick={() => setEditando(true)}
            className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 sf-text-dim transition-colors">
            <Edit3 size={10} /> Editar
          </button>
        )}
        {editando && (
          <div className="flex gap-1.5">
            <button onClick={handleSalvar} disabled={salvando}
              className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors disabled:opacity-50">
              {salvando ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />} Salvar
            </button>
            <button onClick={() => { setEditando(false); setRegraLocal({ ...regras }) }}
              className="text-[10px] px-2.5 py-1 rounded-lg bg-white/5 sf-text-dim hover:bg-white/10 transition-colors">
              Cancelar
            </button>
          </div>
        )}
      </div>

      <div className="space-y-2.5">
        {tipos.map(t => {
          const regra = regraLocal[t.key] || regras_padrao[t.key]
          return (
            <div key={t.key} className="flex items-center gap-3">
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-md border flex-shrink-0 w-16 text-center"
                style={{ color: t.cor, backgroundColor: `${t.cor}10`, borderColor: `${t.cor}25` }}>
                {t.label}
              </span>

              {editando ? (
                <>
                  <input
                    value={regra.descricao}
                    onChange={e => setRegraLocal(prev => ({
                      ...prev,
                      [t.key]: { ...prev[t.key], descricao: e.target.value },
                    }))}
                    className="flex-1 text-xs bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 sf-text-dim outline-none focus:border-emerald-500/50"
                    placeholder="Descricao..."
                  />
                  <select
                    value={regra.aprovador}
                    onChange={e => setRegraLocal(prev => ({
                      ...prev,
                      [t.key]: { ...prev[t.key], aprovador: e.target.value },
                    }))}
                    className="text-[11px] bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 sf-text-dim outline-none focus:border-emerald-500/50"
                  >
                    <option value="lider_tecnico">Lider Tecnico</option>
                    <option value="proprietario">Proprietario</option>
                    <option value="ambos">Proprietario + Lider</option>
                    <option value="nenhum">Auto-aprovacao</option>
                  </select>
                </>
              ) : (
                <>
                  <span className="text-xs sf-text-dim flex-1">{regra.descricao}</span>
                  <span className="text-xs sf-text-dim font-medium">{aprovadorLabels[regra.aprovador] || regra.aprovador}</span>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


/* ================================================================ */
/* Secao Version Control (VCS)                                       */
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
    if (!confirm('Remover configuracao VCS deste projeto?')) return
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
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded"
              style={{ background: vcs.vcs_tipo === 'github' ? 'rgba(36,41,47,0.3)' : 'rgba(139,92,246,0.1)', color: vcs.vcs_tipo === 'github' ? '#e6edf3' : '#a78bfa' }}>
              {vcs.vcs_tipo === 'github' ? 'GitHub' : 'GitBucket'}
            </span>
            <span className="text-xs sf-text-dim font-mono truncate">{vcs.repo_url}</span>
          </div>
          <p className="text-[10px] sf-text-ghost">Branch: <span className="sf-text-dim font-mono">{vcs.branch_padrao}</span> | Token: <span className="text-emerald-400">***configurado***</span></p>
        </div>
      ) : (
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
            <p className="text-[10px] sf-text-ghost mb-1">URL do Repositorio</p>
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
            <p className="text-[10px] sf-text-ghost mb-1">Branch Padrao</p>
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
