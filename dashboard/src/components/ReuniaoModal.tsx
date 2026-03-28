/* ReuniaoModal — Modal de reunião com rodadas interativas em tempo real */

import { useState, useEffect, useRef } from 'react'
import { executarReuniao, buscarTarefa, continuarReuniao, encerrarReuniao } from '../services/api'
import { FileUploadArea } from './FileUpload'
import AgentAvatar from './AgentAvatar'
import type { TarefaResultado, RodadaItem } from '../types'

interface Props {
  squadNome: string
  agentes: { idx: number; nome: string }[]
  onFechar: () => void
}

export default function ReuniaoModal({ squadNome, agentes, onFechar }: Props) {
  const [selecionados, setSelecionados] = useState<number[]>(agentes.map(a => a.idx))
  const [pauta, setPauta] = useState('')
  const [feedback, setFeedback] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<TarefaResultado | null>(null)
  const chatRef = useRef<HTMLDivElement>(null)
  const usuarioNoFundo = useRef(true)
  const numRodadasAnterior = useRef(0)

  const toggleAgente = (idx: number) => {
    setSelecionados(prev =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    )
  }

  // Detectar se o usuário está no fundo do chat ou scrollou para cima
  const handleScroll = () => {
    if (!chatRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = chatRef.current
    // Considera "no fundo" se estiver a menos de 100px do final
    usuarioNoFundo.current = scrollHeight - scrollTop - clientHeight < 100
  }

  // Polling para acompanhar em tempo real
  useEffect(() => {
    if (!resultado) return
    if (resultado.status === 'concluida' || resultado.status === 'erro') return

    const intervalo = setInterval(async () => {
      try {
        const atualizada = await buscarTarefa(resultado.id)
        setResultado(atualizada)
      } catch { /* silencioso */ }
    }, 2000)

    return () => clearInterval(intervalo)
  }, [resultado])

  // Auto-scroll APENAS quando chega mensagem nova E o usuário está no fundo
  useEffect(() => {
    const numAtual = resultado?.rodadas?.length || 0
    const temNovaMensagem = numAtual > numRodadasAnterior.current
    numRodadasAnterior.current = numAtual

    if (temNovaMensagem && usuarioNoFundo.current && chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [resultado?.rodadas])

  const iniciar = async () => {
    if (!pauta.trim() || selecionados.length < 2 || enviando) return
    setEnviando(true)
    try {
      const res = await executarReuniao({
        squad_nome: squadNome,
        agentes_indices: selecionados,
        pauta: pauta.trim(),
      })
      setResultado(res)
    } catch { /* silencioso */ }
    finally { setEnviando(false) }
  }

  const enviarFeedback = async () => {
    if (!feedback.trim() || !resultado || enviando) return
    setEnviando(true)
    try {
      const res = await continuarReuniao(resultado.id, feedback.trim())
      setResultado(res)
      setFeedback('')
    } catch { /* silencioso */ }
    finally { setEnviando(false) }
  }

  const encerrar = async () => {
    if (!resultado) return
    try {
      const res = await encerrarReuniao(resultado.id)
      setResultado(res)
    } catch { /* silencioso */ }
  }

  const rodadas = resultado?.rodadas || []
  const rodadasAgrupadas: Record<number, RodadaItem[]> = {}
  for (const r of rodadas) {
    if (!rodadasAgrupadas[r.rodada]) rodadasAgrupadas[r.rodada] = []
    rodadasAgrupadas[r.rodada].push(r)
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden" style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>
        {/* Header */}
        <div className="px-6 py-4 flex items-center gap-3 shrink-0" style={{ background: 'var(--sf-accent-dim)', borderBottom: '1px solid var(--sf-border-default)' }}>
          <div className="w-9 h-9 rounded-lg bg-emerald-500/20 flex items-center justify-center">
            <span className="text-sm">👥</span>
          </div>
          <div className="flex-1">
            <h3 className="font-bold sf-text-white">Reunião do Squad</h3>
            <p className="text-xs text-emerald-400">
              {squadNome}
              {resultado && ` · Rodada ${resultado.rodada_atual}`}
              {resultado?.agente_atual && ` · ${resultado.agente_atual}`}
            </p>
          </div>
          {resultado && (
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              resultado.status === 'executando' ? 'bg-blue-500/20 text-blue-400 animate-pulse' :
              resultado.status === 'aguardando_feedback' ? 'bg-amber-500/20 text-amber-400' :
              resultado.status === 'concluida' ? 'bg-emerald-500/20 text-emerald-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {resultado.status === 'executando' ? `${resultado.agente_atual || 'Processando...'}` :
               resultado.status === 'aguardando_feedback' ? 'Sua vez!' :
               resultado.status === 'concluida' ? 'Encerrada' :
               resultado.status === 'erro' ? 'Erro' : 'Aguardando'}
            </span>
          )}
          <button onClick={onFechar} className="w-8 h-8 rounded-lg flex items-center justify-center sf-text-dim hover:sf-text-white transition-colors" style={{ background: 'var(--sf-bg-hover)' }}>✕</button>
        </div>

        {!resultado ? (
          /* Formulário inicial */
          <div className="p-6 space-y-4 overflow-y-auto flex-1">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium sf-text-white">Participantes</label>
                <div className="flex gap-2">
                  <button onClick={() => setSelecionados(agentes.map(a => a.idx))} className="text-xs text-emerald-400 hover:underline">Todos</button>
                  <button onClick={() => setSelecionados([])} className="text-xs sf-text-dim hover:underline">Nenhum</button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {agentes.map(agente => (
                  <label
                    key={agente.idx}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                      selecionados.includes(agente.idx) ? 'bg-emerald-500/15 border-emerald-500/30' : ''
                    }`}
                    style={!selecionados.includes(agente.idx) ? { background: 'var(--sf-bg-2)', borderColor: 'var(--sf-border-default)' } : undefined}
                  >
                    <input type="checkbox" checked={selecionados.includes(agente.idx)}
                      onChange={() => toggleAgente(agente.idx)} className="accent-emerald-500" />
                    <AgentAvatar agentName={agente.nome} size="sm" noHover />
                    <span className="text-xs sf-text-dim">{agente.nome}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium sf-text-white mb-1">Pauta da Reunião</label>
              <textarea value={pauta} onChange={e => setPauta(e.target.value)}
                placeholder="Ex: Construção de uma LandingPage para o produto DiamondOne..."
                rows={4}
                className="w-full rounded-lg px-4 py-2 text-sm sf-text-white focus:outline-none focus:border-emerald-500 resize-none"
                style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}
              />
            </div>
            <button onClick={iniciar} disabled={enviando || !pauta.trim() || selecionados.length < 2}
              className="w-full px-4 py-3 bg-emerald-500/20 text-emerald-400 border border-emerald-500/25 rounded-lg text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-40 transition-all">
              {enviando ? 'Iniciando...' : `Iniciar Reunião com ${selecionados.length} agente(s)`}
            </button>
          </div>
        ) : (
          /* Chat da reunião em tempo real */
          <>
            <div ref={chatRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4 space-y-3" style={{ background: 'var(--sf-bg-0)' }}>
              {/* Pauta */}
              <div className="flex justify-end">
                <div className="bg-emerald-500/20 border border-emerald-500/25 text-emerald-400 rounded-xl rounded-br-sm px-4 py-2 max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-emerald-300">Pauta</p>
                  <p className="text-sm sf-text-white">{resultado.descricao}</p>
                </div>
              </div>

              {/* Rodadas */}
              {Object.entries(rodadasAgrupadas).map(([rodNum, items]) => (
                <div key={rodNum} className="space-y-2">
                  <div className="text-center">
                    <span className="text-xs px-3 py-1 rounded-full sf-text-dim" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}>
                      Rodada {rodNum}
                    </span>
                  </div>
                  {items.map((item, i) => {
                    const isCeo = item.agente.includes('CEO')
                    return (
                      <div key={`${rodNum}-${i}`} className={`flex ${isCeo ? 'justify-end' : 'justify-start'} gap-2`}>
                        {!isCeo && <AgentAvatar agentName={item.agente} size="sm" className="mt-1 shrink-0" noHover />}
                        <div className={`rounded-xl px-4 py-2 max-w-[75%] ${
                          isCeo
                            ? 'bg-emerald-500/20 border border-emerald-500/25 rounded-br-sm'
                            : 'rounded-bl-sm'
                        }`} style={!isCeo ? { background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' } : undefined}>
                          <p className={`text-xs font-medium mb-1 ${isCeo ? 'text-emerald-300' : 'text-emerald-400'}`}>
                            {item.agente}
                          </p>
                          <p className="text-sm whitespace-pre-wrap sf-text-white">
                            {item.resposta}
                          </p>
                          <p className="text-xs mt-1 sf-text-ghost">
                            {new Date(item.timestamp).toLocaleTimeString('pt-BR')}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}

              {/* Agente atual falando */}
              {resultado.status === 'executando' && resultado.agente_atual && (
                <div className="flex justify-start">
                  <div className="rounded-xl rounded-bl-sm px-4 py-2 max-w-[80%] bg-blue-500/10 border border-blue-500/20">
                    <p className="text-xs font-medium text-blue-400 mb-1">{resultado.agente_atual}</p>
                    <p className="text-sm text-blue-400 animate-pulse">Digitando...</p>
                  </div>
                </div>
              )}
            </div>

            {/* Área de feedback / ações */}
            <div className="shrink-0 p-4" style={{ borderTop: '1px solid var(--sf-border-default)', background: 'var(--sf-bg-1)' }}>
              {resultado.status === 'aguardando_feedback' && (
                <div className="space-y-2">
                  <p className="text-xs text-amber-400 font-medium">Rodada {resultado.rodada_atual} concluída — é sua vez!</p>

                  <FileUploadArea
                    onUpload={(arquivos) => {
                      const lista = arquivos.map(a => `[Anexo: ${a.nome_original} (${a.url})]`).join('\n')
                      setFeedback(prev => prev ? `${prev}\n\nArquivos:\n${lista}` : `Arquivos anexados:\n${lista}`)
                    }}
                  />

                  <div className="flex gap-2">
                    <input
                      value={feedback}
                      onChange={e => setFeedback(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && enviarFeedback()}
                      placeholder="Feedback, direcionamento ou nova pergunta..."
                      disabled={enviando}
                      className="flex-1 rounded-lg px-4 py-2 text-sm sf-text-white focus:outline-none focus:border-emerald-500"
                      style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}
                    />
                    <button onClick={enviarFeedback} disabled={enviando || !feedback.trim()}
                      className="px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/25 rounded-lg text-sm hover:bg-emerald-500/30 disabled:opacity-40 transition-all">
                      {enviando ? '...' : 'Continuar →'}
                    </button>
                  </div>
                  <button onClick={encerrar}
                    className="w-full px-3 py-2 rounded-lg text-xs sf-text-dim hover:sf-text-white transition-colors" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}>
                    Encerrar Reunião
                  </button>
                </div>
              )}

              {resultado.status === 'executando' && (
                <div className="text-center">
                  <p className="text-sm text-blue-400 animate-pulse">
                    {resultado.agente_atual || 'Agentes processando...'}
                  </p>
                </div>
              )}

              {resultado.status === 'concluida' && (
                <div className="text-center space-y-2">
                  <p className="text-sm text-emerald-400">Reunião encerrada — {rodadas.length} contribuições em {resultado.rodada_atual} rodada(s)</p>
                  <button onClick={() => { setResultado(null); setPauta(''); setFeedback('') }}
                    className="px-4 py-2 rounded-lg text-sm sf-text-dim hover:sf-text-white transition-colors" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}>
                    Nova Reunião
                  </button>
                </div>
              )}

              {resultado.status === 'erro' && (
                <div className="text-center">
                  <p className="text-sm text-red-400">{resultado.erro}</p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
