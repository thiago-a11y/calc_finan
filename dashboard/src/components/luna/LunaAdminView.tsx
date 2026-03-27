/* LunaAdminView — Painel de Supervisao para proprietarios (CEO/Operations Lead) */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { ArrowLeft, Shield, Search, User, MessageSquare, Eye, Moon, ChevronRight, Trash2, RotateCcw, AlertTriangle } from 'lucide-react'
import { motion } from 'framer-motion'
import MarkdownRenderer from './MarkdownRenderer'
import {
  listarUsuariosLuna,
  listarConversasFuncionario,
  verConversaFuncionario,
  listarLixeira,
  verConversaLixeira,
  restaurarConversa,
  excluirPermanente,
} from '../../services/luna'
import type { LunaConversaLixeira } from '../../services/luna'
import type { LunaUsuarioResumo, LunaConversa, LunaMensagem } from '../../types'

interface LunaAdminViewProps {
  onVoltar: () => void
}

/** Formata data relativa curta */
function formatarDataCurta(iso: string | null): string {
  if (!iso) return 'Nunca'
  try {
    const d = new Date(iso)
    const agora = new Date()
    const diffMs = agora.getTime() - d.getTime()
    const diffH = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffH < 1) return 'Agora'
    if (diffH < 24) return `${diffH}h atras`
    const diffD = Math.floor(diffH / 24)
    if (diffD === 1) return 'Ontem'
    if (diffD < 7) return `${diffD}d atras`
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  } catch {
    return iso || ''
  }
}

