/* Escritório Virtual — Isométrico premium estilo Sowork */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarSquads, buscarHistoricoTarefas } from '../services/api'
import { useChatManager } from '../components/ChatManager'
import type { TarefaResultado } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { Users, MessageSquare, Crown, X, User, Eye, ChevronDown, Video } from 'lucide-react'
import ReuniaoVideo from '../components/ReuniaoVideo'
import { motion, AnimatePresence } from 'framer-motion'

interface SquadComMeta {
  nome: string; especialidade: string; contexto: string
  num_agentes: number; num_tarefas: number; nomes_agentes: string[]
  proprietario_email?: string; tipo?: string; is_meu?: boolean
}

const CORES = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ec4899','#6366f1','#ef4444','#14b8a6','#d946ef','#f97316','#06b6d4','#84cc16']
const SKINS = ['#f5d0a9','#8d5524','#c68642','#f5d0a9','#a0522d','#f5cba7','#c68642','#f5cba7','#c68642','#f5d0a9','#8d5524','#f5cba7']
const HAIRS = ['#1a1a2e','#0a0a0a','#2d1810','#0a0a0a','#1a1000','#b8860b','#0a0a0a','#3d2b1f','#1a0a00','#1a1a2e','#0a0a0a','#3d2b1f']

function agCfg(i: number, name: string) {
  const label = name.split('/')[0]?.trim() || name
  return { nome: label.split(' ')[0] || `Ag${i+1}`, label, cor: CORES[i%CORES.length], skin: SKINS[i%SKINS.length], hair: HAIRS[i%HAIRS.length] }
}

/* Positions — CANVAS 2X MAIOR (1400x700) com espaçamento generoso */
const DK = [
  {x:380,y:100},{x:580,y:100},{x:780,y:100},
  {x:380,y:260},{x:580,y:260},{x:780,y:260},
  {x:380,y:420},{x:580,y:420},{x:780,y:420},
]
const CEO = {x:100,y:230}
const CEO_SIDE = {x:220,y:200}
const MEET = {x:1080,y:230}
/* Posições das cadeiras ao redor da mesa de reunião (até 12 cadeiras) */
const MEET_CHAIRS = [
  {x:-90,y:-45},{x:-45,y:-70},{x:15,y:-75},{x:75,y:-65},{x:120,y:-35},  // topo
  {x:120,y:35},{x:75,y:65},{x:15,y:75},{x:-45,y:70},{x:-90,y:45},       // baixo
  {x:-110,y:0},{x:140,y:0},                                               // laterais
]

const CSS = `
@keyframes typing{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.5px)}}
@keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.01)}}
@keyframes screenPulse{0%,100%{opacity:.5}50%{opacity:.9}}
@keyframes steam{0%{opacity:.4;transform:translateY(0) scale(1)}100%{opacity:0;transform:translateY(-10px) scale(1.5)}}
@keyframes leafSway{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(2deg)}}
@keyframes meetGlow{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.2)}50%{box-shadow:0 0 0 15px rgba(16,185,129,0)}}
`

/* ===== FLOOR PATTERN — Wood planks ===== */
function WoodFloor() {
  return (
    <div className="absolute inset-0" style={{
      background: 'var(--office-floor)',
      backgroundImage: `
        repeating-linear-gradient(90deg, transparent, transparent 79px, var(--office-floor-line) 79px, var(--office-floor-line) 80px),
        repeating-linear-gradient(0deg, transparent, transparent 19px, var(--office-floor-line) 19px, var(--office-floor-line) 20px)
      `,
    }} />
  )
}

/* ===== WALL with windows ===== */
function BackWall() {
  return (
    <div className="absolute top-0 left-0 right-0" style={{ height: 60, background: 'var(--office-wall)', borderBottom: '3px solid var(--office-wall-trim)' }}>
      {/* Windows — mais janelas para canvas maior */}
      {[120, 300, 480, 660, 840, 1020, 1200].map((x, i) => (
        <div key={i} className="absolute" style={{
          left: x, top: 8, width: 120, height: 38, borderRadius: 4,
          background: 'var(--office-window)',
          border: '2px solid var(--office-wall-trim)',
          boxShadow: 'inset 0 0 20px var(--office-window-glow)',
        }}>
          {/* Window divider */}
          <div className="absolute top-0 bottom-0 left-1/2" style={{ width: 2, background: 'var(--office-wall-trim)' }} />
          {/* Sky reflection */}
          <div className="absolute inset-1 opacity-30" style={{ background: 'linear-gradient(180deg, var(--office-sky) 0%, transparent 100%)' }} />
        </div>
      ))}
    </div>
  )
}

