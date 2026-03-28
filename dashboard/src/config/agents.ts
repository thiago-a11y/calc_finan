/**
 * Configuração centralizada dos agentes do Synerium Factory.
 * Mapeamento de nomes, avatares, bandeiras e funções.
 *
 * Avatares ficam em: /avatars/{nome}.jpg
 */

export interface AgentConfig {
  /** Identificador único (minúsculo, sem acento) */
  id: string
  /** Nome de exibição */
  nome: string
  /** URL do avatar (relativo ao public/) */
  avatarUrl: string
  /** Emoji da bandeira do país (vazio para Luna) */
  countryFlag: string
  /** Código ISO do país */
  country: string
  /** Função/papel do agente */
  role: string
  /** Categoria do agente */
  categoria: 'desenvolvimento' | 'gestao' | 'seguranca' | 'ia' | 'operacional'
  /** Cor principal do agente (hex) */
  cor: string
  /** Cor de fundo do avatar (fallback) */
  corFundo: string
  /** Iniciais para fallback */
  iniciais: string
}

/**
 * Lista completa dos agentes com seus avatares e metadados.
 */
export const AGENTES: AgentConfig[] = [
  {
    id: 'kenji',
    nome: 'Kenji',
    avatarUrl: '/avatars/kenji.jpg',
    countryFlag: '🇰🇷',
    country: 'KR',
    role: 'Tech Lead / Arquiteto',
    categoria: 'desenvolvimento',
    cor: '#3b82f6',
    corFundo: '#1e3a5f',
    iniciais: 'KE',
  },
  {
    id: 'amara',
    nome: 'Amara',
    avatarUrl: '/avatars/amara.jpg',
    countryFlag: '🇳🇬',
    country: 'NG',
    role: 'Backend PHP/Python',
    categoria: 'desenvolvimento',
    cor: '#8b5cf6',
    corFundo: '#3b1f7a',
    iniciais: 'AM',
  },
  {
    id: 'carlos',
    nome: 'Carlos',
    avatarUrl: '/avatars/carlos.jpg',
    countryFlag: '🇲🇽',
    country: 'MX',
    role: 'Frontend React/TS',
    categoria: 'desenvolvimento',
    cor: '#f59e0b',
    corFundo: '#5c3d0e',
    iniciais: 'CA',
  },
  {
    id: 'yuki',
    nome: 'Yuki',
    avatarUrl: '/avatars/yuki.jpg',
    countryFlag: '🇯🇵',
    country: 'JP',
    role: 'Especialista IA',
    categoria: 'ia',
    cor: '#ec4899',
    corFundo: '#5c1d3e',
    iniciais: 'YU',
  },
  {
    id: 'rafael',
    nome: 'Rafael',
    avatarUrl: '/avatars/rafael.jpg',
    countryFlag: '🇧🇷',
    country: 'BR',
    role: 'Integrações/APIs',
    categoria: 'desenvolvimento',
    cor: '#10b981',
    corFundo: '#0d4f3a',
    iniciais: 'RA',
  },
  {
    id: 'hans',
    nome: 'Hans',
    avatarUrl: '/avatars/hans.jpg',
    countryFlag: '🇩🇪',
    country: 'DE',
    role: 'DevOps/Infra',
    categoria: 'operacional',
    cor: '#6366f1',
    corFundo: '#2d2f7a',
    iniciais: 'HA',
  },
  {
    id: 'fatima',
    nome: 'Fatima',
    avatarUrl: '/avatars/fatima.jpg',
    countryFlag: '🇸🇦',
    country: 'SA',
    role: 'QA/Segurança',
    categoria: 'seguranca',
    cor: '#ef4444',
    corFundo: '#5c1d1d',
    iniciais: 'FA',
  },
  {
    id: 'marco',
    nome: 'Marco',
    avatarUrl: '/avatars/marco.jpg',
    countryFlag: '🇮🇹',
    country: 'IT',
    role: 'Product Manager',
    categoria: 'gestao',
    cor: '#14b8a6',
    corFundo: '#0d4f47',
    iniciais: 'MA',
  },
  {
    id: 'sofia',
    nome: 'Sofia',
    avatarUrl: '/avatars/sofia.jpg',
    countryFlag: '🇧🇷',
    country: 'BR',
    role: 'Secretária Executiva',
    categoria: 'operacional',
    cor: '#d946ef',
    corFundo: '#5c1d6b',
    iniciais: 'SO',
  },
  {
    id: 'luna',
    nome: 'Luna',
    avatarUrl: '/avatars/luna.jpg',
    countryFlag: '',
    country: '',
    role: 'Assistente IA Integrada',
    categoria: 'ia',
    cor: '#10b981',
    corFundo: '#0d4f3a',
    iniciais: 'LU',
  },
]

