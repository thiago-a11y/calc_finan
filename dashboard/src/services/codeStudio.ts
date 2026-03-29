/**
 * Code Studio — Serviço de API para o editor de código integrado.
 */

const API = import.meta.env.VITE_API_URL || ''

function headers() {
  const token = localStorage.getItem('token')
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

// ============================================================
// Funções de API
// ============================================================

export async function buscarArvore(path = ''): Promise<ArquivoArvore[]> {
  const params = path ? `?path=${encodeURIComponent(path)}` : ''
  const res = await fetch(`${API}/api/code-studio/tree${params}`, { headers: headers() })
  if (!res.ok) throw new Error('Erro ao carregar árvore de arquivos')
  const data = await res.json()
  return data.arvore
}

export async function lerArquivo(caminho: string): Promise<ArquivoConteudo> {
  const res = await fetch(`${API}/api/code-studio/file?path=${encodeURIComponent(caminho)}`, {
    headers: headers(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao ler arquivo' }))
    throw new Error(err.detail || 'Erro ao ler arquivo')
  }
  return res.json()
}

export async function salvarArquivo(caminho: string, conteudo: string): Promise<{ sucesso: boolean }> {
  const res = await fetch(`${API}/api/code-studio/file`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ caminho, conteudo }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro ao salvar' }))
    throw new Error(err.detail || 'Erro ao salvar arquivo')
  }
  return res.json()
}

export async function analisarCodigo(
  caminho: string,
  conteudo: string,
  instrucao: string,
  modelo = 'auto'
): Promise<AnaliseResposta> {
  const res = await fetch(`${API}/api/code-studio/analyze`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ caminho, conteudo, instrucao, modelo }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro na análise' }))
    throw new Error(err.detail || 'Erro na análise')
  }
  return res.json()
}
