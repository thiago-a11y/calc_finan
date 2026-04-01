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
  AgenteCatalogo,
  AgenteCatalogoCreate,
  AgenteCatalogoUpdate,
  AgenteAtribuido,
  SolicitacaoAgente,
  PerfilDisponivel,
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

/* --- Auto-refresh de token JWT --- */

let refreshEmAndamento: Promise<boolean> | null = null

async function tentarRefresh(): Promise<boolean> {
  // Evitar multiplos refreshes simultaneos
  if (refreshEmAndamento) return refreshEmAndamento

  refreshEmAndamento = (async () => {
    const refreshToken = localStorage.getItem('sf_refresh')
    if (!refreshToken) return false

    try {
      const res = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('sf_token', data.access_token)
        return true
      }
    } catch { /* falhou */ }
    return false
  })()

  const resultado = await refreshEmAndamento
  refreshEmAndamento = null
  return resultado
}

function redirecionarLogin() {
  localStorage.removeItem('sf_token')
  localStorage.removeItem('sf_refresh')
  window.location.href = '/login'
}

/* --- Funcao base com auto-refresh --- */

async function fetchComRefresh(url: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(url, { ...options, headers: { ...getAuthHeaders(), ...(options.headers || {}) } })

  if (res.status === 401) {
    // Tentar renovar o token automaticamente
    const renovado = await tentarRefresh()
    if (renovado) {
      // Repetir a requisicao com o novo token
      return fetch(url, { ...options, headers: { ...getAuthHeaders(), ...(options.headers || {}) } })
    }
    // Refresh falhou — redirecionar para login
    redirecionarLogin()
    throw new Error('Sessao expirada')
  }

  return res
}

