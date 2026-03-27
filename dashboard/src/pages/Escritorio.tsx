/* =====================================================================
   Escritório Virtual — Revolucionário Premium
   Isométrico 2D aprimorado com profundidade via layers, sombras,
   iluminação cinematográfica e ciclo dia/noite real.
   v0.30.0 — Synerium Factory
   ===================================================================== */

import { useCallback, useState, useMemo, useEffect, memo } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarSquads, buscarHistoricoTarefas } from '../services/api'
import { useChatManager } from '../components/ChatManager'
import type { TarefaResultado } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { Users, MessageSquare, Crown, X, User, Eye, ChevronDown, Video } from 'lucide-react'
import ReuniaoVideo from '../components/ReuniaoVideo'
import { motion, AnimatePresence } from 'framer-motion'

/* =====================================================================
   [A] CONSTANTES, TIPOS E CONFIGS
   ===================================================================== */

interface SquadComMeta {
  nome: string; especialidade: string; contexto: string
  num_agentes: number; num_tarefas: number; nomes_agentes: string[]
  proprietario_email?: string; tipo?: string; is_meu?: boolean
}

const CORES = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ec4899','#6366f1','#ef4444','#14b8a6','#d946ef','#f97316','#06b6d4','#84cc16']
const SKINS = ['#f5d0a9','#8d5524','#c68642','#f5d0a9','#a0522d','#f5cba7','#c68642','#f5cba7','#c68642','#f5d0a9','#8d5524','#f5cba7']
const HAIRS = ['#1a1a2e','#0a0a0a','#2d1810','#0a0a0a','#1a0a00','#b8860b','#0a0a0a','#3d2b1f','#1a0a00','#1a1a2e','#0a0a0a','#3d2b1f']
/* Objeto pessoal aleatorizado por agente */
const DESK_ITEMS = ['frame','book','trophy','cactus','globe','mug2','headphones','figurine','candle']

function agCfg(i: number, name: string) {
  const label = name.split('/')[0]?.trim() || name
  return {
    nome: label.split(' ')[0] || `Ag${i+1}`,
    label,
    cor: CORES[i % CORES.length],
    skin: SKINS[i % SKINS.length],
    hair: HAIRS[i % HAIRS.length],
    item: DESK_ITEMS[i % DESK_ITEMS.length],
  }
}

/* Posições — CANVAS 1600×750 */
const DK = [
  { x: 350, y: 130 }, { x: 550, y: 130 }, { x: 750, y: 130 },
  { x: 350, y: 310 }, { x: 550, y: 310 }, { x: 750, y: 310 },
  { x: 350, y: 490 }, { x: 550, y: 490 }, { x: 750, y: 490 },
]
const CEO_POS = { x: 80, y: 280 }
const CEO_SIDE = { x: 215, y: 248 }
const MEET_CENTER = { x: 1200, y: 330 }
const MEET_CHAIRS = [
  { x: -120, y: -60 }, { x: -60, y: -95 }, { x: 20, y: -100 }, { x: 100, y: -85 }, { x: 150, y: -45 },
  { x: 150, y: 45 }, { x: 100, y: 85 }, { x: 20, y: 100 }, { x: -60, y: 95 }, { x: -120, y: 60 },
  { x: -145, y: 0 }, { x: 175, y: 0 },
]

/* =====================================================================
   [B] CSS KEYFRAMES + THEME VARS
   ===================================================================== */

const CSS = `
@keyframes typing{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}
@keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.015)}}
@keyframes thinking{0%,100%{transform:rotate(0)}25%{transform:rotate(2.5deg)}75%{transform:rotate(-2.5deg)}}
@keyframes screenGlow{0%,100%{opacity:.45}50%{opacity:.85}}
@keyframes steam{0%{opacity:.5;transform:translateY(0) scale(1)}100%{opacity:0;transform:translateY(-14px) scale(1.5)}}
@keyframes leafSway{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(3deg)}}
@keyframes meetGlow{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.2)}50%{box-shadow:0 0 25px rgba(16,185,129,.12)}}
@keyframes bubbleRise{0%{opacity:.6;transform:translateY(0) scale(1)}100%{opacity:0;transform:translateY(-20px) scale(.6)}}
@keyframes spotPulse{0%,100%{opacity:.2}50%{opacity:.45}}
@keyframes clockSecond{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
@keyframes floatBadge{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}
`

const themeCSS = `
:root {
  --office-floor: #e8ddd0; --office-floor-line: rgba(0,0,0,.035);
  --office-floor-grain: rgba(0,0,0,.015);
  --office-wall: #f0ebe4; --office-wall-trim: #c9b99a; --office-wall-shadow: rgba(0,0,0,.06);
  --office-window: rgba(180,210,240,.25); --office-window-glow: rgba(135,206,250,.12); --office-sky: #87ceeb;
  --office-desk: #c69c6d; --office-desk-edge: #a07d5a; --office-desk-grain: rgba(0,0,0,.05); --office-desk-leg: #8a6844;
  --office-desk-shadow: rgba(0,0,0,.1);
  --office-monitor: #2a2a2e; --office-monitor-bezel: #3a3a3e; --office-screen-off: #1a1a1e;
  --office-keyboard: #ddd; --office-mug: #c75050;
  --office-pot: #b07050; --office-lamp-pole: #999; --office-lamp-shade: #f5e6d3;
  --office-carpet: rgba(180,160,140,.25); --office-glass: rgba(200,220,255,.08);
  --office-glass-edge: rgba(200,220,255,.15); --office-glass-reflect: rgba(255,255,255,.05);
  --office-rug: rgba(160,140,120,.15); --office-clock: #bbb;
}
.dark {
  --office-floor: #111114; --office-floor-line: rgba(255,255,255,.018);
  --office-floor-grain: rgba(255,255,255,.008);
  --office-wall: #16161c; --office-wall-trim: #252530; --office-wall-shadow: rgba(0,0,0,.3);
  --office-window: rgba(40,60,100,.12); --office-window-glow: rgba(80,120,200,.06); --office-sky: #0f172a;
  --office-desk: #231c14; --office-desk-edge: #302518; --office-desk-grain: rgba(255,255,255,.025); --office-desk-leg: #1a1410;
  --office-desk-shadow: rgba(0,0,0,.25);
  --office-monitor: #08080c; --office-monitor-bezel: #181820; --office-screen-off: #060608;
  --office-keyboard: #222228; --office-mug: #7a2828;
  --office-pot: #3a2820; --office-lamp-pole: #3a3a40; --office-lamp-shade: #1e1a15;
  --office-carpet: rgba(30,25,35,.3); --office-glass: rgba(60,80,140,.06);
  --office-glass-edge: rgba(80,100,160,.1); --office-glass-reflect: rgba(255,255,255,.02);
  --office-rug: rgba(25,22,30,.25); --office-clock: #444;
}
`

/* =====================================================================
   [C] HOOK: CICLO DIA/NOITE
   ===================================================================== */

type Fase = 'amanhecer' | 'dia' | 'entardecer' | 'noite'

