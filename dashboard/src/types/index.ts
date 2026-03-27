/* Tipos TypeScript — espelhando os schemas Pydantic do FastAPI */

export interface SquadResumo {
  nome: string
  especialidade: string
  contexto: string
  num_agentes: number
  num_tarefas: number
}

export interface VaultResumo {
  nome: string
  caminho: string
}

export interface UsuarioResumo {
  id: string
  nome: string
  cargo: string
  pode_aprovar: boolean
}

export interface Usuario {
  id: string
  nome: string
  cargo: string
  papeis: string[]
  email: string
  pode_aprovar: boolean
  areas_aprovacao: string[]
  ativo: boolean
  telefone?: string
  bio?: string
  avatar_url?: string
  social_linkedin?: string
  social_instagram?: string
  social_whatsapp?: string
  criado_em?: string
  permissoes_granulares?: Record<string, Record<string, boolean>> | null
  permissoes_efetivas?: PermissoesEfetivas
}

export interface PapelDisponivel {
  id: string
  nome: string
  descricao: string
}

export interface AreaAprovacaoDisponivel {
  id: string
  nome: string
  descricao: string
}

export interface CriarUsuarioPayload {
  email: string
  nome: string
  senha: string
  cargo?: string
  papeis?: string[]
  pode_aprovar?: boolean
  areas_aprovacao?: string[]
}

export interface AtualizarPermissoesPayload {
  papeis?: string[]
  pode_aprovar?: boolean
  areas_aprovacao?: string[]
  permissoes_granulares?: Record<string, Record<string, boolean>> | null
}

export interface StatusGeral {
  ambiente: string
  data_hora: string
  pm_central: string
  operations_lead: string
  lideranca: UsuarioResumo[]
  squads: SquadResumo[]
  total_squads: number
  aprovacoes_pendentes: number
  rag_vaults: VaultResumo[]
  total_vaults: number
}

export interface Squad {
  nome: string
  especialidade: string
  contexto: string
  num_agentes: number
  num_tarefas: number
  nomes_agentes: string[]
}

export interface Aprovacao {
  indice: number
  tipo: string
  descricao: string
  solicitante: string
  valor_estimado: number | null
  criado_em: string
  aprovado: boolean | null
  aprovado_por: string | null
}

export interface RAGStatus {
  vaults_configurados: VaultResumo[]
  total_vaults: number
  persist_directory: string
  company_id: string
  chunk_size: number
  chunk_overlap: number
  embedding_model: string
}

export interface RAGStats {
  total_chunks: number
  por_vault: Record<string, number>
  vaults_indexados: string[]
  persist_directory: string
  company_id: string
  chunk_size: number
  chunk_overlap: number
  embedding_model: string
}

export interface RAGChunk {
  vault: string
  arquivo: string
  secao: string
  conteudo: string
}

export interface RAGConsultaResult {
  pergunta: string
  resposta_ia: string
  chunks: RAGChunk[]
  total_chunks: number
}

export interface RAGIndexarResult {
  mensagem: string
  vaults_indexados: string[]
  total_chunks: number
}

export interface StandupRelatorio {
  relatorio: string
  data_execucao: string
  squads_reportados: number
}

export interface RodadaItem {
  rodada: number
  agente: string
  resposta: string
  timestamp: string
}

export interface TarefaResultado {
  id: string
  squad_nome: string
  agente_nome: string
  agente_indice: number
  descricao: string
  resultado: string | null
  status: 'pendente' | 'executando' | 'concluida' | 'erro' | 'aguardando_feedback'
  erro: string | null
  usuario_id: number
  usuario_nome: string
  criado_em: string
  concluido_em: string | null
  tipo: 'tarefa' | 'reuniao'
  participantes: string[] | null
  rodadas: RodadaItem[] | null
  rodada_atual: number
  agente_atual: string | null
}

export interface ChatAberto {
  id: string
  squadNome: string
  agenteIdx: number
  agenteNome: string
  minimizado: boolean
}

export type PermissaoAcao = 'view' | 'create' | 'edit' | 'delete' | 'export'
export type PermissoesModulo = Record<PermissaoAcao, boolean>
export type PermissoesEfetivas = Record<string, PermissoesModulo>

export interface ModuloDisponivel {
  id: string
  nome: string
  icone: string
}

// --- Catálogo de Agentes ---

export interface AgenteCatalogo {
  id: number
  nome_exibicao: string
  papel: string
  objetivo: string
  historia: string
  perfil_agente: string
  categoria: string
  icone: string
  allow_delegation: boolean
  ativo: boolean
  criado_em?: string
  total_usuarios: number
}

export interface AgenteCatalogoCreate {
  nome_exibicao: string
  papel: string
  objetivo: string
  historia: string
  perfil_agente: string
  categoria?: string
  icone?: string
  regras_extras?: string
  allow_delegation?: boolean
}

export interface AgenteCatalogoUpdate {
  nome_exibicao?: string
  papel?: string
  objetivo?: string
  historia?: string
  perfil_agente?: string
  categoria?: string
  icone?: string
  regras_extras?: string
  allow_delegation?: boolean
  ativo?: boolean
}

export interface AgenteAtribuido {
  id: number
  agente_catalogo_id: number
  usuario_id: number
  nome_agente: string
  perfil_agente: string
  categoria: string
  icone: string
  ordem: number
  ativo: boolean
  criado_em?: string
}

export interface SolicitacaoAgente {
  id: number
  usuario_id: number
  usuario_nome: string
  agente_catalogo_id?: number
  nome_agente: string
  descricao: string
  perfil_sugerido: string
  status: string
  aprovado_por_nome: string
  comentario: string
  criado_em?: string
}

export interface PerfilDisponivel {
  perfil: string
  descricao: string
  tier_llm: string
}

export interface FileAttachment {
  nome_original: string
  nome_salvo: string
  url: string
  tipo: 'imagem' | 'video' | 'audio' | 'pdf' | 'documento'
  tamanho: number
  extensao: string
  enviado_por: string
  enviado_em: string
  erro?: string
}
