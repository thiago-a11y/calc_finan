/* Mission Control — Code Studio 2.0 (v0.55.0 → v0.57.0)
 *
 * Painel triplo simultaneo: Editor + Terminal + Navegador
 * Agentes vivos geram artifacts tangiveis com comentarios inline
 *
 * v0.57.0 — Persistencia de sessoes:
 * - Lista de sessoes recentes ao entrar
 * - Auto-save a cada 10s (editor + terminal + artifacts)
 * - URL com ID: /mission-control/{sessionId}
 * - Resume perfeito (estado exato restaurado)
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useParams, useNavigate } from 'react-router-dom'
import ResizableHandle from '../components/code-studio/ResizableHandle'
import {
  Rocket, Terminal, Code2, Bot, FileText, CheckSquare,
  MessageSquare, Play, Send, Loader2,
  Maximize2, Minimize2, Sparkles, Package,
  Clock, ArrowRight, Plus, Save,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

/* ============================================================
   Tipos
   ============================================================ */

interface Artifact {
  artifact_id: string
  tipo: string
  titulo: string
  conteudo: string | null
  dados: Record<string, unknown>
  status: string
  agente_nome: string
  comentarios_inline: Array<{
    id: string; linha: number | null; secao: string
    texto: string; autor: string; data: string; resolvido: boolean
  }>
  criado_em: string | null
}

interface AgenteAtivo {
  id: string; nome: string; status: string
  tarefa: string; tipo: string; inicio: string; resultado?: string; erro?: string
}

interface TerminalEntry {
  comando: string; saida: string; sucesso: boolean; timestamp: string
}

interface Sessao {
  sessao_id: string; titulo: string; status: string; projeto_id: number | null
  agentes_ativos: AgenteAtivo[]; artifacts: Artifact[]
  painel_editor: { arquivos_abertos?: string[]; arquivo_ativo?: string; conteudo?: string } | null
  painel_terminal: { historico: TerminalEntry[]; cwd: string } | null
  total_artifacts: number; total_comandos: number
}

interface SessaoResumo {
  sessao_id: string; titulo: string; status: string; projeto_id: number | null
  agentes_ativos: AgenteAtivo[]; total_artifacts: number; total_comandos: number
  criado_em: string | null; atualizado_em: string | null
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

  // Painel Editor
  const [editorConteudo, setEditorConteudo] = useState('// Selecione um arquivo ou peca ao agente para gerar codigo\n')
  const [editorArquivo, setEditorArquivo] = useState('novo-arquivo.tsx')