/* ===== DESK — Top-down with monitor, keyboard, items ===== */
function Desk({ cor, active, isCeo }: { cor: string; active: boolean; isCeo?: boolean }) {
  const w = isCeo ? 140 : 110
  const h = isCeo ? 65 : 50
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      {/* Shadow */}
      <ellipse cx={w/2} cy={h-3} rx={w*.42} ry={6} fill="rgba(0,0,0,.08)" />
      {/* Desk surface */}
      <rect x={4} y={8} width={w-8} height={h-16} rx={4}
        fill="var(--office-desk)" stroke={active ? cor : 'var(--office-desk-edge)'} strokeWidth={active ? 1.5 : .5} />
      {/* Wood grain subtle */}
      <line x1={10} y1={15} x2={w-10} y2={15} stroke="var(--office-desk-grain)" strokeWidth=".3" />
      <line x1={10} y1={25} x2={w-10} y2={25} stroke="var(--office-desk-grain)" strokeWidth=".3" />
      <line x1={10} y1={35} x2={w-10} y2={35} stroke="var(--office-desk-grain)" strokeWidth=".3" />
      {/* Monitor */}
      <rect x={w*.25} y={2} width={w*.35} height={w*.2} rx={2}
        fill="var(--office-monitor)" stroke={active ? `${cor}80` : 'var(--office-monitor-bezel)'} strokeWidth={1} />
      {/* Screen */}
      <rect x={w*.27} y={4} width={w*.31} height={w*.15} rx={1}
        fill={active ? `${cor}25` : 'var(--office-screen-off)'} />
      {active && (
        <g style={{ animation: 'screenPulse 2.5s infinite' }}>
          <rect x={w*.29} y={7} width={w*.15} height={2} rx={.5} fill={`${cor}50`} />
          <rect x={w*.29} y={11} width={w*.22} height={2} rx={.5} fill={`${cor}35`} />
          <rect x={w*.29} y={15} width={w*.10} height={2} rx={.5} fill={`${cor}40`} />
        </g>
      )}
      {/* Monitor stand */}
      <rect x={w*.39} y={w*.2+1} width={w*.07} height={5} fill="var(--office-monitor-bezel)" />
      <rect x={w*.33} y={w*.2+5} width={w*.19} height={2} rx={1} fill="var(--office-monitor-bezel)" />
      {/* Keyboard */}
      <rect x={w*.3} y={h-14} width={w*.25} height={8} rx={2}
        fill="var(--office-keyboard)" stroke="var(--office-desk-edge)" strokeWidth=".3" />
      {/* Mouse */}
      <ellipse cx={w*.65} cy={h-10} rx={4} ry={5} fill="var(--office-keyboard)" stroke="var(--office-desk-edge)" strokeWidth=".3" />
      {/* Coffee mug (CEO only) */}
      {isCeo && (
        <g>
          <rect x={w-25} y={12} width={8} height={10} rx={2} fill="var(--office-mug)" />
          <path d={`M${w-17} ${14} Q${w-12} ${16} ${w-17} ${20}`} stroke="var(--office-mug)" strokeWidth="1.2" fill="none" />
        </g>
      )}
      {/* Legs */}
      <rect x={8} y={h-8} width={3} height={8} rx={1} fill="var(--office-desk-leg)" />
      <rect x={w-11} y={h-8} width={3} height={8} rx={1} fill="var(--office-desk-leg)" />
    </svg>
  )
}

/* ===== CHAIR ===== */
function Chair({ cor }: { cor: string }) {
  return (
    <svg width="30" height="20" viewBox="0 0 30 20" className="absolute" style={{ bottom: -12, left: '50%', marginLeft: -15 }}>
      <ellipse cx="15" cy="10" rx="12" ry="8" fill={`${cor}30`} stroke={`${cor}50`} strokeWidth=".5" />
      <ellipse cx="15" cy="9" rx="10" ry="6" fill={`${cor}20`} />
    </svg>
  )
}

