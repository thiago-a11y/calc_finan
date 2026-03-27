/* Deploy — Pipeline com barra de progresso em tempo real */

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Rocket, CheckCircle2, XCircle,  Loader2,
  GitBranch, Terminal, Package, TestTube, Upload,
  GitMerge, AlertTriangle, ExternalLink, History,
  ArrowRight,
} from 'lucide-react'

interface Etapa {
  nome: string
  percentual: number
  status: 'executando' | 'ok' | 'erro'
  detalhes?: string
  inicio?: string
  fim?: string
}

interface DeployData {
  id: string
  descricao: string
  usuario: string
  status: 'executando' | 'concluido' | 'erro'
  percentual: number
  etapa_atual: string
  etapas: Etapa[]
  erro: string | null
  pr_url: string | null
  branch: string | null
  iniciado_em: string
  concluido_em: string | null
}

const etapaIcones: Record<string, typeof Rocket> = {
  'Verificando repositório': GitBranch,
  'Staging de arquivos': Terminal,
  'Commitando mudanças': GitBranch,
  'Build do frontend': Package,
  'Executando testes': TestTube,
  'Criando branch': GitBranch,
  'Push + Pull Request': Upload,
  'Merge para produção': GitMerge,
  'Em produção!': Rocket,
}

export default function Deploy() {
  const { token } = useAuth()
  const [descricao, setDescricao] = useState('')
  const [deployAtivo, setDeployAtivo] = useState<string | null>(null)
  const [progresso, setProgresso] = useState<DeployData | null>(null)
  const [historico, setHistorico] = useState<DeployData[]>([])
  const [iniciando, setIniciando] = useState(false)
  const intervalRef = useRef<number | null>(null)

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  // Polling de progresso
  useEffect(() => {
    if (!deployAtivo) return

    const poll = async () => {
      try {
        const r = await fetch(`/api/deploy/progresso/${deployAtivo}`, { headers })
        if (r.ok) {
          const data = await r.json()
          setProgresso(data)
          if (data.status !== 'executando') {
            if (intervalRef.current) clearInterval(intervalRef.current)
            carregarHistorico()
          }
        }
      } catch {}
    }

    poll()
    intervalRef.current = window.setInterval(poll, 1500)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [deployAtivo])

  // Carregar histórico
  const carregarHistorico = async () => {
    try {
      const r = await fetch('/api/deploy/historico', { headers })
      if (r.ok) setHistorico(await r.json())
    } catch {}
  }

  useEffect(() => { carregarHistorico() }, [])

  // Iniciar deploy
  const iniciarDeploy = async () => {
    if (!descricao.trim()) return
    setIniciando(true)
    try {
      const r = await fetch('/api/deploy/executar', {
        method: 'POST', headers,
        body: JSON.stringify({ descricao: descricao.trim() }),
      })
      const data = await r.json()
      if (r.ok) {
        setDeployAtivo(data.deploy_id)
        setDescricao('')
      } else {
        alert(data.detail || 'Erro ao iniciar deploy')
      }
    } catch { alert('Erro de conexão') }
    finally { setIniciando(false) }
  }

  const corStatus = (s: string) =>
    s === 'ok' || s === 'concluido' ? '#10b981' :
    s === 'erro' ? '#ef4444' :
    '#f59e0b'

  return (
    <div className="sf-page">
      <div className="fixed top-0 left-1/3 w-[600px] h-[300px] bg-blue-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold sf-text-white" style={{ letterSpacing: '-0.02em' }}>
          Deploy para Produção
        </h2>
        <p className="text-sm sf-text-dim mt-1">
          Pipeline completo: commit → build → testes → PR → merge → produção
        </p>
      </div>

      {/* ==================== FORMULÁRIO DE DEPLOY ==================== */}
      {!deployAtivo && (
        <div className="sf-glass border sf-border rounded-2xl p-6 mb-8">
          <h3 className="text-sm font-semibold sf-text-white mb-4 flex items-center gap-2">
            <Rocket size={14} className="text-blue-400" />
            Novo Deploy
          </h3>
          <div className="flex gap-3">
            <input
              value={descricao}
              onChange={e => setDescricao(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && iniciarDeploy()}
              placeholder="Descreva o que será deployado (ex: Feature deletar planos individualmente)"
              className="flex-1 px-4 py-3 rounded-xl text-sm sf-text-white focus:outline-none transition-all"
              style={{
                background: 'var(--sf-bg-input, rgba(255,255,255,0.04))',
                border: '1px solid var(--sf-border-default)',
              }}
            />
            <button
              onClick={iniciarDeploy}
              disabled={iniciando || !descricao.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-blue-500/20 text-blue-400 border border-blue-500/25 rounded-xl text-sm font-medium hover:bg-blue-500/30 disabled:opacity-40 transition-all"
            >
              {iniciando ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
              Iniciar Deploy
            </button>
          </div>
        </div>
      )}

      {/* ==================== PROGRESSO EM TEMPO REAL ==================== */}
      {progresso && (
        <div className="sf-glass border sf-border rounded-2xl p-6 mb-8 overflow-hidden relative">
          {/* Glow de fundo baseado no status */}
          <div className="absolute inset-0 pointer-events-none" style={{
            background: progresso.status === 'concluido'
              ? 'radial-gradient(ellipse at top, rgba(16,185,129,0.06) 0%, transparent 60%)'
              : progresso.status === 'erro'
              ? 'radial-gradient(ellipse at top, rgba(239,68,68,0.06) 0%, transparent 60%)'
              : 'radial-gradient(ellipse at top, rgba(59,130,246,0.06) 0%, transparent 60%)',
          }} />

          <div className="relative">
            {/* Cabeçalho */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold sf-text-white flex items-center gap-2">
                  {progresso.status === 'executando' && <Loader2 size={16} className="text-blue-400 animate-spin" />}
                  {progresso.status === 'concluido' && <CheckCircle2 size={16} className="text-emerald-400" />}
                  {progresso.status === 'erro' && <XCircle size={16} className="text-red-400" />}
                  {progresso.descricao}
                </h3>
                <p className="text-xs sf-text-dim mt-1">
                  Deploy #{progresso.id} · Por {progresso.usuario} · {new Date(progresso.iniciado_em).toLocaleString('pt-BR')}
                </p>
              </div>
              <div className="text-right">
                <p className="text-4xl font-bold font-mono" style={{ color: corStatus(progresso.status) }}>
                  {progresso.percentual}%
                </p>
                <p className="text-[10px] sf-text-dim uppercase tracking-wider">{progresso.etapa_atual}</p>
              </div>
            </div>

            {/* Barra de progresso principal */}
            <div className="w-full h-3 rounded-full mb-8 overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <div
                className="h-full rounded-full transition-all duration-700 ease-out relative"
                style={{
                  width: `${progresso.percentual}%`,
                  background: progresso.status === 'erro'
                    ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                    : progresso.status === 'concluido'
                    ? 'linear-gradient(90deg, #10b981, #059669)'
                    : 'linear-gradient(90deg, #3b82f6, #2563eb)',
                }}
              >
                {progresso.status === 'executando' && (
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
                )}
              </div>
            </div>

            {/* Etapas */}
            <div className="space-y-2">
              {progresso.etapas.map((etapa, idx) => {
                const Icon = etapaIcones[etapa.nome] || Terminal
                const isAtual = etapa.status === 'executando'

                return (
                  <div
                    key={idx}
                    className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 ${
                      isAtual ? 'bg-blue-500/[0.06] border border-blue-500/20' : ''
                    }`}
                    style={!isAtual ? { background: 'transparent' } : undefined}
                  >
                    {/* Status ícone */}
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{
                      backgroundColor: etapa.status === 'ok' ? 'rgba(16,185,129,0.1)' :
                        etapa.status === 'erro' ? 'rgba(239,68,68,0.1)' :
                        'rgba(59,130,246,0.1)',
                    }}>
                      {etapa.status === 'executando' ? (
                        <Loader2 size={14} className="text-blue-400 animate-spin" />
                      ) : etapa.status === 'ok' ? (
                        <CheckCircle2 size={14} className="text-emerald-400" />
                      ) : (
                        <XCircle size={14} className="text-red-400" />
                      )}
                    </div>

                    {/* Nome + detalhes */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Icon size={12} className="sf-text-dim shrink-0" />
                        <p className={`text-sm font-medium truncate ${
                          isAtual ? 'text-blue-400' : etapa.status === 'ok' ? 'sf-text-dim' : 'text-red-400'
                        }`}>
                          {etapa.nome}
                        </p>
                      </div>
                      {etapa.detalhes && (
                        <p className="text-xs sf-text-ghost mt-0.5 truncate">{etapa.detalhes}</p>
                      )}
                    </div>

                    {/* Percentual */}
                    <span className="text-xs font-mono sf-text-ghost shrink-0">{etapa.percentual}%</span>
                  </div>
                )
              })}
            </div>

            {/* PR URL se existir */}
            {progresso.pr_url && (
              <div className="mt-6 flex items-center gap-2">
                <a
                  href={progresso.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 rounded-xl text-xs font-medium hover:bg-emerald-500/25 transition-all"
                >
                  <ExternalLink size={12} />
                  Ver Pull Request no GitHub
                </a>
              </div>
            )}

            {/* Erro */}
            {progresso.erro && (
              <div className="mt-4 flex items-start gap-2 px-4 py-3 bg-red-500/[0.06] border border-red-500/20 rounded-xl">
                <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
                <p className="text-xs text-red-400">{progresso.erro}</p>
              </div>
            )}

            {/* Botão voltar */}
            {progresso.status !== 'executando' && (
              <button
                onClick={() => { setDeployAtivo(null); setProgresso(null); carregarHistorico() }}
                className="mt-6 flex items-center gap-2 px-4 py-2 sf-glass border sf-border rounded-xl text-xs sf-text-dim hover:bg-white/5 transition-all"
              >
                <ArrowRight size={12} />
                Novo deploy
              </button>
            )}
          </div>
        </div>
      )}

      {/* ==================== HISTÓRICO ==================== */}
      {historico.length > 0 && !deployAtivo && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <History size={14} className="sf-text-dim" />
            <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">Histórico de Deploys</h3>
          </div>
          <div className="space-y-2">
            {historico.map(d => (
              <div
                key={d.id}
                className="sf-glass border sf-border rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-white/15 transition-all"
                onClick={() => { setDeployAtivo(d.id); setProgresso(d) }}
              >
                <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{
                  backgroundColor: d.status === 'concluido' ? 'rgba(16,185,129,0.1)' :
                    d.status === 'erro' ? 'rgba(239,68,68,0.1)' : 'rgba(59,130,246,0.1)',
                }}>
                  {d.status === 'concluido' ? <CheckCircle2 size={16} className="text-emerald-400" /> :
                   d.status === 'erro' ? <XCircle size={16} className="text-red-400" /> :
                   <Loader2 size={16} className="text-blue-400 animate-spin" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium sf-text-white truncate">{d.descricao}</p>
                  <p className="text-[10px] sf-text-ghost mt-0.5">
                    {new Date(d.iniciado_em).toLocaleString('pt-BR')} · {d.usuario} · {d.etapas.length} etapas
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-lg font-bold font-mono" style={{ color: corStatus(d.status) }}>
                    {d.percentual}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