function formatarHora(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function LunaAdminView({ onVoltar }: LunaAdminViewProps) {
  /* Aba ativa: supervisao ou lixeira */
  const [abaAtiva, setAbaAtiva] = useState<'supervisao' | 'lixeira'>('supervisao')

  /* Estado principal */
  const [usuarios, setUsuarios] = useState<LunaUsuarioResumo[]>([])
  const [carregandoUsuarios, setCarregandoUsuarios] = useState(true)
  const [buscaUsuario, setBuscaUsuario] = useState('')

  /* Funcionario selecionado */
  const [funcSelecionado, setFuncSelecionado] = useState<LunaUsuarioResumo | null>(null)
  const [conversasFunc, setConversasFunc] = useState<LunaConversa[]>([])
  const [carregandoConversas, setCarregandoConversas] = useState(false)

  /* Conversa selecionada */
  const [conversaSelecionada, setConversaSelecionada] = useState<string | null>(null)
  const [mensagensConversa, setMensagensConversa] = useState<LunaMensagem[]>([])
  const [carregandoMensagens, setCarregandoMensagens] = useState(false)
  const [nomeFunc, setNomeFunc] = useState('')

  /* Lixeira */
  const [lixeira, setLixeira] = useState<LunaConversaLixeira[]>([])
  const [carregandoLixeira, setCarregandoLixeira] = useState(false)
  const [lixeiraSelecionada, setLixeiraSelecionada] = useState<string | null>(null)
  const [msgsLixeira, setMsgsLixeira] = useState<LunaMensagem[]>([])
  const [nomeFuncLixeira, setNomeFuncLixeira] = useState('')
  const [confirmExclusao, setConfirmExclusao] = useState<string | null>(null)

  /* Carregar lixeira */
  const carregarLixeira = useCallback(async () => {
    setCarregandoLixeira(true)
    try {
      const data = await listarLixeira()
      setLixeira(data)
    } catch {
      setLixeira([])
    } finally {
      setCarregandoLixeira(false)
    }
  }, [])

  /* Ao trocar de aba */
  useEffect(() => {
    if (abaAtiva === 'lixeira') {
      carregarLixeira()
      setLixeiraSelecionada(null)
      setMsgsLixeira([])
    }
  }, [abaAtiva, carregarLixeira])

  /* Ver conversa da lixeira */
  const verLixeira = useCallback(async (conversaId: string, nomeUsuario: string) => {
    setLixeiraSelecionada(conversaId)
    setNomeFuncLixeira(nomeUsuario)
    setCarregandoMensagens(true)
    try {
      const data = await verConversaLixeira(conversaId)
      setMsgsLixeira(data.mensagens)
    } catch {
      setMsgsLixeira([])
    } finally {
      setCarregandoMensagens(false)
    }
  }, [])

  /* Restaurar conversa */
  const handleRestaurar = useCallback(async (conversaId: string) => {
    try {
      await restaurarConversa(conversaId)
      setLixeira((prev) => prev.filter((c) => c.id !== conversaId))
      if (lixeiraSelecionada === conversaId) {
        setLixeiraSelecionada(null)
        setMsgsLixeira([])
      }
    } catch {
      // silencioso
    }
  }, [lixeiraSelecionada])

  /* Excluir permanentemente */
  const handleExcluirPermanente = useCallback(async (conversaId: string) => {
    try {
      await excluirPermanente(conversaId)
      setLixeira((prev) => prev.filter((c) => c.id !== conversaId))
      setConfirmExclusao(null)
      if (lixeiraSelecionada === conversaId) {
        setLixeiraSelecionada(null)
        setMsgsLixeira([])
      }
    } catch {
      // silencioso
    }
  }, [lixeiraSelecionada])

  /* Carregar lista de usuarios */
  useEffect(() => {
    let ativo = true
    setCarregandoUsuarios(true)
    listarUsuariosLuna()
      .then((data) => {
        if (ativo) setUsuarios(data)
      })
      .catch(() => {})
      .finally(() => {
        if (ativo) setCarregandoUsuarios(false)
      })
    return () => { ativo = false }
  }, [])

  /* Selecionar funcionario */
  const selecionarFunc = useCallback(async (u: LunaUsuarioResumo) => {
    setFuncSelecionado(u)
    setConversaSelecionada(null)
    setMensagensConversa([])
    setNomeFunc(u.nome)
    setCarregandoConversas(true)
    try {
      const convs = await listarConversasFuncionario(u.usuario_id)
      setConversasFunc(convs)
    } catch {
      setConversasFunc([])
    } finally {
      setCarregandoConversas(false)
    }
  }, [])

  /* Selecionar conversa */
  const selecionarConversa = useCallback(
    async (conversaId: string) => {
      if (!funcSelecionado) return
      setConversaSelecionada(conversaId)
      setCarregandoMensagens(true)
      try {
        const data = await verConversaFuncionario(funcSelecionado.usuario_id, conversaId)
        setMensagensConversa(data.mensagens)
      } catch {
        setMensagensConversa([])
      } finally {
        setCarregandoMensagens(false)
      }
    },
    [funcSelecionado],
  )

  /* Filtrar usuarios */
  const usuariosFiltrados = useMemo(() => {
    if (!buscaUsuario.trim()) return usuarios
    const termo = buscaUsuario.toLowerCase()
    return usuarios.filter(
      (u) =>
        u.nome.toLowerCase().includes(termo) ||
        u.email.toLowerCase().includes(termo) ||
        u.cargo.toLowerCase().includes(termo),
    )
  }, [usuarios, buscaUsuario])

  return (
    <div className="flex flex-col h-full sf-animate-in">
      {/* Header com badge */}
      <div
        className="flex items-center gap-3 px-5 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
      >
        <button
          onClick={onVoltar}
          className="p-1.5 rounded-lg transition-colors hover:brightness-125"
          style={{ color: 'var(--sf-text-3)' }}
        >
          <ArrowLeft size={18} />
        </button>

        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
          style={{
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.15)',
          }}
        >
          <Shield size={14} color="#f59e0b" />
          <span className="text-[13px] font-semibold" style={{ color: '#f59e0b' }}>
            {'\u{1F512}'} Modo Supervisao
          </span>
        </div>

        {/* Tabs: Supervisão | Lixeira */}
        <div className="flex items-center gap-1 ml-4">
          <button
            onClick={() => setAbaAtiva('supervisao')}
            className="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
            style={{
              background: abaAtiva === 'supervisao' ? 'rgba(16,185,129,0.1)' : 'transparent',
              color: abaAtiva === 'supervisao' ? 'var(--sf-accent)' : 'var(--sf-text-3)',
              border: abaAtiva === 'supervisao' ? '1px solid rgba(16,185,129,0.2)' : '1px solid transparent',
            }}
          >
            <Eye size={12} className="inline mr-1.5" />
            Supervisão
          </button>
          <button
            onClick={() => setAbaAtiva('lixeira')}
            className="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
            style={{
              background: abaAtiva === 'lixeira' ? 'rgba(239,68,68,0.1)' : 'transparent',
              color: abaAtiva === 'lixeira' ? '#ef4444' : 'var(--sf-text-3)',
              border: abaAtiva === 'lixeira' ? '1px solid rgba(239,68,68,0.2)' : '1px solid transparent',
            }}
          >
            <Trash2 size={12} className="inline mr-1.5" />
            Lixeira
            {lixeira.length > 0 && (
              <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400">
                {lixeira.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Conteudo principal */}
      {abaAtiva === 'lixeira' ? (
        /* ========== ABA LIXEIRA ========== */
        <div className="flex flex-1 overflow-hidden">
          {/* Lista de conversas excluídas */}
          <div
            className="w-[380px] flex-shrink-0 flex flex-col h-full"
            style={{ borderRight: '1px solid var(--sf-border-subtle)' }}
          >
            <div
              className="px-4 py-3 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
            >
              <p className="text-[13px] font-semibold" style={{ color: 'var(--sf-text-1)' }}>
                Conversas excluídas pelos funcionários
              </p>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--sf-text-4)' }}>
                Estas conversas foram removidas da visão do funcionário mas preservadas para análise
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-2" style={{ scrollbarWidth: 'thin' }}>
              {carregandoLixeira && (
                <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                  Carregando...
                </p>
              )}

              {!carregandoLixeira && lixeira.length === 0 && (
                <div className="text-center py-12">
                  <Trash2 size={32} className="mx-auto mb-3" style={{ color: 'var(--sf-text-4)', opacity: 0.3 }} />
                  <p className="text-[13px]" style={{ color: 'var(--sf-text-3)' }}>
                    Lixeira vazia
                  </p>
                  <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-4)' }}>
                    Nenhuma conversa excluída pendente de análise
                  </p>
                </div>
              )}

              {lixeira.map((c) => (
                <div
                  key={c.id}
                  className="rounded-lg mb-2 transition-all"
                  style={{
                    background: lixeiraSelecionada === c.id ? 'rgba(239,68,68,0.06)' : 'rgba(255,255,255,0.02)',
                    border: lixeiraSelecionada === c.id ? '1px solid rgba(239,68,68,0.2)' : '1px solid var(--sf-border-subtle)',
                  }}
                >
                  <button
                    onClick={() => verLixeira(c.id, c.usuario_nome)}
                    className="w-full text-left px-3 py-3"
                  >
                    <p className="text-[13px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                      {c.titulo}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <User size={10} style={{ color: 'var(--sf-text-4)' }} />
                      <span className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
                        {c.usuario_nome}
                      </span>
                      <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                        {c.usuario_email}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                        {c.total_mensagens} msgs
                      </span>
                      <span className="text-[10px] text-red-400">
                        Excluída {formatarDataCurta(c.excluida_em ?? null)}
                      </span>
                    </div>
                    {c.ultima_mensagem && (
                      <p className="text-[11px] truncate mt-1" style={{ color: 'var(--sf-text-4)' }}>
                        {c.ultima_mensagem}
                      </p>
                    )}
                  </button>

                  {/* Ações: Restaurar | Excluir permanente */}
                  <div
                    className="flex items-center gap-2 px-3 py-2"
                    style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
                  >
                    <button
                      onClick={() => handleRestaurar(c.id)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] font-medium transition-all hover:brightness-110"
                      style={{
                        background: 'rgba(16,185,129,0.08)',
                        color: '#10b981',
                        border: '1px solid rgba(16,185,129,0.15)',
                      }}
                    >
                      <RotateCcw size={11} />
                      Restaurar
                    </button>
                    {confirmExclusao === c.id ? (
                      <div className="flex items-center gap-1.5 ml-auto">
                        <span className="text-[10px] text-red-400">Tem certeza?</span>
                        <button
                          onClick={() => handleExcluirPermanente(c.id)}
                          className="px-2 py-1 rounded text-[10px] font-bold bg-red-500 text-white hover:bg-red-600 transition-colors"
                        >
                          Sim, excluir
                        </button>
                        <button
                          onClick={() => setConfirmExclusao(null)}
                          className="px-2 py-1 rounded text-[10px] transition-colors"
                          style={{ color: 'var(--sf-text-3)' }}
                        >
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmExclusao(c.id)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] font-medium ml-auto transition-all hover:brightness-110"
                        style={{
                          background: 'rgba(239,68,68,0.08)',
                          color: '#ef4444',
                          border: '1px solid rgba(239,68,68,0.15)',
                        }}
                      >
                        <AlertTriangle size={11} />
                        Excluir permanente
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Visualização da conversa da lixeira */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {!lixeiraSelecionada ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <Trash2 size={40} className="mx-auto mb-3" style={{ color: 'var(--sf-text-4)', opacity: 0.3 }} />
                  <p className="text-[14px]" style={{ color: 'var(--sf-text-3)' }}>
                    Selecione uma conversa para analisar
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Banner */}
                <div
                  className="flex items-center gap-2 px-4 py-2.5 flex-shrink-0"
                  style={{
                    background: 'rgba(239,68,68,0.06)',
                    borderBottom: '1px solid rgba(239,68,68,0.12)',
                  }}
                >
                  <Trash2 size={14} color="#ef4444" />
                  <span className="text-[12px] font-medium" style={{ color: '#ef4444' }}>
                    Conversa excluída por {nomeFuncLixeira} — somente leitura
                  </span>
                </div>

                {/* Mensagens */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4" style={{ scrollbarWidth: 'thin' }}>
                  {carregandoMensagens && (
                    <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                      Carregando mensagens...
                    </p>
                  )}

                  {msgsLixeira.map((msg) => {
                    const isUser = msg.papel === 'user'
                    return (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                      >
                        {!isUser && (
                          <div
                            className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2 mt-1"
                            style={{ background: 'linear-gradient(135deg, var(--sf-accent), #059669)' }}
                          >
                            <Moon size={14} color="#fff" />
                          </div>
                        )}
                        <div className="max-w-[75%]">
                          <div
                            className={`rounded-2xl px-4 py-3 ${isUser ? 'rounded-br-md' : 'sf-card rounded-bl-md'}`}
                            style={
                              isUser
                                ? { background: 'var(--sf-accent)', color: '#fff' }
                                : { border: '1px solid var(--sf-border-subtle)' }
                            }
                          >
                            {isUser ? (
                              <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{msg.conteudo}</p>
                            ) : (
                              <MarkdownRenderer content={msg.conteudo} />
                            )}
                          </div>
                          <span className="text-[10px] mt-1 block" style={{ color: 'var(--sf-text-4)', textAlign: isUser ? 'right' : 'left' }}>
                            {formatarHora(msg.criado_em)}
                          </span>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>

                {/* Rodapé */}
                <div
                  className="px-4 py-3 text-center flex-shrink-0"
                  style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
                >
                  <p className="text-[11px]" style={{ color: 'var(--sf-text-4)' }}>
                    {'\u{1F5D1}'} Conversa da lixeira — somente leitura
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
      /* ========== ABA SUPERVISÃO (conteúdo original) ========== */
      <div className="flex flex-1 overflow-hidden">
        {/* Coluna Esquerda — Lista de funcionarios */}
        <div
          className="w-[320px] flex-shrink-0 flex flex-col h-full"
          style={{ borderRight: '1px solid var(--sf-border-subtle)' }}
        >
          {/* Busca */}
          <div className="px-3 py-3">
            <div
              className="relative rounded-lg overflow-hidden"
              style={{ border: '1px solid var(--sf-border-subtle)' }}
            >
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--sf-text-4)' }}
              />
              <input
                value={buscaUsuario}
                onChange={(e) => setBuscaUsuario(e.target.value)}
                placeholder="Buscar funcionario..."
                className="w-full bg-transparent pl-8 pr-3 py-2 text-[12px] outline-none placeholder:opacity-40"
                style={{ color: 'var(--sf-text-2)' }}
              />
            </div>
          </div>

          {/* Lista */}
          <div className="flex-1 overflow-y-auto px-2" style={{ scrollbarWidth: 'thin' }}>
            {carregandoUsuarios && (
              <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                Carregando...
              </p>
            )}

            {!carregandoUsuarios && usuariosFiltrados.length === 0 && (
              <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                Nenhum funcionario encontrado
              </p>
            )}

            {usuariosFiltrados.map((u) => (
              <button
                key={u.usuario_id}
                onClick={() => selecionarFunc(u)}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all duration-150 mb-1"
                style={{
                  background:
                    funcSelecionado?.usuario_id === u.usuario_id
                      ? 'rgba(16,185,129,0.08)'
                      : 'transparent',
                  borderLeft:
                    funcSelecionado?.usuario_id === u.usuario_id
                      ? '2px solid var(--sf-accent)'
                      : '2px solid transparent',
                }}
              >
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid var(--sf-border-subtle)',
                  }}
                >
                  <User size={16} style={{ color: 'var(--sf-text-3)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                    {u.nome}
                  </p>
                  <p className="text-[11px] truncate" style={{ color: 'var(--sf-text-4)' }}>
                    {u.email}
                  </p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                      {u.cargo}
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                      {u.total_conversas} conversas
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                      {formatarDataCurta(u.ultimo_uso)}
                    </span>
                  </div>
                </div>
                <ChevronRight size={14} style={{ color: 'var(--sf-text-4)' }} />
              </button>
            ))}
          </div>
        </div>

        {/* Coluna Direita — Conversas ou Chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!funcSelecionado && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Eye size={40} className="mx-auto mb-3" style={{ color: 'var(--sf-text-4)', opacity: 0.3 }} />
                <p className="text-[14px]" style={{ color: 'var(--sf-text-3)' }}>
                  Selecione um funcionario para ver as conversas
                </p>
              </div>
            </div>
          )}

          {/* Lista de conversas do funcionario */}
          {funcSelecionado && !conversaSelecionada && (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div
                className="px-4 py-3 flex-shrink-0"
                style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
              >
                <p className="text-[14px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
                  Conversas de {funcSelecionado.nome}
                </p>
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--sf-text-4)' }}>
                  {funcSelecionado.total_conversas} conversas &middot;{' '}
                  {funcSelecionado.total_mensagens} mensagens
                </p>
              </div>

              <div className="flex-1 overflow-y-auto px-3 py-2" style={{ scrollbarWidth: 'thin' }}>
                {carregandoConversas && (
                  <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                    Carregando conversas...
                  </p>
                )}

                {!carregandoConversas && conversasFunc.length === 0 && (
                  <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                    Nenhuma conversa encontrada
                  </p>
                )}

                {conversasFunc.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => selecionarConversa(c.id)}
                    className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all duration-150 mb-1 hover:brightness-110"
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--sf-border-subtle)',
                    }}
                  >
                    <MessageSquare size={16} style={{ color: 'var(--sf-accent)', flexShrink: 0 }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                        {c.titulo}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                          {new Date(c.criado_em).toLocaleDateString('pt-BR')}
                        </span>
                        {c.ultima_mensagem && (
                          <span
                            className="text-[10px] truncate max-w-[200px]"
                            style={{ color: 'var(--sf-text-4)' }}
                          >
                            {c.ultima_mensagem}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight size={14} style={{ color: 'var(--sf-text-4)' }} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat read-only */}
          {funcSelecionado && conversaSelecionada && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Banner de supervisao */}
              <div
                className="flex items-center gap-2 px-4 py-2.5 flex-shrink-0"
                style={{
                  background: 'rgba(245,158,11,0.06)',
                  borderBottom: '1px solid rgba(245,158,11,0.12)',
                }}
              >
                <Eye size={14} color="#f59e0b" />
                <span className="text-[12px] font-medium" style={{ color: '#f59e0b' }}>
                  Visualizando chat de {nomeFunc}
                </span>
                <button
                  onClick={() => setConversaSelecionada(null)}
                  className="ml-auto text-[11px] px-2 py-1 rounded transition-colors hover:brightness-110"
                  style={{
                    color: 'var(--sf-text-3)',
                    background: 'rgba(255,255,255,0.05)',
                  }}
                >
                  Voltar as conversas
                </button>
              </div>

              {/* Mensagens (somente leitura) */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4" style={{ scrollbarWidth: 'thin' }}>
                {carregandoMensagens && (
                  <p className="text-center text-[12px] py-6" style={{ color: 'var(--sf-text-4)' }}>
                    Carregando mensagens...
                  </p>
                )}

                {mensagensConversa.map((msg) => {
                  const isUser = msg.papel === 'user'
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      {/* Avatar Luna */}
                      {!isUser && (
                        <div
                          className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2 mt-1"
                          style={{ background: 'linear-gradient(135deg, var(--sf-accent), #059669)' }}
                        >
                          <Moon size={14} color="#fff" />
                        </div>
                      )}

                      <div className="max-w-[75%]">
                        <div
                          className={`rounded-2xl px-4 py-3 ${isUser ? 'rounded-br-md' : 'sf-card rounded-bl-md'}`}
                          style={
                            isUser
                              ? { background: 'var(--sf-accent)', color: '#fff' }
                              : { border: '1px solid var(--sf-border-subtle)' }
                          }
                        >
                          {isUser ? (
                            <p className="text-[14px] leading-relaxed whitespace-pre-wrap">
                              {msg.conteudo}
                            </p>
                          ) : (
                            <MarkdownRenderer content={msg.conteudo} />
                          )}
                        </div>
                        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
                          <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                            {formatarHora(msg.criado_em)}
                          </span>
                          {!isUser && msg.modelo_usado && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                              background: 'rgba(255,255,255,0.04)',
                              color: 'var(--sf-text-4)',
                            }}>
                              {msg.modelo_usado}
                            </span>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>

              {/* Barra inferior (somente leitura) */}
              <div
                className="px-4 py-3 text-center flex-shrink-0"
                style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
              >
                <p className="text-[11px]" style={{ color: 'var(--sf-text-4)' }}>
                  {'\u{1F512}'} Modo somente leitura — Supervisao ativa
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  )
}
