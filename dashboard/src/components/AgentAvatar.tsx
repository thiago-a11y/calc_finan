/**
 * AgentAvatar — Componente reutilizável de avatar de agente.
 *
 * Exibe o avatar redondo do agente com:
 * - Imagem de alta qualidade (com fallback para iniciais)
 * - Bandeira do país (opcional)
 * - Efeito hover com scale + glow
 * - Indicador de status (online, ocupado, offline)
 * - Tamanhos: sm (28px), md (36px), lg (48px), xl (64px), 2xl (80px)
 */

import { useState, useMemo } from 'react'
import { buscarAgente, type AgentConfig } from '../config/agents'

export type AvatarSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl'
export type AvatarStatus = 'online' | 'ocupado' | 'offline' | 'pensando' | undefined

interface AgentAvatarProps {
  /** Nome do agente (ex: "kenji", "Luna", "Carlos/Frontend") */
  agentName: string
  /** Tamanho do avatar */
  size?: AvatarSize
  /** Mostrar bandeira do país ao lado */
  showFlag?: boolean
  /** Mostrar nome abaixo ou ao lado */
  showName?: boolean
  /** Disposição do nome */
  namePosition?: 'bottom' | 'right'
  /** Status do agente */
  status?: AvatarStatus
  /** Mostrar indicador de status */
  showStatus?: boolean
  /** Classes extras no container */
  className?: string
  /** Callback ao clicar */
  onClick?: () => void
  /** Desabilitar efeito hover */
  noHover?: boolean
  /** Borda customizada (cor hex) */
  borderColor?: string
}

/** Dimensões por tamanho */
const SIZES: Record<AvatarSize, { px: number; text: string; flag: string; status: number; nameText: string }> = {
  sm:  { px: 28, text: 'text-[10px]', flag: 'text-[10px]', status: 8,  nameText: 'text-[10px]' },
  md:  { px: 36, text: 'text-xs',     flag: 'text-xs',     status: 10, nameText: 'text-xs' },
  lg:  { px: 48, text: 'text-sm',     flag: 'text-sm',     status: 12, nameText: 'text-sm' },
  xl:  { px: 64, text: 'text-lg',     flag: 'text-base',   status: 14, nameText: 'text-sm' },
  '2xl': { px: 80, text: 'text-xl',   flag: 'text-lg',     status: 16, nameText: 'text-base' },
}

/** Cores de status */
const STATUS_COLORS: Record<string, string> = {
  online: '#10b981',
  ocupado: '#f59e0b',
  offline: '#6b7280',
  pensando: '#8b5cf6',
}

