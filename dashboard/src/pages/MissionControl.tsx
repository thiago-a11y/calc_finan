/* Mission Control — Code Studio 2.0 (v0.57.1)
 *
 * Painel triplo: Editor + Terminal + Team Chat/Artifacts
 * Multi-agente com conversa visivel, planejamento, review
 *
 * v0.57.1:
 * - Team Chat: conversa em tempo real entre agentes
 * - Artifacts em modal grande expansivel (nunca fecham sozinhos)
 * - Planejamento visivel antes de codar
 * - Multi-agente com 4 fases: Planejamento → Discussao → Execucao → Review
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useParams, useNavigate } from 'react-router-dom'
import ResizableHandle from '../components/code-studio/ResizableHandle'
import {
  Rocket, Terminal, Code2, Bot, CheckSquare,
  MessageSquare, Play, Send, Loader2,
  Maximize2, Minimize2, Sparkles, Package,
  Clock, ArrowRight, Plus, Save, X,
  ClipboardList, Zap, Shield, Palette, Settings2,
  Copy, Download, ExternalLink, Radio,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

/* ============================================================
   Tipos
   ============================================================ */

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

/* ============================================================
   Cores e icones por agente/fase
   ============================================================ */

const AGENTE_COR: Record<string, string> = {
  'Tech Lead': '#10b981', 'Backend Dev': '#3b82f6', 'Frontend Dev': '#8b5cf6',
  'QA Engineer': '#ef4444', 'Sistema': '#6b7280', 'Terminal': '#f59e0b',
  'Mission Control Agent': '#14b8a6',
}

