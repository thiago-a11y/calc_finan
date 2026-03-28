/* =====================================================================
   Escritório Virtual — 3D Isométrico Premium
   Perspectiva isométrica real via CSS 3D transforms, camadas em Z,
   sombras cinematográficas, piso de madeira com reflexo, paredes de
   vidro translúcidas — visual big-tech / Apple + Linear + Arc.
   v0.31.0 — Synerium Factory
   ===================================================================== */

import { useCallback, useState, useMemo, useEffect, memo } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarSquads, buscarHistoricoTarefas } from '../services/api'
import { useChatManager } from '../components/ChatManager'
import type { TarefaResultado } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { Users, MessageSquare, Crown, X, User, Eye, ChevronDown, Video, Zap } from 'lucide-react'
import ReuniaoVideo from '../components/ReuniaoVideo'
import AgentAvatarPhoto from '../components/AgentAvatar'
import { buscarAgente } from '../config/agents'
import { motion, AnimatePresence } from 'framer-motion'

/* =====================================================================
   [A] CONSTANTES, TIPOS E CONFIGS
   ===================================================================== */

interface SquadComMeta {
  nome: string; especialidade: string; contexto: string
  num_agentes: number; num_tarefas: number; nomes_agentes: string[]
  proprietario_email?: string; tipo?: string; is_meu?: boolean
}

/* Paleta por agente */
const CORES = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ec4899','#6366f1','#ef4444','#14b8a6','#d946ef','#f97316','#06b6d4','#84cc16']
const SKINS = ['#f5d0a9','#8d5524','#c68642','#f5d0a9','#a0522d','#f5cba7','#c68642','#f5cba7','#c68642','#f5d0a9','#8d5524','#f5cba7']
const HAIRS = ['#1a1a2e','#0a0a0a','#2d1810','#0a0a0a','#1a0a00','#b8860b','#0a0a0a','#3d2b1f','#1a0a00','#1a1a2e','#0a0a0a','#3d2b1f']
const DESK_ITEMS = ['frame','book','trophy','cactus','globe','mug2','headphones','figurine','candle']

function agCfg(i: number, name: string) {
  const label = name.split('/')[0]?.trim() || name
  // Usa o nome completo para buscar o agente correto (ex: "Desenvolvedor Backend PHP" → Amara)
  const agente = buscarAgente(name)
  return {
    nome: agente?.nome || label.split(' ')[0] || `Ag${i+1}`,
    nomeCompleto: name,
    label,
    cor: CORES[i % CORES.length],
    skin: SKINS[i % SKINS.length],
    hair: HAIRS[i % HAIRS.length],
    item: DESK_ITEMS[i % DESK_ITEMS.length],
  }
}

/* Posições do grid — em coordenadas isométricas (plano X/Y) */
const DK = [
  { x: 340, y: 160 }, { x: 540, y: 160 }, { x: 740, y: 160 },
  { x: 340, y: 340 }, { x: 540, y: 340 }, { x: 740, y: 340 },
  { x: 340, y: 520 }, { x: 540, y: 520 }, { x: 740, y: 520 },
]
const CEO_POS = { x: 80, y: 310 }
const CEO_SIDE = { x: 210, y: 280 }
const MEET_CENTER = { x: 1180, y: 350 }
const MEET_CHAIRS = [
  { x: -120, y: -60 }, { x: -60, y: -95 }, { x: 20, y: -100 }, { x: 100, y: -85 }, { x: 150, y: -45 },
  { x: 150, y: 45 }, { x: 100, y: 85 }, { x: 20, y: 100 }, { x: -60, y: 95 }, { x: -120, y: 60 },
  { x: -145, y: 0 }, { x: 175, y: 0 },
]

/* =====================================================================
   [B] CSS KEYFRAMES + THEME VARS
   ===================================================================== */

const CSS = `
/* Animações de personagens */
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
@keyframes monitorFlicker{0%,100%{opacity:1}97%{opacity:1}98%{opacity:.85}99%{opacity:1}}

/* Reflexo suave no piso (gradiente de cima para baixo) */
@keyframes floorReflect{0%,100%{opacity:.03}50%{opacity:.06}}

/* Luz pontual pulsando */
@keyframes lightPulse{0%,100%{opacity:.15}50%{opacity:.4}}
`

