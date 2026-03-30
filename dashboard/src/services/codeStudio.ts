/**
 * Code Studio — Servico de API para o editor de codigo integrado (multi-projeto).
 */

const API = import.meta.env.VITE_API_URL || ''

function headers() {
  const token = localStorage.getItem('sf_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ============================================================
// Tipos
// ============================================================

export interface ArquivoArvore {
  nome: string
  caminho: string
  tipo: 'arquivo' | 'pasta'
  extensao?: string
  tamanho?: number
  linguagem?: string
  filhos?: ArquivoArvore[]
}

export interface ArquivoConteudo {
  caminho: string
  conteudo: string
  linguagem: string
  tamanho: number
  editavel: boolean
}

export interface AnaliseResposta {
  resposta: string
  provider: string
  modelo: string
  context_level?: string
}

export interface ArvoreResponse {
  arvore: ArquivoArvore[]
  base: string
  project_id: number
  projeto_nome: string
}

// ============================================================
// Funcoes de API (multi-projeto)
// ============================================================

export async function buscarArvore(path = '', projetoId = 0): Promise<ArvoreResponse> {
  const params = new URLSearchParams()
  if (path) params.set('path', path)
  if (projetoId) params.set('project_id', String(projetoId))
  const qs = params.toString() ? `?${params.toString()}` : ''

  const res = await fetch(`${API}/api/code-studio/tree${qs}`, { headers: headers() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao carregar arvore' }))
    throw new Error(err.detail || 'Erro ao carregar arvore de arquivos')
  }
  return res.json()
}

export async function lerArquivo(caminho: string, projetoId = 0): Promise<ArquivoConteudo> {
  const params = new URLSearchParams({ path: caminho })
  if (projetoId) params.set('project_id', String(projetoId))

  const res = await fetch(`${API}/api/code-studio/file?${params.toString()}`, {
    headers: headers(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao ler arquivo' }))
    throw new Error(err.detail || 'Erro ao ler arquivo')
  }
  return res.json()
}

export async function salvarArquivo(caminho: string, conteudo: string, projetoId = 0): Promise<{ sucesso: boolean }> {
  const res = await fetch(`${API}/api/code-studio/file`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ caminho, conteudo, project_id: projetoId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao salvar' }))
    throw new Error(err.detail || 'Erro ao salvar arquivo')
  }
  return res.json()
}

export interface VCSResultado {
  sucesso: boolean
  mensagem: string
  commit_hash: string | null
  branch: string
}

export interface DiffResumo {
  linhas_antes: number
  linhas_depois: number
  linhas_adicionadas: number
  linhas_removidas: number
}

export interface AplicarAcaoResponse {
  ok: boolean
  caminho: string
  tipo: string
  tamanho: number
  vcs?: VCSResultado | null
  diff_resumo?: DiffResumo | null
}

export async function aplicarAcao(
  caminhoDestino: string,
  conteudoNovo: string,
  tipoAcao: 'substituir' | 'criar' = 'substituir',
  projetoId = 0
): Promise<AplicarAcaoResponse> {
  const res = await fetch(`${API}/api/code-studio/apply-action`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      caminho_destino: caminhoDestino,
      conteudo_novo: conteudoNovo,
      tipo_acao: tipoAcao,
      project_id: projetoId,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao aplicar acao' }))
    throw new Error(err.detail || 'Erro ao aplicar acao')
  }
  return res.json()
}

export async function analisarCodigo(
  caminho: string,
  conteudo: string,
  instrucao: string,
  modelo = 'auto',
  projetoId = 0,
  contextLevel = 'standard',
): Promise<AnaliseResposta> {
  // Timeout de 120s para chamadas de LLM (podem demorar 30-90s)
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 120000)

  try {
    const res = await fetch(`${API}/api/code-studio/analyze`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ caminho, conteudo, instrucao, modelo, project_id: projetoId, context_level: contextLevel }),
      signal: controller.signal,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Erro na analise' }))
      throw new Error(err.detail || 'Erro na analise')
    }
    return res.json()
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error('Timeout: a analise demorou mais de 2 minutos. Tente novamente.')
    }
    throw e
  } finally {
    clearTimeout(timeout)
  }
}

export interface GitPullResponse {
  sucesso: boolean
  mensagem: string
  branch: string
}

export async function gitPull(projetoId = 0): Promise<GitPullResponse> {
  const params = new URLSearchParams()
  if (projetoId) params.set('project_id', String(projetoId))
  const qs = params.toString() ? `?${params.toString()}` : ''

  const res = await fetch(`${API}/api/code-studio/git-pull${qs}`, {
    method: 'POST',
    headers: headers(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro no git pull' }))
    throw new Error(err.detail || 'Erro no git pull')
  }
  return res.json()
}

// ============================================================
// Historico de atividades
// ============================================================

export interface AtividadeHistorico {
  id: number
  usuario_nome: string
  usuario_email: string
  acao: string
  acao_label: string
  descricao: string
  arquivo: string
  criado_em: string
}

export interface HistoricoResponse {
  atividades: AtividadeHistorico[]
  total: number
  pagina: number
  limite: number
}

export async function buscarHistorico(projetoId = 0, limit = 50, page = 1): Promise<HistoricoResponse> {
  const params = new URLSearchParams()
  if (projetoId) params.set('project_id', String(projetoId))
  params.set('limit', String(limit))
  params.set('page', String(page))

  const res = await fetch(`${API}/api/code-studio/historico?${params.toString()}`, {
    headers: headers(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao carregar historico' }))
    throw new Error(err.detail || 'Erro ao carregar historico')
  }
  return res.json()
}

// ============================================================
// Git Log + Push (commits pendentes + criar PR)
// ============================================================

export interface GitCommitInfo {
  hash: string
  hash_curto: string
  mensagem: string
  autor: string
  data: string
}

export interface GitLogResponse {
  commits: GitCommitInfo[]
  branch: string
  branch_remoto: string
  total: number
}

export interface GitPushResponse {
  sucesso: boolean
  pr_url: string
  pr_number: number
  branch: string
  commits_enviados: number
  mensagem: string
}

export async function gitLog(projetoId = 0): Promise<GitLogResponse> {
  const params = new URLSearchParams()
  if (projetoId) params.set('project_id', String(projetoId))

  const res = await fetch(`${API}/api/code-studio/git-log?${params.toString()}`, {
    headers: headers(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao buscar commits' }))
    throw new Error(err.detail || 'Erro ao buscar commits')
  }
  return res.json()
}

export async function gitPush(projetoId = 0, commitHashes: string[] = [], tituloPr = ''): Promise<GitPushResponse> {
  const res = await fetch(`${API}/api/code-studio/git-push`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      project_id: projetoId,
      commit_hashes: commitHashes,
      titulo_pr: tituloPr,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro no push' }))
    throw new Error(err.detail || 'Erro no push')
  }
  return res.json()
}

// Merge PR
export interface GitMergeResponse {
  sucesso: boolean
  mensagem: string
  merge_sha: string
}

export async function gitMerge(projetoId = 0, prNumber: number): Promise<GitMergeResponse> {
  const res = await fetch(`${API}/api/code-studio/git-merge`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ project_id: projetoId, pr_number: prNumber }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro no merge' }))
    throw new Error(err.detail || 'Erro no merge')
  }
  return res.json()
}
