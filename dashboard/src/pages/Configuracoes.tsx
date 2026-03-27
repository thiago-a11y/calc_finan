/* Configurações — Gestão premium dark-mode (zero emojis, zero fundos claros) */

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import PermissoesGranulares from '../components/PermissoesGranulares'
import {
  buscarUsuarios, editarUsuario, atualizarPermissoes,
  desativarUsuario, buscarPapeisDisponiveis, buscarAreasAprovacao,
  enviarConvite, listarConvites,
} from '../services/api'
import type { ConvitePendente } from '../services/api'
import type { Usuario, PapelDisponivel, AreaAprovacaoDisponivel } from '../types'
import {
  Users, ShieldCheck, Settings, X, Pencil, UserX,
  CheckCircle2, Crown, Briefcase, Shield, Target,
  Rocket, Megaphone, AlertTriangle, Lock,
  Server, Cpu, Globe, Mail, Copy, Clock, Send, UserPlus,
  type LucideIcon,
} from 'lucide-react'

type Aba = 'usuarios' | 'permissoes' | 'sistema'

const avatarCores = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#6366f1', '#ef4444', '#14b8a6']

const papelIcons: Record<string, LucideIcon> = {
  ceo: Crown, diretor_tecnico: Briefcase, operations_lead: Shield,
  pm_central: Target, lider: Users, desenvolvedor: Rocket,
  marketing: Megaphone, financeiro: Briefcase, suporte: Globe, membro: Users,
}


