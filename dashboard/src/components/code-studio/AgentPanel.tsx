/* AgentPanel — Painel lateral com chat do agente IA + ações automáticas */

import { useState, useRef, useEffect, useCallback } from 'react'
import { Bot, Send, Sparkles, BookOpen, RefreshCw, FileCode, Loader2, X, TestTube2, Play, Copy, Check, AlertTriangle } from 'lucide-react'
import MarkdownRenderer from '../luna/MarkdownRenderer'
import { analisarCodigo, aplicarAcao } from '../../services/codeStudio'

interface Mensagem {
  papel: 'user' | 'assistant'
  conteudo: string
  provider?: string
  tipoAcao?: 'refatorar' | 'documentar' | 'otimizar' | 'testar' | 'geral'
}

interface AgentPanelProps {
  caminhoAtivo?: string
  conteudoAtivo?: string
  linguagem?: string
  onFechar: () => void
  agenteNome?: string
  onArquivoAtualizado?: () => void  // Recarregar arquivo no editor após aplicar
}

const ACOES_RAPIDAS = [
  { label: 'Explicar', icon: BookOpen, tipo: 'geral' as const, instrucao: 'Explique este código de forma clara e didática. Descreva o que cada parte faz, qual o propósito geral e como se encaixa no projeto.' },
  { label: 'Refatorar', icon: RefreshCw, tipo: 'refatorar' as const, instrucao: 'Sugira melhorias e refatorações para este código. Mostre o código melhorado COMPLETO (todo o arquivo) dentro de um único bloco de código. Não omita nenhuma parte.' },
  { label: 'Documentar', icon: FileCode, tipo: 'documentar' as const, instrucao: 'Adicione docstrings/JSDoc/comentários de documentação profissional. Mostre o código COMPLETO (todo o arquivo) com a documentação dentro de um único bloco de código.' },
  { label: 'Otimizar', icon: Sparkles, tipo: 'otimizar' as const, instrucao: 'Identifique gargalos de performance e sugira otimizações. Mostre o código COMPLETO otimizado dentro de um único bloco de código.' },
  { label: 'Testar', icon: TestTube2, tipo: 'testar' as const, instrucao: 'Crie testes unitários completos para este código. Use o framework adequado (pytest para Python, vitest/jest para TypeScript). Mostre o código completo dos testes dentro de um único bloco de código.' },
]

/** Extrai o maior bloco de código de uma resposta markdown */
function extrairBlocoCodigo(conteudo: string): string | null {
  const regex = /```[\w]*\n([\s\S]*?)```/g
  let maior = ''
  let match
  while ((match = regex.exec(conteudo)) !== null) {
    if (match[1].length > maior.length) maior = match[1]
  }
  return maior.trim() || null
}

/** Gera caminho do arquivo de teste baseado no arquivo original */
function gerarCaminhoTeste(caminho: string): string {
  const partes = caminho.split('/')
  const nome = partes.pop() || 'test'
  const ext = nome.split('.').pop() || 'py'
  const nomeBase = nome.replace(/\.[^.]+$/, '')

  if (ext === 'py') {
    // Python: tests/test_<nome>.py
    return `tests/test_${nomeBase}.py`
  }
  // TypeScript/JavaScript: __tests__/<nome>.test.<ext>
  const dir = partes.join('/')
  return `${dir}/__tests__/${nomeBase}.test.${ext}`
}

