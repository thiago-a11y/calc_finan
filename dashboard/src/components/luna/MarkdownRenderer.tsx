/* MarkdownRenderer — Renderizador Markdown reutilizável com syntax highlight */

import { useState, useCallback, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'

interface MarkdownRendererProps {
  content: string
}

/** Botao de copiar reutilizavel */
function BotaoCopiar({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false)

  const copiar = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // fallback silencioso
    }
  }, [texto])

  return (
    <button
      onClick={copiar}
      className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all duration-200 hover:scale-105"
      style={{
        background: copiado ? 'var(--sf-accent)' : 'rgba(255,255,255,0.08)',
        color: copiado ? '#fff' : 'var(--sf-text-3)',
      }}
      title="Copiar codigo"
    >
      {copiado ? <Check size={12} /> : <Copy size={12} />}
      {copiado ? 'Copiado!' : 'Copiar'}
    </button>
  )
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const { isDark } = useTheme()

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        /* --- Blocos de codigo --- */
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '')
          const codeString = String(children).replace(/\n$/, '')

          if (match) {
            return (
              <div
                className="relative rounded-lg overflow-hidden my-3"
                style={{ border: '1px solid var(--sf-border-subtle)' }}
              >
                {/* Barra superior do bloco de codigo */}
                <div
                  className="flex items-center justify-between px-3 py-1.5"
                  style={{
                    background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)',
                    borderBottom: '1px solid var(--sf-border-subtle)',
                  }}
                >
                  <span
                    className="text-[11px] font-mono font-medium uppercase tracking-wide"
                    style={{ color: 'var(--sf-accent)' }}
                  >
                    {match[1]}
                  </span>
                  <BotaoCopiar texto={codeString} />
                </div>

                <SyntaxHighlighter
                  style={isDark ? oneDark : oneLight}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    padding: '16px',
                    fontSize: '13px',
                    lineHeight: '1.6',
                    background: isDark ? '#1a1b26' : '#fafafa',
                    borderRadius: 0,
                  }}
                >
                  {codeString}
                </SyntaxHighlighter>
              </div>
            )
          }

          // Codigo inline
          return (
            <code
              className="px-1.5 py-0.5 rounded text-[13px] font-mono"
              style={{
                background: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                color: 'var(--sf-accent)',
              }}
              {...props}
            >
              {children}
            </code>
          )
        },

        /* --- Tabelas --- */
        table({ children }) {
          return (
            <div className="overflow-x-auto my-3 rounded-lg" style={{ border: '1px solid var(--sf-border-subtle)' }}>
              <table className="w-full text-[13px]">{children}</table>
            </div>
          )
        },
        thead({ children }) {
          return (
            <thead style={{ background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }}>
              {children}
            </thead>
          )
        },
        th({ children }: { children?: ReactNode }) {
          return (
            <th
              className="px-3 py-2 text-left font-semibold text-[12px] uppercase tracking-wide"
              style={{
                color: 'var(--sf-text-2)',
                borderBottom: '1px solid var(--sf-border-subtle)',
              }}
            >
              {children}
            </th>
          )
        },
        td({ children }: { children?: ReactNode }) {
          return (
            <td
              className="px-3 py-2"
              style={{
                color: 'var(--sf-text-1)',
                borderBottom: '1px solid var(--sf-border-subtle)',
              }}
            >
              {children}
            </td>
          )
        },

        /* --- Links --- */
        a({ href, children }) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 transition-colors hover:brightness-110"
              style={{ color: 'var(--sf-accent)' }}
            >
              {children}
            </a>
          )
        },

        /* --- Paragrafo --- */
        p({ children }) {
          return (
            <p className="my-2 leading-relaxed text-[14px]" style={{ color: 'var(--sf-text-1)' }}>
              {children}
            </p>
          )
        },

        /* --- Headings --- */
        h1({ children }) {
          return (
            <h1 className="text-xl font-bold mt-4 mb-2" style={{ color: 'var(--sf-text-0)' }}>
              {children}
            </h1>
          )
        },
        h2({ children }) {
          return (
            <h2 className="text-lg font-bold mt-3 mb-2" style={{ color: 'var(--sf-text-0)' }}>
              {children}
            </h2>
          )
        },
        h3({ children }) {
          return (
            <h3 className="text-base font-semibold mt-3 mb-1" style={{ color: 'var(--sf-text-0)' }}>
              {children}
            </h3>
          )
        },

        /* --- Listas --- */
        ul({ children }) {
          return <ul className="list-disc list-inside my-2 space-y-1" style={{ color: 'var(--sf-text-1)' }}>{children}</ul>
        },
        ol({ children }) {
          return <ol className="list-decimal list-inside my-2 space-y-1" style={{ color: 'var(--sf-text-1)' }}>{children}</ol>
        },
        li({ children }) {
          return <li className="text-[14px] leading-relaxed">{children}</li>
        },

        /* --- Blockquote --- */
        blockquote({ children }) {
          return (
            <blockquote
              className="my-3 pl-4 py-1 rounded-r"
              style={{
                borderLeft: '3px solid var(--sf-accent)',
                background: isDark ? 'rgba(16,185,129,0.06)' : 'rgba(16,185,129,0.08)',
                color: 'var(--sf-text-2)',
              }}
            >
              {children}
            </blockquote>
          )
        },

        /* --- Linha horizontal --- */
        hr() {
          return <hr className="my-4" style={{ borderColor: 'var(--sf-border-subtle)' }} />
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