function useDayNightCycle() {
  const calc = () => {
    const h = new Date().getHours()
    const m = new Date().getMinutes()
    const t = h + m / 60
    let fase: Fase, progresso: number
    if (t >= 5 && t < 7) { fase = 'amanhecer'; progresso = (t - 5) / 2 }
    else if (t >= 7 && t < 17) { fase = 'dia'; progresso = (t - 7) / 10 }
    else if (t >= 17 && t < 19) { fase = 'entardecer'; progresso = (t - 17) / 2 }
    else { fase = 'noite'; progresso = t >= 19 ? (t - 19) / 10 : (t + 5) / 10 }

    const skyGradients: Record<Fase, string> = {
      amanhecer: 'linear-gradient(180deg, #ff9a76 0%, #ffc3a0 40%, #87ceeb 100%)',
      dia: 'linear-gradient(180deg, #4a90d9 0%, #87ceeb 50%, #a8d8ea 100%)',
      entardecer: 'linear-gradient(180deg, #2d1b69 0%, #c850c0 30%, #ff6b35 70%, #ffaf40 100%)',
      noite: 'linear-gradient(180deg, #0a0a2e 0%, #16213e 50%, #1a1a3e 100%)',
    }
    const ambientOverlays: Record<Fase, string> = {
      amanhecer: 'rgba(255,180,100,.02)',
      dia: 'transparent',
      entardecer: 'rgba(255,120,40,.03)',
      noite: 'rgba(15,20,60,.06)',
    }
    const lampOpacities: Record<Fase, number> = {
      amanhecer: 0.35, dia: 0.15, entardecer: 0.45, noite: 0.8,
    }
    return {
      fase, progresso,
      skyGradient: skyGradients[fase],
      ambientOverlay: ambientOverlays[fase],
      lampOpacity: lampOpacities[fase],
      showStars: fase === 'noite',
    }
  }

  const [state, setState] = useState(calc)
  useEffect(() => {
    const id = setInterval(() => setState(calc), 60000)
    return () => clearInterval(id)
  }, [])
  return state
}

/* =====================================================================
   [D] SUB-COMPONENTES MEMOIZADOS
   ===================================================================== */

/* ── Piso de Madeira ── */
const PremiumFloor = memo(function PremiumFloor() {
  return (
    <div className="absolute inset-0" style={{
      background: 'var(--office-floor)',
      backgroundImage: `
        repeating-linear-gradient(90deg, transparent, transparent 79px, var(--office-floor-line) 79px, var(--office-floor-line) 80px),
        repeating-linear-gradient(0deg, transparent, transparent 19px, var(--office-floor-line) 19px, var(--office-floor-line) 20px),
        repeating-linear-gradient(90deg, var(--office-floor-grain) 0px, transparent 2px, transparent 40px)
      `,
    }} />
  )
})

/* ── Vista do Rio de Janeiro (SVG dentro de cada janela) ── */
const RioSkyline = memo(function RioSkyline({ showStars }: { skyGradient: string; showStars: boolean }) {
  return (
    <svg width="130" height="44" viewBox="0 0 130 44" className="absolute inset-[3px]">
      <defs>
        <linearGradient id="skyG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" />
          <stop offset="100%" stopColor="currentColor" />
        </linearGradient>
      </defs>
      {/* Céu — preenchido via div pai com background */}
      <rect width="130" height="44" rx="1" fill="transparent" />
      {/* Estrelas (noite) */}
      {showStars && <>
        <circle cx="15" cy="6" r=".8" fill="white" opacity=".7" />
        <circle cx="45" cy="10" r=".6" fill="white" opacity=".5" />
        <circle cx="75" cy="4" r=".7" fill="white" opacity=".6" />
        <circle cx="105" cy="8" r=".5" fill="white" opacity=".5" />
        <circle cx="60" cy="14" r=".4" fill="white" opacity=".4" />
      </>}
      {/* Mar */}
      <rect x="0" y="34" width="130" height="10" fill="rgba(30,80,140,.25)" rx="0" />
      {/* Montanhas */}
      <path d="M0 38 L10 28 L22 32 L35 20 L48 30 L55 18 L62 25 L70 14 L78 22 L85 28 L95 16 L105 24 L115 20 L125 28 L130 34 L130 44 L0 44 Z"
        fill="rgba(30,60,30,.35)" />
      {/* Pão de Açúcar (reconhecível) */}
      <path d="M88 28 Q92 10 96 10 Q100 10 104 28" fill="rgba(40,70,40,.4)" stroke="rgba(20,50,20,.15)" strokeWidth=".5" />
      {/* Cristo Redentor (silhueta no pico) */}
      <g transform="translate(55,12)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="rgba(50,50,50,.3)" strokeWidth=".8" />
        <line x1="-3" y1="1.5" x2="3" y2="1.5" stroke="rgba(50,50,50,.3)" strokeWidth=".8" />
        <circle cx="0" cy="-.5" r="1" fill="rgba(50,50,50,.3)" />
      </g>
    </svg>
  )
})

/* ── Parede Traseira com Janelas ── */
const BackWall = memo(function BackWall({ skyGradient, showStars }: { skyGradient: string; showStars: boolean }) {
  const windowPositions = [80, 220, 360, 500, 640, 800, 960, 1120, 1280, 1420]
  return (
    <div className="absolute top-0 left-0 right-0" style={{ height: 80, zIndex: 1 }}>
      {/* Parede */}
      <div className="absolute inset-0" style={{
        background: 'var(--office-wall)',
        borderBottom: '4px solid var(--office-wall-trim)',
        boxShadow: '0 4px 20px var(--office-wall-shadow)',
      }} />
      {/* Moldura decorativa */}
      <div className="absolute bottom-[4px] left-0 right-0 h-[2px]" style={{ background: 'linear-gradient(90deg, transparent, var(--office-wall-trim), transparent)' }} />

      {/* Janelas com vista do Rio */}
      {windowPositions.map((x, i) => (
        <div key={i} className="absolute" style={{
          left: x, top: 10, width: 136, height: 50, borderRadius: 5,
          background: skyGradient,
          border: '2.5px solid var(--office-wall-trim)',
          boxShadow: 'inset 0 0 25px var(--office-window-glow), 0 2px 8px rgba(0,0,0,.08)',
          overflow: 'hidden',
        }}>
          {/* Divisória central */}
          <div className="absolute top-0 bottom-0 left-1/2" style={{ width: 2, background: 'var(--office-wall-trim)' }} />
          {/* Reflexo no vidro */}
          <div className="absolute inset-0" style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,.12) 0%, transparent 50%, rgba(255,255,255,.04) 100%)',
          }} />
          <RioSkyline skyGradient={skyGradient} showStars={showStars} />
        </div>
      ))}
    </div>
  )
})

