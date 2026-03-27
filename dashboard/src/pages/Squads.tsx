/* Squads — Grid premium dark-mode (zero emojis) */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarSquads } from '../services/api'
import { useChatManager } from '../components/ChatManager'
import {
  Crown, Users, ChevronDown, ChevronUp, MessageSquare,
  UserPlus, Zap, Code2, Palette, Megaphone, Bot,
  Sparkles,
} from 'lucide-react'

interface Squad {
  nome: string; especialidade: string; contexto: string
  num_agentes: number; num_tarefas: number; nomes_agentes: string[]
}

const squadIcons: Record<string, { icon: typeof Code2; cor: string }> = {
  'CEO': { icon: Crown, cor: '#10b981' },
  'Backend': { icon: Code2, cor: '#3b82f6' },
  'Frontend': { icon: Palette, cor: '#8b5cf6' },
  'Marketing': { icon: Megaphone, cor: '#f59e0b' },
}

function getSquadConfig(nome: string) {
  for (const [key, val] of Object.entries(squadIcons)) {
    if (nome.includes(key)) return val
  }
  return { icon: Users, cor: '#6b7280' }
}

export default function Squads() {
  const { abrirChat, abrirReuniao } = useChatManager()
  const fetcher = useCallback(() => buscarSquads(), [])
  const { dados, erro, carregando } = usePolling(fetcher, 15000)
  const [expandido, setExpandido] = useState<string | null>(null)

  if (carregando) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" /></div>
  }
  if (erro) return <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">Erro: {erro}</div>

  const squads = (dados || []) as Squad[]
  const totalAgentes = squads.reduce((acc, s) => acc + s.num_agentes, 0)

  return (
    <div className="sf-page">
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-emerald-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
          Squads
        </h2>
        <p className="text-sm sf-text-dim mt-1">
          {squads.length} squad(s) · {totalAgentes} agente(s) no total
        </p>
      </div>

      <div className="space-y-4">
        {squads.map(squad => {
          const isCeo = squad.nome.includes('CEO')
          const isExpandido = expandido === squad.nome
          const cfg = getSquadConfig(squad.nome)
          const Icon = cfg.icon

          return (
            <div
              key={squad.nome}
              className={`group sf-glass backdrop-blur-sm border rounded-2xl transition-all duration-300 hover:-translate-y-0.5 ${
                isCeo
                  ? 'border-emerald-500/20 hover:border-emerald-500/30'
                  : 'sf-border hover:border-white/15'
              }`}
            >
              {/* Header do squad */}
              <div
                className="px-6 py-5 cursor-pointer flex items-center gap-4"
                onClick={() => setExpandido(isExpandido ? null : squad.nome)}
              >
                <div className="w-11 h-11 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-105"
                  style={{ backgroundColor: `${cfg.cor}12`, border: `1.5px solid ${cfg.cor}25` }}>
                  <Icon size={20} style={{ color: cfg.cor }} strokeWidth={1.5} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <h3 className="font-semibold sf-text-white">{squad.nome}</h3>
                    {isCeo && (
                      <span className="text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-lg">
                        Piloto
                      </span>
                    )}
                  </div>
                  <p className="text-xs sf-text-dim mt-0.5">{squad.especialidade}</p>
                </div>

                <div className="flex items-center gap-4 text-xs sf-text-dim mr-2">
                  <span className="flex items-center gap-1.5">
                    <Bot size={12} style={{ color: cfg.cor }} />
                    <span className="font-mono font-medium" style={{ color: cfg.cor }}>{squad.num_agentes}</span>
                    agente(s)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Zap size={12} className="sf-text-ghost" />
                    <span className="font-mono sf-text-dim">{squad.num_tarefas}</span>
                    tarefa(s)
                  </span>
                </div>

                {isExpandido
                  ? <ChevronUp size={16} className="sf-text-ghost shrink-0" />
                  : <ChevronDown size={16} className="sf-text-ghost shrink-0" />
                }
              </div>

              {/* Contexto (sempre visível se CEO) */}
              {(isCeo || isExpandido) && (
                <div className="px-6 pb-2">
                  <p className="text-sm sf-text-dim leading-relaxed">{squad.contexto}</p>
                </div>
              )}

              {/* Expandido: agentes + ações */}
              {isExpandido && squad.nomes_agentes.length > 0 && (
                <div className="px-6 pb-6 pt-3" onClick={e => e.stopPropagation()}>
                  <div className="border-t pt-4" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                    {/* Ações */}
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-[10px] sf-text-ghost uppercase tracking-wider font-medium">
                        Agentes do Squad
                      </p>
                      {squad.nomes_agentes.length >= 2 && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => abrirReuniao(
                              squad.nome,
                              squad.nomes_agentes.map((nome, idx) => ({ idx, nome }))
                            )}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-[10px] font-medium hover:bg-blue-500/20 transition-all"
                          >
                            <Users size={11} /> Reunião com todos
                          </button>
                          <button
                            onClick={() => abrirReuniao(
                              squad.nome,
                              squad.nomes_agentes.map((nome, idx) => ({ idx, nome }))
                            )}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg text-[10px] font-medium hover:bg-purple-500/20 transition-all"
                          >
                            <UserPlus size={11} /> Selecionar participantes
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Grid de agentes */}
                    <div className={`${isCeo ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2' : 'space-y-1.5'}`}>
                      {squad.nomes_agentes.map((nome, idx) => (
                        <div
                          key={nome}
                          onClick={() => abrirChat(squad.nome, idx, nome)}
                          className="flex items-center gap-3 px-3.5 py-2.5 sf-glass border rounded-xl cursor-pointer hover:border-white/15 transition-all duration-200 group/agent" style={{ borderColor: 'var(--sf-border-subtle)' }}
                        >
                          <span className="text-[10px] font-mono font-bold sf-text-ghost w-5">#{idx + 1}</span>
                          <span className="text-xs sf-text-dim flex-1 truncate">{nome}</span>
                          <MessageSquare size={12} className="sf-text-faint group-hover/agent:text-emerald-400 transition-colors shrink-0" />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Preview quando não expandido */}
              {!isExpandido && squad.nomes_agentes.length > 0 && !isCeo && (
                <div className="px-6 pb-4">
                  <p className="text-[10px] sf-text-ghost flex items-center gap-1.5">
                    <Sparkles size={10} />
                    Clique para ver {squad.nomes_agentes.length} agente(s) · chat · reuniões
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
