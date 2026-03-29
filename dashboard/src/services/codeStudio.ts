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

export async function aplicarAcao(
  caminhoDestino: string,
  conteudoNovo: string,
  tipoAcao: 'substituir' | 'criar' = 'substituir',
  projetoId = 0
): Promise<{ ok: boolean; caminho: string; tipo: string; tamanho: number }> {
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
  projetoId = 0
): Promise<AnaliseResposta> {
  const res = await fetch(`${API}/api/code-studio/analyze`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ caminho, conteudo, instrucao, modelo, project_id: projetoId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro na analise' }))
    throw new Error(err.detail || 'Erro na analise')
  }
  return res.json()
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
