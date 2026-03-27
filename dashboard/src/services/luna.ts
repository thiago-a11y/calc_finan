/* Luna — Serviço de API da assistente inteligente */

import type {
  LunaConversa,
  LunaConversaCompleta,
  LunaUsuarioResumo,
  LunaConversaAdmin,
  LunaAnexo,
} from '../types'

const BASE = '/api/luna'

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('sf_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, { headers: getAuthHeaders() })
  if (res.status === 401) {
    localStorage.removeItem('sf_token')
    localStorage.removeItem('sf_refresh')
    window.location.href = '/login'
    throw new Error('Sessão expirada')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Erro ${res.status}`)
  }
  return res.json()
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    localStorage.removeItem('sf_token')
    window.location.href = '/login'
    throw new Error('Sessão expirada')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Erro ${res.status}`)
  }
  return res.json()
}

async function put<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Erro ${res.status}`)
  }
  return res.json()
}

async function del<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Erro ${res.status}`)
  }
  return res.json()
}

/* --- Conversas --- */

export const listarConversas = (limite = 50, offset = 0) =>
  get<LunaConversa[]>(`/conversas?limite=${limite}&offset=${offset}`)

export const criarConversa = (modelo_preferido = 'auto') =>
  post<LunaConversa>('/conversas', { modelo_preferido })

export const buscarConversa = (id: string, limiteMsgs = 50, offsetMsgs = 0) =>
  get<LunaConversaCompleta>(
    `/conversas/${id}?limite_msgs=${limiteMsgs}&offset_msgs=${offsetMsgs}`
  )

export const renomearConversa = (id: string, titulo: string) =>
  put<LunaConversa>(`/conversas/${id}`, { titulo })

export const excluirConversa = (id: string) =>
  del<{ mensagem: string }>(`/conversas/${id}`)

/* --- Mensagens com Streaming SSE --- */

export interface LunaStreamEvento {
  tipo: 'chunk' | 'titulo' | 'fim' | 'erro'
  conteudo?: string
  titulo?: string
  mensagem_id?: number
  modelo?: string
  provider?: string
  tokens_input?: number
  tokens_output?: number
  custo_usd?: number
  mensagem?: string
}

/**
 * Envia mensagem e faz streaming da resposta via SSE.
 * Chama onEvento para cada evento recebido.
 * Retorna um AbortController para cancelar o stream.
 */
export function enviarMensagemStream(
  conversaId: string,
  conteudo: string,
  onEvento: (evento: LunaStreamEvento) => void,
  onErro?: (erro: Error) => void,
  anexos?: LunaAnexo[],
): AbortController {
  const controller = new AbortController()

  const executar = async () => {
    try {
      const token = localStorage.getItem('sf_token')
      const response = await fetch(`${BASE}/conversas/${conversaId}/mensagens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ conteudo, anexos: anexos || null }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `Erro ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const linhas = buffer.split('\n')
        buffer = linhas.pop() || ''

        for (const linha of linhas) {
          if (linha.startsWith('data: ')) {
            try {
              const evento = JSON.parse(linha.slice(6)) as LunaStreamEvento
              onEvento(evento)
            } catch {
              // Ignorar linhas malformadas
            }
          }
        }
      }

      // Processar buffer restante
      if (buffer.startsWith('data: ')) {
        try {
          const evento = JSON.parse(buffer.slice(6)) as LunaStreamEvento
          onEvento(evento)
        } catch {
          // Ignorar
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        onErro?.(e as Error)
      }
    }
  }

  executar()
  return controller
}

/**
 * Regenera a última resposta via streaming SSE.
 */
export function regenerarRespostaStream(
  conversaId: string,
  onEvento: (evento: LunaStreamEvento) => void,
  onErro?: (erro: Error) => void,
): AbortController {
  const controller = new AbortController()

  const executar = async () => {
    try {
      const token = localStorage.getItem('sf_token')
      const response = await fetch(`${BASE}/conversas/${conversaId}/regenerar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`Erro ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const linhas = buffer.split('\n')
        buffer = linhas.pop() || ''

        for (const linha of linhas) {
          if (linha.startsWith('data: ')) {
            try {
              const evento = JSON.parse(linha.slice(6)) as LunaStreamEvento
              onEvento(evento)
            } catch {
              // Ignorar
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        onErro?.(e as Error)
      }
    }
  }

  executar()
  return controller
}

/* --- Admin / Supervisão (Proprietários) --- */

export const listarUsuariosLuna = () =>
  get<LunaUsuarioResumo[]>('/admin/usuarios')

export const listarConversasFuncionario = (usuarioId: number) =>
  get<LunaConversa[]>(`/admin/conversas/${usuarioId}`)

export const verConversaFuncionario = (usuarioId: number, conversaId: string) =>
  get<LunaConversaAdmin>(`/admin/conversas/${usuarioId}/${conversaId}`)

/* --- Lixeira (Proprietários) --- */

export interface LunaConversaLixeira extends LunaConversa {
  usuario_email: string
  usuario_cargo: string
  total_mensagens: number
}

export const listarLixeira = () =>
  get<LunaConversaLixeira[]>('/admin/lixeira')

export const verConversaLixeira = (conversaId: string) =>
  get<LunaConversaAdmin>(`/admin/lixeira/${conversaId}`)

export const restaurarConversa = (conversaId: string) =>
  post<{ mensagem: string }>(`/admin/lixeira/${conversaId}/restaurar`)

export const excluirPermanente = (conversaId: string) =>
  del<{ mensagem: string }>(`/admin/lixeira/${conversaId}`)
