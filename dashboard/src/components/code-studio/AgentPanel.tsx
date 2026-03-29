/* AgentPanel — Painel lateral com chat do agente IA */

import { useState, useRef, useEffect } from 'react'
import { Bot, Send, Sparkles, BookOpen, RefreshCw, FileCode, Loader2, X, TestTube2 } from 'lucide-react'
import MarkdownRenderer from '../luna/MarkdownRenderer'
import { analisarCodigo } from '../../services/codeStudio'

interface Mensagem {
  papel: 'user' | 'assistant'
  conteudo: string
  provider?: string
}

interface AgentPanelProps {
  caminhoAtivo?: string
  conteudoAtivo?: string
  linguagem?: string
  onFechar: () => void
  agenteNome?: string
}

const ACOES_RAPIDAS = [
  { label: 'Explicar', icon: BookOpen, instrucao: 'Explique este código de forma clara e didática. Descreva o que cada parte faz, qual o propósito geral e como se encaixa no projeto.' },
  { label: 'Refatorar', icon: RefreshCw, instrucao: 'Sugira melhorias e refatorações para este código. Mostre o código melhorado completo com explicação das mudanças.' },
  { label: 'Documentar', icon: FileCode, instrucao: 'Adicione docstrings/JSDoc/comentários de documentação profissional neste código. Mostre o código completo com a documentação.' },
  { label: 'Otimizar', icon: Sparkles, instrucao: 'Identifique gargalos de performance, problemas de memória e sugira otimizações. Mostre o código otimizado.' },
  { label: 'Testar', icon: TestTube2, instrucao: 'Crie testes unitários completos para este código. Use o framework de teste adequado (pytest para Python, vitest/jest para TypeScript).' },
]

export default function AgentPanel({ caminhoAtivo, conteudoAtivo, linguagem, onFechar, agenteNome }: AgentPanelProps) {
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [input, setInput] = useState('')
  const [analisando, setAnalisando] = useState(false)
  const chatRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: 'smooth' })
  }, [mensagens])

  const enviar = async (instrucao: string) => {
    if (!caminhoAtivo || !conteudoAtivo || analisando) return

    // Enriquecer instrução com contexto do arquivo
    const nomeArquivo = caminhoAtivo.split('/').pop() || ''
    const lang = linguagem?.toUpperCase() || 'TEXT'
    const instrucaoComContexto = `[Arquivo: ${nomeArquivo} | Linguagem: ${lang} | Caminho: ${caminhoAtivo}]\n\n${instrucao}`

    const novaMensagemUser: Mensagem = { papel: 'user', conteudo: instrucao }
    setMensagens(prev => [...prev, novaMensagemUser])
    setInput('')
    setAnalisando(true)

    try {
      const resultado = await analisarCodigo(caminhoAtivo, conteudoAtivo, instrucaoComContexto)
      setMensagens(prev => [...prev, {
        papel: 'assistant',
        conteudo: resultado.resposta,
        provider: `${resultado.provider} · ${resultado.modelo}`,
      }])
    } catch (e) {
      setMensagens(prev => [...prev, {
        papel: 'assistant',
        conteudo: `Erro: ${e instanceof Error ? e.message : 'Falha na análise'}`,
      }])
    } finally {
      setAnalisando(false)
    }
  }

  return (
    <div className="h-full flex flex-col" style={{ borderLeft: '1px solid var(--sf-border-subtle)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <div className="flex items-center gap-2">
          <Bot size={16} style={{ color: '#8b5cf6' }} />
          <div>
            <span className="text-[12px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
              {agenteNome || 'Agente IA'}
            </span>
            {agenteNome && (
              <p className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>Assistente de código</p>
            )}
          </div>
        </div>
        <button onClick={onFechar} className="p-1 rounded hover:bg-white/5"
          style={{ color: 'var(--sf-text-3)' }}>
          <X size={14} />
        </button>
      </div>

      {/* Ações rápidas */}
      {caminhoAtivo && (
        <div className="flex flex-wrap gap-1 px-2 py-2 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
          {ACOES_RAPIDAS.map(acao => {
            const Icon = acao.icon
            return (
              <button
                key={acao.label}
                onClick={() => enviar(acao.instrucao)}
                disabled={analisando}
                className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-all hover:brightness-125 disabled:opacity-40"
                style={{ background: 'rgba(139,92,246,0.1)', color: '#a78bfa' }}
              >
                <Icon size={10} />
                {acao.label}
              </button>
            )
          })}
        </div>
      )}

      {/* Chat */}
      <div ref={chatRef} className="flex-1 overflow-auto px-3 py-3 space-y-3" style={{ scrollbarWidth: 'thin' }}>
        {mensagens.length === 0 && (
          <div className="text-center py-8">
            <Bot size={32} className="mx-auto mb-3" style={{ color: 'var(--sf-text-3)', opacity: 0.4 }} />
            <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
              {caminhoAtivo
                ? `Analisando ${caminhoAtivo.split('/').pop()}`
                : 'Selecione um arquivo para analisar'}
            </p>
            <p className="text-[10px] mt-1" style={{ color: 'var(--sf-text-3)', opacity: 0.6 }}>
              Use os botões acima ou digite uma pergunta
            </p>
          </div>
        )}

        {mensagens.map((msg, i) => (
          <div key={i} className={`${msg.papel === 'user' ? 'text-right' : ''}`}>
            {msg.papel === 'user' ? (
              <div className="inline-block max-w-[90%] px-3 py-1.5 rounded-xl text-[11px] text-left"
                style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--sf-text-1)' }}>
                {msg.conteudo}
              </div>
            ) : (
              <div className="text-left">
                <div className="text-[11px] leading-relaxed prose-sm" style={{ color: 'var(--sf-text-1)' }}>
                  <MarkdownRenderer content={msg.conteudo} />
                </div>
                {msg.provider && (
                  <p className="text-[9px] mt-1" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>
                    {msg.provider}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}

        {analisando && (
          <div className="flex items-center gap-2 text-[11px]" style={{ color: '#8b5cf6' }}>
            <Loader2 size={12} className="animate-spin" />
            Analisando código...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-2 py-2 flex-shrink-0" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
        <div className="flex items-center gap-1.5">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && input.trim()) enviar(input.trim()) }}
            placeholder={caminhoAtivo ? 'Pergunte sobre o código...' : 'Selecione um arquivo'}
            disabled={!caminhoAtivo || analisando}
            className="flex-1 bg-transparent border rounded-lg px-2 py-1.5 text-[11px] outline-none disabled:opacity-40"
            style={{
              borderColor: 'var(--sf-border-subtle)',
              color: 'var(--sf-text-1)',
            }}
          />
          <button
            onClick={() => input.trim() && enviar(input.trim())}
            disabled={!input.trim() || !caminhoAtivo || analisando}
            className="p-1.5 rounded-lg transition-all disabled:opacity-30"
            style={{ background: 'rgba(139,92,246,0.2)', color: '#a78bfa' }}
          >
            <Send size={12} />
          </button>
        </div>
        {caminhoAtivo && (
          <p className="text-[9px] mt-1 px-1" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>
            {linguagem?.toUpperCase()} · Smart Router · Enter para enviar
          </p>
        )}
      </div>
    </div>
  )
}
