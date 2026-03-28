/* LunaChat — Area de mensagens do chat com auto-scroll e acoes */

import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { Copy, Check, RefreshCw, ChevronUp, Play } from 'lucide-react'
import AgentAvatar from '../AgentAvatar'
import { motion, AnimatePresence } from 'framer-motion'
import MarkdownRenderer from './MarkdownRenderer'
import LunaFileBlock, { extrairBlocosArquivo } from './LunaFileBlock'
import type { LunaMensagem, LunaArtefato } from '../../types'

interface LunaChatProps {
  mensagens: LunaMensagem[]
  streaming: boolean
  textoStreaming: string
  temMais: boolean
  onCarregarMais: () => void
  onCopiar: (texto: string) => void
  onRegenerar: () => void
  onAbrirPreview: (artefato: LunaArtefato) => void
}

/** Formata timestamp para hora legivel */
function formatarHora(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

/** Extrai blocos de codigo de uma string markdown */
function extrairBlocosCodigo(conteudo: string): LunaArtefato[] {
  const regex = /```(\w+)?\n([\s\S]*?)```/g
  const artefatos: LunaArtefato[] = []
  let match: RegExpExecArray | null
  let idx = 0

  while ((match = regex.exec(conteudo)) !== null) {
    const linguagem = match[1] || 'text'
    const codigo = match[2].trim()
    const tipoMap: Record<string, LunaArtefato['tipo']> = {
      html: 'html',
      markdown: 'markdown',
      md: 'markdown',
    }
    const tipo = tipoMap[linguagem] || 'codigo'

    artefatos.push({
      id: `art-${Date.now()}-${idx}`,
      tipo,
      linguagem,
      conteudo: codigo,
      titulo: `${linguagem.toUpperCase()} — Bloco ${idx + 1}`,
    })
    idx++
  }

  return artefatos
}

/** Botao de copiar inline */
function BotaoCopiarInline({ texto, onCopiar }: { texto: string; onCopiar: (t: string) => void }) {
  const [copiado, setCopiado] = useState(false)

  const handleCopiar = useCallback(() => {
    onCopiar(texto)
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }, [texto, onCopiar])

  return (
    <button
      onClick={handleCopiar}
      className="flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-all hover:scale-105"
      style={{
        background: 'rgba(255,255,255,0.05)',
        color: copiado ? 'var(--sf-accent)' : 'var(--sf-text-4)',
      }}
      title="Copiar mensagem"
    >
      {copiado ? <Check size={12} /> : <Copy size={12} />}
    </button>
  )
}

export default function LunaChat({
  mensagens,
  streaming,
  textoStreaming,
  temMais,
  onCarregarMais,
  onCopiar,
  onRegenerar,
  onAbrirPreview,
}: LunaChatProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [hoveredMsgId, setHoveredMsgId] = useState<number | null>(null)

  /* Auto-scroll: detectar scroll manual */
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const distFundo = el.scrollHeight - el.scrollTop - el.clientHeight
    setAutoScroll(distFundo < 80)
  }, [])

  /* Scroll para baixo quando novas mensagens chegam */
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [mensagens, textoStreaming, autoScroll])

  /* Artefatos extraidos de mensagens da Luna (memoizado) */
  const artefatosPorMsg = useMemo(() => {
    const mapa = new Map<number, LunaArtefato[]>()
    for (const msg of mensagens) {
      if (msg.papel === 'assistant') {
        const arts = extrairBlocosCodigo(msg.conteudo)
        if (arts.length > 0) mapa.set(msg.id, arts)
      }
    }
    return mapa
  }, [mensagens])

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      style={{ scrollbarWidth: 'thin' }}
    >
      {/* Carregar mais */}
      {temMais && (
        <div className="flex justify-center mb-2">
          <button
            onClick={onCarregarMais}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
            style={{
              background: 'rgba(255,255,255,0.05)',
              color: 'var(--sf-text-3)',
              border: '1px solid var(--sf-border-subtle)',
            }}
          >
            <ChevronUp size={14} />
            Carregar mais
          </button>
        </div>
      )}

      {/* Mensagens */}
      <AnimatePresence initial={false}>
        {mensagens.map((msg) => {
          const isUser = msg.papel === 'user'
          const artefatos = artefatosPorMsg.get(msg.id) || []

          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
              onMouseEnter={() => setHoveredMsgId(msg.id)}
              onMouseLeave={() => setHoveredMsgId(null)}
            >
              {/* Avatar da Luna */}
              {!isUser && (
                <div className="flex-shrink-0 mr-2 mt-1">
                  <AgentAvatar agentName="luna" size="md" noHover />
                </div>
              )}

              <div className={`max-w-[75%] ${isUser ? '' : 'flex-1'}`}>
                {/* Balao da mensagem */}
                <div
                  className={`rounded-2xl px-4 py-3 ${isUser ? 'rounded-br-md' : 'sf-card rounded-bl-md'}`}
                  style={
                    isUser
                      ? {
                          background: 'var(--sf-accent)',
                          color: '#fff',
                        }
                      : {
                          border: '1px solid var(--sf-border-subtle)',
                        }
                  }
                >
                  {isUser ? (
                    <>
                      <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{msg.conteudo}</p>
                      {/* Anexos do usuário */}
                      {msg.anexos && msg.anexos.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.15)' }}>
                          {msg.anexos.map((a, idx) => (
                            <a
                              key={idx}
                              href={a.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] transition-colors hover:brightness-110"
                              style={{
                                background: 'rgba(255,255,255,0.15)',
                                color: '#fff',
                              }}
                            >
                              <span>{a.tipo === 'imagem' ? '🖼️' : a.tipo === 'pdf' ? '📕' : a.tipo === 'video' ? '🎬' : '📄'}</span>
                              <span className="truncate max-w-[100px]">{a.nome_original}</span>
                            </a>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    (() => {
                      const { textoLimpo, arquivos } = extrairBlocosArquivo(msg.conteudo)
                      return (
                        <>
                          {textoLimpo && <MarkdownRenderer content={textoLimpo} />}
                          {arquivos.map((arq, idx) => (
                            <LunaFileBlock
                              key={`${msg.id}-file-${idx}`}
                              nome={arq.nome}
                              conteudo={arq.conteudo}
                              conversaId={msg.conversa_id}
                              onPreview={(url, fmt, nome) => {
                                onAbrirPreview({
                                  id: `file-${msg.id}-${idx}`,
                                  tipo: fmt === 'html' ? 'html' : 'codigo',
                                  linguagem: fmt,
                                  conteudo: url,
                                  titulo: nome,
                                })
                              }}
                            />
                          ))}
                        </>
                      )
                    })()
                  )}

                  {/* Botoes de preview para blocos de codigo */}
                  {artefatos.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2 pt-2" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
                      {artefatos.map((art) => (
                        <button
                          key={art.id}
                          onClick={() => onAbrirPreview(art)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all hover:scale-105"
                          style={{
                            background: 'rgba(16,185,129,0.1)',
                            color: 'var(--sf-accent)',
                            border: '1px solid rgba(16,185,129,0.2)',
                          }}
                        >
                          <Play size={10} />
                          Preview {art.linguagem.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Timestamp e acoes */}
                <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <span className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>
                    {formatarHora(msg.criado_em)}
                  </span>

                  {/* Acoes (hover) — apenas mensagens da Luna */}
                  {!isUser && hoveredMsgId === msg.id && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="flex items-center gap-1"
                    >
                      <BotaoCopiarInline texto={msg.conteudo} onCopiar={onCopiar} />
                      <button
                        onClick={onRegenerar}
                        className="flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-all hover:scale-105"
                        style={{
                          background: 'rgba(255,255,255,0.05)',
                          color: 'var(--sf-text-4)',
                        }}
                        title="Regenerar resposta"
                      >
                        <RefreshCw size={12} />
                      </button>
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* Streaming em andamento */}
      {streaming && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-start"
        >
          {/* Avatar */}
          <div className="flex-shrink-0 mr-2 mt-1">
            <AgentAvatar agentName="luna" size="md" showStatus status="pensando" noHover />
          </div>

          <div className="max-w-[75%] flex-1">
            <div
              className="sf-card rounded-2xl rounded-bl-md px-4 py-3"
              style={{ border: '1px solid var(--sf-border-subtle)' }}
            >
              {textoStreaming ? (
                <MarkdownRenderer content={textoStreaming} />
              ) : (
                /* Indicador de pulsacao */
                <div className="flex items-center gap-1.5 py-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="inline-block w-2 h-2 rounded-full animate-pulse"
                      style={{
                        background: 'var(--sf-accent)',
                        animationDelay: `${i * 200}ms`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
