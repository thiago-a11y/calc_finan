/* TeamDialog — Modal de selecao de agentes para Collaborative Agent Mode */

import { useState, useEffect } from 'react'
import { X, Loader2, Users, Check, Sparkles } from 'lucide-react'
import AgentAvatar from '../AgentAvatar'

interface AgenteCatalogo {
  id: number
  nome_exibicao: string
  perfil_agente: string
  categoria: string
  icone: string
  objetivo: string
}

interface TeamDialogProps {
  onIniciar: (agentesIds: number[]) => void
  onFechar: () => void
}

const MAX_AGENTES = 3

const API = import.meta.env.VITE_API_URL || ''

export default function TeamDialog({ onIniciar, onFechar }: TeamDialogProps) {
  const [agentes, setAgentes] = useState<AgenteCatalogo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set())

  useEffect(() => {
    const carregar = async () => {
      try {
        const token = localStorage.getItem('sf_token')
        const res = await fetch(`${API}/api/catalogo`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (res.ok) {
          const lista: AgenteCatalogo[] = await res.json()
          setAgentes(lista.filter(a => a.perfil_agente !== 'secretaria_executiva'))
        }
      } catch { /* silencioso */ }
      finally { setCarregando(false) }
    }
    carregar()
  }, [])

  const toggleAgente = (id: number) => {
    setSelecionados(prev => {
      const novo = new Set(prev)
      if (novo.has(id)) {
        novo.delete(id)
      } else if (novo.size < MAX_AGENTES) {
        novo.add(id)
      }
      return novo
    })
  }

  const categoriasCores: Record<string, string> = {
    desenvolvimento: '#10b981',
    gestao: '#8b5cf6',
    seguranca: '#ef4444',
    ia: '#f59e0b',
    operacional: '#3b82f6',
    geral: '#6b7280',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div className="rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
        style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3"
          style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
          <div className="flex items-center gap-2">
            <Users size={16} style={{ color: '#8b5cf6' }} />
            <div>
              <h3 className="text-[14px] font-bold" style={{ color: 'var(--sf-text-0)' }}>
                Chamar Time
              </h3>
              <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                Selecione ate {MAX_AGENTES} especialistas
              </p>
            </div>
          </div>
          <button onClick={onFechar} className="p-1.5 rounded-lg hover:bg-white/5"
            style={{ color: 'var(--sf-text-3)' }}>
            <X size={16} />
          </button>
        </div>

        {/* Lista de agentes */}
        <div className="px-4 py-3 max-h-[50vh] overflow-auto" style={{ scrollbarWidth: 'thin' }}>
          {carregando ? (
            <div className="flex items-center justify-center py-8 gap-2">
              <Loader2 size={16} className="animate-spin" style={{ color: '#8b5cf6' }} />
              <span className="text-[12px]" style={{ color: 'var(--sf-text-3)' }}>Carregando agentes...</span>
            </div>
          ) : (
            <div className="space-y-1.5">
              {agentes.map(ag => {
                const sel = selecionados.has(ag.id)
                const desabilitado = !sel && selecionados.size >= MAX_AGENTES
                const corCat = categoriasCores[ag.categoria] || '#6b7280'

                return (
                  <button
                    key={ag.id}
                    onClick={() => toggleAgente(ag.id)}
                    disabled={desabilitado}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all disabled:opacity-30"
                    style={{
                      background: sel ? 'rgba(139,92,246,0.08)' : 'transparent',
                      border: `1px solid ${sel ? 'rgba(139,92,246,0.2)' : 'var(--sf-border-subtle)'}`,
                    }}
                  >
                    {/* Checkbox */}
                    <div className="w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0"
                      style={{
                        borderColor: sel ? '#8b5cf6' : 'var(--sf-border-default)',
                        background: sel ? '#8b5cf6' : 'transparent',
                      }}>
                      {sel && <Check size={12} color="#fff" strokeWidth={3} />}
                    </div>

                    {/* Avatar */}
                    <AgentAvatar agentName={ag.nome_exibicao.split('/')[0].trim().split(' ')[0]} size="sm" noHover />

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-semibold truncate" style={{ color: 'var(--sf-text-0)' }}>
                        {ag.nome_exibicao}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[9px] px-1.5 py-0.5 rounded font-medium"
                          style={{ background: `${corCat}15`, color: corCat }}>
                          {ag.categoria}
                        </span>
                        <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>
                          {ag.perfil_agente}
                        </span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3"
          style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
          <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
            {selecionados.size}/{MAX_AGENTES} selecionados
          </span>
          <div className="flex items-center gap-2">
            <button onClick={onFechar}
              className="px-3 py-1.5 rounded-lg text-[11px] font-medium hover:bg-white/5"
              style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
              Cancelar
            </button>
            <button
              onClick={() => onIniciar(Array.from(selecionados))}
              disabled={selecionados.size === 0}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
              style={{ background: '#8b5cf6', color: '#fff' }}>
              <Sparkles size={12} />
              Iniciar Analise
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
