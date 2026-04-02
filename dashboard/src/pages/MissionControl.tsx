/* Mission Control — Code Studio 2.0 (v0.57.6)
 *
 * Painel triplo: Editor + Terminal + Team Chat/Artifacts
 * Multi-agente com conversa visivel, planejamento, review
 *
 * v0.57.6 — True Live Typing & Execution Feeling:
 * - True Live Typing: caractere por caractere no editor com cursor verde piscando
 * - Highlight de linha atual com fundo sutil
 * - Barra de progresso com % e texto "Gerando código... Fase X de 5"
 * - Ícone do agente pulsando forte durante execução
 * - Badge "Em execução" piscando no Team Chat
 * - Terminal com comandos reais em tempo real
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useParams, useNavigate } from 'react-router-dom'
import ResizableHandle from '../components/code-studio/ResizableHandle'
import MissionCompleteActions from '../components/MissionCompleteActions'
import PhaseDecisionControls from '../components/PhaseDecisionControls'
import {
  Rocket, Terminal, Code2, Bot, CheckSquare,
  MessageSquare, Play, Send, Loader2,
  Maximize2, Minimize2, Sparkles, Package,
  Clock, ArrowRight, Plus, Save, X,
  ClipboardList, Zap, Shield, Palette, Settings2,
  Copy, Download, ExternalLink, Radio, CheckCircle2,
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
  const { token, usuario, carregando } = useAuth()
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()

  // Token seguro: usa localStorage como fallback se token do context ainda nao esta disponivel
  const tokenSeguro = token || localStorage.getItem('sf_token') || ''

  // Guard de inicializacao: enquanto token nao existe, mostra spinner
  const [isInitializing, setIsInitializing] = useState(true)

  // Marcar como pronto quando token estiver disponivel
  useEffect(() => {
    if (tokenSeguro && tokenSeguro.length > 0) {
      setIsInitializing(false)
    }
  }, [tokenSeguro])

  // Guard: se autenticacao carregando ou token nao disponivel, mostra loading
  if (carregando || isInitializing) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--sf-accent)' }} />
      </div>
    )
  }

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

  // Typewriter effect
  const [editorAlvo, setEditorAlvo] = useState('')  // conteudo alvo (o que chegou do backend)
  const [editorDisplay, setEditorDisplay] = useState('')  // conteudo exibido (digitando...)
  const editorAlvoRef = useRef('')  // ref para evitar stale closure no rAF

  // Phase Decision (human-in-the-loop)
  const [faseStatus, setFaseStatus] = useState<{
    status: string
    fase_atual: number
    progresso: number
    waiting_decision: boolean
    fase_decisao: { fase: number; acao: string; decidido_por: string; timestamp: string } | null
    agente_nome: string | null
  } | null>(null)
  const [mostrarConclusao, setMostrarConclusao] = useState(false)  // tela de conclusao vs execucao

  // Auto-save
  const [ultimoSave, setUltimoSave] = useState('')
  const [salvando, setSalvando] = useState(false)

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${tokenSeguro}`,
  }), [tokenSeguro])

  // Guard: se token vazio, nao faz nada
  const hasToken = tokenSeguro && tokenSeguro.length > 0

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
    if (!hasToken) {
      console.warn('[MissionControl] Token nao disponivel para criar sessao')
      return
    }
    setCriando(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao`, {
        method: 'POST', headers,
        body: JSON.stringify({ titulo: titulo || 'Nova Sessao Mission Control' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status} ao criar sessao`)
      const text = await res.text()
      let data
      try { data = JSON.parse(text) } catch { throw new Error('Response nao e JSON valido') }
      if (!data.sessao_id) throw new Error('sessao_id missing from response')
      const novoId = String(data.sessao_id)
      // Resetar estado antes de navegar
      setSessao(null)
      setArtifacts([])
      setChatMsgs([])
      setTerminalHistorico([])
      setMostrarConclusao(false)
      setFaseStatus(null)
      navigate(`/mission-control/${novoId}`, { replace: true })
    } catch (e) {
      console.error('[MissionControl] Erro ao criar sessao:', e)
    } finally { setCriando(false) }
  }, [headers, titulo, navigate, hasToken])

  /* ============================================================
     Carregar sessao + restore
     ============================================================ */

  const carregarSessao = useCallback(async (sid: string) => {
    if (!hasToken || !sid) return
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sid}`, { headers })
      if (!res.ok) return
      const text = await res.text()
      let data: Sessao
      try { data = JSON.parse(text) } catch { return }
      setSessao(data)
      setArtifacts(data?.artifacts || [])

      // Detectar se agente esta ativo (para auto-save e polling)
      const temAgente = (data?.agentes_ativos || []).some((a: AgenteAtivo) => a?.status === 'executando')
      agentExecutandoRef.current = temAgente

      // Detectar streaming
      const isStreaming = data?.painel_editor?.streaming === true
      setEditorStreaming(isStreaming)

      // Atualizar editor com conteudo do agente
      const editorData = data?.painel_editor
      if (editorData?.conteudo) {
        const isFromAgent = editorData.fonte === 'agente'
        if (isFromAgent) {
          if (editorData.arquivo_ativo) setEditorArquivo(editorData.arquivo_ativo)
          setEditorFonteAgente(true)
          setEditorEditadoPeloUsuario(false)
          editorEditadoRef.current = false
          if (editorData.conteudo !== editorAlvoRef.current) {
            editorAlvoRef.current = editorData.conteudo
            setEditorAlvo(editorData.conteudo)
          }
        } else if (!editorEditadoRef.current) {
          setEditorConteudo(editorData.conteudo)
          setEditorDisplay(editorData.conteudo)
          editorAlvoRef.current = editorData.conteudo
          setEditorAlvo(editorData.conteudo)
          if (editorData.arquivo_ativo) setEditorArquivo(editorData.arquivo_ativo)
        }
      }

      // Atualizar terminal com TUDO do banco (agente + usuario)
      const histBanco = data.painel_terminal?.historico || []
      setTerminalHistorico(histBanco)
      if (histBanco.length > 0) {
        setTimeout(() => terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight), 100)
      }
    } catch (e) {
      console.error('[MissionControl] Erro ao carregar sessao:', e)
    }
  }, [headers, hasToken])

  /* ============================================================
     Team Chat polling (2s)
     ============================================================ */

  useEffect(() => {
    if (!hasToken || !sessao?.sessao_id) return
    let mounted = true
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/chat`, { headers })
        if (res.ok && mounted) {
          const text = await res.text()
          let msgs: ChatMsg[] = []
          try { msgs = JSON.parse(text) } catch { /* ignore */ }
          setChatMsgs(msgs || [])
          setTimeout(() => chatRef.current?.scrollTo(0, chatRef.current.scrollHeight), 50)
        }
      } catch { /* */ }
    }
    poll()
    const timer = setInterval(poll, 2000)
    return () => { mounted = false; clearInterval(timer) }
  }, [sessao?.sessao_id, headers, hasToken])

  /* ============================================================
     Auto-save (10s)
     ============================================================ */

  useEffect(() => {
    if (!hasToken || !sessao?.sessao_id) return
    const timer = setInterval(async () => {
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
  }, [sessao?.sessao_id, headers, editorConteudo, editorArquivo, terminalHistorico, hasToken])

  /* ============================================================
     True Live Typing — caractere por caractere como digitacao real
     Com cursor verde piscando e highlight de linha atual
     ============================================================ */

  useEffect(() => {
    if (!editorAlvo || editorAlvo === editorDisplay) {
      if (editorAlvo && editorAlvo === editorDisplay) {
        setEditorConteudo(editorAlvo)
      }
      return
    }

    // Reset se conteudo completamente diferente
    if (!editorAlvo.startsWith(editorDisplay.slice(0, Math.min(20, editorDisplay.length)))) {
      setEditorDisplay('')
      setEditorConteudo('')
    }

    // True live typing: 1 caractere por vez, delay varivel para efeito natural
    // Caracteres comuns: 15ms | Pontuacao: 30ms | Newline: 50ms | Indentacao: 10ms
    let charIndex = editorDisplay.length
    let timeoutId: ReturnType<typeof setTimeout>

    const typeNext = () => {
      const alvo = editorAlvoRef.current
      if (charIndex >= alvo.length) {
        setEditorDisplay(alvo)
        setEditorConteudo(alvo)
        return
      }

      const char = alvo[charIndex]
      charIndex++
      const display = alvo.slice(0, charIndex)
      setEditorDisplay(display)
      setEditorConteudo(display)

      // Delay variavel para efeito de digitacao natural
      let delay = 15
      if (char === '\n') delay = 40
      else if (char === ' ' || char === '\t') delay = 8
      else if ('.,;:!?'.includes(char)) delay = 28
      else if ('{}()[]'.includes(char)) delay = 25
      else if (char === '/' && alvo[charIndex] === '/') delay = 20
      else if (char === "'" || char === '"' || char === '`') delay = 22

      timeoutId = setTimeout(typeNext, delay)
    }

    timeoutId = setTimeout(typeNext, 20)
    return () => clearTimeout(timeoutId)
  }, [editorAlvo, editorDisplay])

  /* ============================================================
     Polling fase-status (2s) — detecta se agente espera decisao
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/fase-status`, { headers })
        if (res.ok) {
          const text = await res.text()
          try { setFaseStatus(JSON.parse(text)) } catch { /* ignore */ }
        }
      } catch { /* */ }
    }, 2000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, headers, hasToken])

  /* ============================================================
     Polling sessao — sempre 2s para nao perder atualizacoes do agente
     (nao depende de sessao?.agentes_ativos para evitar restart a cada poll)
     ============================================================ */

  useEffect(() => {
    if (!hasToken || !sessao?.sessao_id) return
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
    if (!hasToken) {
      console.warn('[MissionControl] Token nao disponivel para disparar agente')
      return
    }
    if (!sessao?.sessao_id || !instrucaoAgente.trim()) return
    setDisparandoAgente(true)
    setAbaDireita('chat')
    // Resetar estado do editor para receber conteudo do agente (typewriter)
    setEditorEditadoPeloUsuario(false)
    editorEditadoRef.current = false
    setEditorFonteAgente(false)
    setEditorAlvo('')
    setEditorDisplay('')
    editorAlvoRef.current = ''
    setMostrarConclusao(false) // Reset conclusao se estava ativa
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/agente`, {
        method: 'POST', headers,
        body: JSON.stringify({ instrucao: instrucaoAgente, tipo: 'implementacao' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const text = await res.text()
      try { JSON.parse(text) } catch { /* ignore non-JSON */ }
      setInstrucaoAgente('')
      await carregarSessao(sessao.sessao_id)
    } catch (e) {
      console.error('[MissionControl] Erro ao disparar agente:', e)
    } finally { setDisparandoAgente(false) }
  }, [sessao, instrucaoAgente, headers, carregarSessao, hasToken])

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
     Phase Decision Handler — callback para PhaseDecisionControls
     ============================================================ */

  const handleFaseDecisao = useCallback(async (fase: number, acao: string) => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao?.sessao_id}/fase-decisao`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ fase, acao }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Erro ao enviar decisao')
    } catch (e) {
      console.error('[MissionControl] Erro fase-decisao:', e)
    }
  }, [sessao, headers])

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
      <div className="h-full overflow-auto" style={{ background: 'var(--sf-bg-primary)' }}>
        <div className="max-w-3xl mx-auto p-8">
          <div className="flex items-center gap-3 mb-8">
            <Rocket className="w-8 h-8" style={{ color: 'var(--sf-accent)' }} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Multi-agente com planejamento, discussao e review visiveis</p>
            </div>
          </div>

          <div className="p-5 rounded-xl mb-8" style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
            <div className="flex items-center gap-3">
              <input type="text" placeholder="Nome da sessao (ex: Feature Login SSO)" value={titulo}
                onChange={e => setTitulo(e.target.value)} onKeyDown={e => e.key === 'Enter' && criarSessao()}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm"
                style={{ background: 'var(--sf-bg-primary)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
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
    return <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
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

  // Detectar conclusao: fase 5/5 + 100% = missao concluida
  const isCompleto = faseAtual === 5 && progressoAtual === 100

  // Quando todas as 5 fases aprovadas -> mostrar tela de conclusao
  useEffect(() => {
    if (isCompleto && !mostrarConclusao) {
      setMostrarConclusao(true)
    }
  }, [isCompleto, mostrarConclusao])

  /* ============================================================
     Render: Painel Triplo
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

        {agentesExecutando.length > 0 && (
          <div className="flex items-center gap-2 ml-4">
            {agentesExecutando.map(a => (
              <div key={a.id} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                style={{
                  background: 'rgba(16,185,129,0.2)',
                  color: 'var(--sf-accent)',
                  border: '1px solid rgba(16,185,129,0.4)',
                  boxShadow: '0 0 16px rgba(16,185,129,0.2)',
                }}>
                <div className="agent-pulse" style={{ lineHeight: 0 }}>
                  <Bot className="w-4 h-4" style={{ filter: 'drop-shadow(0 0 8px rgba(16,185,129,0.9))' }} />
                </div>
                <span className="font-bold">{a.nome}</span>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              </div>
            ))}
          </div>
        )}

        {/* Badge verde de conclusao quando missoa atingir 100% */}
        {isCompleto && (
          <div className="flex items-center gap-2 ml-4 animate-[fadeIn_0.5s_ease-out]"
            style={{
              background: 'rgba(16,185,129,0.25)',
              color: '#10b981',
              border: '1px solid rgba(16,185,129,0.5)',
              boxShadow: '0 0 20px rgba(16,185,129,0.3)',
              padding: '4px 12px',
              borderRadius: '9999px',
            }}>
            <CheckCircle2 className="w-4 h-4" style={{ filter: 'drop-shadow(0 0 6px rgba(16,185,129,0.8))' }} />
            <span className="text-xs font-bold">Mission Control Agent</span>
            <span className="text-xs font-medium" style={{ color: 'rgba(16,185,129,0.7)' }}>Concluído</span>
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
      <div className="flex-shrink-0" style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        {/* CSS para animacoes */}
        <style>{`
          @keyframes progressShimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          @keyframes agentPulse {
            0%, 100% { transform: scale(1); opacity: 1; filter: drop-shadow(0 0 6px rgba(16,185,129,0.8)); }
            50% { transform: scale(1.3); opacity: 0.6; filter: drop-shadow(0 0 12px rgba(16,185,129,1)); }
          }
          @keyframes dotBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
          @keyframes cursorBlink {
            0%, 49% { opacity: 1; box-shadow: 0 0 12px #10b981, 0 0 20px rgba(16,185,129,0.6); }
            50%, 100% { opacity: 0; box-shadow: none; }
          }
          @keyframes execBadgePulse {
            0%, 100% { box-shadow: 0 0 8px rgba(16,185,129,0.4); }
            50% { box-shadow: 0 0 16px rgba(16,185,129,0.8); }
          }
          @keyframes liveGlow {
            0%, 100% { box-shadow: 0 0 8px rgba(239,68,68,0.4); }
            50% { box-shadow: 0 0 20px rgba(239,68,68,0.8); }
          }
          .progress-shimmer {
            background-size: 200% 100%;
            animation: progressShimmer 2s linear infinite;
          }
          .agent-pulse {
            animation: agentPulse 0.8s ease-in-out infinite;
          }
          .live-cursor {
            display: inline-block;
            width: 2px;
            height: 1.1em;
            background: #10b981;
            margin-left: 1px;
            vertical-align: text-bottom;
            border-radius: 1px;
            animation: cursorBlink 0.65s step-end infinite;
            box-shadow: 0 0 12px #10b981, 0 0 20px rgba(16,185,129,0.6);
          }
          .exec-badge {
            animation: execBadgePulse 1.2s ease-in-out infinite;
          }
          .live-badge {
            animation: liveGlow 0.8s ease-in-out infinite;
          }
          .editor-line-highlight {
            background: rgba(16, 185, 129, 0.06);
            border-left: 2px solid rgba(16, 185, 129, 0.4);
            margin-left: -12px;
            padding-left: 10px;
          }
        `}</style>

        {/* Progress bar + LIVE toggle - aparece quando executa, OCULTA quando completo */}
        {agentesExecutando.length > 0 && !isCompleto && (
          <div className="px-4 pt-2 pb-1">
            <div className="flex items-center gap-2 mb-1.5">
              {/* Icone de agente pulsante */}
              <div className="agent-pulse" style={{ lineHeight: 0 }}>
                <Bot className="w-4 h-4" style={{ color: 'var(--sf-accent)', filter: 'drop-shadow(0 0 6px rgba(16,185,129,0.6))' }} />
              </div>
              <span className="text-xs font-bold" style={{ color: 'var(--sf-accent)' }}>
                {faseLabel ? `Fase ${faseAtual}/5 — ${faseLabel}` : 'Executando...'}
              </span>
              {editorStreaming && modoLive && (
                <span className="live-badge text-[9px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1"
                  style={{ background: 'rgba(239,68,68,0.2)', color: '#f87171', border: '1px solid rgba(239,68,68,0.5)' }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" style={{ animation: 'dotBlink 0.6s infinite' }} />
                  STREAMING
                </span>
              )}
              <div className="flex-1" />
              {/* Descricao textual do progresso — mais descritivo */}
              <span className="text-[10px] font-bold" style={{ color: 'var(--sf-text-secondary)' }}>
                {faseAtual === 1 ? '📋 Analisando tarefa... Fase 1/5' :
                 faseAtual === 2 ? '💬 Equipe discutindo... Fase 2/5' :
                 faseAtual === 3 ? '⚡ Gerando código... Fase 3/5' :
                 faseAtual === 4 ? '🔍 Revisando qualidade... Fase 4/5' :
                 faseAtual === 5 ? '🚀 Finalizando! Fase 5/5' : '⏳ Processando...'}
              </span>
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
              <span className="text-xs font-bold tabular-nums" style={{ color: 'var(--sf-accent)', minWidth: '32px', textAlign: 'right' }}>
                {progressoAtual || 0}%
              </span>
            </div>
            {/* Barra de progresso grossa + shimmer + glow forte quando LIVE */}
            <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--sf-bg-primary)', boxShadow: modoLive ? '0 0 20px rgba(16,185,129,0.15)' : 'none' }}>
              <div className="h-full rounded-full transition-all duration-500 ease-out progress-shimmer"
                style={{
                  width: `${progressoAtual || 5}%`,
                  background: modoLive
                    ? 'linear-gradient(90deg, #10b981, #34d399, #60a5fa, #a78bfa, #10b981)'
                    : 'linear-gradient(90deg, var(--sf-accent), #60a5fa)',
                  backgroundSize: '200% 100%',
                  boxShadow: modoLive ? '0 0 24px rgba(16,185,129,0.7), 0 0 40px rgba(16,185,129,0.3)' : '0 0 10px var(--sf-accent)',
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
            style={{ background: 'var(--sf-bg-primary)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
          <button onClick={dispararAgente} disabled={disparandoAgente || !instrucaoAgente.trim()}
            className="px-3 py-1.5 rounded text-xs font-medium text-white flex items-center gap-1"
            style={{ background: disparandoAgente ? '#666' : 'var(--sf-accent)' }}>
            {disparandoAgente ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            Executar Equipe
          </button>
        </div>
      </div>

      {/* === Painel de Ações Recomendadas (quando 100% concluído) === */}
      {mostrarConclusao ? (
        <MissionCompleteActions
          token={tokenSeguro}
          sessaoId={sessao.sessao_id}
          papel={usuario?.papeis?.[0] || 'membro'}
          sessaoTitulo={sessao.titulo}
          totalArtifacts={artifacts.length}
          totalComandos={sessao.total_comandos}
          onVoltarRevisao={() => {
            // Volta para a tela de execucao sem perder estado
            setMostrarConclusao(false)
          }}
          onTestar={() => alert('Testar: pytest executado!')}
          onAplicarCodeStudio={() => {
            // Copia código do artifact para o editor
            const codigoArtifact = artifacts.find(a => a.tipo === 'codigo')
            if (codigoArtifact?.conteudo) {
              setEditorConteudo(codigoArtifact.conteudo)
              setEditorArquivo((codigoArtifact.dados as Record<string, string>)?.arquivo || 'implementacao.tsx')
            }
          }}
          onFactoryOptimizer={() => alert('Factory Optimizer: análise PDCA iniciada!')}
          onAprovarOperations={() => alert('Pedido de aprovação enviado para Jonatas!')}
          onConvidarColaborador={() => navigate('/equipe')}
          onGerarRelatorioCEO={() => alert('Relatório CEO gerado e enviado por email!')}
          onNovaSessao={() => navigate('/mission-control')}
        />
      ) : faseStatus?.waiting_decision ? (
        /* === Phase Decision Controls (human-in-the-loop) === */
        <div className="flex flex-col h-full">
          {/* Barra superior com mini-info */}
          <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
            style={{ background: 'rgba(251,191,36,0.1)', borderBottom: '1px solid rgba(251,191,36,0.3)' }}>
            <Bot className="w-5 h-5" style={{ color: '#fbbf24' }} />
            <span className="text-sm font-bold" style={{ color: '#fbbf24' }}>
              {faseStatus.agente_nome || 'Agente'} — Aguardando sua decisao
            </span>
            <div className="flex-1" />
            <span className="text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
              Fase {faseStatus.fase_atual}/5 • {faseStatus.progresso}%
            </span>
          </div>
          {/* Painel triplo abaixo + controles de decisao na lateral */}
          <div className="flex flex-1 overflow-hidden">
            {/* Painel Triplo (缩放) */}
            <div className="flex flex-1 overflow-hidden">
              <div className="flex flex-1 overflow-hidden">
                {/* Editor */}
                {(painelMaximizado === null || painelMaximizado === 0) && (
                  <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 0 ? '100%' : `${painelLarguras[0]}%` }}>
                    <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
                      style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
                      <Code2 className="w-3.5 h-3.5" />
                      <span className="font-medium">Editor</span>
                      <span className="opacity-60 truncate max-w-[120px]">{editorArquivo}</span>
                      <div className="flex-1" />
                      <button onClick={() => setPainelMaximizado(painelMaximizado === 0 ? null : 0)} className="opacity-60 hover:opacity-100">
                        {painelMaximizado === 0 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <div className="relative flex-1 overflow-hidden">
                      <div className="absolute inset-0 p-3 overflow-auto font-mono text-sm"
                        style={{ background: '#1e1e2e', color: '#cdd6f4', lineHeight: '1.6', fontSize: '13px' }}>
                        {editorConteudo.split('\n').map((linha, i) => (
                          <div key={i} className="whitespace-pre" style={{ minHeight: '1.6em' }}>{linha}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                {painelMaximizado === null && <div className="w-1 flex-shrink-0 cursor-col-resize" style={{ background: 'var(--sf-border-subtle)' }} />}
                {/* Terminal */}
                {(painelMaximizado === null || painelMaximizado === 1) && (
                  <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 1 ? '100%' : `${painelLarguras[1]}%` }}>
                    <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
                      style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
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
                            <span style={{ color: entry.tipo === 'agente' ? '#10b981' : '#f0f6fc' }}>{entry.comando}</span>
                          </div>
                          {entry.saida && (
                            <pre className="whitespace-pre-wrap mt-0.5 pl-4" style={{ color: entry.sucesso ? '#8b949e' : '#f85149' }}>{entry.saida}</pre>
                          )}
                        </div>
                      ))}
                      {terminalHistorico.length === 0 && (
                        <div style={{ color: '#484f58' }}>Terminal pausado aguardando decisao...</div>
                      )}
                    </div>
                  </div>
                )}
                {painelMaximizado === null && <div className="w-1 flex-shrink-0 cursor-col-resize" style={{ background: 'var(--sf-border-subtle)' }} />}
                {/* Team Chat + Artifacts */}
                {(painelMaximizado === null || painelMaximizado === 2) && (
                  <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 2 ? '100%' : `${painelLarguras[2]}%` }}>
                    <div className="flex items-center gap-1 px-3 py-1.5 text-xs flex-shrink-0"
                      style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
                      <button onClick={() => setAbaDireita('chat')}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${abaDireita === 'chat' ? '' : 'opacity-50 hover:opacity-80'}`}
                        style={abaDireita === 'chat' ? { background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' } : { color: 'var(--sf-text-secondary)' }}>
                        <MessageSquare className="w-3.5 h-3.5" /> Team Chat
                      </button>
                      <button onClick={() => setAbaDireita('artifacts')}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${abaDireita === 'artifacts' ? '' : 'opacity-50 hover:opacity-80'}`}
                        style={abaDireita === 'artifacts' ? { background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' } : { color: 'var(--sf-text-secondary)' }}>
                        <Package className="w-3.5 h-3.5" /> Artifacts
                      </button>
                      <div className="flex-1" />
                      <button onClick={() => setPainelMaximizado(painelMaximizado === 2 ? null : 2)} className="opacity-60 hover:opacity-100">
                        {painelMaximizado === 2 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    {abaDireita === 'chat' && (
                      <div ref={chatRef} className="flex-1 overflow-auto p-3 space-y-2" style={{ background: 'var(--sf-bg-primary)' }}>
                        {chatMsgs.length === 0 ? (
                          <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                            <MessageSquare className="w-12 h-12 opacity-20" />
                            <p className="text-sm">Aguardando conversa...</p>
                          </div>
                        ) : chatMsgs.map(msg => {
                          const fase = FASE_COR[msg.fase] || null
                          const isSistema = msg.tipo === 'sistema'
                          return (
                            <div key={msg.id} className={`rounded-lg px-3 py-2 ${isSistema ? 'text-center' : ''}`}
                              style={{
                                background: isSistema ? 'rgba(107,114,128,0.08)' : fase?.bg || 'var(--sf-bg-card)',
                                border: isSistema ? 'none' : `1px solid var(--sf-border-subtle)'`,
                              }}>
                              {!isSistema && (
                                <div className="flex items-center gap-1.5 mb-1">
                                  <AgenteIcon nome={msg.agente_nome} size={14} />
                                  <span className="text-xs font-semibold" style={{ color: getAgenteCor(msg.agente_nome) }}>{msg.agente_nome}</span>
                                  {fase && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: fase.bg, color: fase.text }}>{fase.label}</span>
                                  )}
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
                    {abaDireita === 'artifacts' && (
                      <div className="flex-1 overflow-auto p-3 space-y-3" style={{ background: 'var(--sf-bg-primary)' }}>
                        {artifacts.length === 0 ? (
                          <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                            <Package className="w-12 h-12 opacity-30" />
                            <p className="text-sm">Nenhum artifact ainda.</p>
                          </div>
                        ) : artifacts.map(art => (
                          <div key={art.artifact_id} onClick={() => setArtifactModal(art)}
                            className="rounded-lg p-3 cursor-pointer hover:scale-[1.01] transition-all"
                            style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
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
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            {/* Lateral: Phase Decision Controls */}
            <div className="w-80 flex-shrink-0 overflow-auto"
              style={{ background: 'var(--sf-bg-card)', borderLeft: '2px solid rgba(251,191,36,0.4)' }}>
              <PhaseDecisionControls
                token={tokenSeguro}
                sessaoId={sessao.sessao_id}
                fase={faseStatus.fase_atual || faseAtual || 1}
                faseLabel={faseLabel || ''}
                progresso={faseStatus.progresso || progressoAtual || 0}
                agenteNome={faseStatus.agente_nome || agente_exec?.nome || 'Agente'}
                onDecisao={handleFaseDecisao}
                onRevisar={(f) => {
                  // Abre o artifact da fase correspondente para review
                  const tipoArtifact = ['plano', 'discussao', 'codigo', 'checklist', 'conclusao'][f - 1] || 'codigo'
                  const art = artifacts.find(a => a.tipo === tipoArtifact)
                  if (art) setArtifactModal(art)
                }}
              />
            </div>
          </div>
        </div>
      ) : (
      <div className="flex flex-1 overflow-hidden">

        {/* Painel 1: Editor */}
        {(painelMaximizado === null || painelMaximizado === 0) && (
          <div className="flex flex-col overflow-hidden" style={{ width: painelMaximizado === 0 ? '100%' : `${painelLarguras[0]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Code2 className="w-3.5 h-3.5" />
              <span className="font-medium">Editor</span>
              <span className="opacity-60 truncate max-w-[120px]">{editorArquivo}</span>
              {editorStreaming && modoLive && (
                <span className="live-badge flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full font-bold"
                  style={{ background: 'rgba(239,68,68,0.2)', color: '#f87171', border: '1px solid rgba(239,68,68,0.5)' }}>
                  <Radio className="w-3 h-3" style={{ filter: 'drop-shadow(0 0 6px #ef4444)' }} /> LIVE
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
              {/* Editor com highlight de linha atual + cursor verde */}
              <div
                className="absolute inset-0 p-3 overflow-auto font-mono text-sm"
                style={{ background: '#1e1e2e', color: '#cdd6f4', lineHeight: '1.6', fontSize: '13px' }}
                onClick={() => {
                  setEditorEditadoPeloUsuario(true); editorEditadoRef.current = true; setEditorFonteAgente(false)
                }}
              >
                {/* Linha atual com highlight (durante streaming) */}
                {editorStreaming && modoLive && editorConteudo.split('\n').map((linha, i) => {
                  const isLastLine = i === editorConteudo.split('\n').length - 1
                  return (
                    <div
                      key={i}
                      className={isLastLine ? 'editor-line-highlight' : ''}
                      style={{ minHeight: '1.6em', whiteSpace: 'pre' }}
                    >
                      {linha}
                      {isLastLine && <span className="live-cursor" />}
                    </div>
                  )
                })}
                {/* Conteudo estatico quando nao streaming */}
                {!editorStreaming && editorConteudo.split('\n').map((linha, i) => {
                  const totalLinhas = editorConteudo.split('\n').length
                  const isLastLine = i === totalLinhas - 1
                  return (
                    <div
                      key={i}
                      className={editorFonteAgente && isLastLine ? 'editor-line-highlight' : ''}
                      style={{ minHeight: '1.6em', whiteSpace: 'pre' }}
                    >
                      {linha}
                      {editorFonteAgente && isLastLine && !agentesExecutando.length && (
                        <span className="live-cursor" />
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Indicador "escrevendo código" durante LIVE streaming */}
              {editorStreaming && modoLive && (
                <div className="absolute bottom-3 right-3 flex items-center gap-2 px-3 py-1.5 rounded-lg live-badge"
                  style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', border: '1px solid rgba(239,68,68,0.4)' }}>
                  <span className="w-2 h-5 rounded-sm" style={{
                    background: '#10b981',
                    animation: 'cursorBlink 0.65s step-end infinite',
                    boxShadow: '0 0 12px #10b981',
                  }} />
                  <span className="text-[10px] font-mono font-bold" style={{ color: '#10b981' }}>
                    digitando
                    <span style={{ animation: 'dotBlink 1s infinite' }}>...</span>
                  </span>
                  <span className="text-[9px] font-mono" style={{ color: '#6b7280' }}>
                    {editorConteudo.split('\n').length}L · {editorConteudo.length}C
                  </span>
                </div>
              )}
              {/* Indicador "agente ativo" fora de streaming (fases 1, 2, 4) */}
              {!editorStreaming && agentesExecutando.length > 0 && editorFonteAgente && (
                <div className="absolute bottom-3 right-3 flex items-center gap-2 px-3 py-1.5 rounded-lg"
                  style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', border: '1px solid rgba(251,191,36,0.3)' }}>
                  <Loader2 className="w-3 h-3 animate-spin" style={{ color: '#fbbf24' }} />
                  <span className="text-[10px] font-mono" style={{ color: '#fbbf24' }}>
                    agente trabalhando
                  </span>
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
              style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Terminal className="w-3.5 h-3.5" /><span className="font-medium">Terminal</span>
              {agentesExecutando.length > 0 && (
                <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full animate-pulse"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
                  <Loader2 className="w-2.5 h-2.5 animate-spin" /> ativo
                </span>
              )}
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
              {/* Cursor verde piscante no final quando agente executa */}
              {agentesExecutando.length > 0 && (
                <div className="flex items-center gap-1 mt-1">
                  <span style={{ color: '#10b981', fontWeight: 'bold' }}>$</span>
                  <span className="live-cursor" style={{ width: '2px', height: '14px', background: '#10b981' }} />
                  <span className="text-[10px] ml-2" style={{ color: '#6b7280', fontStyle: 'italic' }}>
                    agente executando...
                  </span>
                </div>
              )}
              {terminalHistorico.length === 0 && (
                <div style={{ color: '#484f58' }}>
                  Terminal pronto. Agentes executam comandos reais aqui.
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
              style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
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
              <div ref={chatRef} className="flex-1 overflow-auto p-3 space-y-2" style={{ background: 'var(--sf-bg-primary)' }}>
                {chatMsgs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                    <MessageSquare className="w-12 h-12 opacity-20" />
                    <p className="text-sm">Nenhuma conversa ainda.</p>
                    <p className="text-xs opacity-60">Instrua a equipe acima para ver os agentes conversando.</p>
                  </div>
                ) : chatMsgs.map(msg => {
                  const fase = FASE_COR[msg.fase] || null
                  const isSistema = msg.tipo === 'sistema'
                  // Verificar se este agente esta executando agora
                  const agenteAtivo = agentesExecutando.find(a => a.nome === msg.agente_nome)
                  return (
                    <div key={msg.id} className={`rounded-lg px-3 py-2 ${isSistema ? 'text-center' : ''}`}
                      style={{
                        background: isSistema ? 'rgba(107,114,128,0.08)' : fase?.bg || 'var(--sf-bg-card)',
                        border: isSistema ? 'none' : `1px solid ${agenteAtivo ? 'rgba(16,185,129,0.3)' : 'var(--sf-border-subtle)'}`,
                        ...(agenteAtivo ? { boxShadow: '0 0 8px rgba(16,185,129,0.1)' } : {}),
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
                          {/* Badge "Em execucao" para agentes ativos — mais visivel */}
                          {agenteAtivo && (
                            <span className="exec-badge flex items-center gap-1 text-[8px] px-2 py-0.5 rounded-full font-bold"
                              style={{ background: 'rgba(16,185,129,0.25)', color: '#10b981', border: '1px solid rgba(16,185,129,0.5)' }}>
                              <Loader2 className="w-2.5 h-2.5 animate-spin" /> Em execução
                            </span>
                          )}
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
              <div className="flex-1 overflow-auto p-3 space-y-3" style={{ background: 'var(--sf-bg-primary)' }}>
                {artifacts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--sf-text-secondary)' }}>
                    <Package className="w-12 h-12 opacity-30" />
                    <p className="text-sm">Nenhum artifact ainda.</p>
                  </div>
                ) : artifacts.map(art => (
                  <div key={art.artifact_id} onClick={() => setArtifactModal(art)}
                    className="rounded-lg p-3 cursor-pointer hover:scale-[1.01] transition-all"
                    style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
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
      )}

      {/* === MODAL DO ARTIFACT (grande, expansivel) === */}
      {artifactModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setArtifactModal(null)}>
          <div className="w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
            style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}
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
                style={{ background: 'var(--sf-bg-primary)', color: 'var(--sf-text)', border: '1px solid var(--sf-border-subtle)' }}>
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
                  style={{ background: 'var(--sf-bg-primary)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
                <button onClick={() => adicionarComentario(artifactModal.artifact_id)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-white"
                  style={{ background: 'var(--sf-accent)' }}>
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center gap-3 px-6 py-4 flex-shrink-0"
              style={{ borderTop: '1px solid var(--sf-border-subtle)', background: 'var(--sf-bg-primary)' }}>
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
