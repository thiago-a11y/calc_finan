/* LunaPreview — Painel de preview de artefatos (estilo Claude Artifacts) */

import { useState, useCallback } from 'react'
import { X, ExternalLink, Copy, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import MarkdownRenderer from './MarkdownRenderer'
import type { LunaArtefato } from '../../types'

interface LunaPreviewProps {
  artefato: LunaArtefato | null
  artefatos: LunaArtefato[]
  onFechar: () => void
  onSelecionarArtefato: (id: string) => void
}

/** Abre conteudo HTML em nova aba */
function abrirEmNovaAba(html: string) {
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

export default function LunaPreview({
  artefato,
  artefatos,
  onFechar,
  onSelecionarArtefato,
}: LunaPreviewProps) {
  const [copiado, setCopiado] = useState(false)

  const copiar = useCallback(async () => {
    if (!artefato) return
    try {
      await navigator.clipboard.writeText(artefato.conteudo)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // fallback silencioso
    }
  }, [artefato])

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
              width: '50%',
              minWidth: '400px',
              maxWidth: '800px',
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
              <button
                onClick={onFechar}
                className="p-1.5 rounded-lg transition-colors hover:brightness-125"
                style={{ color: 'var(--sf-text-3)' }}
              >
                <X size={18} />
              </button>
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

            {/* Conteudo */}
            <div className="flex-1 overflow-auto" style={{ scrollbarWidth: 'thin' }}>
              {artefato.conteudo.startsWith('/uploads/') && artefato.linguagem === 'pdf' ? (
                /* PDF renderizado em iframe */
                <iframe
                  src={artefato.conteudo}
                  className="w-full h-full border-0"
                  title={artefato.titulo}
                  style={{ background: '#fff' }}
                />
              ) : artefato.conteudo.startsWith('/uploads/') ? (
                /* Arquivo para download — mostrar info + botão */
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
                /* HTML renderizado em iframe sandboxed */
                <iframe
                  srcDoc={artefato.conteudo}
                  sandbox="allow-scripts allow-same-origin"
                  className="w-full h-full border-0"
                  title={artefato.titulo}
                  style={{ background: '#fff' }}
                />
              ) : artefato.tipo === 'markdown' ? (
                /* Markdown renderizado */
                <div className="px-6 py-4">
                  <MarkdownRenderer content={artefato.conteudo} />
                </div>
              ) : (
                /* Codigo com syntax highlight */
                <div className="px-2 py-2">
                  <MarkdownRenderer
                    content={`\`\`\`${artefato.linguagem}\n${artefato.conteudo}\n\`\`\``}
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-between px-4 py-3 flex-shrink-0"
              style={{ borderTop: '1px solid var(--sf-border-subtle)' }}
            >
              <div className="flex items-center gap-2">
                {/* Botao copiar */}
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

              {/* Abrir em nova aba (apenas HTML) */}
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