  // Painel Terminal
  const [comandoTerminal, setComandoTerminal] = useState('')
  const [terminalHistorico, setTerminalHistorico] = useState<TerminalEntry[]>([])
  const [executandoCmd, setExecutandoCmd] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)

  // Artifacts
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [artifactSelecionado, setArtifactSelecionado] = useState<Artifact | null>(null)
  const [novoComentario, setNovoComentario] = useState('')

  // Agente
  const [instrucaoAgente, setInstrucaoAgente] = useState('')
  const [disparandoAgente, setDisparandoAgente] = useState(false)

  // Layout
  const [painelLarguras, setPainelLarguras] = useState([33, 34, 33])
  const [painelMaximizado, setPainelMaximizado] = useState<number | null>(null)

  // Auto-save
  const [ultimoSave, setUltimoSave] = useState<string>('')
  const [salvando, setSalvando] = useState(false)

  /* ============================================================
     Headers helper
     ============================================================ */

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }), [token])

  /* ============================================================
     Listar sessoes recentes
     ============================================================ */

  const carregarSessoes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessoes`, { headers })
      if (res.ok) {
        const data = await res.json()
        setSessoes(data)
      }
    } catch (e) {
      console.error('Erro ao carregar sessoes:', e)
    } finally {
      setCarregandoSessoes(false)
    }
  }, [headers])

  /* ============================================================
     Criar Sessao
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
    } catch (e) {
      console.error('Erro ao criar sessao:', e)
    } finally {
      setCriando(false)
    }
  }, [headers, titulo, navigate])

  /* ============================================================
     Carregar Sessao (com restore de estado)
     ============================================================ */

  const carregarSessao = useCallback(async (sessaoId: string) => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}`, { headers })
      if (!res.ok) return
      const data: Sessao = await res.json()
      setSessao(data)
      setArtifacts(data.artifacts || [])
      setTerminalHistorico(data.painel_terminal?.historico || [])
      // Restaurar editor
      if (data.painel_editor?.conteudo) {
        setEditorConteudo(data.painel_editor.conteudo)
      }
      if (data.painel_editor?.arquivo_ativo) {
        setEditorArquivo(data.painel_editor.arquivo_ativo)
      }
    } catch (e) {
      console.error('Erro ao carregar sessao:', e)
    }
  }, [headers])

  /* ============================================================
     Auto-save a cada 10s
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(async () => {
      try {
        setSalvando(true)
        await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/save`, {
          method: 'PATCH', headers,
          body: JSON.stringify({
            painel_editor: {
              conteudo: editorConteudo,
              arquivo_ativo: editorArquivo,
              arquivos_abertos: [editorArquivo],
            },
            painel_terminal: {
              historico: terminalHistorico.slice(-50),
              cwd: '',
            },
          }),
        })
        setUltimoSave(new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }))
      } catch {
        /* silencioso */
      } finally {
        setSalvando(false)
      }
    }, 10000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, headers, editorConteudo, editorArquivo, terminalHistorico])

  /* ============================================================
     Polling (agentes e artifacts — 5s)
     ============================================================ */

  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(() => carregarSessao(sessao.sessao_id), 5000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, carregarSessao])

  /* ============================================================
     Startup: carregar sessoes ou abrir direto por URL
     ============================================================ */

  useEffect(() => {
    if (urlSessionId) {
      carregarSessao(urlSessionId)
    } else {
      carregarSessoes()
    }
  }, [urlSessionId, carregarSessao, carregarSessoes])

  /* ============================================================
     Terminal
     ============================================================ */

  const executarComando = useCallback(async () => {
    if (!sessao || !comandoTerminal.trim()) return
    setExecutandoCmd(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/comando`, {
        method: 'POST', headers,
        body: JSON.stringify({ comando: comandoTerminal }),
      })
      const data = await res.json()
      setTerminalHistorico(prev => [...prev, {
        comando: comandoTerminal,
        saida: data.saida || '',
        sucesso: data.sucesso,
        timestamp: new Date().toISOString(),
      }])
      setComandoTerminal('')
      setTimeout(() => terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight), 100)
    } catch (e) {
      console.error('Erro no terminal:', e)
    } finally {
      setExecutandoCmd(false)
    }
  }, [sessao, comandoTerminal, headers])

  /* ============================================================
     Agentes
     ============================================================ */

  const dispararAgente = useCallback(async () => {
    if (!sessao || !instrucaoAgente.trim()) return
    setDisparandoAgente(true)
    try {
      await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/agente`, {
        method: 'POST', headers,
        body: JSON.stringify({ instrucao: instrucaoAgente, tipo: 'implementacao' }),
      })
      setInstrucaoAgente('')
    } catch (e) {
      console.error('Erro ao disparar agente:', e)
    } finally {
      setDisparandoAgente(false)
    }
  }, [sessao, instrucaoAgente, headers])

  /* ============================================================
     Comentarios Inline
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
    } catch (e) {
      console.error('Erro ao comentar:', e)
    }
  }, [novoComentario, headers, sessao, carregarSessao])

  /* ============================================================
     Helper: tempo relativo
     ============================================================ */

  function tempoRelativo(iso: string | null): string {
    if (!iso) return ''
    const diff = Date.now() - new Date(iso).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return 'agora'
    if (min < 60) return `${min}min atras`
    const h = Math.floor(min / 60)
    if (h < 24) return `${h}h atras`
    const d = Math.floor(h / 24)
    return `${d}d atras`
  }

  /* ============================================================
     Render: Tela de Sessoes (lista + nova sessao)
     ============================================================ */

  if (!sessao && !urlSessionId) {
    return (
      <div className="h-full overflow-auto" style={{ background: 'var(--sf-bg)' }}>
        <div className="max-w-3xl mx-auto p-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <Rocket className="w-8 h-8" style={{ color: 'var(--sf-accent)' }} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>
                Code Studio 2.0 — Editor + Terminal + Artifacts em painel triplo
              </p>
            </div>
          </div>

          {/* Nova sessao */}
          <div className="p-5 rounded-xl mb-8" style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Nome da sessao (ex: Feature Login SSO)"
                value={titulo}
                onChange={e => setTitulo(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && criarSessao()}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm"
                style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }}
              />
              <button
                onClick={criarSessao}
                disabled={criando}
                className="px-5 py-2.5 rounded-lg font-semibold text-white flex items-center gap-2 transition-transform hover:scale-105"
                style={{ background: 'var(--sf-accent)' }}
              >
                {criando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Nova Sessao
              </button>
            </div>
          </div>

          {/* Sessoes recentes */}
          <h2 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--sf-text-secondary)' }}>
            <Clock className="w-4 h-4" /> Sessoes Recentes
          </h2>

          {carregandoSessoes ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--sf-accent)' }} />
            </div>
          ) : sessoes.length === 0 ? (
            <div className="text-center py-12 rounded-xl" style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30" style={{ color: 'var(--sf-text-secondary)' }} />
              <p className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>Nenhuma sessao anterior.</p>
              <p className="text-xs mt-1" style={{ color: 'var(--sf-text-secondary)', opacity: 0.6 }}>Crie uma nova sessao para comecar.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessoes.map(s => {
                const ultimoAgente = (s.agentes_ativos || []).filter(a => a.status === 'concluido').pop()
                return (
                  <div
                    key={s.sessao_id}
                    onClick={() => navigate(`/mission-control/${s.sessao_id}`)}
                    className="flex items-center gap-4 p-4 rounded-xl cursor-pointer transition-all hover:scale-[1.01]"
                    style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}
                  >
                    <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{ background: s.status === 'ativa' ? 'rgba(16,185,129,0.15)' : 'rgba(107,114,128,0.15)' }}>
                      <Rocket className="w-5 h-5" style={{ color: s.status === 'ativa' ? 'var(--sf-accent)' : '#6b7280' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate" style={{ color: 'var(--sf-text)' }}>{s.titulo}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${s.status === 'ativa' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {s.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
                        <span className="flex items-center gap-1"><Package className="w-3 h-3" /> {s.total_artifacts} artifacts</span>
                        <span className="flex items-center gap-1"><Terminal className="w-3 h-3" /> {s.total_comandos} cmds</span>
                        {ultimoAgente && (
                          <span className="flex items-center gap-1"><Bot className="w-3 h-3" /> {ultimoAgente.nome}</span>
                        )}
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {tempoRelativo(s.atualizado_em)}</span>
                      </div>
                    </div>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
                      style={{ background: 'var(--sf-accent)', color: 'white' }}>
                      <ArrowRight className="w-3.5 h-3.5" /> Retomar
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    )
  }

  /* ============================================================
     Loading (quando vem via URL mas sessao ainda nao carregou)
     ============================================================ */

  if (!sessao && urlSessionId) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg)' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--sf-accent)' }} />
      </div>
    )
  }

  if (!sessao) return null

  /* ============================================================
     Render: Painel Triplo
     ============================================================ */

  const agentes = sessao.agentes_ativos || []
  const agentesExecutando = agentes.filter(a => a.status === 'executando')

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: 'var(--sf-bg)' }}>

      {/* === Header === */}
      <header className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <button onClick={() => { setSessao(null); navigate('/mission-control') }} className="opacity-60 hover:opacity-100">
          <Rocket className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
        </button>
        <span className="font-bold text-sm" style={{ color: 'var(--sf-text)' }}>Mission Control</span>
        <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--sf-bg)', color: 'var(--sf-text-secondary)' }}>
          {sessao.titulo}
        </span>

        {/* Agentes vivos */}
        {agentesExecutando.length > 0 && (
          <div className="flex items-center gap-2 ml-4">
            {agentesExecutando.map(a => (
              <div key={a.id} className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs animate-pulse"
                style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--sf-accent)' }}>
                <Bot className="w-3.5 h-3.5" />
                <span>{a.nome}</span>
                <Loader2 className="w-3 h-3 animate-spin" />
              </div>
            ))}
          </div>
        )}

        <div className="flex-1" />

        {/* Auto-save indicator */}
        {ultimoSave && (
          <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--sf-text-secondary)', opacity: 0.6 }}>
            {salvando ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            {salvando ? 'Salvando...' : `Salvo ${ultimoSave}`}
          </span>
        )}

        {/* Metricas */}
        <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
          <span className="flex items-center gap-1"><Package className="w-3.5 h-3.5" /> {artifacts.length} artifacts</span>
          <span className="flex items-center gap-1"><Terminal className="w-3.5 h-3.5" /> {sessao.total_comandos} cmds</span>
          <span className="flex items-center gap-1"><Bot className="w-3.5 h-3.5" /> {agentes.length} agentes</span>
        </div>
      </header>

      {/* === Instrucao do Agente (barra superior) === */}
      <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <Sparkles className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
        <input
          type="text"
          placeholder="Instruir agente: 'Crie um componente de login com validacao e testes'"
          value={instrucaoAgente}
          onChange={e => setInstrucaoAgente(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && dispararAgente()}
          className="flex-1 px-3 py-1.5 rounded text-sm"
          style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }}
        />
        <button
          onClick={dispararAgente}
          disabled={disparandoAgente || !instrucaoAgente.trim()}
          className="px-3 py-1.5 rounded text-xs font-medium text-white flex items-center gap-1"
          style={{ background: disparandoAgente ? '#666' : 'var(--sf-accent)' }}
        >
          {disparandoAgente ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          Executar
        </button>
      </div>

      {/* === Painel Triplo === */}
      <div className="flex flex-1 overflow-hidden">

        {/* Painel 1: Editor */}
        {(painelMaximizado === null || painelMaximizado === 0) && (
          <div className="flex flex-col overflow-hidden"
            style={{ width: painelMaximizado === 0 ? '100%' : `${painelLarguras[0]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Code2 className="w-3.5 h-3.5" />
              <span className="font-medium">Editor</span>
              <span className="opacity-60">{editorArquivo}</span>
              <div className="flex-1" />
              <button onClick={() => setPainelMaximizado(painelMaximizado === 0 ? null : 0)}
                className="opacity-60 hover:opacity-100">
                {painelMaximizado === 0 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
            <textarea
              className="flex-1 p-3 font-mono text-sm resize-none outline-none"
              style={{ background: '#1e1e2e', color: '#cdd6f4', border: 'none' }}
              value={editorConteudo}
              onChange={e => setEditorConteudo(e.target.value)}
              spellCheck={false}
            />
          </div>
        )}

        {painelMaximizado === null && <ResizableHandle onResize={(d) => {
          setPainelLarguras(prev => {
            const n = [...prev]
            const delta = (d / window.innerWidth) * 100
            n[0] = Math.max(15, Math.min(60, n[0] + delta))
            n[1] = Math.max(15, Math.min(60, n[1] - delta))
            return n
          })
        }} />}

        {/* Painel 2: Terminal */}
        {(painelMaximizado === null || painelMaximizado === 1) && (
          <div className="flex flex-col overflow-hidden"
            style={{ width: painelMaximizado === 1 ? '100%' : `${painelLarguras[1]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <Terminal className="w-3.5 h-3.5" />
              <span className="font-medium">Terminal</span>
              <div className="flex-1" />
              <button onClick={() => setPainelMaximizado(painelMaximizado === 1 ? null : 1)}
                className="opacity-60 hover:opacity-100">
                {painelMaximizado === 1 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
            <div ref={terminalRef} className="flex-1 overflow-auto p-3 font-mono text-xs"
              style={{ background: '#0d1117', color: '#c9d1d9' }}>
              {terminalHistorico.map((entry, i) => (
                <div key={i} className="mb-3">
                  <div className="flex items-center gap-1">
                    <span style={{ color: '#58a6ff' }}>$</span>
                    <span style={{ color: '#f0f6fc' }}>{entry.comando}</span>
                  </div>
                  <pre className="whitespace-pre-wrap mt-0.5"
                    style={{ color: entry.sucesso ? '#8b949e' : '#f85149' }}>
                    {entry.saida}
                  </pre>
                </div>
              ))}
              {terminalHistorico.length === 0 && (
                <div style={{ color: '#484f58' }}>Terminal pronto. Digite um comando abaixo.</div>
              )}
            </div>
            <div className="flex items-center gap-2 px-3 py-2 flex-shrink-0"
              style={{ background: '#161b22', borderTop: '1px solid #30363d' }}>
              <span className="text-xs" style={{ color: '#58a6ff' }}>$</span>
              <input
                type="text"
                value={comandoTerminal}
                onChange={e => setComandoTerminal(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && executarComando()}
                placeholder="Digite comando..."
                className="flex-1 bg-transparent text-xs outline-none font-mono"
                style={{ color: '#f0f6fc' }}
              />
              <button onClick={executarComando} disabled={executandoCmd}
                className="text-xs px-2 py-0.5 rounded"
                style={{ background: '#21262d', color: '#58a6ff' }}>
                {executandoCmd ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              </button>
            </div>
          </div>
        )}

        {painelMaximizado === null && <ResizableHandle onResize={(d) => {
          setPainelLarguras(prev => {
            const n = [...prev]
            const delta = (d / window.innerWidth) * 100
            n[1] = Math.max(15, Math.min(60, n[1] + delta))
            n[2] = Math.max(15, Math.min(60, n[2] - delta))
            return n
          })
        }} />}

        {/* Painel 3: Artifacts/Navegador */}
        {(painelMaximizado === null || painelMaximizado === 2) && (
          <div className="flex flex-col overflow-hidden"
            style={{ width: painelMaximizado === 2 ? '100%' : `${painelLarguras[2]}%` }}>
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs flex-shrink-0"
              style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text-secondary)' }}>
              <FileText className="w-3.5 h-3.5" />
              <span className="font-medium">Artifacts & Navegador</span>
              <div className="flex-1" />
              <button onClick={() => setPainelMaximizado(painelMaximizado === 2 ? null : 2)}
                className="opacity-60 hover:opacity-100">
                {painelMaximizado === 2 ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>

            <div className="flex-1 overflow-auto" style={{ background: 'var(--sf-bg)' }}>
              {artifacts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3"
                  style={{ color: 'var(--sf-text-secondary)' }}>
                  <Package className="w-12 h-12 opacity-30" />
                  <p className="text-sm">Nenhum artifact ainda.</p>
                  <p className="text-xs opacity-60">Instrua um agente para gerar planos, checklists e codigo.</p>
                </div>
              ) : (
                <div className="p-3 space-y-3">
                  {artifacts.map(art => (
                    <div key={art.artifact_id}
                      onClick={() => setArtifactSelecionado(art === artifactSelecionado ? null : art)}
                      className="rounded-lg p-3 cursor-pointer transition-all hover:scale-[1.01]"
                      style={{
                        background: 'var(--sf-surface)',
                        border: art === artifactSelecionado ? '2px solid var(--sf-accent)' : '1px solid var(--sf-border-subtle)',
                      }}>

                      <div className="flex items-center gap-2 mb-2">
                        {art.tipo === 'plano' && <FileText className="w-4 h-4" style={{ color: '#60a5fa' }} />}
                        {art.tipo === 'checklist' && <CheckSquare className="w-4 h-4" style={{ color: '#34d399' }} />}
                        {art.tipo === 'terminal' && <Terminal className="w-4 h-4" style={{ color: '#fbbf24' }} />}
                        {art.tipo === 'codigo' && <Code2 className="w-4 h-4" style={{ color: '#a78bfa' }} />}
                        <span className="text-sm font-medium" style={{ color: 'var(--sf-text)' }}>{art.titulo}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${art.status === 'aprovado' ? 'bg-green-500/20 text-green-400' : art.status === 'rejeitado' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {art.status}
                        </span>
                        <div className="flex-1" />
                        <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--sf-text-secondary)' }}>
                          <Bot className="w-3 h-3" /> {art.agente_nome}
                        </span>
                      </div>

                      {art === artifactSelecionado && (
                        <div className="mt-2">
                          <pre className="text-xs p-3 rounded overflow-auto max-h-60 font-mono whitespace-pre-wrap"
                            style={{ background: 'var(--sf-bg)', color: 'var(--sf-text)' }}>
                            {art.conteudo || JSON.stringify(art.dados, null, 2)}
                          </pre>

                          {(art.comentarios_inline || []).length > 0 && (
                            <div className="mt-3 space-y-2">
                              <span className="text-[10px] font-medium flex items-center gap-1" style={{ color: 'var(--sf-text-secondary)' }}>
                                <MessageSquare className="w-3 h-3" /> Comentarios
                              </span>
                              {art.comentarios_inline.map((c, ci) => (
                                <div key={ci} className="text-xs p-2 rounded"
                                  style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)' }}>
                                  <span className="font-medium" style={{ color: '#60a5fa' }}>{c.autor}</span>
                                  <span className="opacity-60 ml-2">{c.secao || `linha ${c.linha}`}</span>
                                  <p className="mt-1" style={{ color: 'var(--sf-text)' }}>{c.texto}</p>
                                </div>
                              ))}
                            </div>
                          )}

                          <div className="flex items-center gap-2 mt-3">
                            <input
                              type="text"
                              placeholder="Adicionar comentario..."
                              value={novoComentario}
                              onChange={e => setNovoComentario(e.target.value)}
                              onKeyDown={e => e.key === 'Enter' && adicionarComentario(art.artifact_id)}
                              className="flex-1 px-2 py-1 rounded text-xs"
                              style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }}
                              onClick={e => e.stopPropagation()}
                            />
                            <button
                              onClick={(e) => { e.stopPropagation(); adicionarComentario(art.artifact_id) }}
                              className="px-2 py-1 rounded text-xs"
                              style={{ background: 'var(--sf-accent)', color: 'white' }}>
                              <Send className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