/* ===== PERSON ===== */
function Person({ cor, skin, hair, size=1, isTyping=false }: {
  cor:string; skin:string; hair:string; size?:number; isTyping?:boolean
}) {
  const s = 24 * size
  return (
    <svg width={s} height={s*1.55} viewBox="0 0 24 37" style={{
      animation: isTyping ? 'typing .65s infinite' : 'breathe 3.5s infinite',
      transformOrigin: 'bottom center', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.15))',
    }}>
      <ellipse cx="12" cy="35" rx="7" ry="2" fill="rgba(0,0,0,.1)" />
      <path d="M6.5 17 Q12 14.5 17.5 17 L18.5 28 Q12 30 5.5 28 Z" fill={`${cor}bb`} />
      {isTyping ? (
        <>
          <path d="M6.5 18 Q3 22 5.5 25" stroke={skin} strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d="M17.5 18 Q21 22 18.5 25" stroke={skin} strokeWidth="2" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <path d="M6.5 18 Q4 25 6.5 29" stroke={skin} strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d="M17.5 18 Q20 25 17.5 29" stroke={skin} strokeWidth="2" fill="none" strokeLinecap="round" />
        </>
      )}
      <circle cx="12" cy="9" r="6.5" fill={skin} />
      <ellipse cx="12" cy="5.5" rx="6" ry="4" fill={hair} />
      <circle cx="9.5" cy="10" r=".8" fill="#1a1a1a" />
      <circle cx="14.5" cy="10" r=".8" fill="#1a1a1a" />
      <circle cx="9.8" cy="9.6" r=".2" fill="white" />
      <circle cx="14.8" cy="9.6" r=".2" fill="white" />
      <path d="M10 12.5 Q12 13.8 14 12.5" stroke="#1a1a1a" strokeWidth=".4" fill="none" />
    </svg>
  )
}

/* ===== PLANT ===== */
function Plant({ x, y, size=1 }: { x:number; y:number; size?:number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left:x, top:y, transformOrigin:'bottom center', animation:'leafSway 5s infinite ease-in-out' }}>
      <svg width={18*size} height={30*size} viewBox="0 0 18 30">
        <rect x="6" y="20" width="6" height="10" rx="2" fill="var(--office-pot)" />
        <ellipse cx="9" cy="19" rx="5" ry="3" fill="#4ade80" opacity=".6" />
        <ellipse cx="7" cy="15" rx="4" ry="5" fill="#22c55e" opacity=".7" />
        <ellipse cx="12" cy="12" rx="3.5" ry="5" fill="#16a34a" opacity=".6" />
        <ellipse cx="9" cy="9" rx="3" ry="4" fill="#15803d" opacity=".8" />
      </svg>
    </div>
  )
}

/* ===== LAMP ===== */
function FloorLamp({ x, y }: { x:number; y:number }) {
  return (
    <div className="absolute pointer-events-none" style={{ left:x, top:y }}>
      <svg width="16" height="40" viewBox="0 0 16 40">
        <rect x="7" y="12" width="2" height="25" fill="var(--office-lamp-pole)" />
        <ellipse cx="8" cy="38" rx="5" ry="2" fill="var(--office-lamp-pole)" opacity=".5" />
        <path d="M2 12 L8 2 L14 12 Z" fill="var(--office-lamp-shade)" />
        <circle cx="8" cy="10" r="2" fill="#fbbf24" opacity=".4" />
      </svg>
    </div>
  )
}

/* ===== THEME VARS ===== */
const themeCSS = `
:root {
  --office-floor: #e8ddd0; --office-floor-line: rgba(0,0,0,.04);
  --office-wall: #f5f0ea; --office-wall-trim: #c9b99a;
  --office-window: rgba(180,210,240,.3); --office-window-glow: rgba(135,206,250,.15); --office-sky: #87ceeb;
  --office-desk: #d4a574; --office-desk-edge: #b8956a; --office-desk-grain: rgba(0,0,0,.06); --office-desk-leg: #a07d5a;
  --office-monitor: #2d2d2d; --office-monitor-bezel: #444; --office-screen-off: #1a1a1a;
  --office-keyboard: #e5e5e5; --office-mug: #c75050;
  --office-pot: #b07050; --office-lamp-pole: #888; --office-lamp-shade: #f5e6d3; --office-carpet: #c4b5a0;
}
.dark {
  --office-floor: #151518; --office-floor-line: rgba(255,255,255,.02);
  --office-wall: #1a1a22; --office-wall-trim: #2a2a35;
  --office-window: rgba(60,80,120,.15); --office-window-glow: rgba(100,150,255,.05); --office-sky: #1e293b;
  --office-desk: #2a2218; --office-desk-edge: #3a3020; --office-desk-grain: rgba(255,255,255,.03); --office-desk-leg: #1e1810;
  --office-monitor: #0a0a0e; --office-monitor-bezel: #222; --office-screen-off: #0a0a0a;
  --office-keyboard: #2a2a2a; --office-mug: #8b3030;
  --office-pot: #4a3028; --office-lamp-pole: #444; --office-lamp-shade: #2a2520; --office-carpet: #1a1820;
}
`