export default function AgentPanel({
  caminhoAtivo, conteudoAtivo, linguagem, onFechar, agenteNome, onArquivoAtualizado,
}: AgentPanelProps) {
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [input, setInput] = useState('')
  const [analisando, setAnalisando] = useState(false)
  const [aplicando, setAplicando] = useState<number | null>(null)  // índice da mensagem sendo aplicada
  const [toast, setToast] = useState<{ msg: string; tipo: 'ok' | 'erro' } | null>(null)
  const [copiado, setCopiado] = useState<number | null>(null)
  const chatRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: 'smooth' })
  }, [mensagens])

  // Auto-hide toast
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 4000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const enviar = async (instrucao: string, tipoAcao: Mensagem['tipoAcao'] = 'geral') => {
    if (!caminhoAtivo || !conteudoAtivo || analisando) return

    const nomeArquivo = caminhoAtivo.split('/').pop() || ''
    const lang = linguagem?.toUpperCase() || 'TEXT'
    const instrucaoComContexto = `[Arquivo: ${nomeArquivo} | Linguagem: ${lang} | Caminho: ${caminhoAtivo}]\n\n${instrucao}`

    setMensagens(prev => [...prev, { papel: 'user', conteudo: instrucao }])
    setInput('')
    setAnalisando(true)

    try {
      const resultado = await analisarCodigo(caminhoAtivo, conteudoAtivo, instrucaoComContexto)
      setMensagens(prev => [...prev, {
        papel: 'assistant',
        conteudo: resultado.resposta,
        provider: `${resultado.provider} · ${resultado.modelo}`,
        tipoAcao,
      }])
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Falha na análise'
      const ehToken = msg.toLowerCase().includes('token') || msg.includes('401') || msg.includes('expirado')
      setMensagens(prev => [...prev, {
        papel: 'assistant',
        conteudo: ehToken
          ? '⚠️ **Sessão expirada.** Faça logout e login novamente.'
          : `❌ **Erro:** ${msg}`,
      }])
    } finally {
      setAnalisando(false)
    }
  }

  const copiarCodigo = useCallback((idx: number, codigo: string) => {
    navigator.clipboard.writeText(codigo)
    setCopiado(idx)
    setTimeout(() => setCopiado(null), 2000)
  }, [])

  const handleAplicar = useCallback(async (idx: number, msg: Mensagem) => {
    if (!caminhoAtivo || aplicando !== null) return
    const codigo = extrairBlocoCodigo(msg.conteudo)
    if (!codigo) {
      setToast({ msg: 'Nenhum bloco de código encontrado na resposta', tipo: 'erro' })
      return
    }

    setAplicando(idx)
    try {
      if (msg.tipoAcao === 'testar') {
        // Criar arquivo de teste
        const caminhoTeste = gerarCaminhoTeste(caminhoAtivo)
        await aplicarAcao(caminhoTeste, codigo, 'criar')
        setToast({ msg: `✅ Teste criado em ${caminhoTeste}`, tipo: 'ok' })
      } else {
        // Substituir arquivo atual
        await aplicarAcao(caminhoAtivo, codigo, 'substituir')
        setToast({ msg: `✅ ${msg.tipoAcao === 'refatorar' ? 'Refatoração' : msg.tipoAcao === 'documentar' ? 'Documentação' : 'Otimização'} aplicada!`, tipo: 'ok' })
        onArquivoAtualizado?.()
      }
    } catch (e) {
      setToast({ msg: `❌ ${e instanceof Error ? e.message : 'Erro ao aplicar'}`, tipo: 'erro' })
    } finally {
      setAplicando(null)
    }
  }, [caminhoAtivo, linguagem, aplicando, onArquivoAtualizado])

  /** Qual label mostrar no botão de aplicar */
  const labelAplicar = (tipo?: Mensagem['tipoAcao']) => {
    switch (tipo) {
      case 'refatorar': return 'Aplicar Refatoração'
      case 'documentar': return 'Aplicar Documentação'
      case 'otimizar': return 'Aplicar Otimização'
      case 'testar': return 'Criar Arquivo de Teste'
      default: return null
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
                onClick={() => enviar(acao.instrucao, acao.tipo)}
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

      {/* Toast */}
      {toast && (
        <div className="mx-2 mt-2 px-3 py-2 rounded-lg text-[11px] font-medium animate-pulse"
          style={{
            background: toast.tipo === 'ok' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
            color: toast.tipo === 'ok' ? '#10b981' : '#ef4444',
            border: `1px solid ${toast.tipo === 'ok' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
          {toast.msg}
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

                {/* Botões de ação automática */}
                {msg.tipoAcao && msg.tipoAcao !== 'geral' && extrairBlocoCodigo(msg.conteudo) && (
                  <div className="flex items-center gap-1.5 mt-2 pt-2"
                    style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
                    {/* Aplicar */}
                    <button
                      onClick={() => handleAplicar(i, msg)}
                      disabled={aplicando !== null}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
                      style={{
                        background: msg.tipoAcao === 'testar' ? 'rgba(59,130,246,0.15)' : 'rgba(16,185,129,0.15)',
                        color: msg.tipoAcao === 'testar' ? '#3b82f6' : '#10b981',
                        border: `1px solid ${msg.tipoAcao === 'testar' ? 'rgba(59,130,246,0.2)' : 'rgba(16,185,129,0.2)'}`,
                      }}
                    >
                      {aplicando === i ? (
                        <Loader2 size={10} className="animate-spin" />
                      ) : (
                        <Play size={10} />
                      )}
                      {aplicando === i ? 'Aplicando...' : labelAplicar(msg.tipoAcao)}
                    </button>

                    {/* Copiar código */}
                    <button
                      onClick={() => copiarCodigo(i, extrairBlocoCodigo(msg.conteudo) || '')}
                      className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-all hover:bg-white/5"
                      style={{ color: 'var(--sf-text-3)' }}
                    >
                      {copiado === i ? <Check size={10} /> : <Copy size={10} />}
                      {copiado === i ? 'Copiado!' : 'Copiar'}
                    </button>
                  </div>
                )}

                {/* Copiar para respostas normais que têm código */}
                {(!msg.tipoAcao || msg.tipoAcao === 'geral') && extrairBlocoCodigo(msg.conteudo) && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <button
                      onClick={() => copiarCodigo(i, extrairBlocoCodigo(msg.conteudo) || '')}
                      className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-all hover:bg-white/5"
                      style={{ color: 'var(--sf-text-3)' }}
                    >
                      {copiado === i ? <Check size={10} /> : <Copy size={10} />}
                      {copiado === i ? 'Copiado!' : 'Copiar código'}
                    </button>
                  </div>
                )}

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

      {/* Aviso de segurança */}
      {mensagens.some(m => m.tipoAcao && m.tipoAcao !== 'geral') && (
        <div className="px-2 py-1.5 flex items-center gap-1.5 text-[9px] flex-shrink-0"
          style={{ background: 'rgba(245,158,11,0.05)', color: '#f59e0b', borderTop: '1px solid var(--sf-border-subtle)' }}>
          <AlertTriangle size={10} />
          Backup automático antes de cada aplicação
        </div>
      )}

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
            style={{ borderColor: 'var(--sf-border-subtle)', color: 'var(--sf-text-1)' }}
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
