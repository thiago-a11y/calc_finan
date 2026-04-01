/* Mission Control — Code Studio 2.0 (v0.55.0)
 *
 * Painel triplo simultaneo: Editor + Terminal + Navegador
 * Agentes vivos geram artifacts tangiveis com comentarios inline
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import ResizableHandle from '../components/code-studio/ResizableHandle'
import {
  Rocket, Terminal, Code2, Bot, FileText, CheckSquare,
  MessageSquare, Play, Send, Loader2,
  Maximize2, Minimize2, Sparkles, Package,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
  painel_terminal: { historico: TerminalEntry[]; cwd: string }
  total_artifacts: number; total_comandos: number
}

/* ============================================================
   Componente Principal
   ============================================================ */

export default function MissionControl() {
  const { token } = useAuth()

  // Sessao
  const [sessao, setSessao] = useState<Sessao | null>(null)
  const [criando, setCriando] = useState(false)
  const [titulo, setTitulo] = useState('')

  // Painel Editor
  const [editorConteudo] = useState('// Selecione um arquivo ou peça ao agente para gerar código\n')
  const [editorArquivo] = useState('novo-arquivo.tsx')

  // Painel Terminal
  const [comandoTerminal, setComandoTerminal] = useState('')
  const [terminalHistorico, setTerminalHistorico] = useState<TerminalEntry[]>([])
  const [executandoCmd, setExecutandoCmd] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)

  // Painel Navegador (reservado para v0.55.1)

  // Artifacts
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [artifactSelecionado, setArtifactSelecionado] = useState<Artifact | null>(null)
  const [novoComentario, setNovoComentario] = useState('')

  // Agente
  const [instrucaoAgente, setInstrucaoAgente] = useState('')
  const [disparandoAgente, setDisparandoAgente] = useState(false)

  // Layout
  const [painelLarguras, setPainelLarguras] = useState([33, 34, 33]) // % de cada painel
  const [painelMaximizado, setPainelMaximizado] = useState<number | null>(null)
  // Aba inferior (reservado para expansao)

  /* ============================================================
     Criar/Carregar Sessao
     ============================================================ */

  const criarSessao = useCallback(async () => {
    setCriando(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ titulo: titulo || 'Nova Sessão Mission Control' }),
      })
      const data = await res.json()
      // Carregar sessao completa
      await carregarSessao(data.sessao_id)
    } catch (e) {
      console.error('Erro ao criar sessao:', e)
    } finally {
      setCriando(false)
    }
  }, [token, titulo])

  const carregarSessao = useCallback(async (sessaoId: string) => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data: Sessao = await res.json()
      setSessao(data)
      setArtifacts(data.artifacts || [])
      setTerminalHistorico(data.painel_terminal?.historico || [])
    } catch (e) {
      console.error('Erro ao carregar sessao:', e)
    }
  }, [token])

  // Polling para atualizar sessao (agentes, artifacts)
  useEffect(() => {
    if (!sessao?.sessao_id) return
    const timer = setInterval(() => carregarSessao(sessao.sessao_id), 5000)
    return () => clearInterval(timer)
  }, [sessao?.sessao_id, carregarSessao])

  /* ============================================================
     Terminal
     ============================================================ */

  const executarComando = useCallback(async () => {
    if (!sessao || !comandoTerminal.trim()) return
    setExecutandoCmd(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/comando`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
  }, [sessao, comandoTerminal, token])

  /* ============================================================
     Agentes
     ============================================================ */

  const dispararAgente = useCallback(async () => {
    if (!sessao || !instrucaoAgente.trim()) return
    setDisparandoAgente(true)
    try {
      await fetch(`${API}/api/mission-control/sessao/${sessao.sessao_id}/agente`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ instrucao: instrucaoAgente, tipo: 'implementacao' }),
      })
      setInstrucaoAgente('')
      // Polling vai atualizar
    } catch (e) {
      console.error('Erro ao disparar agente:', e)
    } finally {
      setDisparandoAgente(false)
    }
  }, [sessao, instrucaoAgente, token])

  /* ============================================================
     Comentarios Inline
     ============================================================ */

  const adicionarComentario = useCallback(async (artifactId: string) => {
    if (!novoComentario.trim()) return
    try {
      await fetch(`${API}/api/mission-control/artifacts/${artifactId}/comentar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ texto: novoComentario }),
      })
      setNovoComentario('')
      if (sessao) await carregarSessao(sessao.sessao_id)
    } catch (e) {
      console.error('Erro ao comentar:', e)
    }
  }, [novoComentario, token, sessao, carregarSessao])

  /* ============================================================
     Render: Tela Inicial (sem sessao)
     ============================================================ */

  if (!sessao) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg)' }}>
        <div className="text-center max-w-lg p-8 rounded-2xl" style={{ background: 'var(--sf-surface)', border: '1px solid var(--sf-border-subtle)' }}>
          <div className="flex items-center justify-center gap-3 mb-6">
            <Rocket className="w-10 h-10" style={{ color: 'var(--sf-accent)' }} />
            <h1 className="text-3xl font-bold" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
          </div>
          <p className="mb-6" style={{ color: 'var(--sf-text-secondary)' }}>
            Code Studio 2.0 — Editor + Terminal + Navegador em painel triplo.<br />
            Agentes geram artifacts tangíveis em tempo real.
          </p>
          <input
            type="text"
            placeholder="Nome da sessão (ex: Feature Login SSO)"
            value={titulo}
            onChange={e => setTitulo(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && criarSessao()}
            className="w-full px-4 py-3 rounded-lg mb-4 text-sm"
            style={{ background: 'var(--sf-bg)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }}
          />
          <button
            onClick={criarSessao}
            disabled={criando}
            className="px-6 py-3 rounded-lg font-semibold text-white flex items-center gap-2 mx-auto transition-transform hover:scale-105"
            style={{ background: 'var(--sf-accent)' }}
          >
            {criando ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />}
            Iniciar Mission Control
          </button>
        </div>
      </div>
    )
  }

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
        <Rocket className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
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

        {/* Metricas */}
        <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
          <span className="flex items-center gap-1"><Package className="w-3.5 h-3.5" /> {artifacts.length} artifacts</span>
          <span className="flex items-center gap-1"><Terminal className="w-3.5 h-3.5" /> {sessao.total_comandos} cmds</span>
          <span className="flex items-center gap-1"><Bot className="w-3.5 h-3.5" /> {agentes.length} agentes</span>
        </div>
      </header>

      {/* === Instrução do Agente (barra superior) === */}
      <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0"
        style={{ background: 'var(--sf-surface)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <Sparkles className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
        <input
          type="text"
          placeholder="Instruir agente: 'Crie um componente de login com validação e testes'"
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
            <div className="flex-1 overflow-auto p-3 font-mono text-sm"
              style={{ background: '#1e1e2e', color: '#cdd6f4' }}>
              <pre className="whitespace-pre-wrap">{editorConteudo}</pre>
            </div>
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
              {/* Lista de Artifacts */}
              {artifacts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3"
                  style={{ color: 'var(--sf-text-secondary)' }}>
                  <Package className="w-12 h-12 opacity-30" />
                  <p className="text-sm">Nenhum artifact ainda.</p>
                  <p className="text-xs opacity-60">Instrua um agente para gerar planos, checklists e código.</p>
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

                      {/* Header do artifact */}
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

                      {/* Conteudo expandido */}
                      {art === artifactSelecionado && (
                        <div className="mt-2">
                          <pre className="text-xs p-3 rounded overflow-auto max-h-60 font-mono whitespace-pre-wrap"
                            style={{ background: 'var(--sf-bg)', color: 'var(--sf-text)' }}>
                            {art.conteudo || JSON.stringify(art.dados, null, 2)}
                          </pre>

                          {/* Comentarios inline */}
                          {(art.comentarios_inline || []).length > 0 && (
                            <div className="mt-3 space-y-2">
                              <span className="text-[10px] font-medium flex items-center gap-1" style={{ color: 'var(--sf-text-secondary)' }}>
                                <MessageSquare className="w-3 h-3" /> Comentários
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

                          {/* Adicionar comentario */}
                          <div className="flex items-center gap-2 mt-3">
                            <input
                              type="text"
                              placeholder="Adicionar comentário..."
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
