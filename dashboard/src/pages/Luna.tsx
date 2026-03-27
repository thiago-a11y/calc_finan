/* Luna — Assistente Inteligente / Consultora Estratégica
 *
 * Página principal que orquestra todos os componentes Luna:
 * - Sidebar de conversas (esquerda)
 * - Área de chat com streaming (centro)
 * - Preview de artefatos (direita, quando ativo)
 * - Painel de supervisão (proprietários)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import type { LunaConversa, LunaMensagem, LunaArtefato, LunaAnexo } from '../types'
import {
  listarConversas,
  criarConversa,
  buscarConversa,
  renomearConversa,
  excluirConversa,
  enviarMensagemStream,
  regenerarRespostaStream,
} from '../services/luna'
import type { LunaStreamEvento } from '../services/luna'
import LunaSidebar from '../components/luna/LunaSidebar'
import LunaChat from '../components/luna/LunaChat'
import LunaInput from '../components/luna/LunaInput'
import LunaWelcome from '../components/luna/LunaWelcome'
import LunaPreview from '../components/luna/LunaPreview'
import LunaAdminView from '../components/luna/LunaAdminView'

export default function Luna() {
  const { usuario } = useAuth()

  // Estado de conversas
  const [conversas, setConversas] = useState<LunaConversa[]>([])
  const [conversaAtiva, setConversaAtiva] = useState<string | null>(null)
  const [mensagens, setMensagens] = useState<LunaMensagem[]>([])
  const [, setTotalMensagens] = useState(0)
  const [temMais, setTemMais] = useState(false)

  // Estado de streaming
  const [streaming, setStreaming] = useState(false)
  const [textoStreaming, setTextoStreaming] = useState('')
  const controllerRef = useRef<AbortController | null>(null)

  // Estado de artefatos / preview
  const [artefatos, setArtefatos] = useState<LunaArtefato[]>([])
  const [artefatoAtivo, setArtefatoAtivo] = useState<LunaArtefato | null>(null)

  // Estado de UI
  const [busca, setBusca] = useState('')
  const [, setCarregandoConversas] = useState(true)
  const [modoSupervisao, setModoSupervisao] = useState(false)
  const [erro, setErro] = useState('')

  // Verificar se é proprietário (CEO/Operations Lead)
  const papeis = usuario?.papeis || []
  const ehProprietario = papeis.some((p: string) =>
    ['ceo', 'operations_lead', 'proprietario', 'diretor_tecnico'].includes(p)
  )

  // Carregar conversas ao montar
  useEffect(() => {
    carregarConversas()
  }, [])

  const carregarConversas = useCallback(async () => {
    setCarregandoConversas(true)
    try {
      const dados = await listarConversas()
      setConversas(dados)
    } catch (e) {
      console.error('[Luna] Erro ao carregar conversas:', e)
    } finally {
      setCarregandoConversas(false)
    }
  }, [])

  // Carregar mensagens quando conversa ativa muda
  useEffect(() => {
    if (conversaAtiva) {
      carregarMensagens(conversaAtiva)
    } else {
      setMensagens([])
      setTotalMensagens(0)
      setTemMais(false)
    }
    // Limpar artefatos ao trocar de conversa
    setArtefatos([])
    setArtefatoAtivo(null)
  }, [conversaAtiva])

  const carregarMensagens = async (conversaId: string, offset = 0) => {
    try {
      const dados = await buscarConversa(conversaId, 50, offset)
      if (offset === 0) {
        setMensagens(dados.mensagens)
      } else {
        setMensagens(prev => [...dados.mensagens, ...prev])
      }
      setTotalMensagens(dados.total_mensagens)
      setTemMais(dados.tem_mais)
    } catch (e) {
      console.error('[Luna] Erro ao carregar mensagens:', e)
      setErro('Erro ao carregar mensagens')
    }
  }

  const handleCarregarMais = () => {
    if (conversaAtiva) {
      carregarMensagens(conversaAtiva, mensagens.length)
    }
  }

  // Nova conversa
  const handleNovaConversa = async () => {
    try {
      const nova = await criarConversa()
      setConversas(prev => [nova, ...prev])
      setConversaAtiva(nova.id)
    } catch (e) {
      console.error('[Luna] Erro ao criar conversa:', e)
      setErro('Erro ao criar conversa')
    }
  }

  // Selecionar conversa
  const handleSelecionar = (id: string) => {
    if (streaming) {
      controllerRef.current?.abort()
      setStreaming(false)
      setTextoStreaming('')
    }
    setConversaAtiva(id)
  }

  // Renomear conversa
  const handleRenomear = async (id: string, titulo: string) => {
    try {
      await renomearConversa(id, titulo)
      setConversas(prev =>
        prev.map(c => (c.id === id ? { ...c, titulo } : c))
      )
    } catch (e) {
      console.error('[Luna] Erro ao renomear:', e)
    }
  }

  // Excluir conversa
  const handleExcluir = async (id: string) => {
    try {
      await excluirConversa(id)
      setConversas(prev => prev.filter(c => c.id !== id))
      if (conversaAtiva === id) {
        setConversaAtiva(null)
      }
    } catch (e) {
      console.error('[Luna] Erro ao excluir:', e)
    }
  }

  // Enviar mensagem
  const handleEnviar = async (texto: string, anexosMsg?: LunaAnexo[]) => {
    if ((!texto.trim() && (!anexosMsg || anexosMsg.length === 0)) || streaming) return

    let idConversa = conversaAtiva

    // Criar conversa se não existe
    if (!idConversa) {
      try {
        const nova = await criarConversa()
        setConversas(prev => [nova, ...prev])
        setConversaAtiva(nova.id)
        idConversa = nova.id
      } catch (e) {
        setErro('Erro ao criar conversa')
        return
      }
    }

    // Adicionar mensagem do usuário localmente
    const msgUsuario: LunaMensagem = {
      id: Date.now(),
      conversa_id: idConversa,
      papel: 'user',
      conteudo: texto,
      anexos: anexosMsg,
      modelo_usado: '',
      provider_usado: '',
      tokens_input: 0,
      tokens_output: 0,
      custo_usd: 0,
      criado_em: new Date().toISOString(),
    }
    setMensagens(prev => [...prev, msgUsuario])
    setErro('')
    setStreaming(true)
    setTextoStreaming('')

    // Streaming SSE
    const controller = enviarMensagemStream(
      idConversa,
      texto,
      (evento: LunaStreamEvento) => {
        switch (evento.tipo) {
          case 'chunk':
            setTextoStreaming(prev => prev + (evento.conteudo || ''))
            break
          case 'titulo':
            if (evento.titulo) {
              setConversas(prev =>
                prev.map(c =>
                  c.id === idConversa ? { ...c, titulo: evento.titulo! } : c
                )
              )
            }
            break
          case 'fim':
            // Adicionar mensagem completa da assistente
            setMensagens(prev => [
              ...prev,
              {
                id: evento.mensagem_id || Date.now() + 1,
                conversa_id: idConversa!,
                papel: 'assistant',
                conteudo: '', // Será preenchido pelo textoStreaming final
                modelo_usado: evento.modelo || '',
                provider_usado: evento.provider || '',
                tokens_input: evento.tokens_input || 0,
                tokens_output: evento.tokens_output || 0,
                custo_usd: evento.custo_usd || 0,
                criado_em: new Date().toISOString(),
              },
            ])
            // Atualizar com conteúdo completo
            setTextoStreaming(prev => {
              // Salvar o texto acumulado na última mensagem
              setMensagens(msgs => {
                const copia = [...msgs]
                if (copia.length > 0) {
                  copia[copia.length - 1] = {
                    ...copia[copia.length - 1],
                    conteudo: prev,
                    modelo_usado: evento.modelo || '',
                    provider_usado: evento.provider || '',
                  }
                }
                return copia
              })
              return ''
            })
            setStreaming(false)

            // Reordenar conversas (a ativa vai pro topo)
            setConversas(prev => {
              const ativa = prev.find(c => c.id === idConversa)
              if (ativa) {
                return [
                  { ...ativa, atualizado_em: new Date().toISOString() },
                  ...prev.filter(c => c.id !== idConversa),
                ]
              }
              return prev
            })
            break
          case 'erro':
            setErro(evento.mensagem || 'Erro na resposta')
            setStreaming(false)
            setTextoStreaming('')
            break
        }
      },
      (error: Error) => {
        setErro(error.message)
        setStreaming(false)
        setTextoStreaming('')
      },
      anexosMsg,
    )

    controllerRef.current = controller
  }

  // Enviar sugestão do welcome
  const handleSugestao = (texto: string) => {
    handleEnviar(texto)
  }

  // Regenerar
  const handleRegenerar = () => {
    if (!conversaAtiva || streaming) return

    setStreaming(true)
    setTextoStreaming('')

    // Remover última mensagem assistant localmente
    setMensagens(prev => {
      const copia = [...prev]
      if (copia.length > 0 && copia[copia.length - 1].papel === 'assistant') {
        copia.pop()
      }
      return copia
    })

    const controller = regenerarRespostaStream(
      conversaAtiva,
      (evento: LunaStreamEvento) => {
        switch (evento.tipo) {
          case 'chunk':
            setTextoStreaming(prev => prev + (evento.conteudo || ''))
            break
          case 'fim':
            setTextoStreaming(prev => {
              setMensagens(msgs => [
                ...msgs,
                {
                  id: evento.mensagem_id || Date.now(),
                  conversa_id: conversaAtiva!,
                  papel: 'assistant',
                  conteudo: prev,
                  modelo_usado: evento.modelo || '',
                  provider_usado: evento.provider || '',
                  tokens_input: 0,
                  tokens_output: 0,
                  custo_usd: 0,
                  criado_em: new Date().toISOString(),
                },
              ])
              return ''
            })
            setStreaming(false)
            break
          case 'erro':
            setErro(evento.mensagem || 'Erro ao regenerar')
            setStreaming(false)
            setTextoStreaming('')
            break
        }
      },
      (error: Error) => {
        setErro(error.message)
        setStreaming(false)
      }
    )

    controllerRef.current = controller
  }

  // Copiar texto
  const handleCopiar = (texto: string) => {
    navigator.clipboard.writeText(texto).catch(() => {})
  }

  // Preview de artefato
  const handleAbrirPreview = (artefato: LunaArtefato) => {
    if (!artefatos.find(a => a.id === artefato.id)) {
      setArtefatos(prev => [...prev, artefato])
    }
    setArtefatoAtivo(artefato)
  }

  const handleFecharPreview = () => {
    setArtefatoAtivo(null)
  }

  const handleSelecionarArtefato = (id: string) => {
    const a = artefatos.find(art => art.id === id)
    if (a) setArtefatoAtivo(a)
  }

  // Modo supervisão
  if (modoSupervisao && ehProprietario) {
    return (
      <div className="sf-page sf-animate-in">
        <LunaAdminView onVoltar={() => setModoSupervisao(false)} />
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-73px)] -m-6 -mt-0">
      {/* Sidebar de conversas */}
      <LunaSidebar
        conversas={conversas}
        conversaAtiva={conversaAtiva}
        onSelecionar={handleSelecionar}
        onNova={handleNovaConversa}
        onRenomear={handleRenomear}
        onExcluir={handleExcluir}
        onSupervisao={() => setModoSupervisao(true)}
        mostrarSupervisao={ehProprietario}
        busca={busca}
        onBuscaChange={setBusca}
      />

      {/* Área principal (chat + preview) */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat */}
        <div
          className={`flex flex-col flex-1 transition-all duration-300 ${
            artefatoAtivo ? 'w-1/2' : 'w-full'
          }`}
        >
          {conversaAtiva || streaming ? (
            <>
              {/* Header da conversa */}
              <div
                className="flex items-center gap-3 px-6 py-3 shrink-0"
                style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
              >
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                  style={{
                    background: 'linear-gradient(135deg, #10b981, #6366f1)',
                  }}
                >
                  🌙
                </div>
                <div className="flex-1 min-w-0">
                  <h3
                    className="text-sm font-semibold truncate"
                    style={{ color: 'var(--sf-text-0)' }}
                  >
                    {conversas.find(c => c.id === conversaAtiva)?.titulo || 'Nova conversa'}
                  </h3>
                  <p className="text-xs" style={{ color: 'var(--sf-text-3)' }}>
                    Luna — Consultora Estratégica
                  </p>
                </div>
                {streaming && (
                  <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 animate-pulse">
                    Respondendo...
                  </span>
                )}
              </div>

              {/* Mensagens */}
              <LunaChat
                mensagens={mensagens}
                streaming={streaming}
                textoStreaming={textoStreaming}
                temMais={temMais}
                onCarregarMais={handleCarregarMais}
                onCopiar={handleCopiar}
                onRegenerar={handleRegenerar}
                onAbrirPreview={handleAbrirPreview}
              />

              {/* Erro */}
              {erro && (
                <div className="mx-6 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg">
                  {erro}
                  <button
                    onClick={() => setErro('')}
                    className="ml-2 text-red-400/60 hover:text-red-400"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Input */}
              <div className="px-6 pb-4">
                <LunaInput
                  onEnviar={handleEnviar}
                  carregando={streaming}
                />
              </div>
            </>
          ) : (
            /* Tela de boas-vindas */
            <div className="flex-1 flex items-center justify-center p-6">
              <LunaWelcome onSugestao={handleSugestao} />
            </div>
          )}
        </div>

        {/* Preview de artefatos */}
        {artefatoAtivo && (
          <LunaPreview
            artefato={artefatoAtivo}
            artefatos={artefatos}
            onFechar={handleFecharPreview}
            onSelecionarArtefato={handleSelecionarArtefato}
          />
        )}
      </div>
    </div>
  )
}