export default function Configuracoes() {
  const { usuario: eu } = useAuth()
  const [aba, setAba] = useState<Aba>('usuarios')
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [papeis, setPapeis] = useState<PapelDisponivel[]>([])
  const [areas, setAreas] = useState<AreaAprovacaoDisponivel[]>([])
  const [mensagem, setMensagem] = useState('')
  const [erro, setErro] = useState('')

  const carregarDados = useCallback(async () => {
    try {
      const [u, p, a] = await Promise.all([
        buscarUsuarios(), buscarPapeisDisponiveis(), buscarAreasAprovacao(),
      ])
      setUsuarios(u); setPapeis(p); setAreas(a)
    } catch { setErro('Erro ao carregar dados.') }
  }, [])

  useEffect(() => { carregarDados() }, [carregarDados])

  const isAdmin = eu?.papeis?.some(p => ['ceo', 'operations_lead', 'diretor_tecnico'].includes(p))

  if (!isAdmin) {
    return (
      <div className="sf-page flex items-center justify-center">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 max-w-md text-center">
          <AlertTriangle size={32} className="text-red-400 mx-auto mb-3" />
          <p className="text-red-300 text-sm">Apenas CEO, Diretor Técnico ou Operations Lead podem acessar.</p>
        </div>
      </div>
    )
  }

  const abas: { id: Aba; label: string; icon: LucideIcon }[] = [
    { id: 'usuarios', label: 'Usuários', icon: Users },
    { id: 'permissoes', label: 'Permissões', icon: ShieldCheck },
    { id: 'sistema', label: 'Sistema', icon: Settings },
  ]

  return (
    <div className="sf-page">
      <div className="fixed top-0 left-1/4 w-[500px] h-[300px] bg-indigo-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
          Configurações
        </h2>
        <p className="text-sm sf-text-dim mt-1">Gerencie usuários, permissões e sistema</p>
      </div>

      {/* Feedback */}
      {mensagem && (
        <div className="mb-4 px-4 py-3 rounded-xl text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-2">
          <CheckCircle2 size={14} /> {mensagem}
        </div>
      )}
      {erro && (
        <div className="mb-4 px-4 py-3 rounded-xl text-sm bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2">
          <AlertTriangle size={14} /> {erro}
        </div>
      )}

      {/* Abas */}
      <div className="flex gap-1 mb-8 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-1 w-fit">
        {abas.map((a) => {
          const Icon = a.icon
          return (
            <button
              key={a.id}
              onClick={() => { setAba(a.id); setMensagem(''); setErro('') }}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-medium transition-all duration-300 ${
                aba === a.id
                  ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                  : 'sf-text-dim hover:sf-text-dim hover:bg-white/5'
              }`}
            >
              <Icon size={14} strokeWidth={2} />
              {a.label}
            </button>
          )
        })}
      </div>

      {aba === 'usuarios' && (
        <AbaUsuarios usuarios={usuarios} papeis={papeis}
          onRecarregar={carregarDados} setMensagem={setMensagem} setErro={setErro} />
      )}
      {aba === 'permissoes' && (
        <AbaPermissoes usuarios={usuarios} papeis={papeis} areas={areas}
          onRecarregar={carregarDados} setMensagem={setMensagem} setErro={setErro} />
      )}
      {aba === 'sistema' && <AbaSistema />}
    </div>
  )
}


/* ================================================================ */
/* ABA: USUÁRIOS                                                     */
/* ================================================================ */

function AbaUsuarios({ usuarios, papeis, onRecarregar, setMensagem, setErro }: {
  usuarios: Usuario[]; papeis: PapelDisponivel[]
  onRecarregar: () => void; setMensagem: (m: string) => void; setErro: (e: string) => void
}) {
  const [mostrarForm, setMostrarForm] = useState(false)
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [novoNome, setNovoNome] = useState('')
  const [novoEmail, setNovoEmail] = useState('')
  const [novoCargo, setNovoCargo] = useState('')
  const [novoPapeis, setNovoPapeis] = useState<string[]>([])
  const [editNome, setEditNome] = useState('')
  const [editCargo, setEditCargo] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [convites, setConvites] = useState<ConvitePendente[]>([])
  const [linkCopiado, setLinkCopiado] = useState<string | null>(null)

  useEffect(() => {
    listarConvites().then(setConvites).catch(() => {})
  }, [])

  const limparForm = () => {
    setNovoNome(''); setNovoEmail(''); setNovoCargo(''); setNovoPapeis([])
    setMostrarForm(false)
  }

  const enviarNovoConvite = async () => {
    if (!novoNome || !novoEmail) { setErro('Nome e email sao obrigatorios.'); return }
    setSalvando(true); setErro('')
    try {
      const resultado = await enviarConvite({
        email: novoEmail, nome: novoNome, cargo: novoCargo,
        papeis: novoPapeis, enviar_email: true,
      })
      if (resultado.email_enviado) {
        setMensagem(`Convite enviado para ${novoNome} (${novoEmail})! O usuario recebera um email com link para criar a senha.`)
      } else {
        setMensagem(`Convite criado para ${novoNome}. Link: ${resultado.link_registro} (email nao enviado — copie o link manualmente).`)
      }
      limparForm()
      listarConvites().then(setConvites).catch(() => {})
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erro ao enviar convite.'
      if (msg.includes('409')) setErro('Este email ja esta cadastrado ou ja tem um convite pendente.')
      else setErro(msg)
    }
    finally { setSalvando(false) }
  }

  const copiarLink = (convite: ConvitePendente) => {
    const url = `${window.location.origin}/registrar?token=${convite.token}`
    navigator.clipboard.writeText(url)
    setLinkCopiado(convite.token)
    setTimeout(() => setLinkCopiado(null), 2000)
  }

  const salvarEdicao = async (id: string) => {
    setSalvando(true); setErro('')
    try {
      await editarUsuario(id, { nome: editNome, cargo: editCargo, email: editEmail })
      setMensagem('Atualizado!'); setEditandoId(null); onRecarregar()
    } catch (e: unknown) { setErro(e instanceof Error ? e.message : 'Erro.') }
    finally { setSalvando(false) }
  }

  const confirmarDesativar = async (u: Usuario) => {
    if (!confirm(`Desativar "${u.nome}"?`)) return
    try { await desativarUsuario(u.id); setMensagem(`"${u.nome}" desativado.`); onRecarregar() }
    catch (e: unknown) { setErro(e instanceof Error ? e.message : 'Erro.') }
  }

  const papelLabel = (id: string) => papeis.find(p => p.id === id)?.nome || id

  const inputClasses = "w-full sf-glass border sf-border rounded-lg px-3 py-2.5 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"

  const convitesPendentes = convites.filter(c => !c.usado)

  return (
    <div className="relative">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold sf-text-white">
          Usuarios <span className="sf-text-ghost font-normal">({usuarios.length})</span>
        </h3>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
            mostrarForm
              ? 'bg-white/5 sf-text-dim border border-white/10'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/30'
          }`}
        >
          {mostrarForm ? <><X size={14} /> Cancelar</> : <><UserPlus size={14} /> Convidar Membro</>}
        </button>
      </div>

      {/* Form convite */}
      {mostrarForm && (
        <div className="sf-glass border sf-border rounded-2xl p-6 mb-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Mail size={18} className="text-emerald-400" />
            </div>
            <div>
              <h4 className="font-semibold sf-text-white">Convidar Novo Membro</h4>
              <p className="text-xs sf-text-dim">Um email sera enviado com o link para criar a conta</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs sf-text-dim uppercase tracking-wider mb-1.5">Nome *</label>
              <input value={novoNome} onChange={e => setNovoNome(e.target.value)}
                className={inputClasses} placeholder="Nome completo" />
            </div>
            <div>
              <label className="block text-xs sf-text-dim uppercase tracking-wider mb-1.5">Email *</label>
              <input value={novoEmail} onChange={e => setNovoEmail(e.target.value)} type="email"
                className={inputClasses} placeholder="email@objetivasolucao.com.br" />
            </div>
            <div>
              <label className="block text-xs sf-text-dim uppercase tracking-wider mb-1.5">Cargo</label>
              <input value={novoCargo} onChange={e => setNovoCargo(e.target.value)}
                className={inputClasses} placeholder="Ex: Desenvolvedor Senior" />
            </div>
          </div>

          <div className="mt-5">
            <label className="block text-xs sf-text-dim uppercase tracking-wider mb-2">Papeis</label>
            <div className="flex flex-wrap gap-2">
              {papeis.map(p => {
                const selected = novoPapeis.includes(p.id)
                return (
                  <button key={p.id} type="button"
                    onClick={() => setNovoPapeis(prev => prev.includes(p.id) ? prev.filter(x => x !== p.id) : [...prev, p.id])}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
                      selected
                        ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                        : 'sf-glass sf-text-dim hover:border-white/15'
                    }`}>
                    {p.nome}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="mt-5 px-4 py-3 rounded-xl bg-blue-500/5 border border-blue-500/10">
            <div className="flex items-start gap-2">
              <Mail size={14} className="text-blue-400 mt-0.5 shrink-0" />
              <p className="text-xs text-blue-300/80">
                O membro recebera um email via Amazon SES com um link para criar sua senha.
                O convite expira em 7 dias. Permissoes de aprovacao podem ser configuradas depois na aba Permissoes.
              </p>
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            <button onClick={enviarNovoConvite} disabled={salvando}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50 transition-all">
              <Send size={14} />
              {salvando ? 'Enviando...' : 'Enviar Convite'}
            </button>
            <button onClick={limparForm}
              className="px-5 py-2.5 bg-white/5 sf-text-dim border border-white/10 rounded-xl text-sm hover:bg-white/10 transition-all">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Convites pendentes */}
      {convitesPendentes.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium sf-text-dim mb-3 flex items-center gap-2">
            <Clock size={14} /> Convites Pendentes ({convitesPendentes.length})
          </h4>
          <div className="space-y-2">
            {convitesPendentes.map(c => (
              <div key={c.id} className="sf-glass border border-amber-500/10 rounded-xl p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                    <Mail size={14} className="text-amber-400" />
                  </div>
                  <div>
                    <span className="text-sm sf-text-white">{c.nome || c.email}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs sf-text-dim font-mono">{c.email}</span>
                      {c.cargo && <span className="text-xs sf-text-ghost">· {c.cargo}</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] sf-text-ghost">
                    Expira: {new Date(c.expira_em).toLocaleDateString('pt-BR')}
                  </span>
                  <button
                    onClick={() => copiarLink(c)}
                    className="flex items-center gap-1 px-2.5 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs sf-text-dim hover:bg-white/10 transition-all"
                    title="Copiar link de registro"
                  >
                    {linkCopiado === c.token ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
                    {linkCopiado === c.token ? 'Copiado' : 'Link'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lista de usuarios ativos */}
      <div className="space-y-3">
        {usuarios.map((u, idx) => {
          const cor = avatarCores[idx % avatarCores.length]
          const iniciais = u.nome.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()

          return (
            <div key={u.id} className="group sf-glass border sf-border rounded-xl p-4 transition-all duration-300 hover:border-white/15">
              {editandoId === u.id ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input value={editNome} onChange={e => setEditNome(e.target.value)}
                      className={inputClasses} placeholder="Nome" />
                    <input value={editEmail} onChange={e => setEditEmail(e.target.value)}
                      className={inputClasses} placeholder="Email" />
                    <input value={editCargo} onChange={e => setEditCargo(e.target.value)}
                      className={inputClasses} placeholder="Cargo" />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => salvarEdicao(u.id)} disabled={salvando}
                      className="px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-medium hover:bg-emerald-500/30 disabled:opacity-50">
                      {salvando ? 'Salvando...' : 'Salvar'}
                    </button>
                    <button onClick={() => setEditandoId(null)}
                      className="px-4 py-2 bg-white/5 sf-text-dim border border-white/10 rounded-lg text-xs hover:bg-white/10">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold tracking-wide"
                      style={{ backgroundColor: `${cor}15`, border: `1.5px solid ${cor}30`, color: cor }}>
                      {iniciais}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium sf-text-white text-sm">{u.nome}</span>
                        {u.pode_aprovar && (
                          <div className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md">
                            <ShieldCheck size={10} className="text-emerald-400" />
                            <span className="text-[10px] text-emerald-400 font-medium">Aprovador</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs sf-text-dim font-mono">{u.email}</span>
                        {u.cargo && <span className="text-xs sf-text-ghost">· {u.cargo}</span>}
                      </div>
                      <div className="flex gap-1.5 mt-1.5">
                        {u.papeis.map(p => {
                          const Icon = papelIcons[p] || Users
                          return (
                            <div key={p} className="flex items-center gap-1 px-2 py-0.5 sf-glass border rounded-md">
                              <Icon size={10} className="sf-text-dim" />
                              <span className="text-[10px] sf-text-dim">{papelLabel(p)}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => { setEditandoId(u.id); setEditNome(u.nome); setEditEmail(u.email); setEditCargo(u.cargo) }}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 sf-text-dim rounded-lg text-xs hover:bg-white/10 transition-all">
                      <Pencil size={11} /> Editar
                    </button>
                    <button
                      onClick={() => confirmarDesativar(u)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs hover:bg-red-500/20 transition-all">
                      <UserX size={11} /> Desativar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


/* ================================================================ */
/* ABA: PERMISSÕES                                                   */
/* ================================================================ */

function AbaPermissoes({ usuarios, papeis, areas, onRecarregar, setMensagem, setErro }: {
  usuarios: Usuario[]; papeis: PapelDisponivel[]; areas: AreaAprovacaoDisponivel[]
  onRecarregar: () => void; setMensagem: (m: string) => void; setErro: (e: string) => void
}) {
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [editPapeis, setEditPapeis] = useState<string[]>([])
  const [editPodeAprovar, setEditPodeAprovar] = useState(false)
  const [editAreas, setEditAreas] = useState<string[]>([])
  const [salvando, setSalvando] = useState(false)

  const iniciarEdicao = (u: Usuario) => {
    setEditandoId(u.id); setEditPapeis(u.papeis || [])
    setEditPodeAprovar(u.pode_aprovar); setEditAreas(u.areas_aprovacao || [])
  }

  const salvarPermissoes = async (id: string) => {
    setSalvando(true); setErro('')
    try {
      await atualizarPermissoes(id, {
        papeis: editPapeis, pode_aprovar: editPodeAprovar,
        areas_aprovacao: editPodeAprovar ? editAreas : [],
      })
      setMensagem('Permissões atualizadas!'); setEditandoId(null); onRecarregar()
    } catch (e: unknown) { setErro(e instanceof Error ? e.message : 'Erro.') }
    finally { setSalvando(false) }
  }

  const papelLabel = (id: string) => papeis.find(p => p.id === id)?.nome || id
  const areaLabel = (id: string) => areas.find(a => a.id === id)?.nome || id

  return (
    <div className="relative">
      <h3 className="text-lg font-semibold sf-text-white mb-6">Permissões por Usuário</h3>

      <div className="space-y-3">
        {usuarios.map((u, idx) => {
          const cor = avatarCores[idx % avatarCores.length]
          const iniciais = u.nome.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()

          return (
            <div key={u.id} className="sf-glass border sf-border rounded-xl p-5 transition-all duration-300 hover:border-white/15">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold"
                    style={{ backgroundColor: `${cor}15`, border: `1.5px solid ${cor}30`, color: cor }}>
                    {iniciais}
                  </div>
                  <div>
                    <span className="font-medium sf-text-white">{u.nome}</span>
                    <p className="text-xs sf-text-dim font-mono">{u.email}</p>
                  </div>
                </div>
                {editandoId !== u.id && (
                  <button onClick={() => iniciarEdicao(u)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 sf-text-dim rounded-lg text-xs hover:bg-white/10 transition-all">
                    <Pencil size={11} /> Editar
                  </button>
                )}
              </div>

              {editandoId === u.id ? (
                <div className="mt-4 space-y-4 pt-4 border-t sf-border">
                  <div>
                    <label className="block text-xs sf-text-dim uppercase tracking-wider mb-2">Papéis</label>
                    <div className="flex flex-wrap gap-2">
                      {papeis.map(p => (
                        <button key={p.id} type="button"
                          onClick={() => setEditPapeis(prev => prev.includes(p.id) ? prev.filter(x => x !== p.id) : [...prev, p.id])}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                            editPapeis.includes(p.id)
                              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                              : 'sf-glass sf-text-dim hover:border-white/15'
                          }`}>
                          {p.nome}
                        </button>
                      ))}
                    </div>
                  </div>

                  <label className="flex items-center gap-2.5 text-sm cursor-pointer">
                    <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                      editPodeAprovar ? 'bg-emerald-500/20 border-emerald-500/40' : 'border-white/15 bg-white/[0.02]'
                    }`} onClick={() => setEditPodeAprovar(!editPodeAprovar)}>
                      {editPodeAprovar && <CheckCircle2 size={12} className="text-emerald-400" />}
                    </div>
                    <span className="sf-text-dim">Pode aprovar solicitações</span>
                  </label>

                  {editPodeAprovar && (
                    <div className="ml-6">
                      <label className="block text-xs sf-text-dim uppercase tracking-wider mb-2">Áreas</label>
                      <div className="flex flex-wrap gap-2">
                        {areas.map(a => (
                          <button key={a.id} type="button"
                            onClick={() => setEditAreas(prev => prev.includes(a.id) ? prev.filter(x => x !== a.id) : [...prev, a.id])}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                              editAreas.includes(a.id)
                                ? 'bg-blue-500/15 border-blue-500/30 text-blue-400'
                                : 'sf-glass sf-text-dim hover:border-white/15'
                            }`}>
                            {a.nome}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-4 border-t sf-border">
                    <PermissoesGranulares usuario={u}
                      onSalvo={() => { onRecarregar(); setMensagem('Permissões granulares salvas!') }} />
                  </div>

                  <div className="flex gap-2 pt-4 border-t sf-border">
                    <button onClick={() => salvarPermissoes(u.id)} disabled={salvando}
                      className="px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50">
                      {salvando ? 'Salvando...' : 'Salvar'}
                    </button>
                    <button onClick={() => setEditandoId(null)}
                      className="px-4 py-2 bg-white/5 sf-text-dim border border-white/10 rounded-lg text-sm hover:bg-white/10">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 pt-3 border-t sf-border">
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {u.papeis.map(p => {
                      const Icon = papelIcons[p] || Users
                      return (
                        <div key={p} className="flex items-center gap-1 px-2 py-0.5 sf-glass border rounded-md">
                          <Icon size={10} className="sf-text-dim" />
                          <span className="text-[10px] sf-text-dim">{papelLabel(p)}</span>
                        </div>
                      )
                    })}
                    {u.papeis.length === 0 && <span className="text-xs sf-text-ghost">Sem papéis</span>}
                  </div>
                  {u.pode_aprovar && u.areas_aprovacao?.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <ShieldCheck size={12} className="text-emerald-400" />
                      {u.areas_aprovacao.map(a => (
                        <span key={a} className="text-[10px] sf-text-dim sf-glass px-2 py-0.5 rounded border" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                          {areaLabel(a)}
                        </span>
                      ))}
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


/* ================================================================ */
/* ABA: SISTEMA                                                      */
/* ================================================================ */

function AbaSistema() {
  const sections: { title: string; icon: LucideIcon; items: [string, string][] }[] = [
    {
      title: 'Versão', icon: Server,
      items: [['Versão', 'v0.15.0'], ['Ambiente', 'development'], ['Backend', 'FastAPI + SQLite'], ['Frontend', 'React + Vite + Tailwind']],
    },
    {
      title: 'Autenticação', icon: Lock,
      items: [['Método', 'JWT HS256'], ['Access Token', '1 hora'], ['Refresh Token', '30 dias'], ['Senha', 'bcrypt cost 12'], ['Bloqueio', '10 tentativas / 30 min']],
    },
    {
      title: 'Integrações', icon: Cpu,
      items: [['LLM Principal', 'Claude (Anthropic)'], ['Fallback', 'Groq → Fireworks → Together'], ['Observabilidade', 'LangSmith'], ['Agentes', 'CrewAI + LangGraph'], ['Embeddings', 'OpenAI text-embedding-3-small'], ['Vector Store', 'ChromaDB']],
    },
    {
      title: 'Limites', icon: Shield,
      items: [['Gasto IA sem aprovação', 'R$ 50,00'], ['Multi-tenant', 'Sim (company_id)'], ['LGPD', 'Audit Log ativo']],
    },
  ]

  return (
    <div className="relative">
      <h3 className="text-lg font-semibold sf-text-white mb-6">Informações do Sistema</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map(({ title, icon: Icon, items }) => (
          <div key={title} className="sf-glass border sf-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Icon size={16} className="sf-text-dim" strokeWidth={1.8} />
              <h4 className="font-medium sf-text-dim">{title}</h4>
            </div>
            <div className="space-y-2.5">
              {items.map(([label, value]) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-xs sf-text-dim">{label}</span>
                  <span className="text-xs sf-text-dim font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