/* ── Mesa Premium (SVG detalhado) ── */
const PremiumDesk = memo(function PremiumDesk({ cor, active, isCeo, deskItem }: {
  cor: string; active: boolean; isCeo?: boolean; deskItem?: string
}) {
  const w = isCeo ? 200 : 160
  const h = isCeo ? 90 : 75
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ filter: 'drop-shadow(0 3px 6px var(--office-desk-shadow))' }}>
      {/* Sombra da mesa */}
      <ellipse cx={w/2} cy={h-2} rx={w*.44} ry={7} fill="rgba(0,0,0,.06)" />
      {/* Superfície da mesa */}
      <rect x={4} y={10} width={w-8} height={h-20} rx={5}
        fill="var(--office-desk)" stroke={active ? cor : 'var(--office-desk-edge)'} strokeWidth={active ? 2 : .6} />
      {/* Textura de madeira (5 linhas) */}
      {[16, 24, 32, 40, 48].map(ly => (
        <line key={ly} x1={12} y1={ly} x2={w-12} y2={ly} stroke="var(--office-desk-grain)" strokeWidth=".3" />
      ))}
      {/* Borda brilho superior */}
      <line x1={8} y1={11} x2={w-8} y2={11} stroke="rgba(255,255,255,.06)" strokeWidth=".5" />

      {/* Monitor principal */}
      <rect x={isCeo ? w*.2 : w*.22} y={2} width={isCeo ? w*.25 : w*.38} height={isCeo ? h*.24 : h*.25} rx={2.5}
        fill="var(--office-monitor)" stroke={active ? `${cor}80` : 'var(--office-monitor-bezel)'} strokeWidth={1.2} />
      {/* Tela */}
      <rect x={isCeo ? w*.22 : w*.24} y={4} width={isCeo ? w*.21 : w*.34} height={isCeo ? h*.18 : h*.19} rx={1.5}
        fill={active ? `${cor}18` : 'var(--office-screen-off)'} />
      {active && (
        <g style={{ animation: 'screenGlow 2.5s infinite' }}>
          <rect x={isCeo ? w*.24 : w*.27} y={8} width={w*.12} height={2} rx={.5} fill={`${cor}50`} />
          <rect x={isCeo ? w*.24 : w*.27} y={12} width={w*.18} height={1.5} rx={.5} fill={`${cor}35`} />
          <rect x={isCeo ? w*.24 : w*.27} y={15.5} width={w*.08} height={1.5} rx={.5} fill={`${cor}40`} />
          <rect x={isCeo ? w*.24 : w*.27} y={19} width={w*.14} height={1.5} rx={.5} fill={`${cor}30`} />
        </g>
      )}
      {/* Stand do monitor */}
      <rect x={isCeo ? w*.29 : w*.37} y={isCeo ? h*.24 : h*.25} width={w*.06} height={5} fill="var(--office-monitor-bezel)" />
      <rect x={isCeo ? w*.25 : w*.32} y={isCeo ? h*.24+4 : h*.25+4} width={w*.14} height={2.5} rx={1.2} fill="var(--office-monitor-bezel)" />

      {/* Monitor 2 (CEO) */}
      {isCeo && <>
        <rect x={w*.48} y={3} width={w*.25} height={h*.22} rx={2.5}
          fill="var(--office-monitor)" stroke={active ? `${cor}60` : 'var(--office-monitor-bezel)'} strokeWidth={1} />
        <rect x={w*.50} y={5} width={w*.21} height={h*.16} rx={1.5}
          fill={active ? `${cor}12` : 'var(--office-screen-off)'} />
        <rect x={w*.58} y={h*.22+2} width={w*.06} height={4} fill="var(--office-monitor-bezel)" />
        <rect x={w*.54} y={h*.22+5} width={w*.14} height={2.5} rx={1.2} fill="var(--office-monitor-bezel)" />
      </>}

      {/* Teclado */}
      <rect x={isCeo ? w*.28 : w*.28} y={h-18} width={w*.28} height={10} rx={2.5}
        fill="var(--office-keyboard)" stroke="var(--office-desk-edge)" strokeWidth=".3" />
      {/* Teclas (mini linhas) */}
      {[0,3,6].map(r => (
        <line key={r} x1={isCeo ? w*.30 : w*.30} y1={h-16+r} x2={isCeo ? w*.54 : w*.54} y2={h-16+r}
          stroke="var(--office-desk-edge)" strokeWidth=".2" opacity=".4" />
      ))}
      {/* Mouse */}
      <ellipse cx={isCeo ? w*.64 : w*.66} cy={h-13} rx={5} ry={6.5}
        fill="var(--office-keyboard)" stroke="var(--office-desk-edge)" strokeWidth=".3" />

      {/* Café com vapor */}
      <g>
        <rect x={w-30} y={14} width={9} height={12} rx={2.5} fill="var(--office-mug)" />
        <path d={`M${w-21} ${17} Q${w-16} ${19} ${w-21} ${24}`} stroke="var(--office-mug)" strokeWidth="1.3" fill="none" />
        {active && <>
          <circle cx={w-26} cy={11} r="1.5" fill="rgba(200,200,200,.25)" style={{ animation: 'steam 3s infinite' }} />
          <circle cx={w-24} cy={9} r="1" fill="rgba(200,200,200,.2)" style={{ animation: 'steam 3.5s infinite .5s' }} />
        </>}
      </g>

      {/* Planta pessoal */}
      <g>
        <rect x={10} y={15} width={7} height={9} rx={2} fill="var(--office-pot)" />
        <ellipse cx={13.5} cy={13} rx={4} ry={5} fill="#22c55e" opacity=".5" />
        <ellipse cx={12} cy={10} rx={3} ry={4} fill="#16a34a" opacity=".4" />
      </g>

      {/* Objeto pessoal */}
      {deskItem === 'frame' && <rect x={w-45} y={13} width={8} height={10} rx={1} fill="var(--office-wall-trim)" opacity=".5" />}
      {deskItem === 'book' && <rect x={w-48} y={16} width={12} height={7} rx={1} fill={`${cor}40`} />}
      {deskItem === 'trophy' && <path d={`M${w-46} 24 L${w-44} 14 L${w-40} 14 L${w-38} 24`} fill="#fbbf24" opacity=".5" />}
      {deskItem === 'headphones' && <ellipse cx={w-42} cy={18} rx={5} ry={4} fill="var(--office-monitor)" opacity=".5" stroke="var(--office-monitor-bezel)" strokeWidth=".5" />}

      {/* Nameplate CEO */}
      {isCeo && (
        <g>
          <rect x={w*.38} y={h-8} width={w*.24} height={6} rx={1.5} fill="#fbbf2420" stroke="#fbbf2440" strokeWidth=".5" />
          <text x={w*.5} y={h-3.5} textAnchor="middle" fill="#fbbf24" fontSize="4" fontWeight="bold" letterSpacing=".5">CEO</text>
        </g>
      )}

      {/* Pernas */}
      <rect x={8} y={h-10} width={3.5} height={10} rx={1.5} fill="var(--office-desk-leg)" />
      <rect x={w-11.5} y={h-10} width={3.5} height={10} rx={1.5} fill="var(--office-desk-leg)" />
    </svg>
  )
})

/* ── Cadeira ── */
const Chair = memo(function Chair({ cor, large }: { cor: string; large?: boolean }) {
  const s = large ? 1.3 : 1
  return (
    <svg width={36*s} height={22*s} viewBox="0 0 36 22" className="absolute" style={{ bottom: -14, left: '50%', marginLeft: -18*s }}>
      <ellipse cx="18" cy="12" rx="14" ry="9" fill={`${cor}25`} stroke={`${cor}35`} strokeWidth=".6" />
      <ellipse cx="18" cy="11" rx="11" ry="7" fill={`${cor}15`} />
      {/* Encosto */}
      {large && <ellipse cx="18" cy="5" rx="10" ry="5" fill={`${cor}18`} stroke={`${cor}25`} strokeWidth=".4" />}
    </svg>
  )
})

