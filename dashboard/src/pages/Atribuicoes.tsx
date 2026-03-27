/* Atribuicoes — Gerenciar agentes atribuidos aos usuarios */

import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  buscarUsuarios,
  buscarAgentesUsuario,
  buscarCatalogo,
  atribuirAgente,
  removerAtribuicao,
} from '../services/api'
import type { Usuario, AgenteAtribuido, AgenteCatalogo } from '../types'
import {
  ChevronDown,
  Plus,
  Trash2,
  X,
  PackageOpen,
  Code2,
  Server,
  Palette,
  Brain,
  Plug,
  Cloud,
  ShieldCheck,
  ClipboardList,
  FileText,
  SearchCode,
  Network,
  Lock,
  Bot,
  type LucideIcon,
} from 'lucide-react'

/* --- Mapa de icones estatico (lucide-react) --- */
const iconeMapa: Record<string, LucideIcon> = {
  Code2,
  Server,
  Palette,
  Brain,
  Plug,
  Cloud,
  ShieldCheck,
  ClipboardList,
  FileText,
  SearchCode,
  Network,
  Lock,
  Bot,
}

function resolverIcone(nome?: string): LucideIcon {
  if (!nome) return Bot
  return iconeMapa[nome] ?? Bot
}

/* --- Verificacao de admin --- */
const PAPEIS_ADMIN = ['ceo', 'diretor_tecnico', 'operations_lead']

function ehAdmin(papeis: string[]): boolean {
  return papeis.some((p) => PAPEIS_ADMIN.includes(p))
}

/* --- Cores por categoria --- */
const categoriaCor: Record<string, string> = {
  desenvolvimento: '#6366f1',
  infraestrutura: '#3b82f6',
  design: '#ec4899',
  ia: '#8b5cf6',
  integracao: '#f59e0b',
  cloud: '#06b6d4',
  seguranca: '#10b981',
  gestao: '#f97316',
  documentacao: '#84cc16',
  pesquisa: '#14b8a6',
}

function corCategoria(categoria?: string): string {
  if (!categoria) return '#6b7280'
  return categoriaCor[categoria.toLowerCase()] ?? '#6b7280'
}

