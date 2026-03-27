/* LunaSidebar — Barra lateral de conversas da Luna */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { Plus, Search, Moon, MoreHorizontal, Pencil, Trash2, Shield } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { LunaConversa } from '../../types'

interface LunaSidebarProps {
  conversas: LunaConversa[]
  conversaAtiva: string | null
  onSelecionar: (id: string) => void
  onNova: () => void
  onRenomear: (id: string, titulo: string) => void
  onExcluir: (id: string) => void
  onSupervisao: () => void
  mostrarSupervisao: boolean
  busca: string
  onBuscaChange: (v: string) => void
}

/** Agrupa conversas por data relativa */
function agruparPorData(conversas: LunaConversa[]): { label: string; itens: LunaConversa[] }[] {
  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  const ontem = new Date(hoje)
  ontem.setDate(ontem.getDate() - 1)
  const semana = new Date(hoje)
  semana.setDate(semana.getDate() - 7)

  const grupos: Record<string, LunaConversa[]> = {
    Hoje: [],
    Ontem: [],
    'Ultimos 7 dias': [],
    'Mais antigos': [],
  }

  for (const c of conversas) {
    const d = new Date(c.atualizado_em)
    d.setHours(0, 0, 0, 0)
    if (d >= hoje) grupos['Hoje'].push(c)
    else if (d >= ontem) grupos['Ontem'].push(c)
    else if (d >= semana) grupos['Ultimos 7 dias'].push(c)
    else grupos['Mais antigos'].push(c)
  }

  return Object.entries(grupos)
    .filter(([, itens]) => itens.length > 0)
    .map(([label, itens]) => ({ label, itens }))
}