/* ── Pessoa / Avatar do Agente ── */
const AgentAvatar = memo(function AgentAvatar({ cor, skin, hair, size = 1, status = 'idle' }: {
  cor: string; skin: string; hair: string; size?: number; status?: 'idle' | 'typing' | 'thinking' | 'walking'
}) {
  const s = 28 * size
  const anim = status === 'typing' ? 'typing .6s infinite' : status === 'thinking' ? 'thinking 2.5s infinite' : 'breathe 3.5s infinite'
  return (
    <svg width={s} height={s * 1.55} viewBox="0 0 28 43" style={{
      animation: anim,
      transformOrigin: 'bottom center',
      filter: 'drop-shadow(0 3px 5px rgba(0,0,0,.18))',
      willChange: 'transform',
    }}>
      {/* Sombra no chão */}
      <ellipse cx="14" cy="41" rx="8" ry="2" fill="rgba(0,0,0,.08)" />
      {/* Corpo / Camiseta */}
      <path d="M7.5 20 Q14 17 20.5 20 L21.5 33 Q14 35 6.5 33 Z" fill={`${cor}cc`} />
      {/* Colarinho */}
      <path d="M11 20 Q14 21.5 17 20" stroke={`${cor}88`} strokeWidth=".6" fill="none" />
      {/* Braços */}
      {status === 'typing' ? (
        <>
          <path d="M7.5 21 Q4 25 7 29" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M20.5 21 Q24 25 21 29" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <path d="M7.5 21 Q5 28 7.5 33" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M20.5 21 Q23 28 20.5 33" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
        </>
      )}
      {/* Cabeça */}
      <ellipse cx="14" cy="11" rx="7.5" ry="8" fill={skin} />
      {/* Cabelo */}
      <ellipse cx="14" cy="6.5" rx="7" ry="5" fill={hair} />
      <ellipse cx="8" cy="8" rx="2" ry="3" fill={hair} opacity=".6" />
      <ellipse cx="20" cy="8" rx="2" ry="3" fill={hair} opacity=".6" />
      {/* Olhos */}
      <circle cx="10.5" cy="12" r="1" fill="#1a1a1a" />
      <circle cx="17.5" cy="12" r="1" fill="#1a1a1a" />
      {/* Brilho dos olhos */}
      <circle cx="11" cy="11.5" r=".3" fill="white" />
      <circle cx="18" cy="11.5" r=".3" fill="white" />
      {/* Boca */}
      <path d="M11.5 15 Q14 16.5 16.5 15" stroke="#1a1a1a" strokeWidth=".5" fill="none" />
      {/* Bolha de pensamento */}
      {status === 'thinking' && (
        <g opacity=".7">
          <ellipse cx="24" cy="4" rx="6" ry="4" fill="white" stroke="var(--office-desk-edge)" strokeWidth=".4" />
          <circle cx="22" cy="3.5" r="1" fill="var(--office-desk-edge)" opacity=".4" />
          <circle cx="24.5" cy="3.5" r="1" fill="var(--office-desk-edge)" opacity=".4" />
          <circle cx="27" cy="3.5" r="1" fill="var(--office-desk-edge)" opacity=".4" />
          <circle cx="20" cy="8" r="1.5" fill="white" stroke="var(--office-desk-edge)" strokeWidth=".3" />
          <circle cx="19" cy="11" r="1" fill="white" stroke="var(--office-desk-edge)" strokeWidth=".2" />
        </g>
      )}
    </svg>
  )
})

/* ── Planta Decorativa ── */
const Plant = memo(function Plant({ x, y, size = 1, delay = 0 }: { x: number; y: number; size?: number; delay?: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y, animation: `leafSway ${5 + delay}s infinite ease-in-out ${delay}s`, transformOrigin: 'bottom center' }}>
      <svg width={20 * size} height={34 * size} viewBox="0 0 20 34">
        <rect x="7" y="22" width="6" height="12" rx="2.5" fill="var(--office-pot)" />
        <rect x="5" y="21" width="10" height="3" rx="1.5" fill="var(--office-pot)" opacity=".8" />
        <ellipse cx="10" cy="20" rx="6" ry="3.5" fill="#4ade80" opacity=".5" />
        <ellipse cx="8" cy="16" rx="5" ry="6" fill="#22c55e" opacity=".6" />
        <ellipse cx="13" cy="13" rx="4.5" ry="6" fill="#16a34a" opacity=".55" />
        <ellipse cx="10" cy="10" rx="3.5" ry="5" fill="#15803d" opacity=".7" />
      </svg>
    </div>
  )
})

/* ── Luminária de Chão ── */
const FloorLamp = memo(function FloorLamp({ x, y, lampOpacity }: { x: number; y: number; lampOpacity: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="20" height="50" viewBox="0 0 20 50">
        <rect x="9" y="16" width="2" height="30" fill="var(--office-lamp-pole)" />
        <ellipse cx="10" cy="46" rx="6" ry="2.5" fill="var(--office-lamp-pole)" opacity=".4" />
        <path d="M3 16 L10 3 L17 16 Z" fill="var(--office-lamp-shade)" />
        {/* Luz */}
        <circle cx="10" cy="14" r="3.5" fill="#fbbf24" opacity={lampOpacity} />
        <circle cx="10" cy="20" r="12" fill="#fbbf24" opacity={lampOpacity * 0.08} />
      </svg>
    </div>
  )
})

/* ── Tapete ── */
const Rug = memo(function Rug({ x, y, w, h }: { x: number; y: number; w: number; h: number }) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: x, top: y, width: w, height: h, borderRadius: 12,
      background: 'var(--office-rug)',
      border: '1px solid var(--office-glass-edge)',
    }} />
  )
})

/* ── Relógio de Parede ── */
const WallClock = memo(function WallClock({ x, y }: { x: number; y: number }) {
  const now = new Date()
  const hDeg = (now.getHours() % 12 + now.getMinutes() / 60) * 30
  const mDeg = now.getMinutes() * 6
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y, zIndex: 2 }}>
      <svg width="28" height="28" viewBox="0 0 28 28">
        <circle cx="14" cy="14" r="12" fill="var(--office-wall)" stroke="var(--office-clock)" strokeWidth="1.5" />
        <circle cx="14" cy="14" r="1" fill="var(--office-clock)" />
        {/* Hora */}
        <line x1="14" y1="14" x2="14" y2="7" stroke="var(--office-clock)" strokeWidth="1.2" strokeLinecap="round"
          transform={`rotate(${hDeg} 14 14)`} />
        {/* Minuto */}
        <line x1="14" y1="14" x2="14" y2="4.5" stroke="var(--office-clock)" strokeWidth=".8" strokeLinecap="round"
          transform={`rotate(${mDeg} 14 14)`} />
        {/* Segundo (animado via CSS) */}
        <line x1="14" y1="14" x2="14" y2="3.5" stroke="#ef4444" strokeWidth=".4" strokeLinecap="round"
          style={{ transformOrigin: '14px 14px', animation: 'clockSecond 60s linear infinite' }} />
      </svg>
    </div>
  )
})