const themeCSS = `
:root {
  --of-bg: #f5f0ea;
  --of-floor: linear-gradient(165deg, #e8ddd0 0%, #d4c8b8 40%, #cfc2b0 100%);
  --of-floor-plank: rgba(0,0,0,.025);
  --of-floor-grain: rgba(0,0,0,.012);
  --of-floor-reflect: rgba(255,255,255,.12);
  --of-wall: #eee8df;
  --of-wall-trim: #c9b99a;
  --of-wall-shadow: 0 6px 30px rgba(0,0,0,.08);
  --of-desk: #c69c6d;
  --of-desk-dark: #a07d5a;
  --of-desk-top: linear-gradient(135deg, #d4a87c 0%, #c69c6d 50%, #b08a5c 100%);
  --of-desk-shadow: 0 8px 24px rgba(0,0,0,.12);
  --of-desk-leg: #8a6844;
  --of-monitor: #1e1e22;
  --of-monitor-bezel: #2a2a30;
  --of-screen-off: #111114;
  --of-keyboard: #e2e0dc;
  --of-mug: #c75050;
  --of-pot: #b07050;
  --of-lamp-pole: #aaa;
  --of-lamp-shade: #f5e6d3;
  --of-lamp-glow: rgba(255,200,100,.25);
  --of-glass: rgba(200,220,255,.06);
  --of-glass-edge: rgba(200,220,255,.12);
  --of-glass-reflect: rgba(255,255,255,.08);
  --of-carpet: rgba(180,160,140,.15);
  --of-rug: rgba(160,140,120,.1);
  --of-text: #333;
  --of-text-dim: #888;
  --of-clock: #bbb;
  --of-sky: linear-gradient(180deg, #4a90d9 0%, #87ceeb 50%, #a8d8ea 100%);
  --of-window-glow: rgba(135,206,250,.15);
}
.dark {
  --of-bg: #08080c;
  --of-floor: linear-gradient(165deg, #0e0e12 0%, #111116 40%, #0c0c10 100%);
  --of-floor-plank: rgba(255,255,255,.012);
  --of-floor-grain: rgba(255,255,255,.006);
  --of-floor-reflect: rgba(255,255,255,.03);
  --of-wall: #14141a;
  --of-wall-trim: #222230;
  --of-wall-shadow: 0 6px 30px rgba(0,0,0,.35);
  --of-desk: #1e1810;
  --of-desk-dark: #252018;
  --of-desk-top: linear-gradient(135deg, #2a2218 0%, #1e1810 50%, #181208 100%);
  --of-desk-shadow: 0 8px 24px rgba(0,0,0,.35);
  --of-desk-leg: #141010;
  --of-monitor: #060608;
  --of-monitor-bezel: #141418;
  --of-screen-off: #040406;
  --of-keyboard: #1a1a20;
  --of-mug: #6a2222;
  --of-pot: #2a1810;
  --of-lamp-pole: #333340;
  --of-lamp-shade: #1a1610;
  --of-lamp-glow: rgba(255,180,60,.15);
  --of-glass: rgba(60,80,140,.04);
  --of-glass-edge: rgba(80,100,160,.08);
  --of-glass-reflect: rgba(255,255,255,.02);
  --of-carpet: rgba(20,18,25,.25);
  --of-rug: rgba(20,18,22,.2);
  --of-text: #e8e8f0;
  --of-text-dim: #666;
  --of-clock: #444;
  --of-sky: linear-gradient(180deg, #0a0a2e 0%, #16213e 50%, #1a1a3e 100%);
  --of-window-glow: rgba(40,60,120,.08);
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
      amanhecer: 'rgba(255,180,100,.015)',
      dia: 'transparent',
      entardecer: 'rgba(255,120,40,.02)',
      noite: 'rgba(10,15,40,.04)',
    }
    const lampOpacity: Record<Fase, number> = {
      amanhecer: 0.35, dia: 0.12, entardecer: 0.5, noite: 0.85,
    }
    return {
      fase, progresso,
      skyGradient: skyGradients[fase],
      ambientOverlay: ambientOverlays[fase],
      lampOpacity: lampOpacity[fase],
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

/* ── Piso de Madeira Premium (tábuas + reflexo) ── */
const PremiumFloor = memo(function PremiumFloor() {
  return (
    <div className="absolute inset-0" style={{ overflow: 'hidden' }}>
      {/* Base do piso */}
      <div className="absolute inset-0" style={{
        background: 'var(--of-floor)',
      }} />
      {/* Tábuas (horizontais) */}
      <div className="absolute inset-0" style={{
        backgroundImage: `
          repeating-linear-gradient(0deg, transparent, transparent 59px, var(--of-floor-plank) 59px, var(--of-floor-plank) 60px),
          repeating-linear-gradient(90deg, var(--of-floor-grain) 0px, transparent 1px, transparent 120px)
        `,
      }} />
      {/* Reflexo de luz natural (diagonal) */}
      <div className="absolute inset-0" style={{
        background: 'linear-gradient(135deg, var(--of-floor-reflect) 0%, transparent 30%, transparent 70%, var(--of-floor-reflect) 100%)',
        animation: 'floorReflect 8s infinite ease-in-out',
      }} />
    </div>
  )
})

/* ── Vista do Rio de Janeiro (SVG mais detalhado) ── */
const RioSkyline = memo(function RioSkyline({ showStars }: { showStars: boolean }) {
  return (
    <svg width="100%" height="100%" viewBox="0 0 200 70" preserveAspectRatio="xMidYMid slice" className="absolute inset-0">
      {/* Estrelas (noite) */}
      {showStars && <>
        <circle cx="20" cy="8" r="1" fill="white" opacity=".7" />
        <circle cx="55" cy="12" r=".8" fill="white" opacity=".5" />
        <circle cx="90" cy="5" r=".9" fill="white" opacity=".6" />
        <circle cx="130" cy="10" r=".6" fill="white" opacity=".5" />
        <circle cx="170" cy="7" r=".7" fill="white" opacity=".4" />
        <circle cx="40" cy="20" r=".5" fill="white" opacity=".3" />
        <circle cx="155" cy="18" r=".6" fill="white" opacity=".35" />
      </>}
      {/* Mar com ondas sutis */}
      <rect x="0" y="52" width="200" height="18" fill="rgba(30,80,140,.2)" rx="0" />
      <path d="M0 55 Q15 53 30 55 Q45 57 60 55 Q75 53 90 55 Q105 57 120 55 Q135 53 150 55 Q165 57 180 55 Q195 53 200 55" stroke="rgba(100,160,220,.1)" fill="none" strokeWidth=".5" />
      {/* Montanhas (fundo) */}
      <path d="M0 58 L15 42 L30 48 L50 32 L70 42 L85 28 L100 38 L115 22 L130 35 L145 42 L160 26 L175 36 L190 30 L200 42 L200 70 L0 70 Z"
        fill="rgba(30,60,30,.3)" />
      {/* Montanhas (frente) */}
      <path d="M0 60 L20 48 L40 52 L60 40 L80 50 L95 36 L110 44 L125 50 L140 38 L160 48 L180 42 L200 52 L200 70 L0 70 Z"
        fill="rgba(35,70,35,.25)" />
      {/* Pão de Açúcar */}
      <path d="M138 48 Q145 18 152 18 Q159 18 166 48" fill="rgba(40,70,40,.35)" stroke="rgba(20,50,20,.12)" strokeWidth=".6" />
      {/* Bondinho (linha + cabine) */}
      <line x1="142" y1="28" x2="162" y2="22" stroke="rgba(80,80,80,.15)" strokeWidth=".4" />
      <rect x="150" y="24" width="4" height="3" rx=".5" fill="rgba(60,60,60,.2)" />
      {/* Cristo Redentor */}
      <g transform="translate(85,20)">
        <line x1="0" y1="0" x2="0" y2="7" stroke="rgba(50,50,50,.25)" strokeWidth="1.2" />
        <line x1="-5" y1="2" x2="5" y2="2" stroke="rgba(50,50,50,.25)" strokeWidth="1.2" />
        <circle cx="0" cy="-1" r="1.5" fill="rgba(50,50,50,.25)" />
      </g>
      {/* Alguns prédios no horizonte */}
      <rect x="30" y="46" width="3" height="12" fill="rgba(50,50,60,.12)" />
      <rect x="35" y="44" width="4" height="14" fill="rgba(50,50,60,.1)" />
      <rect x="68" y="45" width="3" height="13" fill="rgba(50,50,60,.1)" />
      <rect x="112" y="43" width="5" height="15" fill="rgba(50,50,60,.08)" />
    </svg>
  )
})

/* ── Parede Traseira com Janelas Grandes ── */
const BackWall = memo(function BackWall({ skyGradient, showStars }: { skyGradient: string; showStars: boolean }) {
  const windows = [
    { x: 60, w: 160 }, { x: 250, w: 160 }, { x: 440, w: 160 },
    { x: 640, w: 160 }, { x: 840, w: 160 },
    { x: 1060, w: 160 }, { x: 1250, w: 160 }, { x: 1440, w: 120 },
  ]
  return (
    <div className="absolute top-0 left-0 right-0" style={{ height: 100, zIndex: 1 }}>
      {/* Parede */}
      <div className="absolute inset-0" style={{
        background: 'var(--of-wall)',
        boxShadow: 'var(--of-wall-shadow)',
      }} />
      {/* Rodapé sofisticado */}
      <div className="absolute bottom-0 left-0 right-0 h-[6px]" style={{
        background: 'linear-gradient(180deg, var(--of-wall-trim), var(--of-desk-dark))',
        boxShadow: '0 2px 8px rgba(0,0,0,.06)',
      }} />
      {/* Faixa decorativa superior */}
      <div className="absolute top-0 left-0 right-0 h-[3px]" style={{
        background: 'linear-gradient(90deg, transparent, var(--of-wall-trim), transparent)',
      }} />

      {/* Janelas grandes */}
      {windows.map((win, i) => (
        <div key={i} className="absolute" style={{
          left: win.x, top: 12, width: win.w, height: 68, borderRadius: 6,
          background: skyGradient,
          border: '3px solid var(--of-wall-trim)',
          boxShadow: `
            inset 0 0 30px var(--of-window-glow),
            0 0 20px var(--of-window-glow),
            0 3px 10px rgba(0,0,0,.06)
          `,
          overflow: 'hidden',
        }}>
          {/* Caixilho central vertical */}
          <div className="absolute top-0 bottom-0 left-1/2" style={{ width: 3, marginLeft: -1.5, background: 'var(--of-wall-trim)' }} />
          {/* Caixilho central horizontal */}
          <div className="absolute left-0 right-0 top-1/2" style={{ height: 3, marginTop: -1.5, background: 'var(--of-wall-trim)' }} />
          {/* Reflexo no vidro */}
          <div className="absolute inset-0" style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,.15) 0%, transparent 40%, transparent 60%, rgba(255,255,255,.05) 100%)',
          }} />
          {/* Vista do Rio */}
          <RioSkyline showStars={showStars} />
        </div>
      ))}
    </div>
  )
})

/* ── Mesa Premium com profundidade real ── */
const PremiumDesk = memo(function PremiumDesk({ cor, active, isCeo, deskItem }: {
  cor: string; active: boolean; isCeo?: boolean; deskItem?: string
}) {
  const w = isCeo ? 200 : 155
  const h = isCeo ? 88 : 72
  const depth = 8 /* profundidade 3D lateral */
  return (
    <svg width={w} height={h + depth} viewBox={`0 0 ${w} ${h + depth}`}
      style={{ filter: `drop-shadow(${active ? `0 0 20px ${cor}15` : '0 0 0 transparent'})` }}>
      {/* Sombra real no chão */}
      <ellipse cx={w/2} cy={h + depth - 2} rx={w*.46} ry={8}
        fill="rgba(0,0,0,.08)" style={{ filter: 'blur(3px)' }} />

      {/* LATERAIS DA MESA (profundidade) */}
      <path d={`M6 ${14+depth} L${w-6} ${14+depth} L${w-6} ${14} L6 ${14} Z`}
        fill="var(--of-desk-dark)" />

      {/* Superfície principal */}
      <rect x={4} y={8} width={w-8} height={h - 20} rx={5}
        fill="url(#deskGrain)" stroke={active ? cor : 'var(--of-desk-dark)'} strokeWidth={active ? 1.8 : .5} />
      <defs>
        <linearGradient id="deskGrain" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--of-desk)" />
          <stop offset="50%" stopColor="var(--of-desk)" />
          <stop offset="100%" stopColor="var(--of-desk-dark)" />
        </linearGradient>
      </defs>
      {/* Veios de madeira */}
      {[16, 24, 32, 40, 48].map(ly => (
        <line key={ly} x1={12} y1={ly} x2={w-12} y2={ly+1} stroke="var(--of-floor-plank)" strokeWidth=".4" />
      ))}
      {/* Brilho superior sutil */}
      <line x1={10} y1={9} x2={w-10} y2={9} stroke="rgba(255,255,255,.08)" strokeWidth=".6" />

      {/* MONITOR PRINCIPAL */}
      <g>
        {/* Tela com borda arredondada */}
        <rect x={isCeo ? w*.18 : w*.2} y={0} width={isCeo ? w*.28 : w*.4} height={isCeo ? 22 : 20} rx={3}
          fill="var(--of-monitor)" stroke={active ? `${cor}60` : 'var(--of-monitor-bezel)'} strokeWidth={1.2} />
        {/* Conteúdo na tela */}
        <rect x={(isCeo ? w*.18 : w*.2) + 3} y={2} width={(isCeo ? w*.28 : w*.4) - 6} height={isCeo ? 18 : 16} rx={2}
          fill={active ? `${cor}12` : 'var(--of-screen-off)'}
          style={{ animation: active ? 'monitorFlicker 8s infinite' : 'none' }} />
        {active && (
          <g style={{ animation: 'screenGlow 2.5s infinite' }}>
            <rect x={(isCeo ? w*.20 : w*.23)} y={5} width={w*.12} height={2} rx={.5} fill={`${cor}45`} />
            <rect x={(isCeo ? w*.20 : w*.23)} y={9} width={w*.18} height={1.5} rx={.5} fill={`${cor}30`} />
            <rect x={(isCeo ? w*.20 : w*.23)} y={12.5} width={w*.08} height={1.5} rx={.5} fill={`${cor}35`} />
          </g>
        )}
        {/* Stand do monitor */}
        <rect x={isCeo ? w*.30 : w*.37} y={isCeo ? 22 : 20} width={4} height={5} fill="var(--of-monitor-bezel)" />
        <ellipse cx={isCeo ? w*.32 : w*.39} cy={isCeo ? 27 : 25} rx={8} ry={2} fill="var(--of-monitor-bezel)" />
      </g>

      {/* MONITOR 2 (CEO) */}
      {isCeo && (
        <g>
          <rect x={w*.50} y={1} width={w*.25} height={20} rx={3}
            fill="var(--of-monitor)" stroke={active ? `${cor}40` : 'var(--of-monitor-bezel)'} strokeWidth={1} />
          <rect x={w*.50 + 3} y={3} width={w*.25 - 6} height={16} rx={2}
            fill={active ? `${cor}08` : 'var(--of-screen-off)'} />
          <rect x={w*.60} y={21} width={4} height={4} fill="var(--of-monitor-bezel)" />
          <ellipse cx={w*.62} cy={25} rx={7} ry={1.8} fill="var(--of-monitor-bezel)" />
        </g>
      )}

      {/* Teclado moderno */}
      <rect x={w*.28} y={h - 22} width={w*.30} height={9} rx={2.5}
        fill="var(--of-keyboard)" stroke="var(--of-desk-dark)" strokeWidth=".3" />
      {[0,2.5,5].map(r => (
        <line key={r} x1={w*.30} y1={h-20+r} x2={w*.56} y2={h-20+r}
          stroke="var(--of-desk-dark)" strokeWidth=".15" opacity=".3" />
      ))}

      {/* Mouse moderno (arredondado) */}
      <ellipse cx={w*.66} cy={h - 17} rx={4.5} ry={6}
        fill="var(--of-keyboard)" stroke="var(--of-desk-dark)" strokeWidth=".3" />
      <line x1={w*.66} y1={h-21} x2={w*.66} y2={h-18} stroke="var(--of-desk-dark)" strokeWidth=".2" opacity=".3" />

      {/* Caneca com vapor */}
      <g>
        <rect x={w-28} y={12} width={8} height={11} rx={2.5} fill="var(--of-mug)" />
        <path d={`M${w-20} ${15} Q${w-16} ${17} ${w-20} ${21}`} stroke="var(--of-mug)" strokeWidth="1.2" fill="none" />
        {active && <>
          <circle cx={w-24} cy={9} r="1.5" fill="rgba(200,200,200,.2)" style={{ animation: 'steam 3s infinite' }} />
          <circle cx={w-22} cy={7} r="1" fill="rgba(200,200,200,.15)" style={{ animation: 'steam 3.5s infinite .5s' }} />
        </>}
      </g>

      {/* Planta pessoal */}
      <g>
        <rect x={8} y={13} width={6} height={8} rx={2} fill="var(--of-pot)" />
        <ellipse cx={11} cy={11} rx={4} ry={5} fill="#22c55e" opacity=".5" />
        <ellipse cx={10} cy={8} rx={3} ry={4} fill="#16a34a" opacity=".4" />
      </g>

      {/* Objeto pessoal */}
      {deskItem === 'frame' && <rect x={w-42} y={12} width={7} height={9} rx={1} fill="var(--of-wall-trim)" opacity=".5" />}
      {deskItem === 'book' && <rect x={w-45} y={15} width={11} height={6} rx={1} fill={`${cor}35`} />}
      {deskItem === 'trophy' && <path d={`M${w-43} 22 L${w-41} 12 L${w-37} 12 L${w-35} 22`} fill="#fbbf24" opacity=".4" />}
      {deskItem === 'headphones' && <ellipse cx={w-39} cy={16} rx={5} ry={4} fill="var(--of-monitor)" opacity=".4" />}

      {/* Nameplate CEO */}
      {isCeo && (
        <g>
          <rect x={w*.38} y={h - 10} width={w*.24} height={6} rx={1.5} fill="#fbbf2418" stroke="#fbbf2430" strokeWidth=".5" />
          <text x={w*.5} y={h - 5.5} textAnchor="middle" fill="#fbbf24" fontSize="4" fontWeight="bold" letterSpacing=".5">CEO</text>
        </g>
      )}

      {/* Pernas com profundidade */}
      <rect x={8} y={h - 8} width={3} height={10 + depth} rx={1.5} fill="var(--of-desk-leg)" />
      <rect x={w-11} y={h - 8} width={3} height={10 + depth} rx={1.5} fill="var(--of-desk-leg)" />
    </svg>
  )
})

/* ── Cadeira Ergonômica ── */
const Chair = memo(function Chair({ cor, large }: { cor: string; large?: boolean }) {
  const s = large ? 1.3 : 1
  return (
    <svg width={38*s} height={24*s} viewBox="0 0 38 24" className="absolute" style={{ bottom: -12, left: '50%', marginLeft: -19*s }}>
      {/* Sombra */}
      <ellipse cx="19" cy="20" rx="14" ry="4" fill="rgba(0,0,0,.06)" />
      {/* Assento */}
      <ellipse cx="19" cy="14" rx="14" ry="8" fill={`${cor}20`} stroke={`${cor}30`} strokeWidth=".6" />
      <ellipse cx="19" cy="13" rx="11" ry="6" fill={`${cor}10`} />
      {/* Encosto */}
      <ellipse cx="19" cy="6" rx="10" ry="6" fill={`${cor}15`} stroke={`${cor}22`} strokeWidth=".4" />
      {/* Rodas (5 pontinhos) */}
      {[7, 13, 19, 25, 31].map(rx => (
        <circle key={rx} cx={rx} cy="22" r="1.2" fill="var(--of-desk-leg)" opacity=".3" />
      ))}
    </svg>
  )
})

/* ── Agente / Avatar SVG Premium ── */
const AgentAvatar = memo(function AgentAvatar({ cor, skin, hair, size = 1, status = 'idle' }: {
  cor: string; skin: string; hair: string; size?: number; status?: 'idle' | 'typing' | 'thinking' | 'walking'
}) {
  const s = 28 * size
  const anim = status === 'typing' ? 'typing .6s infinite' : status === 'thinking' ? 'thinking 2.5s infinite' : 'breathe 3.5s infinite'
  return (
    <svg width={s} height={s * 1.55} viewBox="0 0 28 43" style={{
      animation: anim,
      transformOrigin: 'bottom center',
      filter: 'drop-shadow(0 4px 8px rgba(0,0,0,.2))',
      willChange: 'transform',
    }}>
      {/* Sombra no chão */}
      <ellipse cx="14" cy="41" rx="8" ry="2.5" fill="rgba(0,0,0,.1)" />
      {/* Sapatos */}
      <ellipse cx="10" cy="39" rx="3.5" ry="1.8" fill="#222" />
      <ellipse cx="18" cy="39" rx="3.5" ry="1.8" fill="#222" />
      {/* Calça */}
      <path d="M9 32 L8 38 L12 38 L14 34 L16 38 L20 38 L19 32 Z" fill="#334155" />
      {/* Corpo / Camiseta com degradê */}
      <defs>
        <linearGradient id={`shirt-${cor.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={cor} stopOpacity=".9" />
          <stop offset="100%" stopColor={cor} stopOpacity=".7" />
        </linearGradient>
      </defs>
      <path d="M7.5 20 Q14 17 20.5 20 L21 33 Q14 35 7 33 Z" fill={`url(#shirt-${cor.replace('#','')})`} />
      {/* Gola */}
      <path d="M11 20 Q14 22 17 20" stroke="rgba(0,0,0,.15)" strokeWidth=".6" fill="none" />
      {/* Braços */}
      {status === 'typing' ? (
        <>
          <path d="M7.5 21 Q4 25 7 29" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M20.5 21 Q24 25 21 29" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          {/* Mãos no teclado */}
          <circle cx="7" cy="29.5" r="2" fill={skin} />
          <circle cx="21" cy="29.5" r="2" fill={skin} />
        </>
      ) : (
        <>
          <path d="M7.5 21 Q5 28 7.5 33" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M20.5 21 Q23 28 20.5 33" stroke={skin} strokeWidth="2.5" fill="none" strokeLinecap="round" />
        </>
      )}
      {/* Pescoço */}
      <rect x="12" y="17" width="4" height="4" rx="2" fill={skin} />
      {/* Cabeça */}
      <ellipse cx="14" cy="11" rx="7.5" ry="8" fill={skin} />
      {/* Cabelo */}
      <ellipse cx="14" cy="6.5" rx="7.2" ry="5.2" fill={hair} />
      <ellipse cx="7.5" cy="8" rx="2.2" ry="3.2" fill={hair} opacity=".6" />
      <ellipse cx="20.5" cy="8" rx="2.2" ry="3.2" fill={hair} opacity=".6" />
      {/* Orelhas */}
      <ellipse cx="6" cy="12" rx="1.5" ry="2" fill={skin} />
      <ellipse cx="22" cy="12" rx="1.5" ry="2" fill={skin} />
      {/* Olhos */}
      <ellipse cx="10.5" cy="12" rx="1.2" ry="1.3" fill="#1a1a1a" />
      <ellipse cx="17.5" cy="12" rx="1.2" ry="1.3" fill="#1a1a1a" />
      {/* Brilho dos olhos */}
      <circle cx="11" cy="11.5" r=".4" fill="white" />
      <circle cx="18" cy="11.5" r=".4" fill="white" />
      {/* Sobrancelhas */}
      <line x1="8.5" y1="9.5" x2="12.5" y2="9.5" stroke={hair} strokeWidth=".5" strokeLinecap="round" />
      <line x1="15.5" y1="9.5" x2="19.5" y2="9.5" stroke={hair} strokeWidth=".5" strokeLinecap="round" />
      {/* Boca */}
      <path d="M11.5 15 Q14 16.5 16.5 15" stroke="#1a1a1a" strokeWidth=".5" fill="none" />
      {/* Bolha de pensamento */}
      {status === 'thinking' && (
        <g opacity=".7">
          <ellipse cx="24" cy="3" rx="6" ry="4" fill="white" stroke="rgba(0,0,0,.1)" strokeWidth=".4" />
          <circle cx="22" cy="2.5" r="1" fill="rgba(0,0,0,.15)" />
          <circle cx="24.5" cy="2.5" r="1" fill="rgba(0,0,0,.15)" />
          <circle cx="27" cy="2.5" r="1" fill="rgba(0,0,0,.15)" />
          <circle cx="20" cy="7" r="1.5" fill="white" stroke="rgba(0,0,0,.08)" strokeWidth=".3" />
          <circle cx="19" cy="10" r="1" fill="white" stroke="rgba(0,0,0,.06)" strokeWidth=".2" />
        </g>
      )}
    </svg>
  )
})