export default function Escritorio() {
  const { abrirChat, abrirReuniao } = useChatManager()
  const { usuario } = useAuth()
  const fetchSquads = useCallback(() => buscarSquads(), [])
  const fetchTarefas = useCallback(() => buscarHistoricoTarefas(20), [])
  const { dados: squadsData } = usePolling(fetchSquads, 15000)
  const { dados: tarefasData } = usePolling(fetchTarefas, 3000)

  const [hovered, setHovered] = useState<number|null>(null)
  const [visitando, setVisitando] = useState<number|null>(null)
  const [emReuniao, setEmReuniao] = useState(false)
  const [squadSelecionado, setSquadSelecionado] = useState<string|null>(null)
  const [mostrarSeletor, setMostrarSeletor] = useState(false)
  const [videoCall, setVideoCall] = useState<{sala:string;participantes:string[]}|null>(null)

  const squads = (squadsData||[]) as SquadComMeta[]
  const tarefas = (tarefasData||[]) as TarefaResultado[]
  const squadsPessoais = squads.filter(s => s.tipo === 'pessoal')
  const temVisaoGeral = squadsPessoais.length > 1
  const meuSquadOriginal = squads.find(s => s.is_meu)
  const verTodos = squadSelecionado === '__todos__'
  const meuSquad = verTodos ? meuSquadOriginal : squadSelecionado ? squads.find(s => s.nome === squadSelecionado) || meuSquadOriginal : meuSquadOriginal
  const nomeUsuario = meuSquad?.is_meu ? (usuario?.nome||'Usuário') : (meuSquad?.nome.split('—')[1]?.trim()||'Usuário')

  const getStatus = (i:number) => {
    if (!meuSquad) return 'livre'
    if (emReuniao) return 'reuniao'
    if (visitando === i) return 'reuniao'
    if (tarefas.find(t => t.squad_nome === meuSquad.nome && t.agente_indice === i && t.status === 'executando')) return 'trabalhando'
    return 'livre'
  }

  const handleClick = (i:number) => {
    if (emReuniao) return
    if (visitando === i) { setVisitando(null); return }
    setVisitando(i)
    abrirChat(meuSquad!.nome, i, meuSquad!.nomes_agentes[i]||`Agente ${i+1}`)
  }

  const handleReunir = () => {
    if (emReuniao) { setEmReuniao(false); setVisitando(null) }
    else { setVisitando(null); setEmReuniao(true); abrirReuniao(meuSquad!.nome, meuSquad!.nomes_agentes.map((n,i) => ({idx:i,nome:n}))) }
  }

  if (!meuSquad) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"/></div>

  const getPos = (i:number) => {
    if (emReuniao) {
      const chair = MEET_CHAIRS[i % MEET_CHAIRS.length]
      return { x: MEET.x + chair.x, y: MEET.y + chair.y }
    }
    if (visitando === i) return CEO_SIDE
    return DK[i]||DK[0]
  }

  return (
    <div className="sf-page overflow-hidden select-none" style={{margin:'-24px',padding:0,minHeight:'100vh'}}
      onClick={() => mostrarSeletor && setMostrarSeletor(false)}>
      <style>{CSS}{themeCSS}</style>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-8 pt-5 pb-3">
        <div>
          <h2 className="text-2xl font-bold sf-text-white" style={{letterSpacing:'-0.02em'}}>Escritório Virtual</h2>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-xs sf-text-dim">{meuSquad.nome} · {meuSquad.num_agentes} agentes</p>
            {temVisaoGeral && (
              <div className="relative">
                <button onClick={() => setMostrarSeletor(!mostrarSeletor)}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-medium bg-purple-500/15 text-purple-400 border border-purple-500/25 hover:bg-purple-500/25 transition-all">
                  <Eye size={10}/>{squadSelecionado ? 'Visão Geral' : 'Ver outros squads'}<ChevronDown size={10}/>
                </button>
                {mostrarSeletor && (
                  <div className="absolute top-full left-0 mt-1 rounded-xl shadow-2xl py-1 z-30 min-w-[220px]" style={{background:'var(--sf-bg-1)',border:'1px solid var(--sf-border-default)'}}>
                    <button onClick={() => {setSquadSelecionado('__todos__');setMostrarSeletor(false);setVisitando(null);setEmReuniao(false)}}
                      className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${verTodos?'text-purple-400 bg-purple-500/10':'sf-text-dim hover:bg-white/5'}`}>
                      <Eye size={11}/> Ver todos
                    </button>
                    <div className="mx-3 my-1" style={{borderTop:'1px solid var(--sf-border-subtle)'}}/>
                    <button onClick={() => {setSquadSelecionado(null);setMostrarSeletor(false);setVisitando(null);setEmReuniao(false)}}
                      className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${!squadSelecionado?'text-emerald-400 bg-emerald-500/10':'sf-text-dim hover:bg-white/5'}`}>
                      <Crown size={11}/> {meuSquadOriginal?.nome||'Meu Squad'}
                    </button>
                    {squadsPessoais.filter(s => !s.is_meu).map(s => (
                      <button key={s.nome} onClick={() => {setSquadSelecionado(s.nome);setMostrarSeletor(false);setVisitando(null);setEmReuniao(false)}}
                        className={`w-full text-left px-4 py-2.5 text-xs flex items-center gap-2 ${squadSelecionado===s.nome?'text-purple-400 bg-purple-500/10':'sf-text-dim hover:bg-white/5'}`}>
                        <User size={11}/> {s.nome} <span className="ml-auto text-[9px] sf-text-ghost">{s.num_agentes}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {squadSelecionado && <button onClick={() => {setSquadSelecionado(null);setVisitando(null);setEmReuniao(false)}}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20">
              Voltar ao meu squad
            </button>}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setVideoCall({ sala: `sf-${Date.now()}`, participantes: [usuario?.nome || 'CEO', 'Jonatas'] })}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/20 hover:bg-blue-500/25 transition-all"
          >
            <Video size={13}/> Video Call
          </button>
          <button onClick={handleReunir} className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
            emReuniao ? 'bg-red-500/15 text-red-400 border border-red-500/20':'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'}`}>
            {emReuniao ? <><X size={13}/> Encerrar Reunião</> : <><Users size={13}/> Reunir todos</>}
          </button>
        </div>
      </div>

      {/* Ver Todos */}
      {verTodos && (
        <div className="px-8 pb-8 overflow-y-auto" style={{height:'calc(100vh - 120px)'}}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {squadsPessoais.map(sq => (
              <div key={sq.nome} className="rounded-2xl p-5 cursor-pointer hover:-translate-y-0.5 transition-all"
                style={{background:'var(--sf-bg-2)',border:`1px solid ${sq.is_meu?'rgba(16,185,129,.3)':'var(--sf-border-default)'}`}}
                onClick={() => {setSquadSelecionado(sq.nome);setVisitando(null);setEmReuniao(false)}}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{background:sq.is_meu?'rgba(16,185,129,.15)':'rgba(139,92,246,.15)'}}>
                    {sq.is_meu ? <Crown size={18} className="text-emerald-400"/> : <User size={18} className="text-purple-400"/>}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold sf-text-white">{sq.nome}</h3>
                    <p className="text-[10px] sf-text-dim">{sq.especialidade}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {sq.nomes_agentes.map((n,i) => {
                    const a = agCfg(i,n)
                    return <div key={i} className="flex flex-col items-center"><Person cor={a.cor} skin={a.skin} hair={a.hair} size={.6}/><p className="text-[6px] sf-text-ghost">{a.nome}</p></div>
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===== OFFICE SCENE ===== */}
      {!verTodos && (
        <div className="relative w-full overflow-x-auto overflow-y-auto" style={{height:'calc(100vh - 100px)'}}>
          <div className="relative mx-auto" style={{width:1400,height:620,minWidth:1400}}>

            {/* Wood floor */}
            <WoodFloor />

            {/* Back wall with windows */}
            <BackWall />

            {/* Decorative elements — mais plantas e lâmpadas para canvas maior */}
            <Plant x={50} y={70} size={1.4} />
            <Plant x={300} y={60} size={1.1} />
            <Plant x={950} y={65} size={1.2} />
            <Plant x={1350} y={70} size={1.3} />
            <Plant x={50} y={450} size={1.1} />
            <Plant x={950} y={500} />
            <FloorLamp x={260} y={55} />
            <FloorLamp x={940} y={55} />
            <FloorLamp x={1340} y={400} />

            {/* ===== CEO DESK ===== */}
            <div className="absolute" style={{left:CEO.x-20,top:CEO.y-15,zIndex:25}}>
              {/* Glow highlight */}
              <div className="absolute -inset-8 rounded-3xl" style={{background:'radial-gradient(ellipse,rgba(16,185,129,.08) 0%,transparent 70%)'}}/>

              <div className="absolute -top-8 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1 rounded-lg"
                style={{background:'var(--sf-accent-dim)',border:'1px solid rgba(16,185,129,.25)'}}>
                <Crown size={9} className="text-emerald-400"/><span className="text-[9px] font-bold text-emerald-400 tracking-widest">CEO</span>
              </div>

              <Desk cor="#10b981" active isCeo />
              <Chair cor="#10b981" />

              <div className="absolute" style={{left:52,top:-35}}>
                <Person cor="#10b981" skin="#f5cba7" hair="#3d2b1f" size={1.05} isTyping={visitando===null && !emReuniao}/>
              </div>

              <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                <p className="text-[13px] font-bold text-emerald-500">{nomeUsuario}</p>
                <p className="text-[9px] sf-text-dim">Sua mesa</p>
              </div>

              <AnimatePresence>
                {visitando !== null && !emReuniao && (() => {
                  const v = agCfg(visitando, meuSquad?.nomes_agentes[visitando]||'')
                  return (
                    <motion.div className="absolute" style={{left:130,top:-25,zIndex:40}}
                      initial={{opacity:0,scale:.5}} animate={{opacity:1,scale:1}} exit={{opacity:0,scale:.5}} transition={{duration:.4,ease:'backOut'}}>
                      <Person cor={v.cor} skin={v.skin} hair={v.hair}/>
                      <motion.div className="absolute -top-5 left-1/2 -translate-x-1/2" initial={{scale:0}} animate={{scale:1}} transition={{delay:.3,type:'spring'}}>
                        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full" style={{background:'var(--sf-bg-elevated)',border:'1px solid var(--sf-border-default)'}}>
                          <MessageSquare size={7} className="text-emerald-400"/><span className="text-[7px] text-emerald-400 font-medium">Chat</span>
                        </div>
                      </motion.div>
                      <p className="text-[7px] font-medium text-center mt-1" style={{color:v.cor}}>{v.nome}</p>
                    </motion.div>
                  )
                })()}
              </AnimatePresence>
            </div>

            {/* ===== MEETING ROOM — Premium Conference Room ===== */}
            <div className="absolute" style={{left:MEET.x-140,top:MEET.y-120,width:320,height:280,zIndex:5}}>

              {/* Room outline — glass walls */}
              <div className="absolute inset-0 rounded-2xl transition-all duration-700"
                style={{
                  border: emReuniao ? '2px solid rgba(16,185,129,.25)' : '1.5px solid var(--office-wall-trim)',
                  background: emReuniao ? 'rgba(16,185,129,.03)' : 'var(--office-window)',
                  boxShadow: emReuniao ? '0 0 30px rgba(16,185,129,.08), inset 0 0 20px rgba(16,185,129,.03)' : 'none',
                  backdropFilter: 'blur(1px)',
                }}>

                {/* Glass panel reflections */}
                <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl" style={{background:'linear-gradient(90deg,transparent,rgba(255,255,255,.06),transparent)'}} />
                <div className="absolute top-0 bottom-0 left-0 w-[2px] rounded-l-2xl" style={{background:'linear-gradient(180deg,transparent,rgba(255,255,255,.04),transparent)'}} />
              </div>

              {/* Carpet / Floor */}
              <div className="absolute rounded-xl" style={{left:15,top:20,right:15,bottom:15,background:'var(--office-carpet)',opacity:.5,borderRadius:12}} />

              {/* Conference Table — large oval */}
              <svg className="absolute pointer-events-none" style={{left:55,top:80}} width="210" height="110" viewBox="0 0 210 110">
                {/* Table shadow */}
                <ellipse cx="105" cy="60" rx="95" ry="45" fill="rgba(0,0,0,.08)" />
                {/* Table surface */}
                <ellipse cx="105" cy="55" rx="90" ry="42" fill="var(--office-desk)" stroke="var(--office-desk-edge)" strokeWidth=".8" />
                {/* Wood grain */}
                <ellipse cx="105" cy="55" rx="75" ry="32" fill="none" stroke="var(--office-desk-grain)" strokeWidth=".4" />
                <ellipse cx="105" cy="55" rx="55" ry="22" fill="none" stroke="var(--office-desk-grain)" strokeWidth=".3" />
                {/* Items on table */}
                {emReuniao && (
                  <g>
                    {/* Laptop */}
                    <rect x="55" y="30" width="15" height="10" rx="1.5" fill="var(--office-monitor)" stroke="var(--office-monitor-bezel)" strokeWidth=".3" />
                    {/* Notebook */}
                    <rect x="85" y="28" width="12" height="16" rx="1" fill="var(--office-keyboard)" opacity=".5" />
                    {/* Coffee cups */}
                    <circle cx="45" cy="38" r="3" fill="var(--office-mug)" opacity=".6" />
                    <circle cx="110" cy="42" r="3" fill="var(--office-mug)" opacity=".5" />
                    {/* Pen */}
                    <line x1="95" y1="46" x2="105" y2="48" stroke="var(--office-lamp-pole)" strokeWidth="1" strokeLinecap="round" />
                  </g>
                )}
              </svg>

              {/* Chairs around table */}
              {MEET_CHAIRS.slice(0, Math.max(meuSquad?.num_agentes || 0, 6)).map((ch, ci) => (
                <svg key={ci} className="absolute pointer-events-none" style={{left:140+ch.x-10,top:130+ch.y-8}} width="24" height="18" viewBox="0 0 24 18">
                  <ellipse cx="10" cy="8" rx="9" ry="6"
                    fill={emReuniao && ci < (meuSquad?.num_agentes||0) ? `${CORES[ci%CORES.length]}20` : 'var(--office-keyboard)'}
                    stroke={emReuniao && ci < (meuSquad?.num_agentes||0) ? `${CORES[ci%CORES.length]}40` : 'var(--office-desk-edge)'}
                    strokeWidth=".4" opacity=".7" />
                </svg>
              ))}

              {/* Telão / Screen on wall */}
              <div className="absolute" style={{left:70,top:10}}>
                <svg width="180" height="40" viewBox="0 0 180 40">
                  {/* Frame */}
                  <rect x="5" y="2" width="110" height="22" rx="2"
                    fill={emReuniao ? 'var(--office-monitor)' : 'var(--office-screen-off)'}
                    stroke={emReuniao ? 'rgba(16,185,129,.4)' : 'var(--office-monitor-bezel)'} strokeWidth="1" />
                  {/* Screen content */}
                  {emReuniao ? (
                    <g>
                      <rect x="10" y="6" width="40" height="2" rx=".5" fill="#10b98150" style={{animation:'screenPulse 2s infinite'}} />
                      <rect x="10" y="10" width="60" height="2" rx=".5" fill="#10b98135" style={{animation:'screenPulse 2.5s infinite .3s'}} />
                      <rect x="10" y="14" width="30" height="2" rx=".5" fill="#10b98140" style={{animation:'screenPulse 3s infinite .6s'}} />
                      <rect x="10" y="18" width="50" height="2" rx=".5" fill="#10b98130" style={{animation:'screenPulse 2s infinite .9s'}} />
                      {/* Recording indicator */}
                      <circle cx="105" cy="7" r="2.5" fill="#ef4444" opacity=".8">
                        <animate attributeName="opacity" values=".4;.9;.4" dur="1.5s" repeatCount="indefinite" />
                      </circle>
                    </g>
                  ) : (
                    <text x="60" y="16" textAnchor="middle" fill="var(--office-desk-edge)" fontSize="5" opacity=".4">DISPLAY</text>
                  )}
                  {/* Stand */}
                  <rect x="55" y="24" width="10" height="4" fill="var(--office-monitor-bezel)" />
                </svg>
              </div>

              {/* Plants in corners */}
              <svg className="absolute pointer-events-none" style={{left:8,top:15,animation:'leafSway 5s infinite'}} width="14" height="24" viewBox="0 0 14 24">
                <rect x="4" y="16" width="5" height="8" rx="1.5" fill="var(--office-pot)" />
                <ellipse cx="7" cy="14" rx="4" ry="4" fill="#22c55e" opacity=".6" />
                <ellipse cx="5" cy="11" rx="3" ry="4" fill="#16a34a" opacity=".5" />
              </svg>
              <svg className="absolute pointer-events-none" style={{right:8,bottom:15,animation:'leafSway 6s infinite .5s'}} width="14" height="24" viewBox="0 0 14 24">
                <rect x="4" y="16" width="5" height="8" rx="1.5" fill="var(--office-pot)" />
                <ellipse cx="7" cy="14" rx="4" ry="4" fill="#4ade80" opacity=".5" />
                <ellipse cx="9" cy="11" rx="3" ry="3.5" fill="#22c55e" opacity=".6" />
              </svg>

              {/* Wall art / Frame */}
              <svg className="absolute pointer-events-none" style={{left:18,top:8}} width="25" height="18" viewBox="0 0 25 18">
                <rect x="1" y="1" width="23" height="16" rx="1" fill="var(--office-wall)" stroke="var(--office-desk-edge)" strokeWidth=".5" />
                <rect x="3" y="3" width="19" height="12" rx=".5" fill="var(--office-window)" opacity=".3" />
              </svg>

              {/* Label */}
              <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                {emReuniao ? (
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/25">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[9px] font-semibold text-emerald-400">Reunião Ativa</span>
                    <span className="text-[8px] sf-text-ghost">· {meuSquad?.num_agentes} agentes</span>
                  </div>
                ) : (
                  <p className="text-[8px] sf-text-ghost">Sala de Reunião</p>
                )}
              </div>
            </div>

            {/* ===== AGENT DESKS ===== */}
            {DK.map((d,i) => {
              if (i >= (meuSquad?.num_agentes||0)) return null
              const a = agCfg(i, meuSquad?.nomes_agentes[i]||'')
              const st = getStatus(i)
              const isH = hovered===i
              const isV = visitando===i
              const tp = getPos(i)
              const sc = st==='trabalhando'?'#3b82f6':st==='reuniao'?'#f59e0b':'#10b981'

              return (
                <div key={i}>
                  {/* Fixed desk */}
                  <div className="absolute" style={{left:d.x-15,top:d.y,zIndex:10+Math.floor(d.y/20)}}>
                    <Desk cor={a.cor} active={(isH||st==='trabalhando') && !isV && !emReuniao}/>
                    <Chair cor={a.cor}/>

                    <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                      <p className="text-[11px] font-bold" style={{color:isV||emReuniao?'var(--sf-text-4)':isH?a.cor:'var(--sf-text-2)',letterSpacing:'0.01em'}}>{a.nome}</p>
                      <p className="text-[9px] sf-text-dim" style={{maxWidth:120,overflow:'hidden',textOverflow:'ellipsis'}}>{a.label}</p>
                    </div>

                    <div className="absolute -top-1 right-0 flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full border border-white/20" style={{
                        backgroundColor:sc, opacity:isV||emReuniao?.3:1,
                        boxShadow:st!=='livre'?`0 0 6px ${sc}60`:'none',
                      }}/>
                    </div>
                  </div>

                  {/* Animated agent */}
                  <motion.div className="absolute cursor-pointer" style={{zIndex:isH?50:20+i}}
                    animate={{x:tp.x+30,y:tp.y-28,scale:isH && !isV && !emReuniao?1.12:1}}
                    transition={{type:'spring',stiffness:100,damping:16,mass:.7}}
                    onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}
                    onClick={() => handleClick(i)}>
                    <Person cor={a.cor} skin={a.skin} hair={a.hair} isTyping={st==='trabalhando' && !isV && !emReuniao}/>
                    <AnimatePresence>
                      {isH && !isV && !emReuniao && (
                        <motion.div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap"
                          initial={{opacity:0,y:3}} animate={{opacity:1,y:0}} exit={{opacity:0,y:3}}>
                          <div className="flex items-center gap-1 px-2 py-0.5 rounded-md" style={{background:'var(--sf-bg-elevated)',border:'1px solid var(--sf-border-default)'}}>
                            <MessageSquare size={7} className="text-emerald-400"/><span className="text-[7px] text-emerald-400 font-medium">Chamar</span>
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
        <ReuniaoVideo
          sala={videoCall.sala}
          participantes={videoCall.participantes}
          onFechar={() => setVideoCall(null)}
        />
      )}

      {/* Legend */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-6 px-5 py-2.5 rounded-2xl"
        style={{background:'var(--sf-bg-elevated)',border:'1px solid var(--sf-border-default)',backdropFilter:'blur(12px)'}}>
        <span className="flex items-center gap-1.5 text-[10px] sf-text-dim"><span className="w-2 h-2 bg-emerald-500 rounded-full"/> Disponível</span>
        <span className="flex items-center gap-1.5 text-[10px] sf-text-dim"><span className="w-2 h-2 bg-blue-500 rounded-full"/> Trabalhando</span>
        <span className="flex items-center gap-1.5 text-[10px] sf-text-dim"><span className="w-2 h-2 bg-amber-500 rounded-full"/> Em reunião</span>
        {visitando!==null && <>
          <span className="sf-text-ghost">·</span>
          <button onClick={() => setVisitando(null)} className="text-[10px] sf-text-dim hover:text-emerald-400 transition-colors">
            Dispensar {agCfg(visitando, meuSquad?.nomes_agentes[visitando]||'').nome}
          </button>
        </>}
      </div>
    </div>
  )
}
