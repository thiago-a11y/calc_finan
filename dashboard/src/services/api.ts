/* Serviço de API — comunicação com o backend FastAPI (com auth JWT) */

import type {
  StatusGeral,
  Squad,
  Aprovacao,
  RAGStatus,
  RAGStats,
  RAGConsultaResult,
  RAGIndexarResult,
  StandupRelatorio,
  Usuario,
  PapelDisponivel,
  AreaAprovacaoDisponivel,
  CriarUsuarioPayload,
  AtualizarPermissoesPayload,
  TarefaResultado,
} from '../types'

const BASE = '/api'

/* --- Headers com token JWT --- */

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
    // Token expirado — limpar e redirecionar
    localStorage.removeItem('sf_token')
    localStorage.removeItem('sf_refresh')
    window.location.href = '/login'
    throw new Error('Sessão expirada')
  }
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
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
    localStorage.removeItem('sf_refresh')
    window.location.href = '/login'
    throw new Error('Sessão expirada')
  }
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function put<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function del<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
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

/* --- Endpoints --- */

export const buscarStatus = () => get<StatusGeral>('/status')

export const buscarSquads = () => get<Squad[]>('/squads')

export const buscarAprovacoes = (pendentes = false) =>
  get<Aprovacao[]>(`/aprovacoes${pendentes ? '?pendentes=true' : ''}`)

export const acaoAprovacao = (indice: number, aprovado: boolean) =>
  post<Aprovacao>(`/aprovacoes/${indice}/acao`, { aprovado })

export const criarAprovacao = (dados: {
  tipo: string
  descricao: string
  solicitante: string
  valor_estimado?: number
}) => post<Aprovacao>('/aprovacoes', dados)

// --- Propostas de Edição (SyneriumX) ---
export const buscarPropostas = () => get<any[]>('/propostas')

export const aprovarProposta = (id: string) =>
  post<any>(`/propostas/${id}/aprovar`, {})

export const rejeitarProposta = (id: string, motivo = '') =>
  post<any>(`/propostas/${id}/rejeitar`, { motivo })

// --- Deploys (2ª aprovação — push para produção) ---
export const buscarDeploys = () => get<any[]>('/deploys')

export const aprovarDeploy = (id: string) =>
  post<any>(`/deploys/${id}/aprovar`, {})

export const rejeitarDeploy = (id: string) =>
  post<any>(`/deploys/${id}/rejeitar`, {})

export const buscarRAGStatus = () => get<RAGStatus>('/rag/status')

export const buscarRAGStats = () => get<RAGStats>('/rag/stats')

export const consultarRAG = (pergunta: string, vault?: string) =>
  post<RAGConsultaResult>('/rag/consultar', { pergunta, vault })

export const indexarRAG = (vault?: string) =>
  post<RAGIndexarResult>('/rag/indexar', { vault })

export const gerarStandup = () => post<StandupRelatorio>('/standup')

export const buscarUsuarios = () => get<Usuario[]>('/usuarios')

export const buscarUsuario = (id: string) => get<Usuario>(`/usuarios/${id}`)

export const atualizarPerfil = (dados: { nome?: string; cargo?: string }) =>
  put<Usuario>('/usuarios/perfil', dados)

/* --- Gestão de Usuários (admin) --- */

export const criarUsuario = (dados: CriarUsuarioPayload) =>
  post<Usuario>('/usuarios', dados)

/* --- Convites por Email --- */

export interface ConviteResponse {
  id: number
  email: string
  nome: string
  token: string
  link_registro: string
  expira_em: string
  usado: boolean
  email_enviado: boolean
}

export interface ConvitePendente {
  id: number
  email: string
  nome: string
  cargo: string
  usado: boolean
  token: string
  expira_em: string
  criado_em: string
}

export const enviarConvite = (dados: {
  email: string
  nome: string
  cargo: string
  papeis: string[]
  enviar_email: boolean
}) => post<ConviteResponse>('/convites', dados)

export const listarConvites = () =>
  get<ConvitePendente[]>('/convites')

export const editarUsuario = (id: string, dados: Record<string, unknown>) =>
  put<Usuario>(`/usuarios/${id}`, dados)

export const atualizarPermissoes = (id: string, dados: AtualizarPermissoesPayload) =>
  put<Usuario>(`/usuarios/${id}/permissoes`, dados)

export const desativarUsuario = (id: string) =>
  del<{ mensagem: string }>(`/usuarios/${id}`)

export const buscarPapeisDisponiveis = () =>
  get<PapelDisponivel[]>('/usuarios/papeis-disponiveis')

export const buscarAreasAprovacao = () =>
  get<AreaAprovacaoDisponivel[]>('/usuarios/areas-aprovacao-disponiveis')

export const buscarModulosDisponiveis = () =>
  get<{ modulos: import('../types').ModuloDisponivel[]; acoes: string[]; permissoes_por_papel: Record<string, Record<string, Record<string, boolean>>> }>('/usuarios/modulos-disponiveis')

/* --- Tarefas dos Agentes --- */

export const executarTarefa = (dados: {
  squad_nome: string
  agente_indice: number
  descricao: string
  resultado_esperado?: string
}) => post<TarefaResultado>('/tarefas/executar', dados)

export const buscarHistoricoTarefas = (limite = 20) =>
  get<TarefaResultado[]>(`/tarefas/historico?limite=${limite}`)

export const buscarTarefa = (id: string) =>
  get<TarefaResultado>(`/tarefas/${id}`)

export const executarReuniao = (dados: {
  squad_nome: string
  agentes_indices: number[]
  pauta: string
}) => post<TarefaResultado>('/tarefas/reuniao', dados)

export const continuarReuniao = (id: string, feedback: string) =>
  post<TarefaResultado>(`/tarefas/${id}/continuar`, { feedback })

export const encerrarReuniao = (id: string) =>
  post<TarefaResultado>(`/tarefas/${id}/encerrar`, {})

export const reabrirReuniao = (id: string) =>
  post<TarefaResultado>(`/tarefas/${id}/reabrir`, {})

/* --- Upload de Arquivos --- */

export const uploadArquivos = async (files: File[]): Promise<import('../types').FileAttachment[]> => {
  const token = localStorage.getItem('sf_token')
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))

  const res = await fetch('/api/uploads', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })

  if (!res.ok) throw new Error(`Upload falhou: ${res.status}`)
  const data = await res.json()
  return data.arquivos
}