/* ── Planta decorativa grande ── */
const Plant = memo(function Plant({ x, y, size = 1, delay = 0 }: { x: number; y: number; size?: number; delay?: number }) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: x, top: y,
      animation: `leafSway ${5 + delay}s infinite ease-in-out ${delay}s`,
      transformOrigin: 'bottom center',
    }}>
      <svg width={22 * size} height={38 * size} viewBox="0 0 22 38">
        {/* Vaso com profundidade */}
        <path d="M5 26 L7 36 L15 36 L17 26 Z" fill="var(--of-pot)" />
        <ellipse cx="11" cy="26" rx="6" ry="2" fill="var(--of-pot)" />
        <ellipse cx="11" cy="26" rx="5" ry="1.5" fill="rgba(0,0,0,.08)" />
        {/* Terra */}
        <ellipse cx="11" cy="26" rx="4.5" ry="1.2" fill="rgba(60,30,10,.3)" />
        {/* Folhas */}
        <ellipse cx="11" cy="22" rx="6" ry="4" fill="#4ade80" opacity=".5" />
        <ellipse cx="8" cy="17" rx="5" ry="7" fill="#22c55e" opacity=".55" />
        <ellipse cx="14" cy="14" rx="5" ry="7" fill="#16a34a" opacity=".5" />
        <ellipse cx="11" cy="11" rx="4" ry="6" fill="#15803d" opacity=".65" />
        {/* Brilho de folha */}
        <ellipse cx="9" cy="14" rx="2" ry="4" fill="rgba(255,255,255,.06)" />
      </svg>
    </div>
  )
})

