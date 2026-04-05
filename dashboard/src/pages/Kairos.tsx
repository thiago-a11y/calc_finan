/* Kairos — Painel de Memória Auto-Evolutiva (CEO Only)
 *
 * v0.60.4 — Visualização de snapshots, memórias consolidadas e controle do AutoDream.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Brain, Database, Sparkles, Play, RefreshCw, Loader2,
  CheckCircle, Clock, Search, AlertTriangle,
  Zap, Eye, Tag, BarChart3, Archive,
} from 'lucide-react'

// ─── Tipos ──────────────────────────────────────────────────────────

interface KairosStatus {
  ativo: boolean
  auto_dream_rodando: boolean
  lock_ativo: boolean
  snapshots_pendentes: number
  memorias_ativas: number
  config: {
    dream_interval_min: number
    max_snapshots_por_dream: number
    modelo_consolidacao: string
    habilitar_auto_dream: boolean
  }
  snapshots_por_source: Record<string, number>
  memorias_por_agente: Record<string, number>
}

interface Snapshot {
  id: string
  agente_id: string
  source: string
  conteudo: string
  contexto: Record<string, unknown>
  relevancia: number
  consolidado: boolean
  consolidado_em: string | null
  criado_em: string | null
}

interface Memory {
  id: string
  agente_id: string
  tipo: string
  titulo: string
  conteudo: string
  tags: string[]
  relevancia: number
  acessos: number
  ultimo_acesso: string | null
  fonte_snapshots: string[]
  criado_em: string | null
  atualizado_em: string | null
}

interface DreamResult {
  dream_id: string
  status: string
  snapshots_processados: number
  memorias_criadas: number
  memorias_atualizadas: number
  duracao_ms: number
  erro: string | null
}

// ─── Helpers ────────────────────────────────────────────────────────

const API = import.meta.env.VITE_API_URL || ''

function getToken(): string {
  try { return localStorage.getItem('sf_token') || '' }
  catch { return '' }
}

function headers() {
  return {
    Authorization: `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

function formatRelevancia(r: number): string {
  return `${Math.round(r * 100)}%`
}

const TIPO_COLORS: Record<string, string> = {
  episodica: '#60a5fa',
  semantica: '#34d399',
  procedural: '#fbbf24',
  estrategica: '#f472b6',
}

const TIPO_LABELS: Record<string, string> = {
  episodica: 'Episodica',
  semantica: 'Semantica',
  procedural: 'Procedural',
  estrategica: 'Estrategica',
}

const SOURCE_COLORS: Record<string, string> = {
  luna: '#a78bfa',
  mission_control: '#60a5fa',
  reuniao: '#fbbf24',
  workflow: '#34d399',
  agente: '#f472b6',
  manual: '#6b7280',
}

// ─── Componentes internos ───────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color }: {
  icon: typeof Brain
  label: string
  value: string | number
  color: string
}) {
  return (
    <div
      className="rounded-2xl p-4 flex items-center gap-3"
      style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-subtle)' }}
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: color + '15' }}
      >
        <Icon size={18} color={color} />
      </div>
      <div>
        <div className="text-[11px] font-medium" style={{ color: 'var(--sf-text-3)' }}>{label}</div>
        <div className="text-lg font-bold" style={{ color: 'var(--sf-text-1)' }}>{value}</div>
      </div>
    </div>
  )
}

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span
      className="px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ background: color + '18', color, border: `1px solid ${color}30` }}
    >
      {text}
    </span>
  )
}

// ─── Tabs ───────────────────────────────────────────────────────────

type Tab = 'status' | 'snapshots' | 'memories' | 'dream'

const TABS: { id: Tab; label: string; Icon: typeof Brain }[] = [
  { id: 'status', label: 'Status', Icon: BarChart3 },
  { id: 'snapshots', label: 'Snapshots', Icon: Archive },
  { id: 'memories', label: 'Memorias', Icon: Brain },
  { id: 'dream', label: 'Dream', Icon: Sparkles },
]

// ─── Pagina principal ───────────────────────────────────────────────

export default function Kairos() {
  useAuth()
  const [tab, setTab] = useState<Tab>('status')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // Status
  const [status, setStatus] = useState<KairosStatus | null>(null)

  // Snapshots
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [snapshotsTotal, setSnapshotsTotal] = useState(0)
  const [snapFilter, setSnapFilter] = useState({ source: '', consolidado: '' })

  // Memories
  const [memories, setMemories] = useState<Memory[]>([])
  const [memoriesTotal, setMemoriesTotal] = useState(0)
  const [memSearch, setMemSearch] = useState('')
  const [memTipo, setMemTipo] = useState('')

  // Dream
  const [dreamResult, setDreamResult] = useState<DreamResult | null>(null)
  const [dreaming, setDreaming] = useState(false)

  // ─── Fetchers ───────────────────────────────────────────────────

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/kairos/status`, { headers: headers() })
      if (res.ok) setStatus(await res.json())
    } catch { /* silenciar */ }
  }, [])

  const fetchSnapshots = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limite: '100' })
      if (snapFilter.source) params.set('source', snapFilter.source)
      if (snapFilter.consolidado) params.set('consolidado', snapFilter.consolidado)
      const res = await fetch(`${API}/api/kairos/snapshots?${params}`, { headers: headers() })
      if (res.ok) {
        const data = await res.json()
        setSnapshots(data.snapshots)
        setSnapshotsTotal(data.total)
      }
    } catch { /* silenciar */ }
  }, [snapFilter])

  const fetchMemories = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limite: '100' })
      if (memSearch) params.set('q', memSearch)
      if (memTipo) params.set('tipo', memTipo)
      const res = await fetch(`${API}/api/kairos/memories?${params}`, { headers: headers() })
      if (res.ok) {
        const data = await res.json()
        setMemories(data.memories)
        setMemoriesTotal(data.total)
      }
    } catch { /* silenciar */ }
  }, [memSearch, memTipo])

  const triggerDream = async () => {
    setDreaming(true)
    setDreamResult(null)
    try {
      const res = await fetch(`${API}/api/kairos/dream/manual`, {
        method: 'POST', headers: headers(),
      })
      if (res.ok) {
        const data = await res.json()
        setDreamResult(data)
        fetchStatus()
        fetchSnapshots()
        fetchMemories()
      }
    } catch {
      setDreamResult({ dream_id: '', status: 'falhou', snapshots_processados: 0, memorias_criadas: 0, memorias_atualizadas: 0, duracao_ms: 0, erro: 'Erro de conexao' })
    } finally {
      setDreaming(false)
    }
  }

  // ─── Effects ────────────────────────────────────────────────────

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchStatus(), fetchSnapshots(), fetchMemories()])
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchSnapshots() }, [snapFilter])
  useEffect(() => { fetchMemories() }, [memSearch, memTipo])

  // ─── Render ─────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 gap-2" style={{ color: 'var(--sf-text-3)' }}>
        <Loader2 size={20} className="animate-spin" />
        Carregando Kairos...
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(168,85,247,0.12)' }}
          >
            <Brain size={20} color="#a855f7" />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: 'var(--sf-text-1)' }}>Kairos</h1>
            <p className="text-xs" style={{ color: 'var(--sf-text-3)' }}>Memoria Auto-Evolutiva</p>
          </div>
        </div>
        <button
          onClick={async () => {
            setRefreshing(true)
            await Promise.all([fetchStatus(), fetchSnapshots(), fetchMemories()])
            setRefreshing(false)
          }}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
          style={{
            background: 'var(--sf-bg-2)',
            color: refreshing ? 'var(--sf-text-3)' : 'var(--sf-text-2)',
            border: '1px solid var(--sf-border-subtle)',
            cursor: refreshing ? 'not-allowed' : 'pointer',
          }}
        >
          {refreshing
            ? <Loader2 size={13} className="animate-spin" />
            : <RefreshCw size={13} />
          }
          {refreshing ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {/* Stat Cards */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            icon={status.ativo ? CheckCircle : AlertTriangle}
            label="Status"
            value={status.ativo ? 'Ativo' : 'Inativo'}
            color={status.ativo ? '#10b981' : '#ef4444'}
          />
          <StatCard
            icon={Database}
            label="Snapshots Pendentes"
            value={status.snapshots_pendentes}
            color="#60a5fa"
          />
          <StatCard
            icon={Brain}
            label="Memorias Consolidadas"
            value={status.memorias_ativas}
            color="#a855f7"
          />
          <StatCard
            icon={status.auto_dream_rodando ? Sparkles : Clock}
            label="AutoDream"
            value={status.auto_dream_rodando ? `A cada ${status.config.dream_interval_min}min` : 'Parado'}
            color={status.auto_dream_rodando ? '#34d399' : '#6b7280'}
          />
        </div>
      )}

      {/* Tabs */}
      <div
        className="flex gap-1 p-1 rounded-xl"
        style={{ background: 'var(--sf-bg-2)' }}
      >
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all"
            style={{
              background: tab === t.id ? 'var(--sf-bg-3, rgba(255,255,255,0.08))' : 'transparent',
              color: tab === t.id ? 'var(--sf-text-1)' : 'var(--sf-text-3)',
            }}
          >
            <t.Icon size={14} />
            {t.label}
            {t.id === 'snapshots' && <span className="ml-1 opacity-50">({snapshotsTotal})</span>}
            {t.id === 'memories' && <span className="ml-1 opacity-50">({memoriesTotal})</span>}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div
        className="rounded-2xl p-5"
        style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-subtle)' }}
      >
        {/* ── Status Tab ──────────────────────────────────────────── */}
        {tab === 'status' && status && (
          <div className="space-y-5">
            <h3 className="text-sm font-semibold" style={{ color: 'var(--sf-text-1)' }}>
              Distribuicao de Snapshots
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(status.snapshots_por_source).map(([source, count]) => (
                <div key={source} className="flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{ background: 'var(--sf-bg-1)' }}
                >
                  <div className="w-2 h-2 rounded-full" style={{ background: SOURCE_COLORS[source] || '#6b7280' }} />
                  <span className="text-xs" style={{ color: 'var(--sf-text-2)' }}>{source}</span>
                  <span className="ml-auto text-xs font-bold" style={{ color: 'var(--sf-text-1)' }}>{count}</span>
                </div>
              ))}
            </div>

            <h3 className="text-sm font-semibold mt-4" style={{ color: 'var(--sf-text-1)' }}>
              Memorias por Agente
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(status.memorias_por_agente).map(([agente, count]) => (
                <div key={agente} className="flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{ background: 'var(--sf-bg-1)' }}
                >
                  <Brain size={12} color="#a855f7" />
                  <span className="text-xs truncate" style={{ color: 'var(--sf-text-2)' }}>{agente}</span>
                  <span className="ml-auto text-xs font-bold" style={{ color: 'var(--sf-text-1)' }}>{count}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 p-3 rounded-lg text-xs" style={{ background: 'var(--sf-bg-1)', color: 'var(--sf-text-3)' }}>
              <div className="flex items-center gap-1.5 font-medium mb-1" style={{ color: 'var(--sf-text-2)' }}>
                <Zap size={12} /> Configuracao
              </div>
              Modelo: <strong>{status.config.modelo_consolidacao}</strong> | Max snapshots/dream: <strong>{status.config.max_snapshots_por_dream}</strong> | Lock: <strong>{status.lock_ativo ? 'Ativo' : 'Livre'}</strong>
            </div>
          </div>
        )}

        {/* ── Snapshots Tab ───────────────────────────────────────── */}
        {tab === 'snapshots' && (
          <div className="space-y-4">
            {/* Filtros */}
            <div className="flex flex-wrap gap-2">
              <select
                value={snapFilter.source}
                onChange={e => setSnapFilter(f => ({ ...f, source: e.target.value }))}
                className="px-3 py-1.5 rounded-lg text-xs"
                style={{ background: 'var(--sf-bg-1)', color: 'var(--sf-text-2)', border: '1px solid var(--sf-border-subtle)' }}
              >
                <option value="">Todas as fontes</option>
                <option value="luna">Luna</option>
                <option value="mission_control">Mission Control</option>
                <option value="reuniao">Reuniao</option>
                <option value="workflow">Workflow</option>
              </select>
              <select
                value={snapFilter.consolidado}
                onChange={e => setSnapFilter(f => ({ ...f, consolidado: e.target.value }))}
                className="px-3 py-1.5 rounded-lg text-xs"
                style={{ background: 'var(--sf-bg-1)', color: 'var(--sf-text-2)', border: '1px solid var(--sf-border-subtle)' }}
              >
                <option value="">Todos</option>
                <option value="true">Consolidados</option>
                <option value="false">Pendentes</option>
              </select>
            </div>

            {/* Tabela */}
            {snapshots.length === 0 ? (
              <div className="text-center py-8 text-xs" style={{ color: 'var(--sf-text-3)' }}>
                Nenhum snapshot encontrado
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs" style={{ color: 'var(--sf-text-2)' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
                      <th className="text-left py-2 px-2 font-medium" style={{ color: 'var(--sf-text-3)' }}>Agente</th>
                      <th className="text-left py-2 px-2 font-medium" style={{ color: 'var(--sf-text-3)' }}>Fonte</th>
                      <th className="text-left py-2 px-2 font-medium" style={{ color: 'var(--sf-text-3)' }}>Conteudo</th>
                      <th className="text-center py-2 px-2 font-medium" style={{ color: 'var(--sf-text-3)' }}>Status</th>
                      <th className="text-right py-2 px-2 font-medium" style={{ color: 'var(--sf-text-3)' }}>Data</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshots.map(s => (
                      <tr key={s.id} style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
                        <td className="py-2 px-2 font-medium">{s.agente_id}</td>
                        <td className="py-2 px-2">
                          <Badge text={s.source} color={SOURCE_COLORS[s.source] || '#6b7280'} />
                        </td>
                        <td className="py-2 px-2 max-w-xs truncate" title={s.conteudo}>{s.conteudo.slice(0, 80)}...</td>
                        <td className="py-2 px-2 text-center">
                          {s.consolidado
                            ? <CheckCircle size={14} color="#10b981" />
                            : <Clock size={14} color="#fbbf24" />
                          }
                        </td>
                        <td className="py-2 px-2 text-right" style={{ color: 'var(--sf-text-3)' }}>{formatDate(s.criado_em)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── Memories Tab ────────────────────────────────────────── */}
        {tab === 'memories' && (
          <div className="space-y-4">
            {/* Filtros */}
            <div className="flex flex-wrap gap-2">
              <div className="relative flex-1 min-w-[200px]">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--sf-text-3)' }} />
                <input
                  type="text"
                  placeholder="Buscar nas memorias..."
                  value={memSearch}
                  onChange={e => setMemSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs"
                  style={{ background: 'var(--sf-bg-1)', color: 'var(--sf-text-2)', border: '1px solid var(--sf-border-subtle)' }}
                />
              </div>
              <select
                value={memTipo}
                onChange={e => setMemTipo(e.target.value)}
                className="px-3 py-1.5 rounded-lg text-xs"
                style={{ background: 'var(--sf-bg-1)', color: 'var(--sf-text-2)', border: '1px solid var(--sf-border-subtle)' }}
              >
                <option value="">Todos os tipos</option>
                <option value="episodica">Episodica</option>
                <option value="semantica">Semantica</option>
                <option value="procedural">Procedural</option>
                <option value="estrategica">Estrategica</option>
              </select>
            </div>

            {/* Cards de memórias */}
            {memories.length === 0 ? (
              <div className="text-center py-8 text-xs" style={{ color: 'var(--sf-text-3)' }}>
                Nenhuma memoria encontrada
              </div>
            ) : (
              <div className="space-y-3">
                {memories.map(m => (
                  <div
                    key={m.id}
                    className="rounded-xl p-4 space-y-2"
                    style={{ background: 'var(--sf-bg-1)', border: `1px solid ${(TIPO_COLORS[m.tipo] || '#6b7280')}25` }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge text={TIPO_LABELS[m.tipo] || m.tipo} color={TIPO_COLORS[m.tipo] || '#6b7280'} />
                        <span className="text-sm font-semibold" style={{ color: 'var(--sf-text-1)' }}>{m.titulo}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold"
                          style={{
                            background: m.relevancia >= 0.8 ? '#f472b618' : m.relevancia >= 0.5 ? '#fbbf2418' : '#6b728018',
                            color: m.relevancia >= 0.8 ? '#f472b6' : m.relevancia >= 0.5 ? '#fbbf24' : '#6b7280',
                          }}
                        >
                          {formatRelevancia(m.relevancia)}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--sf-text-2)' }}>{m.conteudo}</p>
                    <div className="flex items-center gap-3 pt-1" style={{ color: 'var(--sf-text-3)' }}>
                      <span className="text-[10px] flex items-center gap-1"><Brain size={10} /> {m.agente_id}</span>
                      {m.tags.length > 0 && (
                        <span className="text-[10px] flex items-center gap-1">
                          <Tag size={10} /> {m.tags.slice(0, 4).join(', ')}{m.tags.length > 4 ? '...' : ''}
                        </span>
                      )}
                      <span className="text-[10px] flex items-center gap-1"><Eye size={10} /> {m.acessos}x</span>
                      <span className="text-[10px] ml-auto">{formatDate(m.criado_em)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Dream Tab ───────────────────────────────────────────── */}
        {tab === 'dream' && (
          <div className="space-y-5">
            <div className="text-center space-y-3 py-4">
              <Sparkles size={32} color="#a855f7" className="mx-auto" />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--sf-text-1)' }}>
                Dream Manual
              </h3>
              <p className="text-xs max-w-md mx-auto" style={{ color: 'var(--sf-text-3)' }}>
                Dispara um ciclo de consolidacao imediato. O AutoDream processa todos os
                snapshots pendentes e gera memorias consolidadas via LLM.
              </p>
              <button
                onClick={triggerDream}
                disabled={dreaming}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: dreaming ? 'rgba(168,85,247,0.3)' : 'rgba(168,85,247,0.15)',
                  color: '#a855f7',
                  border: '1px solid rgba(168,85,247,0.3)',
                  cursor: dreaming ? 'not-allowed' : 'pointer',
                }}
              >
                {dreaming ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                {dreaming ? 'Processando...' : 'Disparar Dream'}
              </button>
            </div>

            {/* Resultado do dream */}
            {dreamResult && (
              <div
                className="rounded-xl p-4 space-y-2"
                style={{
                  background: dreamResult.status === 'concluido' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                  border: `1px solid ${dreamResult.status === 'concluido' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                }}
              >
                <div className="flex items-center gap-2">
                  {dreamResult.status === 'concluido'
                    ? <CheckCircle size={16} color="#10b981" />
                    : <AlertTriangle size={16} color="#ef4444" />
                  }
                  <span className="text-sm font-semibold" style={{ color: 'var(--sf-text-1)' }}>
                    {dreamResult.status === 'concluido' ? 'Dream concluido' : 'Dream falhou'}
                  </span>
                  <span className="text-[10px] ml-auto" style={{ color: 'var(--sf-text-3)' }}>
                    {dreamResult.dream_id} ({dreamResult.duracao_ms}ms)
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center pt-2">
                  <div>
                    <div className="text-lg font-bold" style={{ color: 'var(--sf-text-1)' }}>{dreamResult.snapshots_processados}</div>
                    <div className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Snapshots</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold" style={{ color: '#10b981' }}>{dreamResult.memorias_criadas}</div>
                    <div className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Criadas</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold" style={{ color: '#60a5fa' }}>{dreamResult.memorias_atualizadas}</div>
                    <div className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Atualizadas</div>
                  </div>
                </div>
                {dreamResult.erro && (
                  <div className="text-xs mt-2 p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>
                    {dreamResult.erro}
                  </div>
                )}
              </div>
            )}

            {/* Info sobre agendamento */}
            {status && (
              <div className="text-[11px] text-center" style={{ color: 'var(--sf-text-3)' }}>
                AutoDream: {status.auto_dream_rodando ? `ativo (a cada ${status.config.dream_interval_min}min)` : 'parado'} | Modelo: {status.config.modelo_consolidacao}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
