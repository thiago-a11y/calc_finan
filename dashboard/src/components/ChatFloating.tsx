/* ChatFloating — Janela de chat flutuante com modo expandido */

import { useState, useEffect, useRef, useCallback } from 'react'
import { executarTarefa, buscarTarefa, buscarHistoricoTarefas } from '../services/api'
import { FileUploadArea } from './FileUpload'
import type { TarefaResultado, FileAttachment } from '../types'
import { Maximize2, Minimize2, Minus, X, Send, Bot, Loader2, Paperclip } from 'lucide-react'
import AgentAvatar from './AgentAvatar'

interface Props {
  squadNome: string
  agenteIdx: number
  agenteNome: string
  minimizado: boolean
  posicao: number
  onMinimizar: () => void
  onFechar: () => void
  onMaximizar: () => void
}

export default function ChatFloating({
  squadNome, agenteIdx, agenteNome, minimizado,
  posicao, onMinimizar, onFechar, onMaximizar,
}: Props) {
  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [historico, setHistorico] = useState<TarefaResultado[]>([])
  const [anexos, setAnexos] = useState<FileAttachment[]>([])
  const [expandido, setExpandido] = useState(false)
  const chatRef = useRef<HTMLDivElement>(null)

  const carregarHistorico = useCallback(async () => {
    try {
      const dados = await buscarHistoricoTarefas(50)
      const filtrado = dados.filter(
        (t) => t.squad_nome === squadNome && t.agente_indice === agenteIdx && t.tipo === 'tarefa'
      )
      setHistorico(filtrado)
    } catch { /* silencioso */ }
  }, [squadNome, agenteIdx])

  useEffect(() => { carregarHistorico() }, [carregarHistorico])

  useEffect(() => {
    const executando = historico.some(t => t.status === 'executando' || t.status === 'pendente')
    if (!executando) return
    const intervalo = setInterval(async () => {
      for (const t of historico.filter(t => t.status === 'executando' || t.status === 'pendente')) {
        try {
          const atualizada = await buscarTarefa(t.id)
          setHistorico(prev => prev.map(h => h.id === atualizada.id ? atualizada : h))
        } catch { /* silencioso */ }
      }
    }, 3000)
    return () => clearInterval(intervalo)
  }, [historico])

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [historico, minimizado, expandido])

  const enviar = async () => {
    if ((!mensagem.trim() && anexos.length === 0) || enviando) return
    setEnviando(true)
    try {
      let descricao = mensagem.trim()
      if (anexos.length > 0) {
        // Imagens: informar ao agente sem enviar URL (evita tokens excessivos)
        // Documentos: enviar referencia normalmente
        const listaAnexos = anexos.map(a => {
          if (a.tipo === 'imagem') {
            return `[Imagem anexada: ${a.nome_original} — o usuario enviou um screenshot/imagem para contexto visual]`
          }
          return `[Anexo: ${a.nome_original} (${a.url})]`
        }).join('\n')
        descricao = descricao
          ? `${descricao}\n\nArquivos anexados:\n${listaAnexos}`
          : `Arquivos anexados:\n${listaAnexos}`
      }
      const resultado = await executarTarefa({
        squad_nome: squadNome,
        agente_indice: agenteIdx,
        descricao,
      })
      setHistorico(prev => [resultado, ...prev])
      setMensagem('')
      setAnexos([])
    } catch { /* silencioso */ }
    finally { setEnviando(false) }
  }

  const nomeAbreviado = agenteNome.split('/')[0].trim()
  const rightOffset = expandido ? 16 : 16 + posicao * 340

  // === MINIMIZADO ===
  if (minimizado) {
    return (
      <div style={{ right: 16 + posicao * 340 }} className="fixed bottom-4 z-50 cursor-pointer" onClick={onMaximizar}>
        <div className="flex items-center gap-2 px-4 py-2 rounded-full shadow-lg transition-all" style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>
          <AgentAvatar agentName={nomeAbreviado} size="sm" noHover />
          <span className="text-xs font-medium sf-text-white max-w-[120px] truncate">{nomeAbreviado}</span>
          {historico.some(t => t.status === 'executando') && (
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
          )}
        </div>
      </div>
    )
  }

  // === CHAT (normal ou expandido) ===
  return (
    <div
      style={{
        right: rightOffset,
        width: expandido ? 'min(720px, calc(100vw - 280px))' : '320px',
        height: expandido ? 'calc(100vh - 100px)' : 'auto',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
      className="fixed bottom-4 z-50 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      {...({ style: { ...{ right: rightOffset, width: expandido ? 'min(720px, calc(100vw - 280px))' : '320px', height: expandido ? 'calc(100vh - 100px)' : 'auto', transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)', background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' } } } as any)}
    >
      {/* Header */}
      <div className="px-4 py-3 flex items-center gap-3 shrink-0" style={{ borderBottom: '1px solid var(--sf-border-default)', background: 'var(--sf-accent-dim)' }}>
        <AgentAvatar agentName={nomeAbreviado} size="md" showStatus status={historico.some(t => t.status === 'executando') ? 'ocupado' : 'online'} noHover />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold sf-text-white truncate">{agenteNome}</p>
          <p className="text-[10px] sf-text-dim">{squadNome}</p>
        </div>
        {historico.some(t => t.status === 'executando') && (
          <Loader2 size={12} className="text-blue-400 animate-spin" />
        )}
        <div className="flex items-center gap-1">
          <button onClick={() => setExpandido(!expandido)} className="w-6 h-6 rounded flex items-center justify-center sf-text-dim hover:sf-text-white transition-colors" style={{ background: 'var(--sf-bg-hover)' }} title={expandido ? 'Diminuir' : 'Expandir'}>
            {expandido ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
          </button>
          <button onClick={onMinimizar} className="w-6 h-6 rounded flex items-center justify-center sf-text-dim hover:sf-text-white transition-colors" style={{ background: 'var(--sf-bg-hover)' }} title="Minimizar">
            <Minus size={11} />
          </button>
          <button onClick={onFechar} className="w-6 h-6 rounded flex items-center justify-center sf-text-dim hover:text-red-400 transition-colors" style={{ background: 'var(--sf-bg-hover)' }} title="Fechar">
            <X size={11} />
          </button>
        </div>
      </div>

      {/* Chat area */}
      <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-3" style={{ background: 'var(--sf-bg-0)', height: expandido ? undefined : '320px', maxHeight: expandido ? undefined : '320px' }}>
        {historico.length === 0 && (
          <div className="text-center py-12">
            <Bot size={28} className="sf-text-ghost mx-auto mb-2" strokeWidth={1} />
            <p className="text-xs sf-text-dim">Envie uma mensagem para {nomeAbreviado}</p>
          </div>
        )}
        {[...historico].reverse().map(tarefa => (
          <div key={tarefa.id} className="space-y-2">
            {/* Usuário */}
            <div className="flex justify-end">
              <div className="bg-emerald-500/20 border border-emerald-500/25 rounded-xl rounded-br-sm px-3 py-2 max-w-[80%]">
                <p className={`${expandido ? 'text-sm' : 'text-xs'} sf-text-white whitespace-pre-wrap`}>{tarefa.descricao}</p>
              </div>
            </div>
            {/* Agente */}
            <div className="flex justify-start">
              <div className="rounded-xl rounded-bl-sm px-3 py-2" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)', maxWidth: expandido ? '85%' : '90%' }}>
                {tarefa.status === 'concluida' && tarefa.resultado && (
                  <p className={`${expandido ? 'text-sm' : 'text-xs'} sf-text-white whitespace-pre-wrap`}>{tarefa.resultado}</p>
                )}
                {tarefa.status === 'executando' && (
                  <div className="flex items-center gap-2">
                    <Loader2 size={12} className="text-blue-400 animate-spin" />
                    <p className="text-xs text-blue-400">Processando...</p>
                  </div>
                )}
                {tarefa.status === 'pendente' && (
                  <p className="text-xs text-amber-400">Aguardando...</p>
                )}
                {tarefa.status === 'erro' && (
                  <p className="text-xs text-red-400">Erro: {tarefa.erro}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Anexos pendentes */}
      {anexos.length > 0 && (
        <div className="px-3 pt-2" style={{ borderTop: '1px solid var(--sf-border-default)' }}>
          <div className="flex flex-wrap gap-1">
            {anexos.map((arq, idx) => (
              <div key={idx} className="flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/20 rounded px-2 py-0.5 text-[10px]">
                {arq.tipo === 'imagem' ? (
                  <img src={arq.url} alt="" className="w-5 h-5 rounded object-cover" />
                ) : (
                  <Paperclip size={10} className="text-emerald-400" />
                )}
                <span className="text-emerald-400 max-w-[80px] truncate">{arq.nome_original}</span>
                <button onClick={() => setAnexos(prev => prev.filter((_, i) => i !== idx))} className="text-emerald-400 hover:text-red-400">
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 flex items-center gap-2 shrink-0" style={{ borderTop: '1px solid var(--sf-border-default)' }}>
        <FileUploadArea compact onUpload={(novos) => setAnexos(prev => [...prev, ...novos])} />
        <input
          value={mensagem}
          onChange={e => setMensagem(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && enviar()}
          placeholder="Mensagem..."
          disabled={enviando}
          className={`flex-1 rounded-lg px-3 py-2 ${expandido ? 'text-sm' : 'text-xs'} sf-text-white focus:outline-none focus:border-emerald-500 disabled:opacity-50`}
          style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}
        />
        <button
          onClick={enviar}
          disabled={enviando || (!mensagem.trim() && anexos.length === 0)}
          className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/25 flex items-center justify-center text-emerald-400 hover:bg-emerald-500/30 disabled:opacity-40 transition-all"
        >
          {enviando ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
        </button>
      </div>
    </div>
  )
}