async function get<T>(url: string): Promise<T> {
  const res = await fetchComRefresh(`${BASE}${url}`)
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetchComRefresh(`${BASE}${url}`, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function put<T>(url: string, body: unknown): Promise<T> {
  const res = await fetchComRefresh(`${BASE}${url}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function del<T>(url: string): Promise<T> {
  const res = await fetchComRefresh(`${BASE}${url}`, {
    method: 'DELETE',
  })
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

export const buscarUsuarios = (incluirInativos = false) =>
  get<Usuario[]>(`/usuarios${incluirInativos ? '?incluir_inativos=true' : ''}`)

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

export const excluirUsuarioPermanente = (id: string) =>
  del<{ mensagem: string }>(`/usuarios/${id}/permanente`)

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
  anexos?: Array<{ nome_original: string; url: string; tipo: string; tamanho: number }>
}) => post<TarefaResultado>('/tarefas/executar', dados)

export const buscarHistoricoTarefas = (limite = 20) =>
  get<TarefaResultado[]>(`/tarefas/historico?limite=${limite}`)

export const buscarTarefa = (id: string) =>
  get<TarefaResultado>(`/tarefas/detalhe/${id}`)

export const executarReuniao = (dados: {
  squad_nome: string
  agentes_indices: number[]
  pauta: string
  paralelo?: boolean
}) => post<TarefaResultado>('/tarefas/reuniao', { paralelo: true, ...dados })

export interface AgenteSugerido {
  id: number; nome: string; perfil: string; categoria: string; razao: string; icone: string
}
export interface MontarTimeResult {
  necessita_time: boolean
  razao_geral?: string; razao?: string
  agentes_sugeridos?: AgenteSugerido[]
  confianca?: number; auto_iniciar?: boolean
  catalogo_completo?: AgenteSugerido[]
}
export const montarTime = (dados: {
  mensagem: string; squad_nome: string; agente_atual_idx?: number; contexto?: string
}) => post<MontarTimeResult>('/tarefas/montar-time', dados)

export const continuarReuniao = (id: string, feedback: string) =>
  post<TarefaResultado>(`/tarefas/${id}/continuar`, { feedback })

export const encerrarReuniao = (id: string) =>
  post<TarefaResultado>(`/tarefas/${id}/encerrar`, {})

export const reabrirReuniao = (id: string) =>
  post<TarefaResultado>(`/tarefas/${id}/reabrir`, {})

export const retomarTarefa = (id: string) =>
  post<TarefaResultado>(`/tarefas/${id}/retomar`, {})

/* --- Catálogo de Agentes --- */

export const buscarCatalogo = (categoria?: string) =>
  get<AgenteCatalogo[]>(`/catalogo${categoria ? `?categoria=${categoria}` : ''}`)

export const buscarAgenteCatalogo = (id: number) =>
  get<AgenteCatalogo>(`/catalogo/${id}`)

export const criarAgenteCatalogo = (dados: AgenteCatalogoCreate) =>
  post<AgenteCatalogo>('/catalogo', dados)

export const atualizarAgenteCatalogo = (id: number, dados: AgenteCatalogoUpdate) =>
  put<AgenteCatalogo>(`/catalogo/${id}`, dados)

export const desativarAgenteCatalogo = (id: number) =>
  del<{ mensagem: string }>(`/catalogo/${id}`)

export const buscarPerfisAgente = () =>
  get<PerfilDisponivel[]>('/catalogo/perfis')

/* --- Atribuições de Agentes --- */

export const buscarMeusAgentes = () =>
  get<AgenteAtribuido[]>('/atribuicoes/meus')

export const buscarAgentesUsuario = (usuarioId: number) =>
  get<AgenteAtribuido[]>(`/atribuicoes/usuario/${usuarioId}`)

export const atribuirAgente = (agente_catalogo_id: number, usuario_id: number) =>
  post<AgenteAtribuido>('/atribuicoes', { agente_catalogo_id, usuario_id })

export const removerAtribuicao = (id: number) =>
  del<{ mensagem: string }>(`/atribuicoes/${id}`)

/* --- Solicitações de Agentes --- */

export const buscarSolicitacoesAgente = () =>
  get<SolicitacaoAgente[]>('/solicitacoes-agente')

export const criarSolicitacaoAgente = (dados: {
  agente_catalogo_id?: number
  descricao: string
  perfil_sugerido?: string
}) => post<SolicitacaoAgente>('/solicitacoes-agente', dados)

export const acaoSolicitacaoAgente = (id: number, aprovado: boolean, comentario = '') =>
  post<SolicitacaoAgente>(`/solicitacoes-agente/${id}/acao`, { aprovado, comentario })

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

/* --- Gestão de Projetos (hierarquia e regras) --- */

export const criarProjeto = (dados: {
  nome: string; descricao?: string; stack?: string; repositorio?: string;
  caminho?: string; icone?: string; fase_atual?: string;
  proprietario_id?: number; lider_tecnico_id?: number;
}) => post<any>('/projetos', dados)

export const nomearProprietario = (projetoId: number, usuarioId: number) =>
  put<{ mensagem: string }>(`/projetos/${projetoId}/proprietario`, { usuario_id: usuarioId })

export const nomearLider = (projetoId: number, usuarioId: number) =>
  put<{ mensagem: string }>(`/projetos/${projetoId}/lider`, { usuario_id: usuarioId })

export const gerenciarMembro = (projetoId: number, acao: 'adicionar' | 'remover', usuarioId: number, papel = 'membro') =>
  put<{ mensagem: string }>(`/projetos/${projetoId}/membros`, { acao, usuario_id: usuarioId, papel })

export const atualizarRegrasAprovacao = (projetoId: number, regras: Record<string, { aprovador: string; descricao: string }>) =>
  put<{ mensagem: string }>(`/projetos/${projetoId}/regras`, { regras })

// ============================================================
// Autonomous Squads — Workflow BMAD completo
// ============================================================

export interface WorkflowAutonomo {
  id: string
  titulo: string
  descricao: string
  fase_atual: number
  fase_nome: string
  status: string
  outputs: Record<string, string>
  gates: Record<string, { status: string; por: string; feedback?: string }>
  agentes_ids: number[]
  tarefa_atual: {
    id: string; status: string; agente_atual: string
    rodadas: any[]; resultado: string
  } | null
  projeto_id: number
  criado_em: string
  atualizado_em: string
}

export const iniciarAutonomo = (dados: {
  titulo: string; descricao?: string; squad_nome: string;
  projeto_id?: number; pular_analise?: boolean
}) => post<{ id: string; titulo: string; fase_atual: number; status: string }>('/tarefas/autonomo', dados)

export const buscarAutonomo = (id: string) =>
  get<WorkflowAutonomo>(`/tarefas/autonomo/${id}`)

export const listarAutonomos = () =>
  get<{ id: string; titulo: string; fase_atual: number; fase_nome: string; status: string; criado_em: string }[]>('/tarefas/autonomo')

export const aprovarGate = (id: string, decisao: string, feedback = '') =>
  post<{ mensagem: string; status: string }>(`/tarefas/autonomo/${id}/aprovar-gate`, { decisao, feedback })

export const cancelarAutonomo = (id: string) =>
  post<{ mensagem: string }>(`/tarefas/autonomo/${id}/cancelar`, {})

export const reiniciarAutonomo = (id: string) =>
  post<{ mensagem: string; status: string; fase: number }>(`/tarefas/autonomo/${id}/reiniciar`, {})

// ============================================================
// Version Control (VCS) — GitHub + GitBucket
// ============================================================

export interface VCSConfig {
  configurado: boolean
  vcs_tipo?: string
  repo_url?: string
  branch_padrao?: string
  token_status?: string
  criado_em?: string
  atualizado_em?: string
}

export const buscarVCS = (projetoId: number) =>
  get<VCSConfig>(`/projetos/${projetoId}/vcs`)

export const salvarVCS = (projetoId: number, dados: {
  vcs_tipo: string; repo_url: string; api_token: string; branch_padrao: string
}) => post<{ mensagem: string }>(`/projetos/${projetoId}/vcs`, dados)

export const testarVCS = (projetoId: number) =>
  post<{ sucesso: boolean; mensagem: string; repo_nome: string; branch_padrao: string }>(
    `/projetos/${projetoId}/vcs/testar`, {}
  )

export const removerVCS = (projetoId: number) =>
  del<{ mensagem: string }>(`/projetos/${projetoId}/vcs`)