/* ── Luminária de Chão moderna ── */
const FloorLamp = memo(function FloorLamp({ x, y, lampOpacity }: { x: number; y: number; lampOpacity: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="24" height="55" viewBox="0 0 24 55">
        {/* Sombra */}
        <ellipse cx="12" cy="52" rx="7" ry="2" fill="rgba(0,0,0,.06)" />
        {/* Base */}
        <ellipse cx="12" cy="50" rx="5" ry="2" fill="var(--of-lamp-pole)" opacity=".5" />
        {/* Haste */}
        <rect x="11" y="16" width="2" height="34" fill="var(--of-lamp-pole)" />
        {/* Abajur */}
        <path d="M3 16 L12 2 L21 16 Z" fill="var(--of-lamp-shade)" stroke="var(--of-desk-dark)" strokeWidth=".3" />
        {/* Luz (glow) */}
        <circle cx="12" cy="14" r="4" fill="#fbbf24" opacity={lampOpacity} />
        <circle cx="12" cy="22" r="16" fill="var(--of-lamp-glow)" opacity={lampOpacity * 0.3} />
      </svg>
    </div>
  )
})

/* ── Tapete Premium ── */
const Rug = memo(function Rug({ x, y, w, h }: { x: number; y: number; w: number; h: number }) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: x, top: y, width: w, height: h, borderRadius: 14,
      background: 'var(--of-rug)',
      border: '1.5px solid var(--of-glass-edge)',
      boxShadow: 'inset 0 0 20px rgba(0,0,0,.02)',
    }}>
      {/* Padrão geométrico sutil */}
      <div className="absolute inset-4 rounded-xl" style={{
        border: '1px solid var(--of-glass-edge)',
        opacity: .3,
      }} />
    </div>
  )
})

