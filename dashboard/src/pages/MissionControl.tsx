/* Mission Control — v0.58.19
 * Adiciona Phase Decision Controls para aprovacao de fases
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Rocket, Loader2, Bot, Terminal, Code2, MessageSquare,
  Package, Sparkles, Plus, X,
  Clock, ArrowRight, Play, Send, Copy, Download,
  Shield, ShieldOff,
} from 'lucide-react'
import PhaseDecisionControls from '../components/PhaseDecisionControls'
import MissionCompleteActions from '../components/MissionCompleteActions'

const API = import.meta.env.VITE_API_URL || ''

interface Artifact {
  artifact_id: string; tipo: string; titulo: string
  conteudo: string | null; dados: Record<string, unknown>
  status: string; agente_nome: string
  comentarios_inline: Array<{
    id: string; linha: number | null; secao: string
    texto: string; autor: string; data: string; resolvido: boolean
  }>
  criado_em: string | null
}

interface AgenteAtivo {
  id: string; nome: string; status: string
  tarefa: string; tipo: string; inicio: string; resultado?: string; erro?: string
  fase_atual?: number; fase_label?: string; progresso?: number
}

interface TerminalEntry { comando: string; saida: string; sucesso: boolean; timestamp: string; tipo?: string }

interface ChatMsg {
  id: number; agente_nome: string; tipo: string
  conteudo: string; fase: string; metadata: Record<string, unknown>
  criado_em: string | null
}

interface Sessao {
  sessao_id: string; titulo: string; status: string; projeto_id: number | null
  agentes_ativos: AgenteAtivo[]; artifacts: Artifact[]
  painel_editor: { conteudo?: string; arquivo_ativo?: string; fonte?: string; streaming?: boolean } | null
  painel_terminal: { historico: TerminalEntry[]; cwd: string } | null
  total_artifacts: number; total_comandos: number
}

interface SessaoResumo {
  sessao_id: string; titulo: string; status: string
  agentes_ativos: AgenteAtivo[]; total_artifacts: number; total_comandos: number
  criado_em: string | null; atualizado_em: string | null
}

export default function MissionControl() {
  const { token } = useAuth()
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()

  const [sessao, setSessao] = useState<Sessao | null>(null)
  const [sessoes, setSessoes] = useState<SessaoResumo[]>([])
  const [carregandoSessoes, setCarregandoSessoes] = useState(true)
  const [criando, setCriando] = useState(false)
  const [titulo, setTitulo] = useState('')

  // Instruction input
  const [instrucao, setInstrucao] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Phase decision state
  const [faseStatus, setFaseStatus] = useState<{
    status: string
    fase_atual: number
    progresso: number
    waiting_decision: boolean
    fase_decisao: string | null
    agente_nome: string | null
  } | null>(null)

  // Team Chat state
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([])
  const chatRef = useRef<HTMLDivElement>(null)

  // Terminal state
  const [comandoTerminal, setComandoTerminal] = useState('')
  const [terminalHistorico, setTerminalHistorico] = useState<TerminalEntry[]>([])
  const [executandoCmd, setExecutandoCmd] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)

  // Artifacts state
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [artifactModal, setArtifactModal] = useState<Artifact | null>(null)
  const [abaPainel3, setAbaPainel3] = useState<'chat' | 'artifacts'>('chat')

  // Plan Mode state
  const [planMode, setPlanMode] = useState(false)
  const [planLoading, setPlanLoading] = useState(false)
  const [planToast, setPlanToast] = useState('')

  // Editor state
  const [editorConteudo, setEditorConteudo] = useState('')
  const [editorArquivo, setEditorArquivo] = useState('novo-arquivo.tsx')

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }), [token])

  // Plan Mode helpers
  const fetchPlanStatus = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${API}/api/mission-control/plan-mode/status`, {
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setPlanMode(data.em_plan_mode)
      }
    } catch { /* silenciar */ }
  }, [token])

  const togglePlanMode = async () => {
    if (!sessao?.sessao_id || planLoading) return
    setPlanLoading(true)
    setPlanToast('')
    const acao = planMode ? 'sair' : 'entrar'
    try {
      const minDelay = new Promise(r => setTimeout(r, 600))
      const [res] = await Promise.all([
        fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/plan-mode/${acao}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ motivo: 'Via Mission Control UI' }),
        }),
        minDelay,
      ])
      if (!res.ok) {
        setPlanToast('Erro ao alterar Plan Mode')
        setTimeout(() => setPlanToast(''), 3000)
        return
      }
      const data = await res.json()
      if (data.sucesso) {
        setPlanMode(acao === 'entrar')
        setPlanToast(acao === 'entrar' ? 'Plan Mode ativado' : 'Modo Normal restaurado')
        setTimeout(() => setPlanToast(''), 2500)
        // Re-fetch para confirmar estado real do servidor
        setTimeout(() => fetchPlanStatus(), 500)
      } else {
        setPlanToast(data.erro || 'Erro ao alterar Plan Mode')
        setTimeout(() => setPlanToast(''), 3000)
      }
    } catch {
      setPlanToast('Falha de conexao')
      setTimeout(() => setPlanToast(''), 3000)
    } finally {
      setPlanLoading(false)
    }
  }

  function tempoRelativo(iso: string | null): string {
    if (!iso) return ''
    const diff = Date.now() - new Date(iso).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return 'agora'
    if (min < 60) return `${min}min`
    const h = Math.floor(min / 60)
    if (h < 24) return `${h}h`
    return `${Math.floor(h / 24)}d`
  }

  /* ============================================================
     Load sessions
   ============================================================ */

  const carregarSessoes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessoes`, { headers })
      if (res.ok) setSessoes(await res.json())
    } catch { /* */ } finally { setCarregandoSessoes(false) }
  }, [headers])

  /* ============================================================
     Load session
   ============================================================ */

  const carregarSessao = useCallback(async (sid: string) => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sid}`, { headers })
      if (!res.ok) return
      const data: Sessao = await res.json()
      setSessao(data)
      setArtifacts(data.artifacts || [])
      setTerminalHistorico(data.painel_terminal?.historico || [])
      if (data.painel_editor?.conteudo) {
        setEditorConteudo(data.painel_editor.conteudo)
        setEditorArquivo(data.painel_editor.arquivo_ativo || 'arquivo.tsx')
      }
    } catch { /* */ }
  }, [headers])

  /* ============================================================
     Create session
   ============================================================ */

  const criarSessao = useCallback(async () => {
    setCriando(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao`, {
        method: 'POST', headers,
        body: JSON.stringify({ titulo: titulo || 'Nova Sessao Mission Control' }),
      })
      const data = await res.json()
      navigate(`/mission-control/${data.sessao_id}`, { replace: true })
    } catch { /* */ } finally { setCriando(false) }
  }, [headers, titulo, navigate])

  /* ============================================================
     Enviar instrucao ao agente
   ============================================================ */

  const enviarInstrucao = useCallback(async () => {
    if (!sessao || !instrucao.trim()) return
    setEnviando(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/agente`, {
        method: 'POST', headers,
        body: JSON.stringify({ instrucao, tipo: 'bmad' }),
      })
      if (res.ok) {
        setInstrucao('')
        await carregarSessao(sessao.sessao_id)
      }
    } catch { /* */ } finally { setEnviando(false) }
  }, [sessao, instrucao, headers, carregarSessao])

  /* ============================================================
     Startup
   ============================================================ */

  useEffect(() => {
    if (urlSessionId) {
      carregarSessao(urlSessionId)
      setCarregandoSessoes(false)
    } else {
      carregarSessoes()
    }
  }, [urlSessionId])

  /* ============================================================
     Chat polling
   ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/chat`, { headers })
        if (res.ok) {
          const msgs: ChatMsg[] = await res.json()
          setChatMsgs(msgs)
        }
      } catch { /* */ }
    }
    poll()
    const timer = setInterval(poll, 3000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, headers])

  /* ============================================================
     Session polling
   ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(() => carregarSessao(sessao.sessao_id), 5000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, carregarSessao])

  /* ============================================================
     Phase status polling — checks if decision is needed
   ============================================================ */

  const carregarFaseStatus = useCallback(async () => {
    if (!sessao?.sessao_id) return
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/fase-status`, { headers })
      if (res.ok) setFaseStatus(await res.json())
    } catch { /* */ }
  }, [sessao?.sessao_id, headers])

  useEffect(() => {
    if (!sessao?.sessao_id) return
    carregarFaseStatus()
    const timer = setInterval(carregarFaseStatus, 2000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, carregarFaseStatus])

  // Plan Mode status — fetch uma vez ao abrir sessão (não no polling)
  useEffect(() => {
    if (!sessao?.sessao_id) return
    fetchPlanStatus()
  }, [sessao?.sessao_id])

  /* ============================================================
     Execute command
   ============================================================ */

  const executarComando = useCallback(async () => {
    if (!sessao || !comandoTerminal.trim()) return
    setExecutandoCmd(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/comando`, {
        method: 'POST', headers, body: JSON.stringify({ comando: comandoTerminal }),
      })
      const data = await res.json()
      setTerminalHistorico(prev => [...prev, {
        comando: comandoTerminal, saida: data.saida || '',
        sucesso: data.sucesso, timestamp: new Date().toISOString(),
      }])
      setComandoTerminal('')
    } catch { /* */ } finally { setExecutandoCmd(false) }
  }, [sessao, comandoTerminal, headers])

  /* ============================================================
     Render: Lista de sessoes
   ============================================================ */

  if (!sessao && !urlSessionId) {
    return (
      <div className="h-full overflow-auto p-8" style={{ background: 'var(--sf-bg-primary)' }}>
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-8">
            <Rocket className="w-8 h-8" style={{ color: 'var(--sf-accent)' }} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Multi-agente com planejamento, discussao e review visiveis</p>
            </div>
          </div>

          <div className="p-5 rounded-xl mb-8" style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
            <div className="flex items-center gap-3">
              <input type="text" placeholder="Nome da sessao" value={titulo}
                onChange={e => setTitulo(e.target.value)} onKeyDown={e => e.key === 'Enter' && criarSessao()}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm"
                style={{ background: 'var(--sf-bg-primary)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
              <button onClick={criarSessao} disabled={criando}
                className="px-5 py-2.5 rounded-lg font-semibold text-white flex items-center gap-2"
                style={{ background: 'var(--sf-accent)' }}>
                {criando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Nova Sessao
              </button>
            </div>
          </div>

          <h2 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--sf-text-secondary)' }}>
            <Clock className="w-4 h-4" /> Sessoes Recentes
          </h2>

          {carregandoSessoes ? (
            <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--sf-accent)' }} /></div>
          ) : sessoes.length === 0 ? (
            <div className="text-center py-12 rounded-xl" style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30" style={{ color: 'var(--sf-text-secondary)' }} />
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Nenhuma sessao anterior.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessoes.map(s => (
                <div key={s.sessao_id} onClick={() => navigate(`/mission-control/${s.sessao_id}`)}
                  className="flex items-center gap-4 p-4 rounded-xl cursor-pointer hover:scale-[1.01] transition-all"
                  style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ background: s.status === 'ativa' ? 'rgba(16,185,129,0.15)' : 'rgba(107,114,128,0.15)' }}>
                    <Rocket className="w-5 h-5" style={{ color: s.status === 'ativa' ? 'var(--sf-accent)' : '#6b7280' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium truncate block" style={{ color: 'var(--sf-text)' }}>{s.titulo}</span>
                    <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
                      <span><Package className="w-3 h-3 inline mr-1" />{s.total_artifacts}</span>
                      <span><Terminal className="w-3 h-3 inline mr-1" />{s.total_comandos}</span>
                      <span><Clock className="w-3 h-3 inline mr-1" />{tempoRelativo(s.atualizado_em)}</span>
                    </div>
                  </div>
                  <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium"
                    style={{ background: 'var(--sf-accent)', color: 'white' }}>
                    <ArrowRight className="w-3.5 h-3.5" /> Retomar
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  if (!sessao && urlSessionId) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--sf-accent)' }} />
      </div>
    )
  }

  if (!sessao) return null

  const agentes = sessao.agentes_ativos || []
  const agentesExecutando = agentes.filter(a => a.status === 'executando')

  // Detectar conclusao: status da sessao OU progresso 100% OU todas fases completas
  const missaoConcluida = sessao.status === 'concluida'
    || (faseStatus && faseStatus.progresso >= 100 && !faseStatus.waiting_decision)
    || (agentes.length > 0 && agentes.every(a => a.status === 'concluido' || a.status === 'erro'))

  // Labels das fases BMAD
  const FASES_BMAD = [
    { num: 1, label: 'Planejamento' },
    { num: 2, label: 'Discussao' },
    { num: 3, label: 'Implementacao' },
    { num: 4, label: 'Review' },
    { num: 5, label: 'Entrega' },
  ]
  const faseAtual = faseStatus?.fase_atual || 0
  const progressoGeral = faseStatus?.progresso || 0

  /* ============================================================
     Render: Painel da sessao — REBUILD STEP 1
     Sem resizable, sem complex layouts
   ============================================================ */

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: 'var(--sf-bg-primary)' }}>

      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <button onClick={() => { setSessao(null); navigate('/mission-control') }} className="opacity-60 hover:opacity-100">
          <Rocket className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
        </button>
        <span className="font-bold text-sm" style={{ color: 'var(--sf-text)' }}>Mission Control</span>
        <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--sf-bg-primary)', color: 'var(--sf-text-secondary)' }}>
          {sessao.titulo}
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
          <span><Package className="w-3.5 h-3.5 inline mr-1" />{artifacts.length}</span>
          <span><Terminal className="w-3.5 h-3.5 inline mr-1" />{sessao.total_comandos}</span>
          <span><MessageSquare className="w-3.5 h-3.5 inline mr-1" />{chatMsgs.length}</span>
        </div>

        {/* Plan Mode toggle */}
        <button
          onClick={togglePlanMode}
          disabled={planLoading || !sessao?.sessao_id}
          title={planMode ? 'Sair do Plan Mode (somente-leitura)' : 'Entrar em Plan Mode (somente-leitura)'}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
          style={{
            background: planToast
              ? (planToast.includes('Erro') || planToast.includes('Falha')
                ? 'rgba(239,68,68,0.12)'
                : 'rgba(16,185,129,0.12)')
              : planMode
                ? 'rgba(168,85,247,0.15)'
                : 'rgba(100,116,139,0.1)',
            color: planToast
              ? (planToast.includes('Erro') || planToast.includes('Falha')
                ? '#ef4444'
                : '#10b981')
              : planMode
                ? '#c084fc'
                : 'var(--sf-text-secondary)',
            border: `1px solid ${
              planToast
                ? (planToast.includes('Erro') || planToast.includes('Falha')
                  ? 'rgba(239,68,68,0.25)'
                  : 'rgba(16,185,129,0.25)')
                : planMode
                  ? 'rgba(168,85,247,0.3)'
                  : 'transparent'
            }`,
            cursor: (planLoading || !sessao?.sessao_id) ? 'not-allowed' : 'pointer',
            opacity: !sessao?.sessao_id ? 0.4 : 1,
          }}
        >
          {planLoading
            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
            : planMode
              ? <Shield className="w-3.5 h-3.5" />
              : <ShieldOff className="w-3.5 h-3.5" />
          }
          {planToast
            ? planToast
            : planLoading
              ? '...'
              : planMode
                ? 'Plan Mode'
                : 'Plan Mode'
          }
          {planMode && !planToast && !planLoading && (
            <span className="w-1.5 h-1.5 rounded-full ml-0.5" style={{ background: '#c084fc' }} />
          )}
        </button>
      </header>

      {/* Instrucoes do Agente */}
      <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <Sparkles className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
        <input type="text" placeholder="Instruir equipe..."
          value={instrucao}
          onChange={e => setInstrucao(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && enviarInstrucao()}
          className="flex-1 px-3 py-1.5 rounded text-sm"
          style={{ background: 'var(--sf-bg-primary)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
        <button onClick={enviarInstrucao} disabled={enviando}
          className="px-3 py-1.5 rounded text-xs font-medium text-white flex items-center gap-1.5"
          style={{ background: 'var(--sf-accent)' }}>
          {enviando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          Executar
        </button>
      </div>

      {/* Agentes Ativos */}
      {agentesExecutando.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2"
          style={{ background: 'rgba(16,185,129,0.1)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
          <Bot className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
          <span className="text-xs font-bold" style={{ color: 'var(--sf-accent)' }}>
            {agentesExecutando.map(a => a.nome).join(', ')} executando
          </span>
        </div>
      )}

      {/* Phase Decision Controls — shown when waiting for user decision */}
      {faseStatus?.waiting_decision && (
        <div className="flex-shrink-0" style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
          <PhaseDecisionControls
            token={token || ''}
            sessaoId={sessao.sessao_id}
            fase={faseStatus.fase_atual || 1}
            faseLabel=""
            progresso={faseStatus.progresso || 0}
            agenteNome={faseStatus.agente_nome || 'Agente'}
            onDecisao={async (fase, acao) => {
              try {
                await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/fase-decisao`, {
                  method: 'POST', headers,
                  body: JSON.stringify({ fase, acao }),
                })
                // Delay para dar tempo ao agente de avançar para a próxima fase
                // antes de recarregar o status (evita esconder botões prematuramente)
                await new Promise(r => setTimeout(r, 2000))
                carregarFaseStatus()
                carregarSessao(sessao.sessao_id)
              } catch { /* */ }
            }}
          />
        </div>
      )}

      {/* Barra de progresso das fases BMAD */}
      {faseAtual > 0 && !missaoConcluida && (
        <div className="flex items-center gap-1 px-4 py-2 flex-shrink-0"
          style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
          {FASES_BMAD.map((fase) => {
            const concluida = faseAtual > fase.num
            const atual = faseAtual === fase.num
            return (
              <div key={fase.num} className="flex items-center gap-1 flex-1">
                <div className="flex items-center gap-1.5 flex-1">
                  <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{
                      background: concluida ? 'var(--sf-accent)' : atual ? 'rgba(16,185,129,0.3)' : 'var(--sf-bg-primary)',
                      color: concluida ? 'white' : atual ? 'var(--sf-accent)' : 'var(--sf-text-secondary)',
                      border: atual ? '2px solid var(--sf-accent)' : '1px solid var(--sf-border-subtle)',
                    }}>
                    {concluida ? '\u2713' : fase.num}
                  </div>
                  <span className="text-xs truncate" style={{
                    color: concluida || atual ? 'var(--sf-text)' : 'var(--sf-text-secondary)',
                    fontWeight: atual ? 600 : 400,
                  }}>{fase.label}</span>
                </div>
                {fase.num < 5 && (
                  <div className="w-8 h-0.5 flex-shrink-0" style={{
                    background: concluida ? 'var(--sf-accent)' : 'var(--sf-border-subtle)',
                  }} />
                )}
              </div>
            )
          })}
          <span className="text-xs font-mono ml-2" style={{ color: 'var(--sf-accent)' }}>
            {progressoGeral}%
          </span>
        </div>
      )}

      {/* Tela de conclusao — mostrada quando missao termina */}
      {missaoConcluida ? (
        <MissionCompleteActions
          token={token || ''}
          sessaoId={sessao.sessao_id}
          projetoId={sessao.projeto_id}
          papel="ceo"
          sessaoTitulo={sessao.titulo}
          totalArtifacts={artifacts.length}
          totalComandos={sessao.total_comandos}
          onVoltarRevisao={() => {
            // Voltar para o painel de execucao (forcar re-render sem conclusao)
            setSessao(prev => prev ? { ...prev, status: 'ativa' } : prev)
          }}
          onNovaSessao={() => {
            setSessao(null)
            navigate('/mission-control')
          }}
        />
      ) : (
      <>
      {/* Painel Triplo SIMPLES — 3 divs uma do lado da outra */}
      <div className="flex flex-1 overflow-hidden">

        {/* Editor */}
        <div className="flex-1 flex flex-col overflow-hidden border-r" style={{ borderColor: 'var(--sf-border-subtle)' }}>
          <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
            style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
            <Code2 className="w-3.5 h-3.5" />
            <span className="font-medium">Editor</span>
            <span className="opacity-60 truncate max-w-[120px]">{editorArquivo}</span>
          </div>
          <div className="flex-1 overflow-auto p-3 font-mono text-sm"
            style={{ background: '#1e1e2e', color: '#cdd6f4', lineHeight: '1.6', fontSize: '13px' }}>
            <pre className="whitespace-pre-wrap">{editorConteudo || '// Aguardando codigo...'}</pre>
          </div>
        </div>

        {/* Terminal */}
        <div className="flex-1 flex flex-col overflow-hidden border-r" style={{ borderColor: 'var(--sf-border-subtle)' }}>
          <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
            style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
            <Terminal className="w-3.5 h-3.5" />
            <span className="font-medium">Terminal</span>
          </div>
          <div ref={terminalRef} className="flex-1 overflow-auto p-3 font-mono text-xs"
            style={{ background: '#0d1117', color: '#c9d1d9' }}>
            {terminalHistorico.map((entry, i) => (
              <div key={i} className="mb-2">
                <div className="flex items-center gap-1">
                  <span style={{ color: '#58a6ff' }}>$</span>
                  <span>{entry.comando}</span>
                </div>
                {entry.saida && (
                  <pre className="whitespace-pre-wrap mt-0.5 pl-4" style={{ color: entry.sucesso ? '#8b949e' : '#f85149' }}>{entry.saida}</pre>
                )}
              </div>
            ))}
            {terminalHistorico.length === 0 && (
              <div style={{ color: '#484f58' }}>Terminal pronto.</div>
            )}
          </div>
          <div className="flex items-center gap-2 px-3 py-2 flex-shrink-0"
            style={{ background: '#161b22', borderTop: '1px solid #30363d' }}>
            <span className="text-xs" style={{ color: '#58a6ff' }}>$</span>
            <input type="text" value={comandoTerminal}
              onChange={e => setComandoTerminal(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && executarComando()}
              placeholder="Comando..."
              className="flex-1 bg-transparent text-xs outline-none font-mono" style={{ color: '#f0f6fc' }} />
            <button onClick={executarComando} disabled={executandoCmd}
              className="text-xs px-2 py-0.5 rounded" style={{ background: '#21262d', color: '#58a6ff' }}>
              {executandoCmd ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Team Chat + Artifacts */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center gap-1 px-3 py-1.5 text-xs flex-shrink-0"
            style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
            <button onClick={() => setAbaPainel3('chat')}
              className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium"
              style={{ background: abaPainel3 === 'chat' ? 'rgba(16,185,129,0.15)' : 'transparent', color: abaPainel3 === 'chat' ? 'var(--sf-accent)' : 'var(--sf-text-secondary)' }}>
              <MessageSquare className="w-3.5 h-3.5" /> Team Chat
            </button>
            <button onClick={() => setAbaPainel3('artifacts')}
              className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium"
              style={{ background: abaPainel3 === 'artifacts' ? 'rgba(16,185,129,0.15)' : 'transparent', color: abaPainel3 === 'artifacts' ? 'var(--sf-accent)' : 'var(--sf-text-secondary)' }}>
              <Package className="w-3.5 h-3.5" /> Artifacts ({artifacts.length})
            </button>
          </div>

          {/* Team Chat */}
          {abaPainel3 === 'chat' && (
            <div ref={chatRef} className="flex-1 overflow-auto p-3 space-y-2"
              style={{ background: 'var(--sf-bg-primary)' }}>
              {chatMsgs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3"
                  style={{ color: 'var(--sf-text-secondary)' }}>
                  <MessageSquare className="w-12 h-12 opacity-20" />
                  <p className="text-sm">Aguardando conversa...</p>
                </div>
              ) : chatMsgs.map(msg => (
                <div key={msg.id} className="rounded-lg px-3 py-2"
                  style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Bot className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
                    <span className="text-xs font-semibold" style={{ color: 'var(--sf-accent)' }}>{msg.agente_nome}</span>
                    {msg.fase && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--sf-accent)' }}>{msg.fase}</span>
                    )}
                  </div>
                  <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--sf-text)' }}>{msg.conteudo}</p>
                </div>
              ))}
            </div>
          )}

          {/* Artifacts */}
          {abaPainel3 === 'artifacts' && (
            <div className="flex-1 overflow-auto p-3 space-y-2"
              style={{ background: 'var(--sf-bg-primary)' }}>
              {artifacts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3"
                  style={{ color: 'var(--sf-text-secondary)' }}>
                  <Package className="w-12 h-12 opacity-20" />
                  <p className="text-sm">Nenhum artifact gerado</p>
                </div>
              ) : artifacts.map(artifact => (
                <div key={artifact.artifact_id}
                  onClick={() => setArtifactModal(artifact)}
                  className="rounded-lg px-3 py-2 cursor-pointer hover:scale-[1.01] transition-all"
                  style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Package className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
                    <span className="text-xs font-semibold" style={{ color: 'var(--sf-text)' }}>{artifact.titulo}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded ml-auto"
                      style={{ background: artifact.status === 'aprovado' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)', color: artifact.status === 'aprovado' ? '#10b981' : '#f59e0b' }}>
                      {artifact.status}
                    </span>
                  </div>
                  <p className="text-[10px]" style={{ color: 'var(--sf-text-secondary)' }}>
                    {artifact.agente_nome} • {artifact.tipo}
                  </p>
                  {artifact.conteudo && (
                    <p className="text-[10px] mt-1 line-clamp-2" style={{ color: 'var(--sf-text-secondary)' }}>
                      {artifact.conteudo.slice(0, 100)}...
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Artifact Modal */}
      {artifactModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setArtifactModal(null)}>
          <div className="w-full max-w-4xl max-h-[85vh] flex flex-col rounded-xl overflow-hidden"
            style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 px-6 py-4"
              style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
              <Package className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
              <h3 className="text-base font-bold" style={{ color: 'var(--sf-text)' }}>{artifactModal.titulo}</h3>
              <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--sf-accent)' }}>{artifactModal.tipo}</span>
              <div className="flex-1" />
              <button onClick={() => setArtifactModal(null)} className="p-1 rounded hover:bg-white/10">
                <X className="w-5 h-5" style={{ color: 'var(--sf-text-secondary)' }} />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-6">
              <pre className="text-sm p-4 rounded-xl font-mono whitespace-pre-wrap overflow-auto"
                style={{ background: 'var(--sf-bg-primary)', color: 'var(--sf-text)' }}>
                {artifactModal.conteudo || JSON.stringify(artifactModal.dados, null, 2)}
              </pre>
            </div>
            <div className="flex items-center gap-3 px-6 py-4"
              style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
              <button onClick={() => {
                if (artifactModal.conteudo) {
                  setEditorConteudo(artifactModal.conteudo)
                  setEditorArquivo(artifactModal.titulo.replace(/\s+/g, '-').toLowerCase())
                }
                setArtifactModal(null)
              }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-white"
                style={{ background: 'var(--sf-accent)' }}>
                <Code2 className="w-4 h-4" /> Aplicar no Editor
              </button>
              <button onClick={() => {
                const text = artifactModal.conteudo || JSON.stringify(artifactModal.dados, null, 2)
                navigator.clipboard.writeText(text)
              }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium"
                style={{ background: 'var(--sf-bg-primary)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
                <Copy className="w-4 h-4" /> Copiar
              </button>
              <button onClick={() => {
                const text = artifactModal.conteudo || JSON.stringify(artifactModal.dados, null, 2)
                const blob = new Blob([text], { type: 'text/plain' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = artifactModal.titulo.replace(/\s+/g, '-').toLowerCase() + '.txt'
                a.click()
                URL.revokeObjectURL(url)
              }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium"
                style={{ background: 'var(--sf-bg-primary)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
                <Download className="w-4 h-4" /> Download
              </button>
            </div>
          </div>
        </div>
      )}
      </>
      )}
    </div>
  )
}
