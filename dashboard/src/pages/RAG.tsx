/* RAG — Base de Conhecimento premium dark-mode (zero emojis) */

import { useState, useEffect, useCallback } from 'react'
import { buscarRAGStats, consultarRAG, indexarRAG } from '../services/api'
import type { RAGStats, RAGConsultaResult } from '../types'
import {
  Database, Layers, Cpu, Ruler, FolderOpen, RefreshCw,
  Loader2, Search, Sparkles, ChevronDown, ChevronUp,
  FileText, BookOpen, XCircle, CheckCircle2, Send,
} from 'lucide-react'

export default function RAG() {
  const [stats, setStats] = useState<RAGStats | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [pergunta, setPergunta] = useState('')
  const [vaultFiltro, setVaultFiltro] = useState('')
  const [resultado, setResultado] = useState<RAGConsultaResult | null>(null)
  const [consultando, setConsultando] = useState(false)
  const [indexando, setIndexando] = useState(false)
  const [mensagemIndex, setMensagemIndex] = useState('')
  const [chunksAberto, setChunksAberto] = useState(false)

  const carregarStats = useCallback(async () => {
    try { setStats(await buscarRAGStats()); setErro('') }
    catch { setErro('Erro ao carregar estatísticas.') }
    finally { setCarregando(false) }
  }, [])

  useEffect(() => { carregarStats() }, [carregarStats])

  const consultar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pergunta.trim()) return
    setConsultando(true); setResultado(null); setChunksAberto(false)
    try { setResultado(await consultarRAG(pergunta, vaultFiltro || undefined)) }
    catch (e) { setErro(e instanceof Error ? e.message : 'Erro.') }
    finally { setConsultando(false) }
  }

  const reindexar = async (vault?: string) => {
    setIndexando(true); setMensagemIndex('')
    try {
      const res = await indexarRAG(vault)
      setMensagemIndex(`${res.total_chunks} chunks em ${res.vaults_indexados.join(', ')}`)
      carregarStats()
    } catch (e) { setMensagemIndex(e instanceof Error ? e.message : 'Erro.') }
    finally { setIndexando(false) }
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  const kpis = stats ? [
    { label: 'Total Chunks', value: stats.total_chunks.toLocaleString(), icon: Layers, cor: '#10b981' },
    { label: 'Vaults Indexados', value: stats.vaults_indexados.length, icon: Database, cor: '#3b82f6' },
    { label: 'Modelo', value: stats.embedding_model.split('-').slice(-2).join('-'), icon: Cpu, cor: '#8b5cf6' },
    { label: 'Chunk Size', value: stats.chunk_size, icon: Ruler, cor: '#f59e0b' },
  ] : []

  return (
    <div className="sf-page">
      <div className="fixed top-0 left-1/3 w-[600px] h-[300px] bg-blue-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
          Base de Conhecimento
        </h2>
        <p className="text-sm sf-text-dim mt-1">
          Consulte a documentação dos projetos com respostas inteligentes da IA
        </p>
      </div>

      {/* Erro */}
      {erro && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-2">
          <XCircle size={14} className="text-red-400" />
          <span className="text-sm text-red-300">{erro}</span>
        </div>
      )}

      {/* KPI Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {kpis.map(kpi => {
            const Icon = kpi.icon
            return (
              <div key={kpi.label}
                className="group sf-glass backdrop-blur-sm border sf-border rounded-2xl p-5 transition-all duration-500 hover:border-white/15 hover:-translate-y-0.5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${kpi.cor}15` }}>
                    <Icon size={14} style={{ color: kpi.cor }} strokeWidth={2} />
                  </div>
                  <p className="text-[10px] sf-text-dim uppercase tracking-wider">{kpi.label}</p>
                </div>
                <p className="text-2xl font-bold sf-text-white font-mono">{kpi.value}</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Vaults + Reindexação */}
      {stats && (
        <div className="sf-glass border sf-border rounded-2xl p-6 mb-8">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <FolderOpen size={16} className="sf-text-dim" strokeWidth={1.8} />
              <h3 className="text-sm font-semibold sf-text-dim">Vaults</h3>
            </div>
            <button
              onClick={() => reindexar()}
              disabled={indexando}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-xs font-medium hover:bg-emerald-500/30 disabled:opacity-50 transition-all"
            >
              <RefreshCw size={12} className={indexando ? 'animate-spin' : ''} />
              {indexando ? 'Reindexando...' : 'Reindexar Todos'}
            </button>
          </div>

          {mensagemIndex && (
            <div className={`mb-4 px-4 py-3 rounded-xl text-sm flex items-center gap-2 ${
              mensagemIndex.includes('Erro')
                ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            }`}>
              {mensagemIndex.includes('Erro') ? <XCircle size={14} /> : <CheckCircle2 size={14} />}
              {mensagemIndex}
            </div>
          )}

          <div className="space-y-2">
            {stats.vaults_indexados.map(vault => (
              <div key={vault}
                className="flex items-center justify-between p-4 sf-glass border rounded-xl hover:border-white/10 transition-all" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                    <Database size={15} className="text-blue-400" strokeWidth={1.8} />
                  </div>
                  <div>
                    <p className="font-medium text-sm sf-text-white">{vault}</p>
                    <p className="text-xs sf-text-dim font-mono">
                      {(stats.por_vault[vault] || 0).toLocaleString()} chunks
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => reindexar(vault)}
                  disabled={indexando}
                  className="flex items-center gap-1.5 px-3 py-1.5 sf-glass border sf-border sf-text-dim rounded-lg text-xs disabled:opacity-50 transition-all"
                >
                  <RefreshCw size={11} />
                  Reindexar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consulta com IA */}
      <div className="sf-glass border sf-border rounded-2xl p-6 mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={16} className="text-emerald-400" strokeWidth={1.8} />
          <h3 className="text-sm font-semibold sf-text-dim">Consultar com IA</h3>
        </div>
        <form onSubmit={consultar} className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 sf-text-ghost" />
            <input
              value={pergunta}
              onChange={e => setPergunta(e.target.value)}
              placeholder="Faça uma pergunta sobre os projetos..."
              className="w-full sf-glass border sf-border rounded-xl pl-10 pr-4 py-3 text-sm sf-text-white placeholder:sf-text-ghost focus:outline-none focus:border-emerald-500/50 transition-colors"
            />
          </div>
          <select
            value={vaultFiltro}
            onChange={e => setVaultFiltro(e.target.value)}
            className="sf-glass border sf-border rounded-xl px-4 py-3 text-sm sf-text-dim focus:outline-none focus:border-emerald-500/50 appearance-none cursor-pointer"
          >
            <option value="">Todos</option>
            {stats?.vaults_indexados.map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={consultando || !pergunta.trim()}
            className="flex items-center gap-2 px-6 py-3 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-xl text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-40 transition-all whitespace-nowrap"
          >
            {consultando ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {consultando ? 'Consultando...' : 'Consultar'}
          </button>
        </form>
      </div>

      {/* Loading consulta */}
      {consultando && (
        <div className="sf-glass border rounded-2xl p-6 mb-6 text-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 border-2 border-emerald-500/20 rounded-full" />
            <div className="absolute inset-0 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <BookOpen size={16} className="text-emerald-400" strokeWidth={1.5} />
            </div>
          </div>
          <p className="text-sm sf-text-dim">Analisando a base de conhecimento...</p>
        </div>
      )}

      {/* Resultado */}
      {resultado && !consultando && (
        <div className="space-y-4">
          {/* Resposta IA */}
          <div className="bg-gradient-to-br from-emerald-500/[0.05] to-white/[0.01] border border-emerald-500/20 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                <Sparkles size={14} className="text-emerald-400" strokeWidth={2} />
              </div>
              <h3 className="text-sm font-semibold sf-text-white">Resposta da IA</h3>
              <span className="text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
                {resultado.total_chunks} fonte(s)
              </span>
            </div>
            <div className="text-sm sf-text-dim leading-relaxed whitespace-pre-wrap">
              {resultado.resposta_ia}
            </div>
          </div>

          {/* Chunks colapsável */}
          {resultado.chunks.length > 0 && (
            <div className="sf-glass border sf-border rounded-2xl overflow-hidden">
              <button
                onClick={() => setChunksAberto(!chunksAberto)}
                className="w-full flex items-center justify-between px-6 py-4 text-sm font-medium sf-text-dim hover:text-gray-300 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <FileText size={14} strokeWidth={1.8} />
                  Fontes consultadas ({resultado.chunks.length} trechos)
                </span>
                {chunksAberto ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {chunksAberto && (
                <div className="border-t" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                  {resultado.chunks.map((chunk, i) => (
                    <div key={i} className="px-6 py-4 border-b border-white/[0.03] last:border-b-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[10px] font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-md">
                          {chunk.vault}
                        </span>
                        <span className="text-xs sf-text-dim font-mono">{chunk.arquivo}</span>
                        <span className="text-xs sf-text-ghost">— {chunk.secao}</span>
                      </div>
                      <p className="text-xs sf-text-dim leading-relaxed">{chunk.conteudo}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