/* ── Relógio de Parede ── */
const WallClock = memo(function WallClock({ x, y }: { x: number; y: number }) {
  const now = new Date()
  const hDeg = (now.getHours() % 12 + now.getMinutes() / 60) * 30
  const mDeg = now.getMinutes() * 6
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y, zIndex: 2 }}>
      <svg width="32" height="32" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="14" fill="var(--of-wall)" stroke="var(--of-clock)" strokeWidth="1.5" />
        <circle cx="16" cy="16" r="12.5" fill="none" stroke="var(--of-clock)" strokeWidth=".3" />
        {/* Marcas das horas */}
        {[...Array(12)].map((_, i) => {
          const angle = (i * 30 - 90) * Math.PI / 180
          const x1 = 16 + Math.cos(angle) * 10
          const y1 = 16 + Math.sin(angle) * 10
          const x2 = 16 + Math.cos(angle) * 12
          const y2 = 16 + Math.sin(angle) * 12
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--of-clock)" strokeWidth={i % 3 === 0 ? "1" : ".4"} />
        })}
        <circle cx="16" cy="16" r="1.2" fill="var(--of-clock)" />
        <line x1="16" y1="16" x2="16" y2="8" stroke="var(--of-clock)" strokeWidth="1.2" strokeLinecap="round"
          transform={`rotate(${hDeg} 16 16)`} />
        <line x1="16" y1="16" x2="16" y2="5.5" stroke="var(--of-clock)" strokeWidth=".8" strokeLinecap="round"
          transform={`rotate(${mDeg} 16 16)`} />
        <line x1="16" y1="16" x2="16" y2="4" stroke="#ef4444" strokeWidth=".4" strokeLinecap="round"
          style={{ transformOrigin: '16px 16px', animation: 'clockSecond 60s linear infinite' }} />
      </svg>
    </div>
  )
})

/* ── Quadro na Parede ── */
const WallArt = memo(function WallArt({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y, zIndex: 2 }}>
      <svg width="40" height="30" viewBox="0 0 40 30">
        {/* Moldura */}
        <rect x="1" y="1" width="38" height="28" rx="2" fill="var(--of-wall)" stroke="var(--of-desk-dark)" strokeWidth="1" />
        <rect x="3" y="3" width="34" height="24" rx="1" fill={`${color}06`} />
        {/* Arte geométrica minimalista */}
        <circle cx="14" cy="15" r="6" fill={`${color}12`} />
        <circle cx="24" cy="13" r="4" fill={`${color}18`} />
        <rect x="18" y="18" width="12" height="4" rx="2" fill={`${color}10`} />
      </svg>
    </div>
  )
})

/* ── Bebedouro Premium ── */
const WaterCooler = memo(function WaterCooler({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="24" height="48" viewBox="0 0 24 48">
        <ellipse cx="12" cy="46" rx="7" ry="2" fill="rgba(0,0,0,.05)" />
        <rect x="4" y="22" width="16" height="22" rx="3" fill="var(--of-keyboard)" stroke="var(--of-desk-dark)" strokeWidth=".4" />
        <ellipse cx="12" cy="20" rx="7" ry="3" fill="rgba(100,180,255,.12)" stroke="rgba(100,180,255,.2)" strokeWidth=".5" />
        <rect x="6" y="6" width="12" height="14" rx="5" fill="rgba(100,180,255,.08)" stroke="rgba(100,180,255,.15)" strokeWidth=".5" />
        <circle cx="12" cy="13" r="1.5" fill="rgba(100,180,255,.15)" style={{ animation: 'bubbleRise 4s infinite 1s' }} />
        <rect x="17" y="26" width="4" height="3" rx="1" fill="var(--of-lamp-pole)" />
      </svg>
    </div>
  )
})

/* ── Máquina de Café Premium ── */
const CoffeeMachine = memo(function CoffeeMachine({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: x, top: y }}>
      <svg width="32" height="54" viewBox="0 0 32 54">
        <ellipse cx="16" cy="52" rx="10" ry="2" fill="rgba(0,0,0,.05)" />
        <rect x="4" y="10" width="24" height="36" rx="4" fill="var(--of-monitor)" stroke="var(--of-monitor-bezel)" strokeWidth=".6" />
        {/* Tela digital */}
        <rect x="8" y="14" width="16" height="8" rx="2" fill="#10b98118" />
        <text x="16" y="20" textAnchor="middle" fill="#10b981" fontSize="3.5" opacity=".5">READY</text>
        {/* Bandeja */}
        <rect x="6" y="38" width="20" height="4" rx="1.5" fill="var(--of-desk-dark)" />
        {/* Xícara */}
        <rect x="10" y="34" width="7" height="5" rx="2" fill="var(--of-mug)" opacity=".6" />
        {/* Vapor */}
        <circle cx="14" cy="30" r="1.5" fill="rgba(200,200,200,.15)" style={{ animation: 'steam 3s infinite' }} />
        <circle cx="16" cy="28" r="1" fill="rgba(200,200,200,.1)" style={{ animation: 'steam 4s infinite .8s' }} />
        {/* Botões */}
        <circle cx="10" cy="26" r="1.8" fill="#10b981" opacity=".4" />
        <circle cx="16" cy="26" r="1.8" fill="#3b82f6" opacity=".25" />
        <circle cx="22" cy="26" r="1.8" fill="#f59e0b" opacity=".25" />
        {/* Marca */}
        <text x="16" y="50" textAnchor="middle" fill="var(--of-clock)" fontSize="3" opacity=".3" fontWeight="bold">NESPRESSO</text>
      </svg>
    </div>
  )
})