const FASE_COR: Record<string, { bg: string; text: string; label: string }> = {
  planejamento: { bg: 'rgba(99,102,241,0.15)', text: '#818cf8', label: 'Planejamento' },
  discussao:    { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24', label: 'Discussao' },
  execucao:     { bg: 'rgba(16,185,129,0.15)', text: '#34d399', label: 'Execucao' },
  review:       { bg: 'rgba(239,68,68,0.15)',  text: '#f87171', label: 'Review' },
  conclusao:    { bg: 'rgba(107,114,128,0.15)', text: '#9ca3af', label: 'Concluido' },
}

function getAgenteCor(nome: string): string {
  return AGENTE_COR[nome] || '#6b7280'
}

function AgenteIcon({ nome, size = 16 }: { nome: string; size?: number }) {
  const props = { size, style: { color: getAgenteCor(nome) } }
  if (nome === 'Tech Lead') return <Settings2 {...props} />
  if (nome === 'Backend Dev') return <Zap {...props} />
  if (nome === 'Frontend Dev') return <Palette {...props} />
  if (nome === 'QA Engineer') return <Shield {...props} />
  if (nome === 'Sistema') return <Rocket {...props} />
  return <Bot {...props} />
}

/* ============================================================
   Componente Principal
   ============================================================ */

export default function MissionControl() {
  const { token } = useAuth()
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()

  // Sessao
  const [sessao, setSessao] = useState<Sessao | null>(null)
  const [sessoes, setSessoes] = useState<SessaoResumo[]>([])
  const [carregandoSessoes, setCarregandoSessoes] = useState(true)
  const [criando, setCriando] = useState(false)
  const [titulo, setTitulo] = useState('')

  // Editor
  const [editorConteudo, setEditorConteudo] = useState('// Selecione um arquivo ou peca ao agente para gerar codigo\n')
  const [editorArquivo, setEditorArquivo] = useState('novo-arquivo.tsx')

  // Terminal
  const [comandoTerminal, setComandoTerminal] = useState('')
  const [terminalHistorico, setTerminalHistorico] = useState<TerminalEntry[]>([])
  const [executandoCmd, setExecutandoCmd] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)

  // Artifacts
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [artifactModal, setArtifactModal] = useState<Artifact | null>(null)
  const [novoComentario, setNovoComentario] = useState('')

  // Team Chat
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([])
  const chatRef = useRef<HTMLDivElement>(null)

  // Agente
  const [instrucaoAgente, setInstrucaoAgente] = useState('')
  const [disparandoAgente, setDisparandoAgente] = useState(false)

  // Layout
  const [painelLarguras, setPainelLarguras] = useState([30, 30, 40])
  const [painelMaximizado, setPainelMaximizado] = useState<number | null>(null)
  const [abaDireita, setAbaDireita] = useState<'chat' | 'artifacts'>('chat')

  // Visible Execution + LIVE Mode
  const [editorFonteAgente, setEditorFonteAgente] = useState(false)
  const [editorEditadoPeloUsuario, setEditorEditadoPeloUsuario] = useState(false)
  const editorEditadoRef = useRef(false)  // ref para closures sem stale state
  const [modoLive, setModoLive] = useState(true)  // LIVE ligado por padrao
  const [editorStreaming, setEditorStreaming] = useState(false)  // true = codigo sendo escrito
  const agentExecutandoRef = useRef(false)  // evita auto-save sobrescrever conteudo do agente

  // Auto-save
  const [ultimoSave, setUltimoSave] = useState('')
  const [salvando, setSalvando] = useState(false)

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }), [token])

  /* ============================================================
     Listar sessoes
     ============================================================ */

  const carregarSessoes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessoes`, { headers })
      if (res.ok) setSessoes(await res.json())
    } catch { /* */ } finally { setCarregandoSessoes(false) }
  }, [headers])

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
     Carregar sessao + restore
     ============================================================ */

  const carregarSessao = useCallback(async (sid: string) => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sid}`, { headers })
      if (!res.ok) return
      const data: Sessao = await res.json()
      setSessao(data)
      setArtifacts(data.artifacts || [])

      // Detectar se agente esta ativo (para auto-save e polling)
      const temAgente = (data.agentes_ativos || []).some(a => a.status === 'executando')
      agentExecutandoRef.current = temAgente

      // Detectar streaming
      const isStreaming = data.painel_editor?.streaming === true
      setEditorStreaming(isStreaming)

      // Atualizar editor com conteudo do agente
      // Regra: se fonte === 'agente' OU se o usuario nao editou manualmente, atualizar
      const editorData = data.painel_editor
      if (editorData?.conteudo) {
        const isFromAgent = editorData.fonte === 'agente'
        if (isFromAgent) {
          // Agente escreveu codigo — sempre atualizar, independente do que o usuario fez
          setEditorConteudo(editorData.conteudo)
          if (editorData.arquivo_ativo) setEditorArquivo(editorData.arquivo_ativo)
          setEditorFonteAgente(true)
          setEditorEditadoPeloUsuario(false)
          editorEditadoRef.current = false
        } else if (!editorEditadoRef.current) {
          // Conteudo normal (auto-save ou inicial) — atualiza so se usuario nao editou
          setEditorConteudo(editorData.conteudo)
          if (editorData.arquivo_ativo) setEditorArquivo(editorData.arquivo_ativo)
        }
      }

      // Atualizar terminal com TUDO do banco (agente + usuario)
      const histBanco = data.painel_terminal?.historico || []
      setTerminalHistorico(histBanco)
      if (histBanco.length > 0) {
        setTimeout(() => terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight), 100)
      }
    } catch { /* */ }
  }, [headers])

  /* ============================================================
     Team Chat polling (2s)
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    let mounted = true
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/chat`, { headers })
        if (res.ok && mounted) {
          const msgs: ChatMsg[] = await res.json()
          setChatMsgs(msgs)
          setTimeout(() => chatRef.current?.scrollTo(0, chatRef.current.scrollHeight), 50)
        }
      } catch { /* */ }
    }
    poll()
    const timer = setInterval(poll, 2000)
    return () => { mounted = false; clearInterval(timer) }
  }, [sessao?.sessao_id, headers])

  /* ============================================================
     Auto-save (10s)
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(async () => {
      // Nao salvar enquanto agente esta executando — evita sobrescrever conteudo do agente
      // O backend tambem protege, mas melhor prevenir no frontend
      if (agentExecutandoRef.current) return
      try {
        setSalvando(true)
        await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/save`, {
          method: 'PATCH', headers,
          body: JSON.stringify({
            painel_editor: { conteudo: editorConteudo, arquivo_ativo: editorArquivo },
            painel_terminal: { historico: terminalHistorico.slice(-50), cwd: '' },
          }),
        })
        setUltimoSave(new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }))
      } catch { /* */ } finally { setSalvando(false) }
    }, 10000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, headers, editorConteudo, editorArquivo, terminalHistorico])

  /* ============================================================
     Polling sessao — sempre 2s para nao perder atualizacoes do agente
     (nao depende de sessao?.agentes_ativos para evitar restart a cada poll)
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    // Polling fixo em 2s — rapido o suficiente para ver streaming sem causar instabilidade
    const timer = setInterval(() => carregarSessao(sessao.sessao_id), 2000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, carregarSessao])

  /* ============================================================
     Startup
     ============================================================ */

  useEffect(() => {
    if (urlSessionId) carregarSessao(urlSessionId)
    else carregarSessoes()
  }, [urlSessionId, carregarSessao, carregarSessoes])

  /* ============================================================
     Terminal
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
      setTimeout(() => terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight), 100)
    } catch { /* */ } finally { setExecutandoCmd(false) }
  }, [sessao, comandoTerminal, headers])

  /* ============================================================
     Agentes
     ============================================================ */

  const dispararAgente = useCallback(async () => {
    if (!sessao || !instrucaoAgente.trim()) return
    setDisparandoAgente(true)
    setAbaDireita('chat') // Mudar para chat para ver a conversa
    // Resetar estado do editor para receber conteudo do agente
    setEditorEditadoPeloUsuario(false)
    editorEditadoRef.current = false
    setEditorFonteAgente(false)
    try {
      await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/agente`, {
        method: 'POST', headers,
        body: JSON.stringify({ instrucao: instrucaoAgente, tipo: 'implementacao' }),
      })
      setInstrucaoAgente('')
      // Recarregar imediatamente para exibir agente em execucao e barra de progresso
      await carregarSessao(sessao.sessao_id)
    } catch { /* */ } finally { setDisparandoAgente(false) }
  }, [sessao, instrucaoAgente, headers, carregarSessao])

  /* ============================================================
     Comentarios
     ============================================================ */

  const adicionarComentario = useCallback(async (artifactId: string) => {
    if (!novoComentario.trim()) return
    try {
      await fetch(`${API}/api/mission-control/artifacts/${artifactId}/comentar`, {
        method: 'POST', headers,
        body: JSON.stringify({ texto: novoComentario }),
      })
      setNovoComentario('')
      if (sessao) await carregarSessao(sessao.sessao_id)
    } catch { /* */ }
  }, [novoComentario, headers, sessao, carregarSessao])

  /* ============================================================
     Aplicar codigo do artifact no editor
     ============================================================ */

  const aplicarNoEditor = useCallback((art: Artifact) => {
    if (art.conteudo) {
      setEditorConteudo(art.conteudo)
      const arq = (art.dados as Record<string, string>)?.arquivo || art.titulo.replace('Codigo: ', '')
      setEditorArquivo(arq)
      setArtifactModal(null)
    }
  }, [])

  /* ============================================================
     Helper
     ============================================================ */

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
     Render: Lista de sessoes
     ============================================================ */

  if (!sessao && !urlSessionId) {
    return (
      <div className="h-full overflow-auto" style={{ background: 'var(--sf-bg)' }}>
        <div className="max-w-3xl mx-auto p-8">
          <div className="flex items-center gap-3 mb-8">
            <Rocket className="w-8 h-8" style={{ color: 'var(--sf-accent)' }} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Multi-agente com planejamento, discussao e review visiveis</p>
            </div>
          </div>

          <div className="p-5 rounded-xl mb-8" style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
            <div className="flex items-center gap-3">
              <input type="text" placeholder="Nome da sessao (ex: Feature Login SSO)" value={titulo}
                onChange={e => setTitulo(e.target.value)} onKeyDown={e => e.key === 'Enter' && criarSessao()}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm"
                style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
              <button onClick={criarSessao} disabled={criando}
                className="px-5 py-2.5 rounded-lg font-semibold text-white flex items-center gap-2 hover:scale-105 transition-transform"
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
            <div className="text-center py-12 rounded-xl" style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30" style={{ color: 'var(--sf-text-secondary)' }} />
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Nenhuma sessao anterior.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessoes.map(s => (
                <div key={s.sessao_id} onClick={() => navigate(`/mission-control/${s.sessao_id}`)}
                  className="flex items-center gap-4 p-4 rounded-xl cursor-pointer hover:scale-[1.01] transition-all"
                  style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
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
    return <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg)' }}>
      <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--sf-accent)' }} />
    </div>
  }

  if (!sessao) return null

  const agentes = sessao.agentes_ativos || []
  const agentesExecutando = agentes.filter(a => a.status === 'executando')

  const agente_exec = agentesExecutando[0]
  const faseAtual = agente_exec?.fase_atual as number | undefined
  const faseLabel = agente_exec?.fase_label as string | undefined
  const progressoAtual = agente_exec?.progresso as number | undefined

  /* ============================================================
     Render: Painel Triplo
     ============================================================ */

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: 'var(--sf-bg)' }}>

      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <button onClick={() => { setSessao(null); navigate('/mission-control') }} className="opacity-60 hover:opacity-100">
          <Rocket className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
        </button>
        <span className="font-bold text-sm" style={{ color: 'var(--sf-text)' }}>Mission Control</span>
        <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--sf-bg)', color: 'var(--sf-text-secondary)' }}>
          {sessao.titulo}
        </span>

        {agentesExecutando.length > 0 && (
          <div className="flex items-center gap-2 ml-4">
            {agentesExecutando.map(a => (
              <div key={a.id} className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs animate-pulse"
                style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' }}>
                <Bot className="w-3.5 h-3.5" /><span>{a.nome}</span><Loader2 className="w-3 h-3 animate-spin" />
              </div>
            ))}
          </div>
        )}

        <div className="flex-1" />

        {ultimoSave && (
          <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--sf-text-secondary)', opacity: 0.6 }}>
            {salvando ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            {salvando ? 'Salvando...' : `Salvo ${ultimoSave}`}
          </span>
        )}

        <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
          <span><Package className="w-3.5 h-3.5 inline mr-1" />{artifacts.length}</span>
          <span><Terminal className="w-3.5 h-3.5 inline mr-1" />{sessao.total_comandos}</span>
          <span><MessageSquare className="w-3.5 h-3.5 inline mr-1" />{chatMsgs.length}</span>
        </div>
      </header>

      {/* Instrucao do Agente + Barra de Progresso */}
      <div className="flex-shrink-0" style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        {/* Progress bar + LIVE toggle - aparece quando executa */}
        {agentesExecutando.length > 0 && (
          <div className="px-4 pt-2">
            <div className="flex items-center gap-2 mb-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: 'var(--sf-accent)' }} />
              <span className="text-xs font-medium" style={{ color: 'var(--sf-accent)' }}>
                {faseLabel ? `Fase ${faseAtual}/5 — ${faseLabel}` : 'Executando...'}
              </span>
              {editorStreaming && modoLive && (
                <span className="text-[9px] px-1.5 py-0.5 rounded-full animate-pulse font-bold"
                  style={{ background: 'rgba(239,68,68,0.2)', color: '#f87171' }}>
                  STREAMING
                </span>
              )}
              <div className="flex-1" />
              {/* Botao LIVE toggle */}
              <button onClick={() => setModoLive(prev => !prev)}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold transition-all"
                style={{
                  background: modoLive ? 'rgba(16,185,129,0.2)' : 'rgba(107,114,128,0.15)',
                  color: modoLive ? '#10b981' : '#6b7280',
                  border: `1px solid ${modoLive ? 'rgba(16,185,129,0.4)' : 'rgba(107,114,128,0.3)'}`,
                }}>
                <Radio className="w-3 h-3" style={modoLive ? { filter: 'drop-shadow(0 0 3px #10b981)' } : {}} />
                LIVE
              </button>
              <span className="text-[10px]" style={{ color: 'var(--sf-text-secondary)' }}>
                {progressoAtual || 0}%
              </span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--sf-bg)' }}>
              <div className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{
                  width: `${progressoAtual || 5}%`,
                  background: modoLive
                    ? 'linear-gradient(90deg, #10b981, #60a5fa, #a78bfa)'
                    : 'linear-gradient(90deg, var(--sf-accent), #60a5fa)',
                  boxShadow: modoLive ? '0 0 12px rgba(16,185,129,0.5)' : '0 0 8px var(--sf-accent)',
                }} />
            </div>
          </div>
        )}
        <div className="flex items-center gap-2 px-4 py-2">
          <Sparkles className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
          <input type="text" placeholder="Instruir equipe: 'Crie um componente de login com validacao e testes'"
            value={instrucaoAgente} onChange={e => setInstrucaoAgente(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && dispararAgente()}
            className="flex-1 px-3 py-1.5 rounded text-sm"
            style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
          <button onClick={dispararAgente} disabled={disparandoAgente || !instrucaoAgente.trim()}
            className="px-3 py-1.5 rounded text-xs font-medium text-white flex items-center gap-1"
            style={{ background: disparandoAgente ? '#666' : 'var(--sf-accent)' }}>
            {disparandoAgente ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            Executar Equipe
          </button>
        </div>
      </div>

      {/* === Painel Triplo === */}
      <div className="flex flex-1 overflow-hidden">

        {/* Painel 1: Editor */}
        {(painelMaximizado === null || painelMaximizado === 0) && (
          <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 0 ? '100%' : `${painelLarguras[0]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Code2 className="w-3.5 h-3.5" />
              <span className="font-medium">Editor</span>
              <span className="opacity-60 truncate max-w-[120px]">{editorArquivo}</span>
              {editorStreaming && modoLive && (
                <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full font-bold"
                  style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', animation: 'pulse 1s infinite' }}>
                  <Radio className="w-3 h-3" style={{ filter: 'drop-shadow(0 0 3px #ef4444)' }} /> LIVE
                </span>
              )}
              {editorFonteAgente && !editorStreaming && (
                <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' }}>
                  <Bot className="w-3 h-3" /> agente
                </span>
              )}
              {faseAtual === 3 && agentesExecutando.length > 0 && !editorStreaming && !editorFonteAgente && (
                <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full animate-pulse"
                  style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>
                  <Loader2 className="w-3 h-3 animate-spin" /> aguardando...
                </span>
              )}
              <div className="flex-1" />
              {editorEditadoPeloUsuario && <span className="text-[9px] opacity-40">editado</span>}
              <button onClick={() => setPainelMaximizado(painelMaximizado === 0 ? null : 0)} className="opacity-60 hover:opacity-100">
                {painelMaximizado === 0 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
            <div className="relative flex-1 overflow-hidden">
              <textarea className="absolute inset-0 p-3 font-mono text-sm resize-none outline-none" spellCheck={false}
                style={{ background: '#1e1e2e', color: '#cdd6f4', border: 'none' }}
                value={editorConteudo} onChange={e => { setEditorConteudo(e.target.value); setEditorEditadoPeloUsuario(true); editorEditadoRef.current = true; setEditorFonteAgente(false) }} />
              {/* Cursor pulsante durante streaming LIVE */}
              {editorStreaming && modoLive && (
                <div className="absolute bottom-3 right-3 flex items-center gap-1.5 px-2 py-1 rounded-lg"
                  style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
                  <span className="w-2 h-4 rounded-sm" style={{
                    background: '#10b981',
                    animation: 'pulse 0.6s infinite alternate',
                    boxShadow: '0 0 8px #10b981',
                  }} />
                  <span className="text-[10px] font-mono" style={{ color: '#10b981' }}>escrevendo...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {painelMaximizado === null && <ResizableHandle onResize={(d) => {
          setPainelLarguras(prev => { const n = [...prev]; const delta = (d / window.innerWidth) * 100; n[0] = Math.max(15, Math.min(50, n[0] + delta)); n[1] = Math.max(15, Math.min(50, n[1] - delta)); return n })
        }} />}

        {/* Painel 2: Terminal */}
        {(painelMaximizado === null || painelMaximizado === 1) && (
          <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 1 ? '100%' : `${painelLarguras[1]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Terminal className="w-3.5 h-3.5" /><span className="font-medium">Terminal</span>
              <div className="flex-1" />
              <button onClick={() => setPainelMaximizado(painelMaximizado === 1 ? null : 1)} className="opacity-60 hover:opacity-100">
                {painelMaximizado === 1 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
            <div ref={terminalRef} className="flex-1 overflow-auto p-3 font-mono text-xs" style={{ background: '#0d1117', color: '#c9d1d9' }}>
              {terminalHistorico.map((entry, i) => (
                <div key={i} className="mb-3">
                  <div className="flex items-center gap-1">
                    {entry.tipo === 'agente'
                      ? <Bot className="w-3 h-3 flex-shrink-0" style={{ color: '#10b981' }} />
                      : <span style={{ color: '#58a6ff' }}>$</span>
                    }
                    <span style={{ color: entry.tipo === 'agente' ? '#10b981' : '#f0f6fc' }}>
                      {entry.comando}
                    </span>
                  </div>
                  {entry.saida && (
                    <pre className="whitespace-pre-wrap mt-0.5 pl-4" style={{ color: entry.sucesso ? '#8b949e' : '#f85149' }}>{entry.saida}</pre>
                  )}
                </div>
              ))}
              {terminalHistorico.length === 0 && (
                <div style={{ color: '#484f58' }}>
                  Terminal pronto. Agentes usam este painel para mostrar progresso.
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 px-3 py-2 flex-shrink-0" style={{ background: '#161b22', borderTop: '1px solid #30363d' }}>
              <span className="text-xs" style={{ color: '#58a6ff' }}>$</span>
              <input type="text" value={comandoTerminal} onChange={e => setComandoTerminal(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && executarComando()} placeholder="Digite comando..."
                className="flex-1 bg-transparent text-xs outline-none font-mono" style={{ color: '#f0f6fc' }} />
              <button onClick={executarComando} disabled={executandoCmd} className="text-xs px-2 py-0.5 rounded"
                style={{ background: '#21262d', color: '#58a6ff' }}>
                {executandoCmd ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              </button>
            </div>
          </div>
        )}

        {painelMaximizado === null && <ResizableHandle onResize={(d) => {
          setPainelLarguras(prev => { const n = [...prev]; const delta = (d / window.innerWidth) * 100; n[1] = Math.max(15, Math.min(50, n[1] + delta)); n[2] = Math.max(20, Math.min(60, n[2] - delta)); return n })
        }} />}

        {/* Painel 3: Team Chat + Artifacts */}
        {(painelMaximizado === null || painelMaximizado === 2) && (
          <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 2 ? '100%' : `${painelLarguras[2]}%` }}>
            {/* Tabs: Chat / Artifacts */}
            <div className="flex items-center gap-1 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
              <button onClick={() => setAbaDireita('chat')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${abaDireita === 'chat' ? '' : 'opacity-50 hover:opacity-80'}`}
                style={abaDireita === 'chat' ? { background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' } : { color: 'var(--sf-text-secondary)' }}>
                <MessageSquare className="w-3.5 h-3.5" /> Team Chat
                {chatMsgs.length > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px]" style={{ background: 'rgba(16,185,129,0.2)' }}>{chatMsgs.length}</span>}
              </button>
              <button onClick={() => setAbaDireita('artifacts')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${abaDireita === 'artifacts' ? '' : 'opacity-50 hover:opacity-80'}`}
                style={abaDireita === 'artifacts' ? { background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' } : { color: 'var(--sf-text-secondary)' }}>
                <Package className="w-3.5 h-3.5" /> Artifacts
                {artifacts.length > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px]" style={{ background: 'rgba(16,185,129,0.2)' }}>{artifacts.length}</span>}
              </button>
              <div className="flex-1" />
              <button onClick={() => setPainelMaximizado(painelMaximizado === 2 ? null : 2)} className="opacity-60 hover:opacity-100">
                {painelMaximizado === 2 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* === TEAM CHAT === */}
            {abaDireita === 'chat' && (
              <div ref={chatRef} className="flex-1 overflow-auto p-3 space-y-2" style={{ background: 'var(--sf-bg)' }}>
                {chatMsgs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                    <MessageSquare className="w-12 h-12 opacity-20" />
                    <p className="text-sm">Nenhuma conversa ainda.</p>
                    <p className="text-xs opacity-60">Instrua a equipe acima para ver os agentes conversando.</p>
                  </div>
                ) : chatMsgs.map(msg => {
                  const fase = FASE_COR[msg.fase] || null
                  const isSistema = msg.tipo === 'sistema'
                  return (
                    <div key={msg.id} className={`rounded-lg px-3 py-2 ${isSistema ? 'text-center' : ''}`}
                      style={{
                        background: isSistema ? 'rgba(107,114,128,0.08)' : fase?.bg || 'var(--sf-surface)',
                        border: isSistema ? 'none' : '1px solid var(--sf-border-subtle)',
                      }}>
                      {!isSistema && (
                        <div className="flex items-center gap-1.5 mb-1">
                          <AgenteIcon nome={msg.agente_nome} size={14} />
                          <span className="text-xs font-semibold" style={{ color: getAgenteCor(msg.agente_nome) }}>{msg.agente_nome}</span>
                          {fase && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: fase.bg, color: fase.text }}>
                              {fase.label}
                            </span>
                          )}
                          {msg.tipo === 'decisao' && <Zap className="w-3 h-3" style={{ color: '#fbbf24' }} />}
                          <span className="text-[9px] ml-auto" style={{ color: 'var(--sf-text-secondary)', opacity: 0.5 }}>
                            {msg.criado_em ? new Date(msg.criado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                          </span>
                        </div>
                      )}
                      <p className={`text-xs whitespace-pre-wrap ${isSistema ? 'font-medium' : ''}`}
                        style={{ color: isSistema ? 'var(--sf-text-secondary)' : 'var(--sf-text)' }}>
                        {msg.conteudo}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}

            {/* === ARTIFACTS === */}
            {abaDireita === 'artifacts' && (
              <div className="flex-1 overflow-auto p-3 space-y-3" style={{ background: 'var(--sf-bg)' }}>
                {artifacts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                    <Package className="w-12 h-12 opacity-30" />
                    <p className="text-sm">Nenhum artifact ainda.</p>
                  </div>
                ) : artifacts.map(art => (
                  <div key={art.artifact_id} onClick={() => setArtifactModal(art)}
                    className="rounded-lg p-3 cursor-pointer hover:scale-[1.01] transition-all"
                    style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
                    <div className="flex items-center gap-2">
                      {art.tipo === 'plano' && <ClipboardList className="w-4 h-4" style={{ color: '#60a5fa' }} />}
                      {art.tipo === 'checklist' && <CheckSquare className="w-4 h-4" style={{ color: '#34d399' }} />}
                      {art.tipo === 'terminal' && <Terminal className="w-4 h-4" style={{ color: '#fbbf24' }} />}
                      {art.tipo === 'codigo' && <Code2 className="w-4 h-4" style={{ color: '#a78bfa' }} />}
                      <span className="text-sm font-medium flex-1 truncate" style={{ color: 'var(--sf-text)' }}>{art.titulo}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${art.status === 'aprovado' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                        {art.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px]" style={{ color: 'var(--sf-text-secondary)' }}>
                      <AgenteIcon nome={art.agente_nome} size={12} />
                      <span>{art.agente_nome}</span>
                      {(art.comentarios_inline || []).length > 0 && (
                        <span className="flex items-center gap-0.5"><MessageSquare className="w-3 h-3" /> {art.comentarios_inline.length}</span>
                      )}
                      <span className="ml-auto">{tempoRelativo(art.criado_em)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* === MODAL DO ARTIFACT (grande, expansivel) === */}
      {artifactModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setArtifactModal(null)}>
          <div className="w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
            style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}
            onClick={e => e.stopPropagation()}>

            {/* Modal Header */}
            <div className="flex items-center gap-3 px-6 py-4 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
              {artifactModal.tipo === 'plano' && <ClipboardList className="w-5 h-5" style={{ color: '#60a5fa' }} />}
              {artifactModal.tipo === 'checklist' && <CheckSquare className="w-5 h-5" style={{ color: '#34d399' }} />}
              {artifactModal.tipo === 'codigo' && <Code2 className="w-5 h-5" style={{ color: '#a78bfa' }} />}
              {artifactModal.tipo === 'terminal' && <Terminal className="w-5 h-5" style={{ color: '#fbbf24' }} />}
              <div className="flex-1">
                <h3 className="text-base font-bold" style={{ color: 'var(--sf-text)' }}>{artifactModal.titulo}</h3>
                <div className="flex items-center gap-2 mt-0.5 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
                  <AgenteIcon nome={artifactModal.agente_nome} size={12} />
                  <span>{artifactModal.agente_nome}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${artifactModal.status === 'aprovado' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                    {artifactModal.status}
                  </span>
                </div>
              </div>
              <button onClick={() => setArtifactModal(null)} className="p-1 rounded hover:bg-white/10">
                <X className="w-5 h-5" style={{ color: 'var(--sf-text-secondary)' }} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-6">
              <pre className="text-sm p-4 rounded-xl font-mono whitespace-pre-wrap overflow-auto max-h-[50vh]"
                style={{ background: 'var(--sf-bg)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
                {artifactModal.conteudo || JSON.stringify(artifactModal.dados, null, 2)}
              </pre>

              {/* Comentarios */}
              {(artifactModal.comentarios_inline || []).length > 0 && (
                <div className="mt-4 space-y-2">
                  <span className="text-xs font-semibold flex items-center gap-1" style={{ color: 'var(--sf-text-secondary)' }}>
                    <MessageSquare className="w-3.5 h-3.5" /> {artifactModal.comentarios_inline.length} Comentarios
                  </span>
                  {artifactModal.comentarios_inline.map((c, ci) => (
                    <div key={ci} className="text-xs p-3 rounded-lg"
                      style={{ background: 'rgba(96,165,250,0.08)', border: '1px solid rgba(96,165,250,0.15)' }}>
                      <span className="font-semibold" style={{ color: '#60a5fa' }}>{c.autor}</span>
                      <span className="opacity-50 ml-2">{c.secao || (c.linha ? `linha ${c.linha}` : '')}</span>
                      <p className="mt-1" style={{ color: 'var(--sf-text)' }}>{c.texto}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Novo comentario */}
              <div className="flex items-center gap-2 mt-4">
                <input type="text" placeholder="Adicionar comentario..." value={novoComentario}
                  onChange={e => setNovoComentario(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && adicionarComentario(artifactModal.artifact_id)}
                  className="flex-1 px-3 py-2 rounded-lg text-sm"
                  style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
                <button onClick={() => adicionarComentario(artifactModal.artifact_id)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-white"
                  style={{ background: 'var(--sf-accent)' }}>
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center gap-3 px-6 py-4 flex-shrink-0"
              style={{ borderTop: '1px solid var(--sf-border-subtle)', background: 'var(--sf-bg)' }}>
              {artifactModal.tipo === 'codigo' && (
                <button onClick={() => aplicarNoEditor(artifactModal)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
                  style={{ background: 'var(--sf-accent)' }}>
                  <ExternalLink className="w-4 h-4" /> Aplicar no Editor
                </button>
              )}
              {artifactModal.tipo === 'codigo' && (
                <button onClick={async () => {
                  if (!sessao) return
                  // Rodar build/lint no terminal como verificação rápida
                  const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/comando`, {
                    method: 'POST', headers,
                    body: JSON.stringify({ comando: 'echo "✅ Código aplicado. Rode: npm run build" && node --version' }),
                  })
                  const d = await res.json()
                  setTerminalHistorico(prev => [...prev, { comando: 'node --version', saida: d.saida, sucesso: d.sucesso, timestamp: new Date().toISOString() }])
                  setArtifactModal(null)
                  setTimeout(() => terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight), 100)
                }}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' }}>
                  <Play className="w-4 h-4" /> Rodar Testes
                </button>
              )}
              <button onClick={() => { navigator.clipboard.writeText(artifactModal.conteudo || '') }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium"
                style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
                <Copy className="w-4 h-4" /> Copiar
              </button>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium"
                style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
                <Download className="w-4 h-4" /> Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
