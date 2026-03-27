/* Agente — Chat + Formulário de Tarefas para um agente específico */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { executarTarefa, buscarTarefa, buscarHistoricoTarefas } from '../services/api'
import type { TarefaResultado } from '../types'

export default function Agente() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  const squadNome = params.get('squad') || ''
  const agenteIdx = parseInt(params.get('agente') || '0', 10)
  const agenteNome = params.get('nome') || 'Agente'

  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [historico, setHistorico] = useState<TarefaResultado[]>([])
  const [erro, setErro] = useState('')
  const chatRef = useRef<HTMLDivElement>(null)

  // Carregar histórico
  const carregarHistorico = useCallback(async () => {
    try {
      const dados = await buscarHistoricoTarefas(50)
      const filtrado = dados.filter(
        (t) => t.squad_nome === squadNome && t.agente_indice === agenteIdx
      )
      setHistorico(filtrado)
    } catch {
      // silencioso
    }
  }, [squadNome, agenteIdx])

  useEffect(() => {
    carregarHistorico()
  }, [carregarHistorico])

  // Polling para tarefas em execução
  useEffect(() => {
    const executando = historico.some(
      (t) => t.status === 'executando' || t.status === 'pendente'
    )
    if (!executando) return

    const intervalo = setInterval(async () => {
      const pendentes = historico.filter(
        (t) => t.status === 'executando' || t.status === 'pendente'
      )
      for (const t of pendentes) {
        try {
          const atualizada = await buscarTarefa(t.id)
          setHistorico((prev) =>
            prev.map((h) => (h.id === atualizada.id ? atualizada : h))
          )
        } catch {
          // silencioso
        }
      }
    }, 3000)

    return () => clearInterval(intervalo)
  }, [historico])

  // Auto-scroll
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [historico])

  const enviar = async () => {
    if (!mensagem.trim() || enviando) return

    setEnviando(true)
    setErro('')

    try {
      const resultado = await executarTarefa({
        squad_nome: squadNome,
        agente_indice: agenteIdx,
        descricao: mensagem.trim(),
        resultado_esperado: 'Resposta completa, detalhada e em português brasileiro.',
      })
      setHistorico((prev) => [resultado, ...prev])
      setMensagem('')
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao enviar tarefa.')
    } finally {
      setEnviando(false)
    }
  }

  const statusCor: Record<string, string> = {
    pendente: 'bg-yellow-500/10 text-yellow-500',
    executando: 'bg-blue-500/10 text-blue-400 animate-pulse',
    concluida: 'bg-emerald-500/10 text-emerald-400',
    erro: 'bg-red-500/10 text-red-400',
  }

  const statusLabel: Record<string, string> = {
    pendente: '⏳ Pendente',
    executando: '🔄 Executando...',
    concluida: '✅ Concluída',
    erro: '❌ Erro',
  }

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => navigate('/squads')}
          className="sf-text-dim hover:sf-text-ghost text-xl"
        >
          ←
        </button>
        <div className="w-10 h-10 bg-emerald-500/10 rounded-full flex items-center justify-center text-lg">
          🤖
        </div>
        <div>
          <h2 className="text-lg font-bold sf-text">{agenteNome}</h2>
          <p className="text-xs sf-text-dim">{squadNome}</p>
        </div>
        <span className={`ml-auto text-xs px-2 py-1 rounded-full ${statusCor['concluida']}`}>
          {historico.length} tarefa(s)
        </span>
      </div>

      {/* Chat Area */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto sf-card rounded-xl p-4 space-y-4 mb-4"
      >
        {historico.length === 0 && (
          <div className="text-center sf-text-dim py-12">
            <div className="text-4xl mb-3">🤖</div>
            <p className="text-sm">Envie uma tarefa para o agente</p>
            <p className="text-xs sf-text-dim mt-1">
              Ex: "Analise os riscos técnicos do projeto"
            </p>
          </div>
        )}

        {[...historico].reverse().map((tarefa) => (
          <div key={tarefa.id} className="space-y-2">
            {/* Mensagem do usuário */}
            <div className="flex justify-end">
              <div className="bg-emerald-600 text-white rounded-xl rounded-br-sm px-4 py-2 max-w-[70%]">
                <p className="text-sm">{tarefa.descricao}</p>
                <p className="text-xs text-emerald-200 mt-1">
                  {tarefa.usuario_nome} · {new Date(tarefa.criado_em).toLocaleTimeString('pt-BR')}
                </p>
              </div>
            </div>

            {/* Resposta do agente */}
            <div className="flex justify-start">
              <div className="sf-card border sf-border rounded-xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium sf-text-dim">
                    {tarefa.agente_nome}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${statusCor[tarefa.status]}`}
                  >
                    {statusLabel[tarefa.status]}
                  </span>
                </div>

                {tarefa.status === 'concluida' && tarefa.resultado && (
                  <div className="text-sm sf-text whitespace-pre-wrap leading-relaxed">
                    {tarefa.resultado}
                  </div>
                )}

                {tarefa.status === 'executando' && (
                  <div className="text-sm text-blue-600 italic">
                    Agente processando a tarefa...
                  </div>
                )}

                {tarefa.status === 'pendente' && (
                  <div className="text-sm text-yellow-600 italic">
                    Aguardando início da execução...
                  </div>
                )}

                {tarefa.status === 'erro' && (
                  <div className="text-sm text-red-600">
                    Erro: {tarefa.erro}
                  </div>
                )}

                {tarefa.concluido_em && (
                  <p className="text-xs sf-text-dim mt-2">
                    {new Date(tarefa.concluido_em).toLocaleTimeString('pt-BR')}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="mb-2 px-3 py-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg">
          {erro}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={mensagem}
          onChange={(e) => setMensagem(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && enviar()}
          placeholder={`Envie uma tarefa para ${agenteNome}...`}
          disabled={enviando}
          className="flex-1 border sf-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50" style={{ background: 'var(--sf-bg-input)' }}
        />
        <button
          onClick={enviar}
          disabled={enviando || !mensagem.trim()}
          className="px-6 py-3 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {enviando ? '...' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}
