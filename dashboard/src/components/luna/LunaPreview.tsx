/* LunaPreview — Painel de preview de artefatos com sistema de comentários */

import { useState, useCallback, useEffect, useRef } from 'react'
import { X, ExternalLink, Copy, Check, MessageCircle, Send, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import MarkdownRenderer from './MarkdownRenderer'
import { listarComentarios, criarComentario, excluirComentario } from '../../services/luna'
import type { LunaArtefato, LunaComentario } from '../../types'

interface LunaPreviewProps {
  artefato: LunaArtefato | null
  artefatos: LunaArtefato[]
  onFechar: () => void
  onSelecionarArtefato: (id: string) => void
  conversaId?: string
  usuarioAtual?: { id: number | string; nome: string; papeis?: string[] } | null
}

/** Abre conteudo HTML em nova aba */
function abrirEmNovaAba(html: string) {
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

/** Formata data relativa (agora, 5min, 2h, ontem, data) */
function formatarDataRelativa(iso: string): string {
  const d = new Date(iso)
  const agora = new Date()
  const diffMs = agora.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'agora'
  if (diffMin < 60) return `${diffMin}min`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

export default function LunaPreview({
  artefato,
  artefatos,
  onFechar,
  onSelecionarArtefato,
  conversaId,
  usuarioAtual,
}: LunaPreviewProps) {
  const [copiado, setCopiado] = useState(false)
  const [mostrarComentarios, setMostrarComentarios] = useState(false)
  const [comentarios, setComentarios] = useState<LunaComentario[]>([])
  const [novoComentario, setNovoComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const comentariosRef = useRef<HTMLDivElement>(null)

  const ehProprietario = usuarioAtual?.papeis?.some(
    p => ['ceo', 'operations_lead'].includes(p)
  ) ?? false

  // Carregar comentários quando o artefato muda
  useEffect(() => {
    if (!artefato || !conversaId) {
      setComentarios([])
      return
    }
    listarComentarios(conversaId, artefato.id)
      .then(setComentarios)
      .catch(() => setComentarios([]))
  }, [artefato?.id, conversaId])

  // Scroll para o último comentário
  useEffect(() => {
    if (comentariosRef.current) {
      comentariosRef.current.scrollTop = comentariosRef.current.scrollHeight
    }
  }, [comentarios.length])

  const copiar = useCallback(async () => {
    if (!artefato) return
    try {
      await navigator.clipboard.writeText(artefato.conteudo)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch { /* fallback silencioso */ }
  }, [artefato])

  const handleEnviarComentario = useCallback(async () => {
    if (!artefato || !conversaId || !novoComentario.trim() || enviando) return
    setEnviando(true)
    try {
      const c = await criarComentario(conversaId, {
        artefato_id: artefato.id,
        conteudo: novoComentario.trim(),
      })
      setComentarios(prev => [...prev, c])
      setNovoComentario('')
    } catch { /* erro silencioso */ }
    finally { setEnviando(false) }
  }, [artefato, conversaId, novoComentario, enviando])

  const handleExcluirComentario = useCallback(async (id: number) => {
    if (!conversaId) return
    try {
      await excluirComentario(conversaId, id)
      setComentarios(prev => prev.filter(c => c.id !== id))
    } catch { /* erro silencioso */ }
  }, [conversaId])

  return (
    <AnimatePresence>
      {artefato && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.3)' }}
            onClick={onFechar}
          />

          {/* Painel deslizante */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full z-50 flex flex-col"
            style={{
              width: '55%',
              minWidth: '450px',
              maxWidth: '900px',
              background: 'var(--sf-bg-0)',
              borderLeft: '1px solid var(--sf-border-subtle)',
              boxShadow: '-8px 0 32px rgba(0,0,0,0.2)',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-4 py-3 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <h3
                  className="text-[14px] font-semibold truncate"
                  style={{ color: 'var(--sf-text-0)' }}
                >
                  {artefato.titulo}
                </h3>
                <span
                  className="flex-shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                  style={{
                    background: 'rgba(16,185,129,0.12)',
                    color: 'var(--sf-accent)',
                  }}
                >
                  {artefato.linguagem}
                </span>
              </div>
              <div className="flex items-center gap-1">
                {/* Toggle comentários */}
                {conversaId && (
                  <button
                    onClick={() => setMostrarComentarios(!mostrarComentarios)}
                    className="relative p-1.5 rounded-lg transition-colors hover:brightness-125"
                    style={{
                      color: mostrarComentarios ? 'var(--sf-accent)' : 'var(--sf-text-3)',
                      background: mostrarComentarios ? 'rgba(16,185,129,0.1)' : 'transparent',
                    }}
                    title="Comentários"
                  >
                    <MessageCircle size={18} />
                    {comentarios.length > 0 && (
                      <span
                        className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
                        style={{ background: 'var(--sf-accent)' }}
                      >
                        {comentarios.length}
                      </span>
                    )}
                  </button>
                )}
                {/* Fechar */}
                <button
                  onClick={onFechar}
                  className="p-1.5 rounded-lg transition-colors hover:brightness-125"
                  style={{ color: 'var(--sf-text-3)' }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Tabs de artefatos (se houver multiplos) */}
            {artefatos.length > 1 && (
              <div
                className="flex items-center gap-1 px-4 py-2 overflow-x-auto flex-shrink-0"
                style={{
                  borderBottom: '1px solid var(--sf-border-subtle)',
                  scrollbarWidth: 'thin',
                }}
              >
                {artefatos.map((art) => (
                  <button
                    key={art.id}
                    onClick={() => onSelecionarArtefato(art.id)}
                    className="flex-shrink-0 px-3 py-1.5 rounded-md text-[11px] font-medium transition-all"
                    style={{
                      background:
                        art.id === artefato.id
                          ? 'rgba(16,185,129,0.12)'
                          : 'transparent',
                      color:
                        art.id === artefato.id
                          ? 'var(--sf-accent)'
                          : 'var(--sf-text-3)',
                      border:
                        art.id === artefato.id
                          ? '1px solid rgba(16,185,129,0.2)'
                          : '1px solid transparent',
                    }}
                  >
                    {art.linguagem.toUpperCase()}
                  </button>
                ))}
              </div>
            )}

            {/* Área principal: Conteúdo + Sidebar de comentários */}
            <div className="flex-1 flex overflow-hidden">
              {/* Conteúdo do artefato */}
              <div className="flex-1 overflow-auto" style={{ scrollbarWidth: 'thin' }}>
                {artefato.conteudo.startsWith('/uploads/') && artefato.linguagem === 'pdf' ? (
                  <iframe
                    src={`${artefato.conteudo}#toolbar=0&navpanes=0`}
                    className="w-full h-full border-0"
                    title={artefato.titulo}
                    style={{ background: '#fff' }}
                  />
                ) : artefato.conteudo.startsWith('/uploads/') ? (
                  <div className="flex flex-col items-center justify-center h-full gap-4 px-6">
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                      style={{ background: 'rgba(16,185,129,0.1)' }}>
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--sf-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold" style={{ color: 'var(--sf-text-0)' }}>{artefato.titulo}</p>
                    <p className="text-xs" style={{ color: 'var(--sf-text-3)' }}>
                      {artefato.linguagem.toUpperCase()} · Pronto para download
                    </p>
                    <a
                      href={artefato.conteudo}
                      download={artefato.titulo}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all hover:brightness-110"
                      style={{ background: 'var(--sf-accent)', color: '#fff' }}
                    >
                      Baixar {artefato.linguagem.toUpperCase()}
                    </a>
                  </div>
                ) : artefato.tipo === 'html' ? (
                  <iframe
                    srcDoc={artefato.conteudo}
                    sandbox="allow-scripts allow-same-origin"
                    className="w-full h-full border-0"
                    title={artefato.titulo}
                    style={{ background: '#fff' }}
                  />
                ) : artefato.tipo === 'markdown' ? (
                  <div className="px-6 py-4">
                    <MarkdownRenderer content={artefato.conteudo} />
                  </div>
                ) : (
                  <div className="px-2 py-2">
                    <MarkdownRenderer
                      content={`\`\`\`${artefato.linguagem}\n${artefato.conteudo}\n\`\`\``}
                    />
                  </div>
                )}
              </div>

              {/* Sidebar de comentários */}
              <AnimatePresence>
                {mostrarComentarios && (
                  <motion.div
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 280, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex flex-col flex-shrink-0 overflow-hidden"
                    style={{
                      borderLeft: '1px solid var(--sf-border-subtle)',
                      background: 'var(--sf-bg-1, rgba(255,255,255,0.02))',
                    }}
                  >
                    {/* Header dos comentários */}
                    <div className="px-3 py-2.5 flex items-center gap-2 flex-shrink-0"
                      style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
                      <MessageCircle size={14} style={{ color: 'var(--sf-accent)' }} />
                      <span className="text-[12px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
                        Comentários
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full"
                        style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--sf-accent)' }}>
                        {comentarios.length}
                      </span>
                    </div>

                    {/* Lista de comentários */}
                    <div ref={comentariosRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-3"
                      style={{ scrollbarWidth: 'thin' }}>
                      {comentarios.length === 0 ? (
                        <p className="text-center text-[11px] py-8" style={{ color: 'var(--sf-text-3)' }}>
                          Nenhum comentário ainda.
                          <br />Seja o primeiro a comentar!
                        </p>
                      ) : (
                        comentarios.map(c => (
                          <div key={c.id} className="group rounded-lg p-2.5 transition-all"
                            style={{ background: 'rgba(255,255,255,0.03)' }}>
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-1.5">
                                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white"
                                  style={{ background: '#10b981' }}>
                                  {c.usuario_nome.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                                </div>
                                <span className="text-[11px] font-semibold" style={{ color: 'var(--sf-text-1)' }}>
                                  {c.usuario_nome.split(' ')[0]}
                                </span>
                                <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>
                                  {formatarDataRelativa(c.criado_em)}
                                </span>
                              </div>
                              {(String(c.usuario_id) === String(usuarioAtual?.id) || ehProprietario) && (
                                <button
                                  onClick={() => handleExcluirComentario(c.id)}
                                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all hover:text-red-400"
                                  style={{ color: 'var(--sf-text-3)' }}
                                  title="Excluir comentário"
                                >
                                  <Trash2 size={11} />
                                </button>
                              )}
                            </div>
                            <p className="text-[12px] leading-relaxed pl-6.5" style={{ color: 'var(--sf-text-1)', paddingLeft: '26px' }}>
                              {c.conteudo}
                            </p>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Input para novo comentário */}
                    <div className="px-3 py-2.5 flex-shrink-0"
                      style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
                      <div className="flex items-center gap-1.5 rounded-lg overflow-hidden"
                        style={{
                          background: 'rgba(255,255,255,0.05)',
                          border: '1px solid var(--sf-border-subtle)',
                        }}>
                        <input
                          type="text"
                          value={novoComentario}
                          onChange={e => setNovoComentario(e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleEnviarComentario()}
                          placeholder="Comentar..."
                          className="flex-1 bg-transparent px-3 py-2 text-[12px] outline-none"
                          style={{ color: 'var(--sf-text-0)' }}
                          disabled={enviando}
                        />
                        <button
                          onClick={handleEnviarComentario}
                          disabled={!novoComentario.trim() || enviando}
                          className="p-2 transition-all disabled:opacity-30"
                          style={{ color: 'var(--sf-accent)' }}
                        >
                          <Send size={14} />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-between px-4 py-3 flex-shrink-0"
              style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
            >
              <div className="flex items-center gap-2">
                <button
                  onClick={copiar}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
                  style={{
                    background: copiado ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.05)',
                    color: copiado ? 'var(--sf-accent)' : 'var(--sf-text-2)',
                    border: '1px solid var(--sf-border-subtle)',
                  }}
                >
                  {copiado ? <Check size={12} /> : <Copy size={12} />}
                  {copiado ? 'Copiado!' : 'Copiar'}
                </button>
              </div>

              {artefato.tipo === 'html' && (
                <button
                  onClick={() => abrirEmNovaAba(artefato.conteudo)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
                  style={{
                    background: 'var(--sf-accent)',
                    color: '#fff',
                  }}
                >
                  <ExternalLink size={12} />
                  Abrir em nova aba
                </button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