/** Item de conversa individual */
function ConversaItem({
  conversa,
  ativa,
  onSelecionar,
  onRenomear,
  onExcluir,
}: {
  conversa: LunaConversa
  ativa: boolean
  onSelecionar: () => void
  onRenomear: (titulo: string) => void
  onExcluir: () => void
}) {
  const [menuAberto, setMenuAberto] = useState(false)
  const [editando, setEditando] = useState(false)
  const [novoTitulo, setNovoTitulo] = useState(conversa.titulo)
  const inputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  /* Fechar menu ao clicar fora */
  useEffect(() => {
    if (!menuAberto) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAberto(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuAberto])

  /* Focar input ao editar */
  useEffect(() => {
    if (editando) inputRef.current?.focus()
  }, [editando])

  const salvarTitulo = useCallback(() => {
    const trimmed = novoTitulo.trim()
    if (trimmed && trimmed !== conversa.titulo) {
      onRenomear(trimmed)
    }
    setEditando(false)
  }, [novoTitulo, conversa.titulo, onRenomear])

  return (
    <div
      className="group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150"
      style={{
        background: ativa ? 'rgba(16,185,129,0.1)' : 'transparent',
        borderLeft: ativa ? '2px solid var(--sf-accent)' : '2px solid transparent',
      }}
      onClick={() => !editando && onSelecionar()}
      onContextMenu={(e) => {
        e.preventDefault()
        setMenuAberto(true)
      }}
    >
      <div className="flex-1 min-w-0">
        {editando ? (
          <input
            ref={inputRef}
            value={novoTitulo}
            onChange={(e) => setNovoTitulo(e.target.value)}
            onBlur={salvarTitulo}
            onKeyDown={(e) => {
              if (e.key === 'Enter') salvarTitulo()
              if (e.key === 'Escape') setEditando(false)
            }}
            className="w-full bg-transparent outline-none text-[13px] font-medium px-1 py-0.5 rounded"
            style={{
              color: 'var(--sf-text-1)',
              border: '1px solid var(--sf-accent)',
            }}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <>
            <p
              className="text-[13px] font-medium truncate"
              style={{ color: ativa ? 'var(--sf-accent)' : 'var(--sf-text-1)' }}
            >
              {conversa.titulo}
            </p>
            {conversa.ultima_mensagem && (
              <p
                className="text-[11px] truncate mt-0.5"
                style={{ color: 'var(--sf-text-4)' }}
              >
                {conversa.ultima_mensagem}
              </p>
            )}
          </>
        )}
      </div>

      {/* Botao "..." */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          setMenuAberto(!menuAberto)
        }}
        className="opacity-0 group-hover:opacity-100 flex-shrink-0 p-1 rounded transition-opacity"
        style={{ color: 'var(--sf-text-4)' }}
      >
        <MoreHorizontal size={14} />
      </button>

      {/* Menu dropdown */}
      <AnimatePresence>
        {menuAberto && (
          <motion.div
            ref={menuRef}
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute right-2 top-full z-50 py-1 rounded-lg shadow-xl min-w-[140px]"
            style={{
              background: 'var(--sf-bg-2)',
              border: '1px solid var(--sf-border-subtle)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-left transition-colors hover:brightness-110"
              style={{ color: 'var(--sf-text-2)' }}
              onClick={() => {
                setEditando(true)
                setNovoTitulo(conversa.titulo)
                setMenuAberto(false)
              }}
            >
              <Pencil size={12} />
              Renomear
            </button>
            <button
              className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-left transition-colors hover:brightness-110"
              style={{ color: '#ef4444' }}
              onClick={() => {
                onExcluir()
                setMenuAberto(false)
              }}
            >
              <Trash2 size={12} />
              Excluir
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function LunaSidebar({
  conversas,
  conversaAtiva,
  onSelecionar,
  onNova,
  onRenomear,
  onExcluir,
  onSupervisao,
  mostrarSupervisao,
  busca,
  onBuscaChange,
}: LunaSidebarProps) {
  /* Filtrar conversas pela busca */
  const conversasFiltradas = useMemo(() => {
    if (!busca.trim()) return conversas
    const termo = busca.toLowerCase()
    return conversas.filter(
      (c) =>
        c.titulo.toLowerCase().includes(termo) ||
        c.ultima_mensagem?.toLowerCase().includes(termo),
    )
  }, [conversas, busca])

  const grupos = useMemo(() => agruparPorData(conversasFiltradas), [conversasFiltradas])

  return (
    <div
      className="w-[280px] h-full flex flex-col flex-shrink-0 transition-colors duration-200"
      style={{
        background: 'var(--sf-bg-1)',
        borderRight: '1px solid var(--sf-border-subtle)',
      }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-center gap-2.5 mb-4">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, var(--sf-accent), #059669)',
              boxShadow: '0 0 16px rgba(16,185,129,0.3)',
            }}
          >
            <Moon size={16} color="#fff" />
          </div>
          <div className="flex items-center gap-2">
            <h2 className="text-[15px] font-bold" style={{ color: 'var(--sf-text-0)' }}>
              Luna {'\u{1F319}'}
            </h2>
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
              style={{
                background: 'rgba(16,185,129,0.15)',
                color: 'var(--sf-accent)',
              }}
            >
              IA
            </span>
          </div>
        </div>

        {/* Botao Nova Conversa */}
        <button
          onClick={onNova}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-[13px] font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
          style={{
            background: 'var(--sf-accent)',
            color: '#fff',
            boxShadow: '0 2px 8px rgba(16,185,129,0.25)',
          }}
        >
          <Plus size={16} />
          Nova Conversa
        </button>

        {/* Campo de busca */}
        <div
          className="relative mt-3 rounded-lg overflow-hidden"
          style={{ border: '1px solid var(--sf-border-subtle)' }}
        >
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2"
            style={{ color: 'var(--sf-text-4)' }}
          />
          <input
            value={busca}
            onChange={(e) => onBuscaChange(e.target.value)}
            placeholder="Buscar conversas..."
            className="w-full bg-transparent pl-8 pr-3 py-2 text-[12px] outline-none placeholder:opacity-40"
            style={{ color: 'var(--sf-text-2)' }}
          />
        </div>
      </div>

      {/* Lista de conversas */}
      <div className="flex-1 overflow-y-auto px-2 pb-2" style={{ scrollbarWidth: 'thin' }}>
        {grupos.length === 0 && (
          <p
            className="text-center text-[12px] py-8"
            style={{ color: 'var(--sf-text-4)' }}
          >
            {busca ? 'Nenhuma conversa encontrada' : 'Nenhuma conversa ainda'}
          </p>
        )}

        {grupos.map((grupo) => (
          <div key={grupo.label} className="mb-3">
            <p
              className="text-[10px] font-semibold uppercase tracking-wider px-3 py-1.5"
              style={{ color: 'var(--sf-text-4)' }}
            >
              {grupo.label}
            </p>
            {grupo.itens.map((c) => (
              <ConversaItem
                key={c.id}
                conversa={c}
                ativa={c.id === conversaAtiva}
                onSelecionar={() => onSelecionar(c.id)}
                onRenomear={(titulo) => onRenomear(c.id, titulo)}
                onExcluir={() => onExcluir(c.id)}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Tab Supervisao (apenas CEO/ops_lead) */}
      {mostrarSupervisao && (
        <div
          className="px-3 py-3"
          style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
        >
          <button
            onClick={onSupervisao}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] font-medium transition-all hover:scale-[1.01]"
            style={{
              background: 'rgba(245,158,11,0.08)',
              color: '#f59e0b',
              border: '1px solid rgba(245,158,11,0.15)',
            }}
          >
            <Shield size={14} />
            Supervisao
          </button>
        </div>
      )}
    </div>
  )
}