export default function AgentAvatar({
  agentName,
  size = 'md',
  showFlag = false,
  showName = false,
  namePosition = 'right',
  status,
  showStatus = false,
  className = '',
  onClick,
  noHover = false,
  borderColor,
}: AgentAvatarProps) {
  const [imgError, setImgError] = useState(false)

  const agent: AgentConfig | undefined = useMemo(() => buscarAgente(agentName), [agentName])
  const s = SIZES[size]

  // Fallback: gerar iniciais e cor a partir do nome
  const fallbackIniciais = useMemo(() => {
    if (agent) return agent.iniciais
    const parts = agentName.split(/[\s/]+/).filter(Boolean)
    return parts.map(p => p[0]).join('').slice(0, 2).toUpperCase()
  }, [agent, agentName])

  const fallbackCor = useMemo(() => {
    if (agent) return agent.corFundo
    // Hash simples do nome para gerar cor
    let hash = 0
    for (let i = 0; i < agentName.length; i++) {
      hash = agentName.charCodeAt(i) + ((hash << 5) - hash)
    }
    const cores = ['#1e3a5f', '#3b1f7a', '#5c3d0e', '#5c1d3e', '#0d4f3a', '#2d2f7a', '#5c1d1d', '#0d4f47']
    return cores[Math.abs(hash) % cores.length]
  }, [agent, agentName])

  const avatarUrl = agent?.avatarUrl
  const showImg = avatarUrl && !imgError

  const containerStyle: React.CSSProperties = {
    width: s.px,
    height: s.px,
    minWidth: s.px,
    minHeight: s.px,
  }

  const borderStyle = borderColor
    ? `2px solid ${borderColor}`
    : '2px solid rgba(255,255,255,0.12)'

  const hoverClass = !noHover && onClick
    ? 'cursor-pointer hover:scale-110 hover:shadow-lg hover:shadow-emerald-500/20'
    : !noHover
      ? 'hover:scale-105'
      : ''

  const avatarElement = (
    <div
      className={`relative rounded-full overflow-hidden transition-all duration-300 ${hoverClass}`}
      style={{ ...containerStyle, border: borderStyle }}
      onClick={onClick}
      title={agent ? `${agent.nome} ${agent.countryFlag} — ${agent.role}` : agentName}
    >
      {showImg ? (
        <img
          src={avatarUrl}
          alt={agent?.nome || agentName}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
          loading="lazy"
          draggable={false}
        />
      ) : (
        <div
          className={`w-full h-full flex items-center justify-center font-bold text-white ${s.text}`}
          style={{ backgroundColor: fallbackCor }}
        >
          {fallbackIniciais}
        </div>
      )}

      {/* Indicador de status */}
      {showStatus && status && (
        <div
          className="absolute bottom-0 right-0 rounded-full border-2"
          style={{
            width: s.status,
            height: s.status,
            backgroundColor: STATUS_COLORS[status] || STATUS_COLORS.offline,
            borderColor: 'var(--sf-bg-1, #0f0f12)',
          }}
        />
      )}

      {/* Animação de pensando */}
      {status === 'pensando' && (
        <div className="absolute inset-0 rounded-full animate-pulse bg-purple-500/20" />
      )}
    </div>
  )

  // Sem nome e sem bandeira: retorna só o avatar
  if (!showName && !showFlag) {
    return <div className={className}>{avatarElement}</div>
  }

  // Com nome e/ou bandeira
  const isBottom = namePosition === 'bottom'

  return (
    <div className={`flex ${isBottom ? 'flex-col items-center gap-1' : 'items-center gap-2'} ${className}`}>
      {avatarElement}
      <div className={`flex ${isBottom ? 'flex-col items-center' : 'flex-col'} min-w-0`}>
        {showName && (
          <span className={`${s.nameText} font-medium sf-text-white truncate flex items-center gap-1`}>
            {agent?.nome || agentName}
            {showFlag && agent?.countryFlag && (
              <span className={s.flag}>{agent.countryFlag}</span>
            )}
          </span>
        )}
        {showName && agent?.role && (
          <span className="text-[10px] sf-text-ghost truncate">{agent.role}</span>
        )}
        {!showName && showFlag && agent?.countryFlag && (
          <span className={s.flag}>{agent.countryFlag}</span>
        )}
      </div>
    </div>
  )
}

/**
 * Grupo de avatares empilhados (ex: participantes de reunião).
 */
export function AgentAvatarGroup({
  agents,
  size = 'sm',
  max = 5,
  className = '',
}: {
  agents: string[]
  size?: AvatarSize
  max?: number
  className?: string
}) {
  const visibles = agents.slice(0, max)
  const remaining = agents.length - max

  return (
    <div className={`flex -space-x-2 ${className}`}>
      {visibles.map((nome, i) => (
        <div key={`${nome}-${i}`} className="relative" style={{ zIndex: visibles.length - i }}>
          <AgentAvatar agentName={nome} size={size} noHover borderColor="var(--sf-bg-1, #0f0f12)" />
        </div>
      ))}
      {remaining > 0 && (
        <div
          className="relative flex items-center justify-center rounded-full bg-white/10 text-[10px] font-bold sf-text-dim border-2"
          style={{
            width: SIZES[size].px,
            height: SIZES[size].px,
            borderColor: 'var(--sf-bg-1, #0f0f12)',
            zIndex: 0,
          }}
        >
          +{remaining}
        </div>
      )}
    </div>
  )
}
