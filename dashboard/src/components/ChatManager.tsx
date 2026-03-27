/* ChatManager — Gerencia múltiplas janelas de chat flutuantes + reuniões */

import { createContext, useContext, useState, useCallback } from 'react'
import ChatFloating from './ChatFloating'
import ReuniaoModal from './ReuniaoModal'
import type { ChatAberto } from '../types'

interface ChatContextType {
  abrirChat: (squadNome: string, agenteIdx: number, agenteNome: string) => void
  fecharChat: (id: string) => void
  abrirReuniao: (squadNome: string, agentes: { idx: number; nome: string }[]) => void
  chatsAbertos: ChatAberto[]
}

const ChatContext = createContext<ChatContextType>({
  abrirChat: () => {},
  fecharChat: () => {},
  abrirReuniao: () => {},
  chatsAbertos: [],
})

export function useChatManager() {
  return useContext(ChatContext)
}

interface ReuniaoState {
  aberta: boolean
  squadNome: string
  agentes: { idx: number; nome: string }[]
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chats, setChats] = useState<ChatAberto[]>([])
  const [reuniao, setReuniao] = useState<ReuniaoState>({
    aberta: false,
    squadNome: '',
    agentes: [],
  })

  const abrirChat = useCallback((squadNome: string, agenteIdx: number, agenteNome: string) => {
    const id = `${squadNome}__${agenteIdx}`
    setChats(prev => {
      const existente = prev.find(c => c.id === id)
      if (existente) {
        // Se já existe, maximizar
        return prev.map(c => c.id === id ? { ...c, minimizado: false } : c)
      }
      // Limitar a 4 chats abertos simultâneos
      const novos = prev.length >= 4 ? prev.slice(1) : prev
      return [...novos, { id, squadNome, agenteIdx, agenteNome, minimizado: false }]
    })
  }, [])

  const fecharChat = useCallback((id: string) => {
    setChats(prev => prev.filter(c => c.id !== id))
  }, [])

  const minimizarChat = useCallback((id: string) => {
    setChats(prev => prev.map(c => c.id === id ? { ...c, minimizado: true } : c))
  }, [])

  const maximizarChat = useCallback((id: string) => {
    setChats(prev => prev.map(c => c.id === id ? { ...c, minimizado: false } : c))
  }, [])

  const abrirReuniao = useCallback((squadNome: string, agentes: { idx: number; nome: string }[]) => {
    setReuniao({ aberta: true, squadNome, agentes })
  }, [])

  return (
    <ChatContext.Provider value={{ abrirChat, fecharChat, abrirReuniao, chatsAbertos: chats }}>
      {children}

      {/* Janelas de chat flutuantes */}
      {chats.map((chat, idx) => (
        <ChatFloating
          key={chat.id}
          squadNome={chat.squadNome}
          agenteIdx={chat.agenteIdx}
          agenteNome={chat.agenteNome}
          minimizado={chat.minimizado}
          posicao={idx}
          onMinimizar={() => minimizarChat(chat.id)}
          onFechar={() => fecharChat(chat.id)}
          onMaximizar={() => maximizarChat(chat.id)}
        />
      ))}

      {/* Modal de Reunião */}
      {reuniao.aberta && (
        <ReuniaoModal
          squadNome={reuniao.squadNome}
          agentes={reuniao.agentes}
          onFechar={() => setReuniao(prev => ({ ...prev, aberta: false }))}
        />
      )}
    </ChatContext.Provider>
  )
}
