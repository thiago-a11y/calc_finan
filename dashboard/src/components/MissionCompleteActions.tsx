/* MissionCompleteActions — v0.57.7
 *
 * Painel de açoes recomendado quando missao atinge 100% concluído.
 * Exibe botões grandes com ícones para próximo passos.
 *
 * v0.57.7 — Novo: tela de conclusao com açoes recomendadas
 */

import { useState } from 'react'
import {
  Play, Code2, Bot, ShieldCheck, Users,
  FileText, Plus, Loader2, CheckCircle2, Sparkles,
} from 'lucide-react'

interface MissionCompleteActionsProps {
  onTestar?: () => void
  onAplicarCodeStudio?: () => void
  onFactoryOptimizer?: () => void
  onAprovarOperations?: () => void
  onConvidarColaborador?: () => void
  onGerarRelatorioCEO?: () => void
  onNovaSessao?: () => void
  sessaoTitulo?: string
  totalArtifacts?: number
  totalComandos?: number
}

type ActionLoading = 'testar' | 'codeStudio' | 'optimizer' | 'aprovar' | 'convidar' | 'relatorio' | null

export default function MissionCompleteActions({
  onTestar,
  onAplicarCodeStudio,
  onFactoryOptimizer,
  onAprovarOperations,
  onConvidarColaborador,
  onGerarRelatorioCEO,
  onNovaSessao,
  sessaoTitulo = 'Missão',
  totalArtifacts = 0,
  totalComandos = 0,
}: MissionCompleteActionsProps) {
  const [loading, setLoading] = useState<ActionLoading>(null)
  const [resultado, setResultado] = useState<{ tipo: ActionLoading; mensagem: string } | null>(null)

  const handleAction = async (action: ActionLoading, fn: (() => void) | undefined) => {
    if (!fn) return
    setLoading(action)
    setResultado(null)
    try {
      await fn()
      setResultado({ tipo: action, mensagem: 'Ação executada com sucesso!' })
    } catch (e) {
      setResultado({ tipo: action, mensagem: `Erro: ${String(e)}` })
    } finally {
      setLoading(null)
    }
  }

  const botoes = [
    {
      id: 'testar' as ActionLoading,
      titulo: 'Testar Agora',
      descricao: 'Executa testes automatizados no código gerado',
      icone: <Play className="w-6 h-6" />,
      cor: 'from-blue-500 to-blue-600',
      hoverCor: 'hover:from-blue-600 hover:to-blue-700',
      ativo: !!onTestar,
      fn: onTestar,
    },
    {
      id: 'codeStudio' as ActionLoading,
      titulo: 'Aplicar no Code Studio',
      descricao: 'Abre no editor para revisar e aplicar mudanças',
      icone: <Code2 className="w-6 h-6" />,
      cor: 'from-purple-500 to-purple-600',
      hoverCor: 'hover:from-purple-600 hover:to-purple-700',
      ativo: !!onAplicarCodeStudio,
      fn: onAplicarCodeStudio,
    },
    {
      id: 'optimizer' as ActionLoading,
      titulo: 'Revisar com Factory Optimizer',
      descricao: 'Análise de código pelo Factory Optimizer (PDCA)',
      icone: <Bot className="w-6 h-6" />,
      cor: 'from-amber-500 to-amber-600',
      hoverCor: 'hover:from-amber-600 hover:to-amber-700',
      ativo: !!onFactoryOptimizer,
      fn: onFactoryOptimizer,
    },
    {
      id: 'aprovar' as ActionLoading,
      titulo: 'Pedir Aprovação',
      descricao: 'Envia para Operations Lead (Jonatas) aprovar',
      icone: <ShieldCheck className="w-6 h-6" />,
      cor: 'from-emerald-500 to-emerald-600',
      hoverCor: 'hover:from-emerald-600 hover:to-emerald-700',
      ativo: !!onAprovarOperations,
      fn: onAprovarOperations,
    },
    {
      id: 'convidar' as ActionLoading,
      titulo: 'Convidar Colaborador',
      descricao: 'Convida um membro da equipe para colaborar',
      icone: <Users className="w-6 h-6" />,
      cor: 'from-cyan-500 to-cyan-600',
      hoverCor: 'hover:from-cyan-600 hover:to-cyan-700',
      ativo: !!onConvidarColaborador,
      fn: onConvidarColaborador,
    },
    {
      id: 'relatorio' as ActionLoading,
      titulo: 'Gerar Relatório CEO',
      descricao: 'Resumo executive para o CEO (Thiago)',
      icone: <FileText className="w-6 h-6" />,
      cor: 'from-rose-500 to-rose-600',
      hoverCor: 'hover:from-rose-600 hover:to-rose-700',
      ativo: !!onGerarRelatorioCEO,
      fn: onGerarRelatorioCEO,
    },
    {
      id: 'novaSessao' as ActionLoading,
      titulo: 'Nova Sessão',
      descricao: 'Inicia uma nova missão do zero',
      icone: <Plus className="w-6 h-6" />,
      cor: 'from-gray-500 to-gray-600',
      hoverCor: 'hover:from-gray-600 hover:to-gray-700',
      ativo: !!onNovaSessao,
      fn: onNovaSessao,
    },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 gap-8" style={{ background: 'var(--sf-bg)' }}>
      {/* Header de Sucesso */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <CheckCircle2 className="w-12 h-12" style={{ color: '#10b981', filter: 'drop-shadow(0 0 16px rgba(16,185,129,0.5))' }} />
        </div>
        <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--sf-text)' }}>
          ✅ Concluído com Sucesso!
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

      {/* Painel de Ações */}
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
          <h3 className="text-lg font-bold" style={{ color: 'var(--sf-text)' }}>
            Ações Recomendadas
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {botoes.map(botao => (
            <button
              key={botao.id}
              onClick={() => handleAction(botao.id, botao.fn)}
              disabled={!botao.ativo || loading !== null}
              className={`
                relative flex items-start gap-4 p-4 rounded-xl text-left transition-all
                bg-gradient-to-br ${botao.cor} ${botao.hoverCor}
                ${botao.ativo && loading === null ? 'hover:scale-[1.02] hover:shadow-lg cursor-pointer' : 'opacity-50 cursor-not-allowed'}
              `}
              style={{
                boxShadow: botao.ativo && loading === null ? '0 4px 20px rgba(0,0,0,0.3)' : 'none',
              }}
            >
              {/* Ícone */}
              <div className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center bg-white/20">
                {loading === botao.id ? (
                  <Loader2 className="w-6 h-6 animate-spin text-white" />
                ) : (
                  <span className="text-white">{botao.icone}</span>
                )}
              </div>

              {/* Texto */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">{botao.titulo}</span>
                  {resultado?.tipo === botao.id && (
                    <CheckCircle2 className="w-4 h-4 text-green-300 flex-shrink-0" />
                  )}
                </div>
                <p className="text-xs text-white/70 mt-0.5">{botao.descricao}</p>
                {resultado?.tipo === botao.id && resultado.mensagem && (
                  <p className="text-xs text-green-200 mt-1 font-medium">{resultado.mensagem}</p>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center mt-2" style={{ color: 'var(--sf-text-secondary)', opacity: 0.5 }}>
        <p className="text-xs">Todas as ações são opcionais • Clique em "Nova Sessão" para continuar</p>
      </div>
    </div>
  )
}