/* ── Bebedouro ── */
const WaterCooler = memo(function WaterCooler({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="22" height="44" viewBox="0 0 22 44">
        {/* Base */}
        <rect x="4" y="20" width="14" height="20" rx="2" fill="var(--office-keyboard)" stroke="var(--office-desk-edge)" strokeWidth=".4" />
        {/* Galão */}
        <ellipse cx="11" cy="18" rx="6" ry="3" fill="rgba(100,180,255,.15)" stroke="rgba(100,180,255,.25)" strokeWidth=".5" />
        <rect x="6" y="6" width="10" height="12" rx="4" fill="rgba(100,180,255,.1)" stroke="rgba(100,180,255,.2)" strokeWidth=".5" />
        {/* Bolha */}
        <circle cx="11" cy="12" r="1.5" fill="rgba(100,180,255,.2)" style={{ animation: 'bubbleRise 4s infinite 1s' }} />
        <circle cx="9" cy="10" r="1" fill="rgba(100,180,255,.15)" style={{ animation: 'bubbleRise 5s infinite 2.5s' }} />
        {/* Torneira */}
        <rect x="15" y="24" width="4" height="3" rx="1" fill="var(--office-lamp-pole)" />
      </svg>
    </div>
  )
})

/* ── Quadro na Parede ── */
const WallArt = memo(function WallArt({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y, zIndex: 2 }}>
      <svg width="36" height="26" viewBox="0 0 36 26">
        <rect x="1" y="1" width="34" height="24" rx="1.5" fill="var(--office-wall)" stroke="var(--office-desk-edge)" strokeWidth=".8" />
        <rect x="3" y="3" width="30" height="20" rx="1" fill={`${color}08`} />
        {/* Arte abstrata */}
        <circle cx="12" cy="13" r="5" fill={`${color}15`} />
        <circle cx="22" cy="11" r="3.5" fill={`${color}20`} />
        <line x1="8" y1="18" x2="28" y2="8" stroke={`${color}25`} strokeWidth="1" />
      </svg>
    </div>
  )
})

/* ── Máquina de Café (ao lado da sala de reunião) ── */
const CoffeeMachine = memo(function CoffeeMachine({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="30" height="50" viewBox="0 0 30 50">
        {/* Corpo */}
        <rect x="4" y="10" width="22" height="32" rx="3" fill="var(--office-monitor)" stroke="var(--office-monitor-bezel)" strokeWidth=".6" />
        {/* Tela */}
        <rect x="8" y="14" width="14" height="6" rx="1" fill="#10b98120" />
        {/* Bandeja */}
        <rect x="6" y="36" width="18" height="3" rx="1" fill="var(--office-desk-edge)" />
        {/* Xícara */}
        <rect x="10" y="32" width="6" height="5" rx="1.5" fill="var(--office-mug)" opacity=".6" />
        {/* Vapor */}
        <circle cx="13" cy="28" r="1.5" fill="rgba(200,200,200,.2)" style={{ animation: 'steam 3s infinite' }} />
        <circle cx="15" cy="26" r="1" fill="rgba(200,200,200,.15)" style={{ animation: 'steam 4s infinite .8s' }} />
        {/* Botões */}
        <circle cx="10" cy="24" r="1.5" fill="#10b981" opacity=".5" />
        <circle cx="15" cy="24" r="1.5" fill="#3b82f6" opacity=".3" />
        <circle cx="20" cy="24" r="1.5" fill="#f59e0b" opacity=".3" />
        {/* Label */}
        <text x="15" y="48" textAnchor="middle" fill="var(--office-clock)" fontSize="3.5" opacity=".5">COFFEE</text>
      </svg>
    </div>
  )
})

/* =====================================================================
   [E] COMPONENTE PRINCIPAL — ESCRITÓRIO VIRTUAL
   ===================================================================== */