export default function Atribuicoes() {
  const { usuario: usuarioLogado } = useAuth()
  const admin = usuarioLogado ? ehAdmin(usuarioLogado.papeis) : false

  /* --- Estados --- */
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [usuarioSelecionadoId, setUsuarioSelecionadoId] = useState<number | null>(null)
  const [agentes, setAgentes] = useState<AgenteAtribuido[]>([])
  const [catalogo, setCatalogo] = useState<AgenteCatalogo[]>([])
  const [carregandoUsuarios, setCarregandoUsuarios] = useState(true)
  const [carregandoAgentes, setCarregandoAgentes] = useState(false)
  const [modalAberto, setModalAberto] = useState(false)
  const [carregandoCatalogo, setCarregandoCatalogo] = useState(false)
  const [atribuindo, setAtribuindo] = useState<number | null>(null)
  const [removendo, setRemovendo] = useState<number | null>(null)
  const [confirmarRemocao, setConfirmarRemocao] = useState<number | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [dropdownAberto, setDropdownAberto] = useState(false)

  /* --- Carregar usuarios --- */
  useEffect(() => {
    buscarUsuarios()
      .then((lista) => {
        setUsuarios(lista)
        /* Se nao for admin, selecionar o proprio usuario */
        if (!admin && usuarioLogado) {
          const proprio = lista.find((u) => u.id === usuarioLogado.id)
          if (proprio) setUsuarioSelecionadoId(Number(proprio.id))
        }
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregandoUsuarios(false))
  }, [])

  /* --- Carregar agentes do usuario selecionado --- */
  const carregarAgentes = useCallback(async () => {
    if (!usuarioSelecionadoId) {
      setAgentes([])
      return
    }
    setCarregandoAgentes(true)
    setErro(null)
    try {
      const lista = await buscarAgentesUsuario(usuarioSelecionadoId)
      setAgentes(lista)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao carregar agentes')
    } finally {
      setCarregandoAgentes(false)
    }
  }, [usuarioSelecionadoId])

  useEffect(() => {
    carregarAgentes()
  }, [carregarAgentes])

  /* --- Abrir modal do catalogo --- */
  const abrirCatalogo = async () => {
    setModalAberto(true)
    setCarregandoCatalogo(true)
    try {
      const lista = await buscarCatalogo()
      setCatalogo(lista)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao carregar catalogo')
    } finally {
      setCarregandoCatalogo(false)
    }
  }

  /* --- Atribuir agente --- */
  const handleAtribuir = async (agenteCatalogoId: number) => {
    if (!usuarioSelecionadoId) return
    setAtribuindo(agenteCatalogoId)
    try {
      await atribuirAgente(agenteCatalogoId, usuarioSelecionadoId)
      await carregarAgentes()
      /* Atualizar catalogo para refletir total_usuarios */
      const novosCatalogo = await buscarCatalogo()
      setCatalogo(novosCatalogo)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao atribuir agente')
    } finally {
      setAtribuindo(null)
    }
  }

  /* --- Remover atribuicao --- */
  const handleRemover = async (id: number) => {
    setRemovendo(id)
    try {
      await removerAtribuicao(id)
      setConfirmarRemocao(null)
      await carregarAgentes()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao remover atribuicao')
    } finally {
      setRemovendo(null)
    }
  }

  /* --- Usuario selecionado --- */
  const usuarioSelecionado = usuarios.find((u) => Number(u.id) === usuarioSelecionadoId)

  /* --- IDs ja atribuidos (para desabilitar no catalogo) --- */
  const idsAtribuidos = new Set(agentes.map((a) => a.agente_catalogo_id))

  /* --- Loading inicial --- */
  if (carregandoUsuarios) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="sf-page">
      {/* Glow sutil */}
      <div
        className="fixed top-0 left-1/3 w-[500px] h-[300px] bg-indigo-500/5 blur-[120px] pointer-events-none sf-glow"
        style={{ opacity: 'var(--sf-glow-opacity)' }}
      />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
          Atribuicoes de Agentes
        </h2>
        <p className="text-sm sf-text-dim mt-1">
          Gerencie quais agentes estao vinculados a cada usuario
        </p>
      </div>

      {/* Dropdown de usuarios */}
      <div className="relative mb-6 max-w-md">
        <label className="block text-[10px] sf-text-ghost uppercase tracking-wider font-medium mb-2">
          Usuario
        </label>
        <button
          onClick={() => setDropdownAberto(!dropdownAberto)}
          className="w-full flex items-center justify-between gap-2 px-4 py-3 sf-glass border sf-border rounded-xl text-sm sf-text-white hover:border-white/15 transition-colors cursor-pointer"
        >
          <span>{usuarioSelecionado ? usuarioSelecionado.nome : 'Selecione um usuario'}</span>
          <ChevronDown
            size={16}
            className={`sf-text-dim transition-transform ${dropdownAberto ? 'rotate-180' : ''}`}
          />
        </button>

        {dropdownAberto && (
          <div className="absolute z-50 mt-1 w-full sf-glass border sf-border rounded-xl overflow-hidden shadow-2xl max-h-60 overflow-y-auto">
            {usuarios.map((u) => (
              <button
                key={u.id}
                onClick={() => {
                  setUsuarioSelecionadoId(Number(u.id))
                  setDropdownAberto(false)
                }}
                className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-white/5 cursor-pointer ${
                  Number(u.id) === usuarioSelecionadoId
                    ? 'sf-text-white bg-white/5'
                    : 'sf-text-dim'
                }`}
              >
                <span className="font-medium">{u.nome}</span>
                <span className="ml-2 text-xs sf-text-ghost">{u.cargo}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Erro global */}
      {erro && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <span>{erro}</span>
          <button onClick={() => setErro(null)} className="ml-4 hover:text-red-300 cursor-pointer">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Conteudo principal */}
      {!usuarioSelecionadoId ? (
        /* Nenhum usuario selecionado */
        <div className="flex flex-col items-center justify-center py-20 sf-glass border sf-border rounded-2xl">
          <PackageOpen size={48} className="sf-text-ghost mb-4" strokeWidth={1} />
          <p className="sf-text-dim text-sm">Selecione um usuario para ver os agentes atribuidos</p>
        </div>
      ) : carregandoAgentes ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Barra de acoes */}
          <div className="flex items-center justify-between mb-6">
            <p className="text-sm sf-text-dim">
              {agentes.length} agente{agentes.length !== 1 ? 's' : ''} atribuido{agentes.length !== 1 ? 's' : ''}
            </p>
            {admin && (
              <button
                onClick={abrirCatalogo}
                className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-sm text-emerald-400 font-medium hover:bg-emerald-500/20 hover:border-emerald-500/30 transition-all cursor-pointer"
              >
                <Plus size={16} />
                Adicionar do Catalogo
              </button>
            )}
          </div>

          {/* Lista de agentes ou empty state */}
          {agentes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 sf-glass border sf-border rounded-2xl">
              <Bot size={48} className="sf-text-ghost mb-4" strokeWidth={1} />
              <p className="sf-text-dim text-sm mb-1">Nenhum agente atribuido</p>
              <p className="sf-text-ghost text-xs">
                {admin
                  ? 'Clique em "Adicionar do Catalogo" para vincular agentes a este usuario'
                  : 'Solicite ao administrador a atribuicao de agentes'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {agentes.map((agente) => {
                const Icone = resolverIcone(agente.icone)
                const cor = corCategoria(agente.categoria)
                const confirmando = confirmarRemocao === agente.id

                return (
                  <div
                    key={agente.id}
                    className="group relative sf-glass backdrop-blur-sm border sf-border rounded-2xl p-5 transition-all duration-500 hover:border-white/15 hover:-translate-y-0.5"
                  >
                    {/* Glow hover */}
                    <div
                      className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                      style={{ background: `radial-gradient(ellipse at top left, ${cor}08, transparent 60%)` }}
                    />

                    <div className="relative">
                      {/* Cabecalho do card */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-105"
                            style={{
                              backgroundColor: `${cor}15`,
                              border: `2px solid ${cor}30`,
                            }}
                          >
                            <Icone size={18} style={{ color: cor }} strokeWidth={1.8} />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold sf-text-white">{agente.nome_agente}</h3>
                            <p className="text-[11px] sf-text-ghost">{agente.perfil_agente}</p>
                          </div>
                        </div>

                        {/* Botao remover */}
                        {admin && (
                          <div className="relative">
                            {confirmando ? (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleRemover(agente.id)}
                                  disabled={removendo === agente.id}
                                  className="px-2 py-1 text-[10px] font-medium bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 hover:bg-red-500/30 transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  {removendo === agente.id ? 'Removendo...' : 'Confirmar'}
                                </button>
                                <button
                                  onClick={() => setConfirmarRemocao(null)}
                                  className="px-2 py-1 text-[10px] sf-text-ghost hover:sf-text-dim transition-colors cursor-pointer"
                                >
                                  Cancelar
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setConfirmarRemocao(agente.id)}
                                className="p-1.5 rounded-lg sf-text-ghost hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100 cursor-pointer"
                                title="Remover atribuicao"
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Categoria e status */}
                      <div className="flex items-center gap-2 mt-3">
                        <span
                          className="inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-medium border"
                          style={{
                            backgroundColor: `${cor}10`,
                            borderColor: `${cor}20`,
                            color: cor,
                          }}
                        >
                          {agente.categoria || 'Sem categoria'}
                        </span>
                        {agente.ativo ? (
                          <span className="inline-flex items-center px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-[10px] text-emerald-400 font-medium">
                            Ativo
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 bg-red-500/10 border border-red-500/20 rounded-lg text-[10px] text-red-400 font-medium">
                            Inativo
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* Modal do catalogo */}
      {modalAberto && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setModalAberto(false)}
          />

          {/* Painel do modal */}
          <div className="relative w-full max-w-2xl max-h-[80vh] mx-4 sf-glass border sf-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            {/* Header do modal */}
            <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--sf-border-subtle)' }}>
              <div>
                <h3 className="text-lg font-semibold sf-text-white">Catalogo de Agentes</h3>
                <p className="text-xs sf-text-dim mt-0.5">
                  Selecione agentes para atribuir a {usuarioSelecionado?.nome}
                </p>
              </div>
              <button
                onClick={() => setModalAberto(false)}
                className="p-2 rounded-lg sf-text-ghost hover:sf-text-dim hover:bg-white/5 transition-all cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Conteudo do modal */}
            <div className="flex-1 overflow-y-auto p-6">
              {carregandoCatalogo ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
                </div>
              ) : catalogo.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <PackageOpen size={40} className="sf-text-ghost mb-3" strokeWidth={1} />
                  <p className="sf-text-dim text-sm">Nenhum agente disponivel no catalogo</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {catalogo.map((item) => {
                    const Icone = resolverIcone(item.icone)
                    const cor = corCategoria(item.categoria)
                    const jaAtribuido = idsAtribuidos.has(item.id)
                    const atribuindoEste = atribuindo === item.id

                    return (
                      <div
                        key={item.id}
                        className={`flex items-center gap-4 p-4 sf-glass border sf-border rounded-xl transition-all ${
                          jaAtribuido ? 'opacity-50' : 'hover:border-white/15'
                        }`}
                      >
                        {/* Icone */}
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                          style={{
                            backgroundColor: `${cor}15`,
                            border: `2px solid ${cor}30`,
                          }}
                        >
                          <Icone size={18} style={{ color: cor }} strokeWidth={1.8} />
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold sf-text-white truncate">{item.nome_exibicao}</h4>
                          <p className="text-[11px] sf-text-dim truncate">{item.objetivo}</p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <span
                              className="inline-flex px-2 py-0.5 rounded text-[9px] font-medium border"
                              style={{
                                backgroundColor: `${cor}10`,
                                borderColor: `${cor}20`,
                                color: cor,
                              }}
                            >
                              {item.categoria}
                            </span>
                            <span className="text-[10px] sf-text-ghost">
                              {item.total_usuarios} usuario{item.total_usuarios !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>

                        {/* Botao atribuir */}
                        <button
                          onClick={() => handleAtribuir(item.id)}
                          disabled={jaAtribuido || atribuindoEste}
                          className={`shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                            jaAtribuido
                              ? 'bg-white/5 sf-text-ghost border sf-border cursor-not-allowed'
                              : atribuindoEste
                                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 opacity-60 cursor-wait'
                                : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/30'
                          }`}
                        >
                          {jaAtribuido
                            ? 'Atribuido'
                            : atribuindoEste
                              ? 'Atribuindo...'
                              : 'Atribuir'}
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
