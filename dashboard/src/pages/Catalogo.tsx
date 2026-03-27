/* Catálogo de Agentes — Grid de agentes disponíveis com filtros, criação e atribuição */

import { useState, useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import {
  buscarCatalogo, criarAgenteCatalogo, buscarPerfisAgente,
  atribuirAgente, buscarUsuarios,
} from '../services/api'
import type { AgenteCatalogo, PerfilDisponivel, Usuario } from '../types'
import {
  Bot, Plus, X, Users, Search, Code2, Server, Palette, Brain,
  Plug, Cloud, ShieldCheck, ClipboardList, FileText, SearchCode,
  Network, Lock,
} from 'lucide-react'

/* --- Mapa estático de ícones lucide (fallback: Bot) --- */

const iconesMap: Record<string, typeof Bot> = {
  Code2, Server, Palette, Brain, Plug, Cloud, ShieldCheck,
  ClipboardList, FileText, SearchCode, Network, Lock, Bot,
}

function IconeDinamico({ nome, size = 20, className = '' }: { nome: string; size?: number; className?: string }) {
  const Icone = iconesMap[nome] || Bot
  return <Icone size={size} className={className} strokeWidth={1.8} />
}

/* --- Cores por categoria --- */

const categoriaCores: Record<string, { bg: string; text: string; border: string }> = {
  desenvolvimento: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  gestao:          { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
  seguranca:       { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  ia:              { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  operacional:     { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
}

function corCategoria(cat: string) {
  return categoriaCores[cat] || { bg: 'bg-white/5', text: 'sf-text-dim', border: 'border-white/10' }
}

/* --- Categorias disponíveis para filtro --- */

const categoriasFiltro = [
  { id: 'todas', label: 'Todas' },
  { id: 'desenvolvimento', label: 'Desenvolvimento' },
  { id: 'gestao', label: 'Gestão' },
  { id: 'seguranca', label: 'Segurança' },
  { id: 'ia', label: 'IA' },
  { id: 'operacional', label: 'Operacional' },
]

/* --- Classes reutilizáveis --- */

const inputCls = "w-full sf-glass border sf-border rounded-xl px-4 py-2.5 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"
const selectCls = `${inputCls} appearance-none`
const btnPrimario = "flex items-center gap-2 px-5 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-sm font-medium hover:bg-emerald-500/30 transition-all"
const btnSecundario = "flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 text-gray-400 rounded-lg text-xs font-medium hover:bg-white/10 transition-all"

/* ==================== COMPONENTE PRINCIPAL ==================== */

export default function Catalogo() {
  const { usuario } = useAuth()
  const isAdmin = (usuario?.papeis || []).some(p => ['ceo', 'diretor_tecnico', 'operations_lead'].includes(p))

  /* --- Estado --- */
  const [filtroCategoria, setFiltroCategoria] = useState('todas')
  const [busca, setBusca] = useState('')
  const [mostrarFormCriacao, setMostrarFormCriacao] = useState(false)
  const [modalAtribuir, setModalAtribuir] = useState<AgenteCatalogo | null>(null)
  const [processando, setProcessando] = useState(false)

  /* --- Dados --- */
  const fetchCatalogo = useCallback(() => buscarCatalogo(), [])
  const { dados: catalogo, carregando, recarregar } = usePolling(fetchCatalogo, 15000)

  /* --- Filtros --- */
  const agenteFiltrado = (catalogo || []).filter((a: AgenteCatalogo) => {
    if (filtroCategoria !== 'todas' && a.categoria !== filtroCategoria) return false
    if (busca) {
      const termo = busca.toLowerCase()
      return (
        a.nome_exibicao.toLowerCase().includes(termo) ||
        a.perfil_agente.toLowerCase().includes(termo) ||
        a.papel.toLowerCase().includes(termo)
      )
    }
    return true
  })

  /* --- Ações --- */
  const handleCriarAgente = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setProcessando(true)
    const form = new FormData(e.currentTarget)
    try {
      await criarAgenteCatalogo({
        nome_exibicao: form.get('nome_exibicao') as string,
        papel: form.get('papel') as string,
        objetivo: form.get('objetivo') as string,
        historia: form.get('historia') as string,
        perfil_agente: form.get('perfil_agente') as string,
        categoria: form.get('categoria') as string || undefined,
        icone: form.get('icone') as string || undefined,
      })
      setMostrarFormCriacao(false)
      await recarregar()
    } catch (e) {
      alert(`Erro ao criar agente: ${e instanceof Error ? e.message : 'desconhecido'}`)
    } finally {
      setProcessando(false)
    }
  }

  const handleAtribuir = async (agenteCatalogoId: number, usuarioId: number) => {
    setProcessando(true)
    try {
      await atribuirAgente(agenteCatalogoId, usuarioId)
      setModalAtribuir(null)
      await recarregar()
    } catch (e) {
      alert(`Erro ao atribuir: ${e instanceof Error ? e.message : 'desconhecido'}`)
    } finally {
      setProcessando(false)
    }
  }

  /* --- Loading --- */
  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="sf-page">
      {/* Glow decorativo */}
      <div
        className="fixed top-0 right-1/4 w-[500px] h-[300px] bg-blue-500/5 blur-[120px] pointer-events-none sf-glow"
        style={{ opacity: 'var(--sf-glow-opacity)' }}
      />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Catálogo de Agentes
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            {agenteFiltrado.length} agente(s) disponíve{agenteFiltrado.length === 1 ? 'l' : 'is'}
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setMostrarFormCriacao(!mostrarFormCriacao)}
            className={mostrarFormCriacao
              ? 'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 bg-white/5 text-gray-400 border border-white/10'
              : btnPrimario
            }
          >
            {mostrarFormCriacao ? <><X size={14} /> Cancelar</> : <><Plus size={14} /> Novo Agente</>}
          </button>
        )}
      </div>

      {/* Filtros por categoria (chips/pills) */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        {categoriasFiltro.map(cat => {
          const ativo = filtroCategoria === cat.id
          const cor = cat.id !== 'todas' ? corCategoria(cat.id) : null
          return (
            <button
              key={cat.id}
              onClick={() => setFiltroCategoria(cat.id)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
                ativo
                  ? cor
                    ? `${cor.bg} ${cor.text} ${cor.border}`
                    : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20'
                  : 'bg-white/5 sf-text-dim border-white/10 hover:bg-white/10'
              }`}
            >
              {cat.label}
            </button>
          )
        })}

        {/* Campo de busca */}
        <div className="relative ml-auto">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 sf-text-ghost" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar agente..."
            className="sf-glass border sf-border rounded-xl pl-9 pr-4 py-1.5 text-xs sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors w-56"
          />
        </div>
      </div>

      {/* Modal de criação (formulário inline) */}
      {mostrarFormCriacao && (
        <FormCriarAgente
          onSubmit={handleCriarAgente}
          processando={processando}
        />
      )}

      {/* Grid de cards */}
      {agenteFiltrado.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agenteFiltrado.map((agente: AgenteCatalogo) => {
            const cor = corCategoria(agente.categoria)
            return (
              <div
                key={agente.id}
                className="sf-glass border rounded-2xl p-5 transition-all duration-300 hover:border-white/15 hover:shadow-lg group"
                style={{ borderColor: 'var(--sf-border-subtle)' }}
              >
                {/* Topo: ícone + categoria */}
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${cor.bg} border ${cor.border}`}>
                    <IconeDinamico nome={agente.icone} size={20} className={cor.text} />
                  </div>
                  <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${cor.bg} ${cor.text} ${cor.border}`}>
                    {agente.categoria}
                  </span>
                </div>

                {/* Nome e perfil */}
                <h3 className="font-semibold sf-text-white text-sm mb-1">
                  {agente.nome_exibicao}
                </h3>
                <p className="text-xs sf-text-dim leading-relaxed line-clamp-2 mb-3">
                  {agente.perfil_agente}
                </p>

                {/* Rodapé: badge de usuários + botão atribuir */}
                <div className="flex items-center justify-between pt-3 border-t" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                  <span className="flex items-center gap-1.5 text-[11px] sf-text-ghost">
                    <Users size={12} />
                    {agente.total_usuarios} usuário{agente.total_usuarios !== 1 ? 's' : ''}
                  </span>
                  <button
                    onClick={() => setModalAtribuir(agente)}
                    className={btnSecundario}
                  >
                    <Plus size={12} /> Atribuir
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-16">
          <div
            className="w-14 h-14 mx-auto mb-4 rounded-2xl sf-glass border flex items-center justify-center"
            style={{ borderColor: 'var(--sf-border-subtle)' }}
          >
            <Bot size={24} className="sf-text-ghost" strokeWidth={1.5} />
          </div>
          <p className="text-sm sf-text-dim">Nenhum agente encontrado.</p>
          <p className="text-xs sf-text-ghost mt-1">
            {filtroCategoria !== 'todas' || busca
              ? 'Tente alterar os filtros ou a busca.'
              : 'Crie o primeiro agente no catálogo.'}
          </p>
        </div>
      )}

      {/* Modal de atribuição */}
      {modalAtribuir && (
        <ModalAtribuir
          agente={modalAtribuir}
          onAtribuir={handleAtribuir}
          onFechar={() => setModalAtribuir(null)}
          processando={processando}
        />
      )}
    </div>
  )
}

/* ==================== FORMULÁRIO DE CRIAÇÃO ==================== */

function FormCriarAgente({
  onSubmit,
  processando,
}: {
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  processando: boolean
}) {
  const [perfis, setPerfis] = useState<PerfilDisponivel[]>([])
  const [carregouPerfis, setCarregouPerfis] = useState(false)

  /* Carregar perfis na primeira renderização */
  if (!carregouPerfis) {
    setCarregouPerfis(true)
    buscarPerfisAgente()
      .then(setPerfis)
      .catch(() => { /* silencioso */ })
  }

  const iconesDisponiveis = Object.keys(iconesMap)

  return (
    <form onSubmit={onSubmit} className="sf-glass border sf-border rounded-2xl p-6 mb-8 space-y-4">
      <h4 className="font-semibold sf-text-white mb-2">Novo Agente no Catálogo</h4>

      <div className="grid grid-cols-2 gap-3">
        <input name="nome_exibicao" placeholder="Nome de exibição" required className={inputCls} />
        <input name="papel" placeholder="Papel (ex: Desenvolvedor Backend)" required className={inputCls} />
      </div>

      <input name="objetivo" placeholder="Objetivo do agente" required className={inputCls} />
      <textarea name="historia" placeholder="História / backstory do agente" required className={`${inputCls} min-h-[80px] resize-y`} />

      <div className="grid grid-cols-3 gap-3">
        {/* Perfil do agente */}
        <select name="perfil_agente" required className={selectCls}>
          <option value="">Perfil do agente</option>
          {perfis.map(p => (
            <option key={p.perfil} value={p.perfil}>{p.perfil} — {p.tier_llm}</option>
          ))}
        </select>

        {/* Categoria */}
        <select name="categoria" className={selectCls}>
          <option value="">Categoria</option>
          {categoriasFiltro.filter(c => c.id !== 'todas').map(c => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>

        {/* Ícone */}
        <select name="icone" className={selectCls}>
          <option value="">Ícone</option>
          {iconesDisponiveis.map(nome => (
            <option key={nome} value={nome}>{nome}</option>
          ))}
        </select>
      </div>

      <div className="flex justify-end">
        <button type="submit" disabled={processando} className={`${btnPrimario} disabled:opacity-50`}>
          {processando ? 'Criando...' : <><Plus size={13} /> Criar Agente</>}
        </button>
      </div>
    </form>
  )
}

/* ==================== MODAL DE ATRIBUIÇÃO ==================== */

function ModalAtribuir({
  agente,
  onAtribuir,
  onFechar,
  processando,
}: {
  agente: AgenteCatalogo
  onAtribuir: (agenteCatalogoId: number, usuarioId: number) => void
  onFechar: () => void
  processando: boolean
}) {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [carregouUsuarios, setCarregouUsuarios] = useState(false)
  const [usuarioSelecionado, setUsuarioSelecionado] = useState<number | null>(null)

  /* Carregar usuários na primeira renderização */
  if (!carregouUsuarios) {
    setCarregouUsuarios(true)
    buscarUsuarios()
      .then(setUsuarios)
      .catch(() => { /* silencioso */ })
  }

  const cor = corCategoria(agente.categoria)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onFechar} />

      {/* Conteúdo do modal */}
      <div className="relative sf-glass border sf-border rounded-2xl p-6 w-full max-w-md shadow-2xl">
        {/* Botão fechar */}
        <button onClick={onFechar} className="absolute top-4 right-4 sf-text-ghost hover:sf-text-dim transition-colors">
          <X size={18} />
        </button>

        {/* Header do agente */}
        <div className="flex items-center gap-3 mb-5">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cor.bg} border ${cor.border}`}>
            <IconeDinamico nome={agente.icone} size={18} className={cor.text} />
          </div>
          <div>
            <h3 className="font-semibold sf-text-white text-sm">{agente.nome_exibicao}</h3>
            <p className="text-xs sf-text-dim">{agente.perfil_agente}</p>
          </div>
        </div>

        {/* Seleção de usuário */}
        <label className="block text-xs sf-text-dim mb-2">Atribuir para qual usuário?</label>
        <select
          value={usuarioSelecionado ?? ''}
          onChange={(e) => setUsuarioSelecionado(Number(e.target.value) || null)}
          className={selectCls}
        >
          <option value="">Selecione um usuário</option>
          {usuarios.filter(u => u.ativo).map(u => (
            <option key={u.id} value={u.id}>{u.nome} — {u.cargo || u.email}</option>
          ))}
        </select>

        {/* Botões */}
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onFechar} className={btnSecundario}>
            Cancelar
          </button>
          <button
            onClick={() => usuarioSelecionado && onAtribuir(agente.id, usuarioSelecionado)}
            disabled={!usuarioSelecionado || processando}
            className={`${btnPrimario} disabled:opacity-50`}
          >
            {processando ? 'Atribuindo...' : <><Users size={13} /> Atribuir</>}
          </button>
        </div>
      </div>
    </div>
  )
}
