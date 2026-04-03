/* MissionCompleteActions — v0.57.7
 *
 * Painel de açoes recomendado quando missao atinge 100% concluido.
 * Inclui açoes de Git (Commit, Push, PR, Merge) funcionais.
 *
 * v0.57.7 — Git actions funcionais (Commit, Push, PR, Merge)
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Play, Code2, Bot, ShieldCheck, Users,
  FileText, Plus, Loader2, CheckCircle2, Sparkles,
  GitCommit, GitBranch,
  AlertCircle, Check, X,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

interface GitInfo {
  eh_git: boolean
  cwd: string
  projeto_nome: string | null
  projeto_id: number | null
  branch: string
  commits_pendentes: number
  ultimo_commit: string
  vcs_configurado: boolean
  vcs_tipo: string | null
  repo_url: string | null
  branch_padrao: string
}

interface Toast {
  tipo: 'success' | 'error' | 'info'
  mensagem: string
}

interface MissionCompleteActionsProps {
  token: string
  sessaoId: string
  projetoId?: number | null
  papel?: string // 'ceo' | 'diretor_tecnico' | 'operations_lead' | etc
  onTestar?: () => void
  onAplicarCodeStudio?: () => void
  onFactoryOptimizer?: () => void
  onAprovarOperations?: () => void
  onConvidarColaborador?: () => void
  onGerarRelatorioCEO?: () => void
  onNovaSessao?: () => void
  onVoltarRevisao?: () => void  // volta para tela de execucao completa
  sessaoTitulo?: string
  totalArtifacts?: number
  totalComandos?: number
}

type GitAction = 'commit' | 'push' | 'pr' | 'merge' | 'testar' | 'codeStudio' | 'optimizer' | 'aprovar' | 'convidar' | 'relatorio' | 'novaSessao' | 'voltarRevisao' | null

export default function MissionCompleteActions({
  token,
  sessaoId,
  papel = 'membro',
  onTestar,
  onAplicarCodeStudio,
  onFactoryOptimizer,
  onAprovarOperations,
  onConvidarColaborador,
  onGerarRelatorioCEO,
  onNovaSessao,
  onVoltarRevisao,
  sessaoTitulo = 'Missao',
  totalArtifacts = 0,
  totalComandos = 0,
}: MissionCompleteActionsProps) {
  const [loading, setLoading] = useState<GitAction>(null)
  const [toast, setToast] = useState<Toast | null>(null)
  const [gitInfo, setGitInfo] = useState<GitInfo | null>(null)

  // Papéis que podem fazer Git actions
  const podeGit = ['ceo', 'diretor_tecnico', 'operations_lead', 'pm_central', 'lider'].includes(papel)

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  // Carregar info do Git ao montar
  useEffect(() => {
    if (!podeGit || !sessaoId) return
    const fetchGitInfo = async () => {
      try {
        const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/git-info`, { headers })
        if (res.ok) setGitInfo(await res.json())
      } catch { /* silencioso */ }
    }
    fetchGitInfo()
  }, [sessaoId, podeGit])

  const showToast = useCallback((tipo: Toast['tipo'], mensagem: string) => {
    setToast({ tipo, mensagem })
    setTimeout(() => setToast(null), 5000)
  }, [])

  const handleAction = async (action: GitAction, fn: (() => void) | undefined) => {
    if (!fn) return
    setLoading(action)
    setToast(null)
    try {
      await fn()
      showToast('success', 'Acao executada com sucesso!')
    } catch (e) {
      showToast('error', `Erro: ${String(e)}`)
    } finally {
      setLoading(null)
    }
  }

  // Ações de Git
  const handleGitCommit = async () => {
    const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/git-commit`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ mensagem: `Mission Control: ${sessaoTitulo}` }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Commit falhou')
    showToast('success', `Commit ${data.commit_hash} criado!`)
    // Refresh git info
    const infoRes = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/git-info`, { headers })
    if (infoRes.ok) setGitInfo(await infoRes.json())
  }

  const handleGitPush = async () => {
    const res = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/git-push`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ titulo_pr: `[Mission Control] ${sessaoTitulo}` }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Push falhou')
    showToast('success', `PR #${data.pr_number} criada! ${data.pr_url}`)
    // Refresh git info
    const infoRes = await fetch(`${API}/api/mission-control/sessao/${sessaoId}/git-info`, { headers })
    if (infoRes.ok) setGitInfo(await infoRes.json())
  }

  // Botões de ações gerais
  const botoesAcoes = [
    {
      id: 'voltarRevisao' as GitAction,
      titulo: 'Voltar para Revisao',
      descricao: 'Revisar sessoes, codigo e artefatos gerados',
      icone: <FileText className="w-6 h-6" />,
      cor: 'from-indigo-500 to-indigo-600',
      hoverCor: 'hover:from-indigo-600 hover:to-indigo-700',
      ativo: !!onVoltarRevisao,
      fn: onVoltarRevisao,
    },
    {
      id: 'testar' as GitAction,
      titulo: 'Testar Agora',
      descricao: 'Executa testes automatizados no codigo gerado',
      icone: <Play className="w-6 h-6" />,
      cor: 'from-blue-500 to-blue-600',
      hoverCor: 'hover:from-blue-600 hover:to-blue-700',
      ativo: !!onTestar,
      fn: onTestar,
    },
    {
      id: 'codeStudio' as GitAction,
      titulo: 'Aplicar no Code Studio',
      descricao: 'Abre no editor para revisar e aplicar mudancas',
      icone: <Code2 className="w-6 h-6" />,
      cor: 'from-purple-500 to-purple-600',
      hoverCor: 'hover:from-purple-600 hover:to-purple-700',
      ativo: !!onAplicarCodeStudio,
      fn: onAplicarCodeStudio,
    },
    {
      id: 'optimizer' as GitAction,
      titulo: 'Revisar Factory Optimizer',
      descricao: 'Analise de codigo pelo Factory Optimizer (PDCA)',
      icone: <Bot className="w-6 h-6" />,
      cor: 'from-amber-500 to-amber-600',
      hoverCor: 'hover:from-amber-600 hover:to-amber-700',
      ativo: !!onFactoryOptimizer,
      fn: onFactoryOptimizer,
    },
    {
      id: 'aprovar' as GitAction,
      titulo: 'Pedir Aprovacao',
      descricao: 'Envia para Operations Lead (Jonatas) aprovar',
      icone: <ShieldCheck className="w-6 h-6" />,
      cor: 'from-emerald-500 to-emerald-600',
      hoverCor: 'hover:from-emerald-600 hover:to-emerald-700',
      ativo: !!onAprovarOperations,
      fn: onAprovarOperations,
    },
    {
      id: 'convidar' as GitAction,
      titulo: 'Convidar Colaborador',
      descricao: 'Convida um membro da equipe para colaborar',
      icone: <Users className="w-6 h-6" />,
      cor: 'from-cyan-500 to-cyan-600',
      hoverCor: 'hover:from-cyan-600 hover:to-cyan-700',
      ativo: !!onConvidarColaborador,
      fn: onConvidarColaborador,
    },
    {
      id: 'relatorio' as GitAction,
      titulo: 'Gerar Relatorio CEO',
      descricao: 'Resumo executive para o CEO (Thiago)',
      icone: <FileText className="w-6 h-6" />,
      cor: 'from-rose-500 to-rose-600',
      hoverCor: 'hover:from-rose-600 hover:to-rose-700',
      ativo: !!onGerarRelatorioCEO,
      fn: onGerarRelatorioCEO,
    },
    {
      id: 'novaSessao' as GitAction,
      titulo: 'Nova Sessao',
      descricao: 'Inicia uma nova missao do zero',
      icone: <Plus className="w-6 h-6" />,
      cor: 'from-gray-500 to-gray-600',
      hoverCor: 'hover:from-gray-600 hover:to-gray-700',
      ativo: !!onNovaSessao,
      fn: onNovaSessao,
    },
  ]

  // Botões de Git
  const botoesGit = [
    {
      id: 'commit' as GitAction,
      titulo: 'Commit',
      descricao: gitInfo?.commits_pendentes
        ? `${gitInfo.commits_pendentes} alteracao(oes) para commitar`
        : 'Commitar alteracoes locally',
      icone: <GitCommit className="w-5 h-5" />,
      cor: 'from-orange-500 to-orange-600',
      hoverCor: 'hover:from-orange-600 hover:to-orange-700',
      ativo: podeGit && !!gitInfo?.eh_git && (gitInfo?.commits_pendentes ?? 0) > 0,
      loadingOverride: loading === 'commit',
      fn: () => handleGitCommit(),
    },
    {
      id: 'push' as GitAction,
      titulo: 'Push + PR',
      descricao: gitInfo?.vcs_configurado
        ? `Branch: ${gitInfo.branch} → ${gitInfo.branch_padrao}`
        : 'Push + Pull Request (requer VCS configurado)',
      icone: <GitBranch className="w-5 h-5" />,
      cor: 'from-green-600 to-green-700',
      hoverCor: 'hover:from-green-700 hover:to-green-800',
      ativo: podeGit && !!gitInfo?.vcs_configurado,
      loadingOverride: loading === 'push',
      fn: () => handleGitPush(),
    },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 gap-6 overflow-auto" style={{ background: 'var(--sf-bg)' }}>
      {/* Toast de feedback */}
      {toast && (
        <div className={`
          fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg max-w-md
          ${toast.tipo === 'success' ? 'bg-green-500/90 text-white' :
            toast.tipo === 'error' ? 'bg-red-500/90 text-white' :
            'bg-blue-500/90 text-white'}
        `}>
          {toast.tipo === 'success' && <Check className="w-5 h-5 flex-shrink-0" />}
          {toast.tipo === 'error' && <AlertCircle className="w-5 h-5 flex-shrink-0" />}
          <span className="text-sm font-medium">{toast.mensagem}</span>
          <button onClick={() => setToast(null)} className="ml-2 opacity-70 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header de Sucesso */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <CheckCircle2 className="w-12 h-12" style={{ color: '#10b981', filter: 'drop-shadow(0 0 16px rgba(16,185,129,0.5))' }} />
        </div>
        <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--sf-text)' }}>
          Concluido com Sucesso!
        </h2>
        <p className="text-base mb-1" style={{ color: 'var(--sf-text-secondary)' }}>
          {sessaoTitulo}
        </p>
        <div className="flex items-center justify-center gap-4 mt-3 text-sm" style={{ color: 'var(--sf-text-secondary)' }}>
          <span className="flex items-center gap-1">
            <FileText className="w-4 h-4" /> {totalArtifacts} artifacts
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Code2 className="w-4 h-4" /> {totalComandos} comandos
          </span>
        </div>
      </div>

      {/* Git Status Bar (se pode Git) */}
      {podeGit && gitInfo && (
        <div className="w-full max-w-3xl">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl"
            style={{
              background: gitInfo.vcs_configurado ? 'rgba(16,185,129,0.1)' : 'rgba(251,191,36,0.1)',
              border: `1px solid ${gitInfo.vcs_configurado ? 'rgba(16,185,129,0.3)' : 'rgba(251,191,36,0.3)'}`,
            }}>
            {loading && loading !== 'novaSessao' ? (
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: '#10b981' }} />
            ) : gitInfo.vcs_configurado ? (
              <GitBranch className="w-5 h-5" style={{ color: '#10b981' }} />
            ) : (
              <AlertCircle className="w-5 h-5" style={{ color: '#fbbf24' }} />
            )}
            <div className="flex-1 min-w-0">
              {gitInfo.eh_git ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-mono" style={{ color: 'var(--sf-text)' }}>
                    {gitInfo.projeto_nome || 'Projeto'}:{gitInfo.branch}
                  </span>
                  {gitInfo.commits_pendentes > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                      style={{ background: 'rgba(251,191,36,0.2)', color: '#fbbf24' }}>
                      {gitInfo.commits_pendentes} pendente(s)
                    </span>
                  )}
                  {gitInfo.vcs_configurado && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                      style={{ background: 'rgba(16,185,129,0.2)', color: '#10b981' }}>
                      VCS: {gitInfo.vcs_tipo}
                    </span>
                  )}
                  {!gitInfo.vcs_configurado && (
                    <span className="text-xs px-2 py-0.5 rounded-full"
                      style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>
                      Sem VCS (vC inProjetos para configurar)
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-sm" style={{ color: 'var(--sf-text-secondary)' }}>
                  Nao e um repositorio git
                </span>
              )}
            </div>
            {gitInfo.ultimo_commit && (
              <span className="text-xs font-mono opacity-60" style={{ color: 'var(--sf-text-secondary)' }}>
                {gitInfo.ultimo_commit}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Painel de Ações de Git (se pode Git) */}
      {podeGit && (
        <div className="w-full max-w-3xl">
          <div className="flex items-center gap-2 mb-3">
            <GitBranch className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
            <h3 className="text-sm font-bold" style={{ color: 'var(--sf-text)' }}>
              Git Actions
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {botoesGit.map(botao => (
              <button
                key={botao.id}
                onClick={() => handleAction(botao.id, botao.fn)}
                disabled={!botao.ativo || (loading !== null && loading !== botao.id)}
                className={`
                  relative flex items-start gap-3 p-3 rounded-xl text-left transition-all
                  bg-gradient-to-br ${botao.cor} ${botao.ativo && loading === null ? botao.hoverCor + ' hover:scale-[1.02]' : 'opacity-50 cursor-not-allowed'}
                `}
                style={{ boxShadow: botao.ativo && loading === null ? '0 4px 20px rgba(0,0,0,0.3)' : 'none' }}
              >
                <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center bg-white/20">
                  {(botao.loadingOverride || loading === botao.id) ? (
                    <Loader2 className="w-5 h-5 animate-spin text-white" />
                  ) : (
                    <span className="text-white">{botao.icone}</span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="font-bold text-white text-sm">{botao.titulo}</span>
                  <p className="text-xs text-white/70 mt-0.5">{botao.descricao}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Painel de Ações Gerais */}
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4" style={{ color: 'var(--sf-accent)' }} />
          <h3 className="text-sm font-bold" style={{ color: 'var(--sf-text)' }}>
            Acoes Recomendadas
          </h3>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {botoesAcoes.map(botao => (
            <button
              key={botao.id}
              onClick={() => handleAction(botao.id, botao.fn)}
              disabled={!botao.ativo || loading !== null}
              className={`
                relative flex items-start gap-4 p-4 rounded-xl text-left transition-all
                bg-gradient-to-br ${botao.cor} ${botao.ativo && loading === null ? botao.hoverCor + ' hover:scale-[1.02]' : 'opacity-50 cursor-not-allowed'}
              `}
              style={{ boxShadow: botao.ativo && loading === null ? '0 4px 20px rgba(0,0,0,0.3)' : 'none' }}
            >
              <div className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center bg-white/20">
                {loading === botao.id ? (
                  <Loader2 className="w-6 h-6 animate-spin text-white" />
                ) : (
                  <span className="text-white">{botao.icone}</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <span className="font-bold text-white">{botao.titulo}</span>
                <p className="text-xs text-white/70 mt-0.5">{botao.descricao}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center" style={{ color: 'var(--sf-text-secondary)', opacity: 0.5 }}>
        <p className="text-xs">Todas as acoes sao opcionais • Clique em Nova Sessaopara continuar</p>
      </div>
    </div>
  )
}