/** Mapa rápido por ID */
export const AGENTES_MAP: Record<string, AgentConfig> = Object.fromEntries(
  AGENTES.map(a => [a.id, a])
)

/**
 * Mapeamento de papéis (como vêm do backend) → ID do agente.
 * Os squads enviam nomes como "Tech Lead / Arquiteto de Software",
 * "Desenvolvedor Backend PHP/Python", etc.
 */
const PAPEL_PARA_AGENTE: Record<string, string> = {
  'tech lead': 'kenji',
  'arquiteto': 'kenji',
  'backend': 'amara',
  'backend php': 'amara',
  'php': 'amara',
  'frontend': 'carlos',
  'frontend react': 'carlos',
  'react': 'carlos',
  'inteligência artificial': 'yuki',
  'inteligencia artificial': 'yuki',
  'especialista ia': 'yuki',
  'ia': 'yuki',
  'integrações': 'rafael',
  'integracoes': 'rafael',
  'apis': 'rafael',
  'devops': 'hans',
  'infra': 'hans',
  'infraestrutura': 'hans',
  'qa': 'fatima',
  'segurança': 'fatima',
  'seguranca': 'fatima',
  'qualidade': 'fatima',
  'product manager': 'marco',
  'product': 'marco',
  'pm': 'marco',
  'analista': 'marco',
  'secretária': 'sofia',
  'secretaria': 'sofia',
  'executiva': 'sofia',
  'luna': 'luna',
  'assistente': 'luna',
  'consultora': 'luna',
}

/**
 * Busca agente pelo nome ou papel (case-insensitive, parcial).
 * Ex: buscarAgente("kenji") → AgentConfig
 * Ex: buscarAgente("Kenji/Tech Lead") → AgentConfig
 * Ex: buscarAgente("Tech Lead / Arquiteto de Software") → Kenji
 * Ex: buscarAgente("Desenvolvedor Backend PHP/Python") → Amara
 */
export function buscarAgente(nome: string): AgentConfig | undefined {
  const fullLower = nome.toLowerCase().trim()
  const firstPart = fullLower.split('/')[0].trim()

  // 1. Busca direta por ID ou nome exato
  const direto = AGENTES.find(a => a.id === firstPart || a.nome.toLowerCase() === firstPart)
  if (direto) return direto

  // 2. Busca pelo nome completo (inclui tudo após a barra) contra os roles
  //    Ex: "Desenvolvedor Backend PHP/Python" deve bater com role "Backend PHP/Python"
  const porRole = AGENTES.find(a => fullLower.includes(a.role.toLowerCase()) || a.role.toLowerCase().includes(fullLower))
  if (porRole) return porRole

  // 3. Busca por keywords no mapeamento — usa o nome COMPLETO para melhor match
  //    Ordena por tamanho da keyword (maior = mais específico primeiro)
  const keywords = Object.entries(PAPEL_PARA_AGENTE).sort((a, b) => b[0].length - a[0].length)
  for (const [keyword, agId] of keywords) {
    if (fullLower.includes(keyword)) {
      return AGENTES_MAP[agId]
    }
  }

  // 4. Fallback com primeira parte
  for (const [keyword, agId] of keywords) {
    if (firstPart.includes(keyword) || keyword.includes(firstPart)) {
      return AGENTES_MAP[agId]
    }
  }

  return undefined
}

/**
 * Retorna o avatar URL para um nome de agente.
 * Fallback: retorna undefined se não encontrado.
 */
export function avatarDoAgente(nome: string): string | undefined {
  return buscarAgente(nome)?.avatarUrl
}

/** Cores por categoria para badges */
export const CORES_CATEGORIA: Record<string, { bg: string; text: string; border: string }> = {
  desenvolvimento: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  gestao: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
  seguranca: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  ia: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  operacional: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
}