export default function Escritorio() {
  const { abrirChat, abrirReuniao } = useChatManager()
  const { usuario } = useAuth()
  const dayNight = useDayNightCycle()
  const fetchSquads = useCallback(() => buscarSquads(), [])
  const fetchTarefas = useCallback(() => buscarHistoricoTarefas(20), [])
  const { dados: squadsData } = usePolling(fetchSquads, 15000)
  const { dados: tarefasData } = usePolling(fetchTarefas, 3000)

  const [hovered, setHovered] = useState<number | null>(null)
  const [visitando, setVisitando] = useState<number | null>(null)
  const [emReuniao, setEmReuniao] = useState(false)
  const [squadSelecionado, setSquadSelecionado] = useState<string | null>(null)
  const [mostrarSeletor, setMostrarSeletor] = useState(false)
  const [videoCall, setVideoCall] = useState<{ sala: string; participantes: string[] } | null>(null)

  const squads = (squadsData || []) as SquadComMeta[]
  const tarefas = (tarefasData || []) as TarefaResultado[]
  const squadsPessoais = squads.filter(s => s.tipo === 'pessoal')
  const temVisaoGeral = squadsPessoais.length > 1
  const meuSquadOriginal = squads.find(s => s.is_meu)
  const verTodos = squadSelecionado === '__todos__'
  const meuSquad = verTodos ? meuSquadOriginal : squadSelecionado ? squads.find(s => s.nome === squadSelecionado) || meuSquadOriginal : meuSquadOriginal
  const nomeUsuario = meuSquad?.is_meu ? (usuario?.nome || 'Usuário') : (meuSquad?.nome.split('—')[1]?.trim() || 'Usuário')

  const agentes = useMemo(() => {
    if (!meuSquad) return []
    return meuSquad.nomes_agentes.map((n, i) => agCfg(i, n))
  }, [meuSquad?.nomes_agentes?.join(',')])

  const getStatus = useCallback((i: number): 'livre' | 'trabalhando' | 'reuniao' => {
    if (!meuSquad) return 'livre'
    if (emReuniao) return 'reuniao'
    if (visitando === i) return 'reuniao'
    if (tarefas.find(t => t.squad_nome === meuSquad.nome && t.agente_indice === i && t.status === 'executando')) return 'trabalhando'
    return 'livre'
  }, [meuSquad, emReuniao, visitando, tarefas])

  const getPos = useCallback((i: number) => {
    if (emReuniao) {
      const chair = MEET_CHAIRS[i % MEET_CHAIRS.length]
      return { x: MEET_CENTER.x + chair.x, y: MEET_CENTER.y + chair.y }
    }
    if (visitando === i) return CEO_SIDE
    return DK[i] || DK[0]
  }, [emReuniao, visitando])

  const handleClick = useCallback((i: number) => {
    if (emReuniao) return
    if (visitando === i) { setVisitando(null); return }
    setVisitando(i)
    if (meuSquad) abrirChat(meuSquad.nome, i, meuSquad.nomes_agentes[i] || `Agente ${i + 1}`)
  }, [emReuniao, visitando, meuSquad, abrirChat])

  const handleReunir = useCallback(() => {
    if (emReuniao) { setEmReuniao(false); setVisitando(null) }
    else {
      setVisitando(null); setEmReuniao(true)
      if (meuSquad) abrirReuniao(meuSquad.nome, meuSquad.nomes_agentes.map((n, i) => ({ idx: i, nome: n })))
    }
  }, [emReuniao, meuSquad, abrirReuniao])

  if (!meuSquad) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
    </div>
  )

  const statusColor = (st: string) => st === 'trabalhando' ? '#3b82f6' : st === 'reuniao' ? '#f59e0b' : '#10b981'
  const statusLabel = (st: string) => st === 'trabalhando' ? 'Trabalhando' : st === 'reuniao' ? 'Em reunião' : 'Disponível'

  return (
    <div className="sf-page overflow-hidden select-none" style={{ margin: '-24px', padding: 0, minHeight: '100vh' }}
      onClick={() => mostrarSeletor && setMostrarSeletor(false)}>
      <style>{CSS}{themeCSS}</style>

      {/* ── Header ── */}
      <div className="relative z-10 flex items-center justify-between px-8 pt-5 pb-3">
        <div>
          <h2 className="text-2xl font-bold sf-text-white" style={{ letterSpacing: '-0.02em' }}>
            Escritório Virtual
          </h2>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-xs sf-text-dim">{meuSquad.nome} · {meuSquad.num_agentes} agentes</p>
            {/* Indicador dia/noite */}
            <span className="text-[9px] sf-text-ghost px-2 py-0.5 rounded-md" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-subtle)' }}>
              {dayNight.fase === 'dia' ? '☀️' : dayNight.fase === 'noite' ? '🌙' : dayNight.fase === 'amanhecer' ? '🌅' : '🌇'} {dayNight.fase}
            </span>
            {temVisaoGeral && (
              <div className="relative">
                <button onClick={() => setMostrarSeletor(!mostrarSeletor)}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-medium bg-purple-500/15 text-purple-400 border border-purple-500/25 hover:bg-purple-500/25 transition-all">
                  <Eye size={10} />{squadSelecionado ? 'Visão Geral' : 'Ver outros squads'}<ChevronDown size={10} />
                </button>
                {mostrarSeletor && (
                  <div className="absolute top-full left-0 mt-1 rounded-xl shadow-2xl py-1 z-30 min-w-[220px]" style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>
                    <button onClick={() => { setSquadSelecionado('__todos__'); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                      className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${verTodos ? 'text-purple-400 bg-purple-500/10' : 'sf-text-dim hover:bg-white/5'}`}>
                      <Eye size={11} /> Ver todos
                    </button>
                    <div className="mx-3 my-1" style={{ borderTop: '1px solid var(--sf-border-subtle)' }} />
                    <button onClick={() => { setSquadSelecionado(null); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                      className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${!squadSelecionado ? 'text-emerald-400 bg-emerald-500/10' : 'sf-text-dim hover:bg-white/5'}`}>
                      <Crown size={11} /> {meuSquadOriginal?.nome || 'Meu Squad'}
                    </button>
                    {squadsPessoais.filter(s => !s.is_meu).map(s => (
                      <button key={s.nome} onClick={() => { setSquadSelecionado(s.nome); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                        className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${squadSelecionado === s.nome ? 'text-purple-400 bg-purple-500/10' : 'sf-text-dim hover:bg-white/5'}`}>
                        <User size={11} /> {s.nome} <span className="ml-auto text-[9px] sf-text-ghost">{s.num_agentes}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {squadSelecionado && (
              <button onClick={() => { setSquadSelecionado(null); setVisitando(null); setEmReuniao(false) }}
                className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20">
                Voltar ao meu squad
              </button>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setVideoCall({ sala: `sf-${Date.now()}`, participantes: [usuario?.nome || 'CEO', 'Jonatas'] })}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/20 hover:bg-blue-500/25 transition-all"
          >
            <Video size={13} /> Video Call
          </button>
          <button onClick={handleReunir} className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${emReuniao ? 'bg-red-500/15 text-red-400 border border-red-500/20' : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'}`}>
            {emReuniao ? <><X size={13} /> Encerrar Reunião</> : <><Users size={13} /> Reunir todos</>}
          </button>
        </div>
      </div>

      {/* ── Ver Todos (grid de squads) ── */}
      {verTodos && (
        <div className="px-8 pb-8 overflow-y-auto" style={{ height: 'calc(100vh - 120px)' }}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {squadsPessoais.map(sq => (
              <div key={sq.nome} className="rounded-2xl p-5 cursor-pointer hover:-translate-y-0.5 transition-all"
                style={{ background: 'var(--sf-bg-2)', border: `1px solid ${sq.is_meu ? 'rgba(16,185,129,.3)' : 'var(--sf-border-default)'}` }}
                onClick={() => { setSquadSelecionado(sq.nome); setVisitando(null); setEmReuniao(false) }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: sq.is_meu ? 'rgba(16,185,129,.15)' : 'rgba(139,92,246,.15)' }}>
                    {sq.is_meu ? <Crown size={18} className="text-emerald-400" /> : <User size={18} className="text-purple-400" />}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold sf-text-white">{sq.nome}</h3>
                    <p className="text-[10px] sf-text-dim">{sq.especialidade}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {sq.nomes_agentes.map((n, i) => {
                    const a = agCfg(i, n)
                    return (
                      <div key={i} className="flex flex-col items-center">
                        <AgentAvatar cor={a.cor} skin={a.skin} hair={a.hair} size={.55} />
                        <p className="text-[6px] sf-text-ghost mt-0.5">{a.nome}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          OFFICE SCENE — O coração do escritório
          ═══════════════════════════════════════════════════════════════ */}
      {!verTodos && (
        <div className="relative w-full overflow-x-auto overflow-y-auto" style={{ height: 'calc(100vh - 100px)' }}>
          <div className="relative mx-auto" style={{ width: 1600, height: 750, minWidth: 1600 }}>

            {/* Piso */}
            <PremiumFloor />

            {/* Overlay de iluminação ambiente (dia/noite) */}
            <div className="absolute inset-0 pointer-events-none" style={{ background: dayNight.ambientOverlay, zIndex: 60 }} />

            {/* Parede traseira com janelas do Rio */}
            <BackWall skyGradient={dayNight.skyGradient} showStars={dayNight.showStars} />

            {/* Relógio na parede */}
            <WallClock x={50} y={26} />

            {/* Quadros na parede */}
            <WallArt x={170} y={18} color="#8b5cf6" />
            <WallArt x={480} y={22} color="#3b82f6" />

            {/* Tapetes */}
            <Rug x={310} y={100} w={490} h={150} />
            <Rug x={310} y={280} w={490} h={150} />
            <Rug x={310} y={460} w={490} h={150} />

            {/* Plantas decorativas */}
            <Plant x={40} y={90} size={1.5} delay={0} />
            <Plant x={280} y={80} size={1.1} delay={.8} />
            <Plant x={880} y={85} size={1.3} delay={1.2} />
            <Plant x={40} y={500} size={1.2} delay={.4} />
            <Plant x={280} y={440} size={1} delay={1.6} />
            <Plant x={880} y={540} size={1.1} delay={.6} />
            <Plant x={1540} y={90} size={1.4} delay={2} />
            <Plant x={1540} y={620} size={1.2} delay={1} />

            {/* Luminárias */}
            <FloorLamp x={250} y={60} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={860} y={60} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={250} y={580} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={860} y={580} lampOpacity={dayNight.lampOpacity} />

            {/* Bebedouro */}
            <WaterCooler x={920} y={280} />

            {/* ── CEO DESK ── */}
            <div className="absolute" style={{ left: CEO_POS.x - 30, top: CEO_POS.y - 20, zIndex: 25 }}>
              {/* Glow */}
              <div className="absolute -inset-10 rounded-3xl" style={{ background: 'radial-gradient(ellipse,rgba(16,185,129,.06) 0%,transparent 70%)' }} />

              {/* Badge CEO */}
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                style={{ background: 'var(--sf-accent-dim)', border: '1px solid rgba(16,185,129,.3)' }}>
                <Crown size={10} className="text-emerald-400" />
                <span className="text-[10px] font-bold text-emerald-400 tracking-widest">CEO</span>
              </div>

              <PremiumDesk cor="#10b981" active isCeo />
              <Chair cor="#10b981" large />

              {/* CEO Avatar */}
              <div className="absolute" style={{ left: 72, top: -42 }}>
                <AgentAvatar cor="#10b981" skin="#f5cba7" hair="#3d2b1f" size={1.1} status={visitando === null && !emReuniao ? 'typing' : 'idle'} />
              </div>

              {/* Nome do CEO */}
              <div className="absolute -bottom-14 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                <p className="text-[14px] font-bold text-emerald-500">{nomeUsuario}</p>
                <p className="text-[10px] sf-text-dim">Sua mesa</p>
              </div>

              {/* Agente visitando (ao lado do CEO) */}
              <AnimatePresence>
                {visitando !== null && !emReuniao && (() => {
                  const v = agentes[visitando]
                  if (!v) return null
                  return (
                    <motion.div className="absolute" style={{ left: 165, top: -30, zIndex: 40 }}
                      initial={{ opacity: 0, scale: .5 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: .5 }}
                      transition={{ duration: .4, ease: 'backOut' }}>
                      <AgentAvatar cor={v.cor} skin={v.skin} hair={v.hair} />
                      <motion.div className="absolute -top-7 left-1/2 -translate-x-1/2"
                        initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: .3, type: 'spring' }}>
                        <div className="flex items-center gap-1 px-2.5 py-1 rounded-full" style={{
                          background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)',
                          animation: 'floatBadge 2s infinite ease-in-out',
                        }}>
                          <MessageSquare size={8} className="text-emerald-400" />
                          <span className="text-[8px] text-emerald-400 font-semibold">Chat</span>
                        </div>
                      </motion.div>
                      <p className="text-[8px] font-semibold text-center mt-1" style={{ color: v.cor }}>{v.nome}</p>
                    </motion.div>
                  )
                })()}
              </AnimatePresence>
            </div>

            {/* ── SALA DE REUNIÃO ── */}
            <div className="absolute" style={{ left: MEET_CENTER.x - 200, top: MEET_CENTER.y - 210, width: 420, height: 480, zIndex: 5 }}>
              {/* Paredes de vidro */}
              <div className="absolute inset-0 rounded-2xl transition-all duration-700" style={{
                border: emReuniao ? '2.5px solid rgba(16,185,129,.3)' : '1.5px solid var(--office-glass-edge)',
                background: emReuniao ? 'rgba(16,185,129,.02)' : 'var(--office-glass)',
                boxShadow: emReuniao ? '0 0 35px rgba(16,185,129,.08), inset 0 0 25px rgba(16,185,129,.02)' : 'none',
                backdropFilter: 'blur(1.5px)',
                animation: emReuniao ? 'meetGlow 3s infinite' : 'none',
              }}>
                {/* Reflexos no vidro */}
                <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl" style={{ background: 'linear-gradient(90deg,transparent,var(--office-glass-reflect),transparent)' }} />
                <div className="absolute top-0 bottom-0 left-0 w-[2px] rounded-l-2xl" style={{ background: 'linear-gradient(180deg,transparent,var(--office-glass-reflect),transparent)' }} />
                <div className="absolute inset-0 rounded-2xl" style={{ background: 'linear-gradient(135deg, var(--office-glass-reflect), transparent 60%)' }} />
              </div>

              {/* Tapete da sala */}
              <div className="absolute rounded-xl" style={{ left: 20, top: 30, right: 20, bottom: 20, background: 'var(--office-carpet)', borderRadius: 14 }} />

              {/* Spots de luz */}
              {[100, 210, 320].map((sx, si) => (
                <div key={si} className="absolute pointer-events-none" style={{
                  left: sx - 25, top: 10, width: 50, height: 50, borderRadius: '50%',
                  background: emReuniao ? 'radial-gradient(circle, rgba(16,185,129,.08) 0%, transparent 70%)' : 'radial-gradient(circle, rgba(255,255,255,.03) 0%, transparent 70%)',
                  animation: emReuniao ? 'spotPulse 4s infinite' : 'none',
                }} />
              ))}

              {/* Mesa oval grande */}
              <svg className="absolute pointer-events-none" style={{ left: 65, top: 150 }} width="290" height="150" viewBox="0 0 290 150">
                <ellipse cx="145" cy="80" rx="130" ry="60" fill="rgba(0,0,0,.06)" />
                <ellipse cx="145" cy="75" rx="125" ry="56" fill="var(--office-desk)" stroke="var(--office-desk-edge)" strokeWidth="1" />
                <ellipse cx="145" cy="75" rx="100" ry="42" fill="none" stroke="var(--office-desk-grain)" strokeWidth=".5" />
                <ellipse cx="145" cy="75" rx="70" ry="28" fill="none" stroke="var(--office-desk-grain)" strokeWidth=".3" />
                {emReuniao && (
                  <g>
                    <rect x="80" y="50" width="18" height="12" rx="2" fill="var(--office-monitor)" opacity=".7" />
                    <rect x="130" y="48" width="14" height="18" rx="1" fill="var(--office-keyboard)" opacity=".35" />
                    <circle cx="65" cy="60" r="4" fill="var(--office-mug)" opacity=".5" />
                    <circle cx="200" cy="65" r="3.5" fill="var(--office-mug)" opacity=".4" />
                    <line x1="160" y1="70" x2="175" y2="73" stroke="var(--office-lamp-pole)" strokeWidth="1.2" strokeLinecap="round" />
                  </g>
                )}
              </svg>

              {/* Cadeiras */}
              {MEET_CHAIRS.slice(0, Math.max(meuSquad.num_agentes + 1, 8)).map((ch, ci) => (
                <svg key={ci} className="absolute pointer-events-none" style={{ left: 200 + ch.x - 12, top: 220 + ch.y - 10 }} width="28" height="20" viewBox="0 0 28 20">
                  <ellipse cx="14" cy="10" rx="11" ry="8"
                    fill={emReuniao && ci < meuSquad.num_agentes ? `${CORES[ci % CORES.length]}25` : 'var(--office-keyboard)'}
                    stroke={emReuniao && ci < meuSquad.num_agentes ? `${CORES[ci % CORES.length]}45` : 'var(--office-desk-edge)'}
                    strokeWidth=".5" opacity=".7" />
                </svg>
              ))}

              {/* Telão */}
              <div className="absolute" style={{ left: 95, top: 20 }}>
                <svg width="230" height="45" viewBox="0 0 230 45">
                  <rect x="20" y="2" width="150" height="28" rx="3" fill={emReuniao ? 'var(--office-monitor)' : 'var(--office-screen-off)'}
                    stroke={emReuniao ? 'rgba(16,185,129,.4)' : 'var(--office-monitor-bezel)'} strokeWidth="1.2" />
                  {emReuniao ? (
                    <g>
                      <rect x="28" y="8" width="50" height="2.5" rx={.5} fill="#10b98150" style={{ animation: 'screenGlow 2s infinite' }} />
                      <rect x="28" y="13" width="75" height="2" rx={.5} fill="#10b98135" style={{ animation: 'screenGlow 2.5s infinite .3s' }} />
                      <rect x="28" y="17.5" width="38" height="2" rx={.5} fill="#10b98140" style={{ animation: 'screenGlow 3s infinite .6s' }} />
                      <rect x="28" y="22" width="60" height="2" rx={.5} fill="#10b98130" style={{ animation: 'screenGlow 2s infinite .9s' }} />
                      <circle cx="160" cy="8" r="3" fill="#ef4444" opacity=".8">
                        <animate attributeName="opacity" values=".3;.9;.3" dur="1.5s" repeatCount="indefinite" />
                      </circle>
                      <text x="160" y="18" textAnchor="middle" fill="#ef4444" fontSize="4" opacity=".6">REC</text>
                    </g>
                  ) : (
                    <text x="95" y="20" textAnchor="middle" fill="var(--office-desk-edge)" fontSize="6" opacity=".3">DISPLAY</text>
                  )}
                  <rect x="88" y="30" width="14" height="5" fill="var(--office-monitor-bezel)" />
                </svg>
              </div>

              {/* Plantas na sala */}
              <Plant x={15} y={20} size={.8} delay={2.5} />
              <Plant x={385} y={420} size={.85} delay={3} />

              {/* Label */}
              <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                {emReuniao ? (
                  <div className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/25">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] font-semibold text-emerald-400">Reunião Ativa</span>
                    <span className="text-[9px] sf-text-ghost">· {meuSquad.num_agentes} agentes</span>
                  </div>
                ) : (
                  <p className="text-[9px] sf-text-ghost">Sala de Reunião</p>
                )}
              </div>
            </div>

            {/* Máquina de café */}
            <CoffeeMachine x={MEET_CENTER.x + 240} y={MEET_CENTER.y + 100} />

            {/* ── MESAS DOS AGENTES ── */}
            {DK.map((d, i) => {
              if (i >= meuSquad.num_agentes) return null
              const a = agentes[i]
              if (!a) return null
              const st = getStatus(i)
              const isH = hovered === i
              const isV = visitando === i
              const tp = getPos(i)
              const sc = statusColor(st)

              return (
                <div key={i}>
                  {/* Mesa fixa */}
                  <div className="absolute" style={{ left: d.x - 20, top: d.y, zIndex: 10 + Math.floor(d.y / 20) }}>
                    <PremiumDesk cor={a.cor} active={(isH || st === 'trabalhando') && !isV && !emReuniao} deskItem={a.item} />
                    <Chair cor={a.cor} />

                    {/* Nome e status */}
                    <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                      <p className="text-[13px] font-bold" style={{
                        color: isV || emReuniao ? 'var(--sf-text-4)' : isH ? a.cor : 'var(--sf-text-1)',
                        letterSpacing: '0.01em', transition: 'color .2s',
                      }}>{a.nome}</p>
                      <p className="text-[9px] sf-text-dim" style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {a.label}
                      </p>
                      <div className="flex items-center justify-center gap-1.5 mt-1">
                        <div className="w-[6px] h-[6px] rounded-full" style={{
                          backgroundColor: sc,
                          boxShadow: st !== 'livre' ? `0 0 8px ${sc}70` : 'none',
                          opacity: isV || emReuniao ? .3 : 1,
                          transition: 'all .3s',
                        }} />
                        <span className="text-[8px]" style={{ color: sc, opacity: isV || emReuniao ? .3 : .7 }}>
                          {statusLabel(st)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Agente animado (Framer Motion) */}
                  <motion.div className="absolute cursor-pointer" style={{ zIndex: isH ? 50 : 20 + i }}
                    animate={{
                      x: tp.x + 38,
                      y: tp.y - 32,
                      scale: isH && !isV && !emReuniao ? 1.15 : 1,
                    }}
                    transition={{
                      type: 'spring', stiffness: emReuniao ? 60 : 80, damping: emReuniao ? 20 : 16, mass: emReuniao ? 1 : .7,
                      delay: emReuniao ? i * 0.08 : 0,
                    }}
                    onMouseEnter={() => setHovered(i)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => handleClick(i)}>
                    <AgentAvatar cor={a.cor} skin={a.skin} hair={a.hair}
                      status={st === 'trabalhando' && !isV && !emReuniao ? 'typing' : emReuniao ? 'idle' : 'idle'} />
                    {/* Tooltip "Chamar" ao hover */}
                    <AnimatePresence>
                      {isH && !isV && !emReuniao && (
                        <motion.div className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap"
                          initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}>
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg" style={{
                            background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)',
                            boxShadow: '0 4px 12px rgba(0,0,0,.15)',
                          }}>
                            <MessageSquare size={8} className="text-emerald-400" />
                            <span className="text-[8px] text-emerald-400 font-semibold">Chamar</span>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                </div>
              )
            })}

          </div>
        </div>
      )}

      {/* Video Call Modal */}
      {videoCall && (
        <ReuniaoVideo sala={videoCall.sala} participantes={videoCall.participantes} onFechar={() => setVideoCall(null)} />
      )}

      {/* ── Legend Bar ── */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-6 px-6 py-3 rounded-2xl"
        style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)', backdropFilter: 'blur(16px)', boxShadow: '0 8px 30px rgba(0,0,0,.12)' }}>
        <span className="flex items-center gap-2 text-[10px] sf-text-dim">
          <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(16,185,129,.4)' }} /> Disponível
        </span>
        <span className="flex items-center gap-2 text-[10px] sf-text-dim">
          <span className="w-2.5 h-2.5 bg-blue-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(59,130,246,.4)' }} /> Trabalhando
        </span>
        <span className="flex items-center gap-2 text-[10px] sf-text-dim">
          <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(245,158,11,.4)' }} /> Em reunião
        </span>
        {visitando !== null && <>
          <span className="sf-text-ghost">·</span>
          <button onClick={() => setVisitando(null)} className="text-[10px] sf-text-dim hover:text-emerald-400 transition-colors">
            Dispensar {agentes[visitando]?.nome}
          </button>
        </>}
      </div>
    </div>
  )
}