/* ── Divisória de vidro (separação de ambientes) ── */
const GlassDivider = memo(function GlassDivider({ x, y, w, h }: { x: number; y: number; w: number; h: number }) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: x, top: y, width: w, height: h,
      background: 'var(--of-glass)',
      border: '1px solid var(--of-glass-edge)',
      borderRadius: 4,
    }}>
      {/* Reflexo */}
      <div className="absolute inset-0" style={{
        background: 'linear-gradient(135deg, var(--of-glass-reflect) 0%, transparent 60%)',
        borderRadius: 4,
      }} />
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
    <div className="sf-page overflow-hidden select-none" style={{ margin: '-24px', padding: 0, minHeight: '100vh', background: 'var(--of-bg)' }}
      onClick={() => mostrarSeletor && setMostrarSeletor(false)}>
      <style>{CSS}{themeCSS}</style>

      {/* ── Header Premium ── */}
      <div className="relative z-10 flex items-center justify-between px-8 pt-5 pb-3" style={{
        background: 'linear-gradient(180deg, var(--of-bg), transparent)',
      }}>
        <div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{
              background: 'rgba(16,185,129,.12)',
              border: '1px solid rgba(16,185,129,.2)',
            }}>
              <Zap size={14} className="text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ color: 'var(--of-text)', letterSpacing: '-0.02em' }}>
                Escritório Virtual
              </h2>
              <div className="flex items-center gap-3 mt-0.5">
                <p className="text-[10px]" style={{ color: 'var(--of-text-dim)' }}>{meuSquad.nome} · {meuSquad.num_agentes} agentes</p>
                <span className="text-[9px] px-2 py-0.5 rounded-md" style={{
                  color: 'var(--of-text-dim)',
                  background: 'var(--of-glass)',
                  border: '1px solid var(--of-glass-edge)',
                }}>
                  {dayNight.fase === 'dia' ? '☀️' : dayNight.fase === 'noite' ? '🌙' : dayNight.fase === 'amanhecer' ? '🌅' : '🌇'} {dayNight.fase}
                </span>
                {temVisaoGeral && (
                  <div className="relative">
                    <button onClick={(e) => { e.stopPropagation(); setMostrarSeletor(!mostrarSeletor) }}
                      className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-medium transition-all"
                      style={{ background: 'rgba(139,92,246,.1)', color: '#a78bfa', border: '1px solid rgba(139,92,246,.2)' }}>
                      <Eye size={10} />{squadSelecionado ? 'Visão Geral' : 'Ver squads'}<ChevronDown size={10} />
                    </button>
                    {mostrarSeletor && (
                      <div className="absolute top-full left-0 mt-1 rounded-xl shadow-2xl py-1 z-30 min-w-[220px]" style={{
                        background: 'var(--of-wall)', border: '1px solid var(--of-glass-edge)',
                        boxShadow: '0 20px 50px rgba(0,0,0,.15)',
                      }}>
                        <button onClick={() => { setSquadSelecionado('__todos__'); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                          className="w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 hover:opacity-80" style={{
                            color: verTodos ? '#a78bfa' : 'var(--of-text-dim)',
                            background: verTodos ? 'rgba(139,92,246,.08)' : 'transparent',
                          }}>
                          <Eye size={11} /> Ver todos
                        </button>
                        <div className="mx-3 my-1" style={{ borderTop: '1px solid var(--of-glass-edge)' }} />
                        <button onClick={() => { setSquadSelecionado(null); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                          className="w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 hover:opacity-80" style={{
                            color: !squadSelecionado ? '#10b981' : 'var(--of-text-dim)',
                            background: !squadSelecionado ? 'rgba(16,185,129,.08)' : 'transparent',
                          }}>
                          <Crown size={11} /> {meuSquadOriginal?.nome || 'Meu Squad'}
                        </button>
                        {squadsPessoais.filter(s => !s.is_meu).map(s => (
                          <button key={s.nome} onClick={() => { setSquadSelecionado(s.nome); setMostrarSeletor(false); setVisitando(null); setEmReuniao(false) }}
                            className="w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 hover:opacity-80" style={{
                              color: squadSelecionado === s.nome ? '#a78bfa' : 'var(--of-text-dim)',
                              background: squadSelecionado === s.nome ? 'rgba(139,92,246,.08)' : 'transparent',
                            }}>
                            <User size={11} /> {s.nome} <span className="ml-auto text-[9px]" style={{ color: 'var(--of-text-dim)' }}>{s.num_agentes}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {squadSelecionado && (
                  <button onClick={() => { setSquadSelecionado(null); setVisitando(null); setEmReuniao(false) }}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px]"
                    style={{ color: '#f59e0b', background: 'rgba(245,158,11,.08)', border: '1px solid rgba(245,158,11,.15)' }}>
                    Voltar ao meu squad
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setVideoCall({ sala: `sf-${Date.now()}`, participantes: [usuario?.nome || 'CEO', 'Jonatas'] })}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all"
            style={{ background: 'rgba(59,130,246,.1)', color: '#60a5fa', border: '1px solid rgba(59,130,246,.15)' }}
          >
            <Video size={13} /> Video Call
          </button>
          <button onClick={handleReunir}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all"
            style={emReuniao
              ? { background: 'rgba(239,68,68,.1)', color: '#f87171', border: '1px solid rgba(239,68,68,.15)' }
              : { background: 'rgba(16,185,129,.1)', color: '#34d399', border: '1px solid rgba(16,185,129,.15)' }
            }>
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
                style={{
                  background: 'var(--of-wall)',
                  border: `1px solid ${sq.is_meu ? 'rgba(16,185,129,.25)' : 'var(--of-glass-edge)'}`,
                  boxShadow: '0 4px 20px rgba(0,0,0,.06)',
                }}
                onClick={() => { setSquadSelecionado(sq.nome); setVisitando(null); setEmReuniao(false) }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{
                    background: sq.is_meu ? 'rgba(16,185,129,.12)' : 'rgba(139,92,246,.12)',
                  }}>
                    {sq.is_meu ? <Crown size={18} className="text-emerald-400" /> : <User size={18} className="text-purple-400" />}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--of-text)' }}>{sq.nome}</h3>
                    <p className="text-[10px]" style={{ color: 'var(--of-text-dim)' }}>{sq.especialidade}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {sq.nomes_agentes.map((n, i) => {
                    const a = agCfg(i, n)
                    const agentCfg = buscarAgente(a.nome)
                    return (
                      <div key={i} className="flex flex-col items-center">
                        {agentCfg ? (
                          <AgentAvatarPhoto agentName={a.nome} size="sm" noHover />
                        ) : (
                          <AgentAvatar cor={a.cor} skin={a.skin} hair={a.hair} size={.55} />
                        )}
                        <p className="text-[6px] mt-0.5" style={{ color: 'var(--of-text-dim)' }}>{a.nome}</p>
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
          OFFICE SCENE — Canvas 3D Isométrico
          ═══════════════════════════════════════════════════════════════ */}
      {!verTodos && (
        <div className="relative w-full overflow-x-auto overflow-y-auto" style={{ height: 'calc(100vh - 100px)' }}>
          <div className="relative mx-auto" style={{ width: 1600, height: 780, minWidth: 1600 }}>

            {/* Piso Premium */}
            <PremiumFloor />

            {/* Overlay de iluminação ambiente (dia/noite) */}
            <div className="absolute inset-0 pointer-events-none" style={{ background: dayNight.ambientOverlay, zIndex: 60 }} />

            {/* Luzes pontuais no teto (simulação) */}
            {[200, 500, 800, 1100, 1400].map((lx, li) => (
              <div key={li} className="absolute pointer-events-none" style={{
                left: lx - 40, top: 100, width: 80, height: 120, borderRadius: '50%',
                background: `radial-gradient(ellipse, var(--of-lamp-glow) 0%, transparent 70%)`,
                opacity: dayNight.lampOpacity * 0.4,
                animation: `lightPulse ${6 + li}s infinite ease-in-out ${li * .5}s`,
                zIndex: 2,
              }} />
            ))}

            {/* Parede traseira com janelas panorâmicas */}
            <BackWall skyGradient={dayNight.skyGradient} showStars={dayNight.showStars} />

            {/* Relógio na parede */}
            <WallClock x={46} y={20} />

            {/* Quadros na parede */}
            <WallArt x={170} y={16} color="#8b5cf6" />
            <WallArt x={670} y={18} color="#3b82f6" />

            {/* Divisórias de vidro (entre áreas) */}
            <GlassDivider x={910} y={100} w={4} h={600} />

            {/* Tapetes premium */}
            <Rug x={300} y={130} w={510} h={155} />
            <Rug x={300} y={310} w={510} h={155} />
            <Rug x={300} y={490} w={510} h={155} />

            {/* Plantas decorativas */}
            <Plant x={35} y={100} size={1.6} delay={0} />
            <Plant x={270} y={90} size={1.2} delay={.8} />
            <Plant x={870} y={95} size={1.4} delay={1.2} />
            <Plant x={35} y={530} size={1.3} delay={.4} />
            <Plant x={270} y={470} size={1} delay={1.6} />
            <Plant x={870} y={570} size={1.2} delay={.6} />
            <Plant x={1540} y={100} size={1.5} delay={2} />
            <Plant x={1540} y={650} size={1.3} delay={1} />

            {/* Luminárias modernas */}
            <FloorLamp x={240} y={70} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={850} y={70} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={240} y={610} lampOpacity={dayNight.lampOpacity} />
            <FloorLamp x={850} y={610} lampOpacity={dayNight.lampOpacity} />

            {/* Bebedouro */}
            <WaterCooler x={920} y={300} />

            {/* ── CEO DESK ── */}
            <div className="absolute" style={{ left: CEO_POS.x - 30, top: CEO_POS.y - 20, zIndex: 25 }}>
              {/* Glow sutil do CEO */}
              <div className="absolute -inset-12 rounded-3xl" style={{
                background: 'radial-gradient(ellipse, rgba(16,185,129,.05) 0%, transparent 70%)',
              }} />

              {/* Badge CEO premium */}
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                style={{
                  background: 'rgba(16,185,129,.08)',
                  border: '1px solid rgba(16,185,129,.2)',
                  boxShadow: '0 4px 12px rgba(16,185,129,.08)',
                }}>
                <Crown size={10} className="text-emerald-400" />
                <span className="text-[10px] font-bold text-emerald-400 tracking-widest">CEO</span>
              </div>

              <PremiumDesk cor="#10b981" active isCeo />
              <Chair cor="#10b981" large />

              {/* CEO Avatar */}
              <div className="absolute" style={{ left: 72, top: -42 }}>
                <AgentAvatar cor="#10b981" skin="#f5cba7" hair="#3d2b1f" size={1.1}
                  status={visitando === null && !emReuniao ? 'typing' : 'idle'} />
              </div>

              {/* Nome do CEO */}
              <div className="absolute -bottom-14 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                <p className="text-[14px] font-bold text-emerald-500">{nomeUsuario}</p>
                <p className="text-[10px]" style={{ color: 'var(--of-text-dim)' }}>Sua mesa</p>
              </div>

              {/* Agente visitando */}
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
                          background: 'var(--of-wall)', border: '1px solid var(--of-glass-edge)',
                          boxShadow: '0 4px 12px rgba(0,0,0,.1)',
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
            <div className="absolute" style={{ left: MEET_CENTER.x - 200, top: MEET_CENTER.y - 210, width: 420, height: 490, zIndex: 5 }}>
              {/* Paredes de vidro com efeito translúcido */}
              <div className="absolute inset-0 rounded-2xl transition-all duration-700" style={{
                border: emReuniao ? '2px solid rgba(16,185,129,.25)' : '1.5px solid var(--of-glass-edge)',
                background: emReuniao ? 'rgba(16,185,129,.015)' : 'var(--of-glass)',
                boxShadow: emReuniao
                  ? '0 0 40px rgba(16,185,129,.06), inset 0 0 30px rgba(16,185,129,.015), 0 20px 60px rgba(0,0,0,.06)'
                  : '0 10px 40px rgba(0,0,0,.04)',
                backdropFilter: 'blur(2px)',
                animation: emReuniao ? 'meetGlow 3s infinite' : 'none',
              }}>
                {/* Reflexos no vidro (múltiplos) */}
                <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl" style={{
                  background: 'linear-gradient(90deg, transparent, var(--of-glass-reflect), transparent)',
                }} />
                <div className="absolute top-0 bottom-0 left-0 w-[2px] rounded-l-2xl" style={{
                  background: 'linear-gradient(180deg, transparent, var(--of-glass-reflect), transparent)',
                }} />
                <div className="absolute inset-0 rounded-2xl" style={{
                  background: 'linear-gradient(135deg, var(--of-glass-reflect) 0%, transparent 30%, transparent 70%, rgba(255,255,255,.01) 100%)',
                }} />
              </div>

              {/* Tapete interno */}
              <div className="absolute rounded-xl" style={{
                left: 25, top: 35, right: 25, bottom: 25,
                background: 'var(--of-carpet)',
                borderRadius: 14,
              }} />

              {/* Spots de luz no teto */}
              {[100, 210, 320].map((sx, si) => (
                <div key={si} className="absolute pointer-events-none" style={{
                  left: sx - 30, top: 15, width: 60, height: 60, borderRadius: '50%',
                  background: emReuniao
                    ? 'radial-gradient(circle, rgba(16,185,129,.06) 0%, transparent 70%)'
                    : 'radial-gradient(circle, rgba(255,255,255,.02) 0%, transparent 70%)',
                  animation: emReuniao ? 'spotPulse 4s infinite' : 'none',
                }} />
              ))}

              {/* Mesa oval grande com profundidade */}
              <svg className="absolute pointer-events-none" style={{ left: 60, top: 155 }} width="300" height="160" viewBox="0 0 300 160">
                {/* Sombra */}
                <ellipse cx="150" cy="90" rx="135" ry="65" fill="rgba(0,0,0,.05)" style={{ filter: 'blur(4px)' }} />
                {/* Borda lateral (profundidade) */}
                <ellipse cx="150" cy="85" rx="130" ry="60" fill="var(--of-desk-dark)" />
                {/* Superfície */}
                <ellipse cx="150" cy="80" rx="128" ry="58" fill="var(--of-desk)" stroke="var(--of-desk-dark)" strokeWidth=".8" />
                {/* Veios */}
                <ellipse cx="150" cy="80" rx="100" ry="42" fill="none" stroke="var(--of-floor-plank)" strokeWidth=".4" />
                <ellipse cx="150" cy="80" rx="70" ry="28" fill="none" stroke="var(--of-floor-plank)" strokeWidth=".3" />
                {/* Brilho */}
                <ellipse cx="130" cy="70" rx="60" ry="25" fill="rgba(255,255,255,.03)" />
                {emReuniao && (
                  <g>
                    <rect x="80" y="55" width="18" height="12" rx="2" fill="var(--of-monitor)" opacity=".6" />
                    <rect x="130" y="52" width="14" height="18" rx="1" fill="var(--of-keyboard)" opacity=".3" />
                    <circle cx="65" cy="65" r="4" fill="var(--of-mug)" opacity=".4" />
                    <circle cx="210" cy="70" r="3.5" fill="var(--of-mug)" opacity=".35" />
                    <line x1="170" y1="75" x2="185" y2="78" stroke="var(--of-lamp-pole)" strokeWidth="1" strokeLinecap="round" />
                  </g>
                )}
              </svg>

              {/* Cadeiras */}
              {MEET_CHAIRS.slice(0, Math.max(meuSquad.num_agentes + 1, 8)).map((ch, ci) => (
                <svg key={ci} className="absolute pointer-events-none" style={{ left: 200 + ch.x - 12, top: 225 + ch.y - 10 }} width="28" height="20" viewBox="0 0 28 20">
                  <ellipse cx="14" cy="10" rx="11" ry="8"
                    fill={emReuniao && ci < meuSquad.num_agentes ? `${CORES[ci % CORES.length]}20` : 'var(--of-keyboard)'}
                    stroke={emReuniao && ci < meuSquad.num_agentes ? `${CORES[ci % CORES.length]}35` : 'var(--of-desk-dark)'}
                    strokeWidth=".5" opacity=".6" />
                </svg>
              ))}

              {/* Telão grande premium */}
              <div className="absolute" style={{ left: 90, top: 22 }}>
                <svg width="240" height="50" viewBox="0 0 240 50">
                  {/* Moldura fina */}
                  <rect x="15" y="2" width="170" height="32" rx="4" fill={emReuniao ? 'var(--of-monitor)' : 'var(--of-screen-off)'}
                    stroke={emReuniao ? 'rgba(16,185,129,.3)' : 'var(--of-monitor-bezel)'} strokeWidth="1.5" />
                  {emReuniao ? (
                    <g>
                      <rect x="22" y="7" width="55" height="2.5" rx={.5} fill="#10b98145" style={{ animation: 'screenGlow 2s infinite' }} />
                      <rect x="22" y="12" width="80" height="2" rx={.5} fill="#10b98130" style={{ animation: 'screenGlow 2.5s infinite .3s' }} />
                      <rect x="22" y="17" width="40" height="2" rx={.5} fill="#10b98135" style={{ animation: 'screenGlow 3s infinite .6s' }} />
                      <rect x="22" y="22" width="65" height="2" rx={.5} fill="#10b98128" style={{ animation: 'screenGlow 2s infinite .9s' }} />
                      <circle cx="175" cy="8" r="3" fill="#ef4444" opacity=".7">
                        <animate attributeName="opacity" values=".3;.8;.3" dur="1.5s" repeatCount="indefinite" />
                      </circle>
                      <text x="175" y="17" textAnchor="middle" fill="#ef4444" fontSize="4" opacity=".5">REC</text>
                    </g>
                  ) : (
                    <text x="100" y="22" textAnchor="middle" fill="var(--of-desk-dark)" fontSize="6" opacity=".2">DISPLAY</text>
                  )}
                  {/* Stand fino */}
                  <rect x="94" y="34" width="12" height="6" fill="var(--of-monitor-bezel)" />
                  <rect x="85" y="40" width="30" height="3" rx="1.5" fill="var(--of-monitor-bezel)" />
                </svg>
              </div>

              {/* Plantas na sala */}
              <Plant x={12} y={22} size={.9} delay={2.5} />
              <Plant x={388} y={430} size={.9} delay={3} />

              {/* Label */}
              <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                {emReuniao ? (
                  <div className="flex items-center gap-2 px-4 py-1.5 rounded-lg" style={{
                    background: 'rgba(16,185,129,.08)',
                    border: '1px solid rgba(16,185,129,.2)',
                    boxShadow: '0 4px 16px rgba(16,185,129,.08)',
                  }}>
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] font-semibold text-emerald-400">Reunião Ativa</span>
                    <span className="text-[9px]" style={{ color: 'var(--of-text-dim)' }}>· {meuSquad.num_agentes} agentes</span>
                  </div>
                ) : (
                  <p className="text-[9px]" style={{ color: 'var(--of-text-dim)' }}>Sala de Reunião</p>
                )}
              </div>
            </div>

            {/* Máquina de café premium */}
            <CoffeeMachine x={MEET_CENTER.x + 240} y={MEET_CENTER.y + 110} />

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

                    {/* Nome e status do agente */}
                    <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                      <p className="text-[13px] font-bold" style={{
                        color: isV || emReuniao ? 'var(--of-text-dim)' : isH ? a.cor : 'var(--of-text)',
                        letterSpacing: '0.01em', transition: 'color .2s',
                      }}>{a.nome}</p>
                      <p className="text-[9px]" style={{ color: 'var(--of-text-dim)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
                    {/* Foto real flutuante acima do boneco */}
                    {buscarAgente(a.nome) && (
                      <div className="absolute -top-10 left-1/2 -translate-x-1/2" style={{ zIndex: 2 }}>
                        <AgentAvatarPhoto agentName={a.nome} size="lg"
                          showStatus status={st === 'trabalhando' ? 'ocupado' : st === 'reuniao' ? 'ocupado' : 'online'}
                          noHover />
                      </div>
                    )}
                    <AgentAvatar cor={a.cor} skin={a.skin} hair={a.hair}
                      status={st === 'trabalhando' && !isV && !emReuniao ? 'typing' : emReuniao ? 'idle' : 'idle'} />
                    {/* Tooltip hover */}
                    <AnimatePresence>
                      {isH && !isV && !emReuniao && (
                        <motion.div className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap"
                          initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}>
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg" style={{
                            background: 'var(--of-wall)', border: '1px solid var(--of-glass-edge)',
                            boxShadow: '0 6px 20px rgba(0,0,0,.12)',
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
        style={{
          background: 'var(--of-wall)',
          border: '1px solid var(--of-glass-edge)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 40px rgba(0,0,0,.1)',
        }}>
        <span className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--of-text-dim)' }}>
          <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(16,185,129,.4)' }} /> Disponível
        </span>
        <span className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--of-text-dim)' }}>
          <span className="w-2.5 h-2.5 bg-blue-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(59,130,246,.4)' }} /> Trabalhando
        </span>
        <span className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--of-text-dim)' }}>
          <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" style={{ boxShadow: '0 0 6px rgba(245,158,11,.4)' }} /> Em reunião
        </span>
        {visitando !== null && <>
          <span style={{ color: 'var(--of-text-dim)' }}>·</span>
          <button onClick={() => setVisitando(null)} className="text-[10px] hover:text-emerald-400 transition-colors"
            style={{ color: 'var(--of-text-dim)' }}>
            Dispensar {agentes[visitando]?.nome}
          </button>
        </>}
      </div>
    </div>
  )
}
