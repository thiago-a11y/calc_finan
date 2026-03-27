/* Equipe — Liderança premium dark-mode (zero emojis, zero fundos claros) */

import { useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import { buscarUsuarios } from '../services/api'
import {
  Shield, CheckCircle2, Mail, Crown, Briefcase, Users,
  Rocket, ShieldCheck, Zap, Target, Megaphone, Radio,
} from 'lucide-react'

/* Cores premium por papel */
const papelConfig: Record<string, { label: string; cor: string; icon: typeof Crown }> = {
  ceo: { label: 'CEO', cor: '#10b981', icon: Crown },
  diretor_tecnico: { label: 'Diretor Técnico', cor: '#3b82f6', icon: Briefcase },
  operations_lead: { label: 'Operations Lead', cor: '#8b5cf6', icon: Shield },
  pm_central: { label: 'PM Central', cor: '#f59e0b', icon: Target },
  lider: { label: 'Líder', cor: '#ec4899', icon: Users },
  desenvolvedor: { label: 'Desenvolvedor', cor: '#6366f1', icon: Rocket },
  membro: { label: 'Membro', cor: '#6b7280', icon: Users },
}

const areaConfig: Record<string, { label: string; icon: typeof Zap }> = {
  deploy_producao: { label: 'Deploy Produção', icon: Rocket },
  gasto_ia: { label: 'Gasto IA', icon: Zap },
  mudanca_arquitetura: { label: 'Mudança Arquitetura', icon: Briefcase },
  campanha_marketing: { label: 'Campanha Marketing', icon: Megaphone },
  outreach_massa: { label: 'Outreach Massa', icon: Radio },
}

/* Cores de avatar baseadas no índice */
const avatarCores = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#6366f1', '#ef4444', '#14b8a6']

export default function Equipe() {
  const fetcher = useCallback(() => buscarUsuarios(), [])
  const { dados, erro, carregando } = usePolling(fetcher, 30000)

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (erro) {
    return <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">Erro: {erro}</div>
  }

  const usuarios = dados || []

  return (
    <div className="sf-page">
      {/* Glow sutil */}
      <div className="fixed top-0 right-1/4 w-[500px] h-[300px] bg-purple-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
          Equipe de Liderança
        </h2>
        <p className="text-sm sf-text-dim mt-1">
          {usuarios.length} usuário{usuarios.length !== 1 ? 's' : ''} com acesso ao Synerium Factory
        </p>
      </div>

      {/* Grid de membros */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {usuarios.map((usuario: any, idx: number) => {
          const corAvatar = avatarCores[idx % avatarCores.length]
          const iniciais = usuario.nome.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()

          return (
            <div
              key={usuario.id}
              className="group relative sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6 transition-all duration-500 hover:border-white/15 hover:-translate-y-0.5"
            >
              {/* Glow hover */}
              <div
                className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{ background: `radial-gradient(ellipse at top left, ${corAvatar}08, transparent 60%)` }}
              />

              <div className="relative">
                {/* Cabeçalho: Avatar + Info */}
                <div className="flex items-center gap-4 mb-5">
                  {/* Avatar premium */}
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center text-lg font-bold tracking-wide transition-transform duration-300 group-hover:scale-105"
                    style={{
                      backgroundColor: `${corAvatar}15`,
                      border: `2px solid ${corAvatar}30`,
                      color: corAvatar,
                    }}
                  >
                    {iniciais}
                  </div>

                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold sf-text-white">{usuario.nome}</h3>
                    <p className="text-sm sf-text-dim">{usuario.cargo || 'Sem cargo definido'}</p>
                  </div>

                  {/* Badge ativo */}
                  {usuario.ativo && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                      <CheckCircle2 size={12} className="text-emerald-400" />
                      <span className="text-[11px] text-emerald-400 font-medium">Ativo</span>
                    </div>
                  )}
                </div>

                {/* Papéis */}
                <div className="mb-4">
                  <p className="text-[10px] sf-text-ghost uppercase tracking-wider font-medium mb-2">Papéis</p>
                  <div className="flex flex-wrap gap-2">
                    {usuario.papeis.map((papel: string) => {
                      const cfg = papelConfig[papel] || { label: papel, cor: '#6b7280', icon: Users }
                      const Icon = cfg.icon
                      return (
                        <div
                          key={papel}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all duration-200 hover:scale-[1.02]"
                          style={{
                            backgroundColor: `${cfg.cor}10`,
                            borderColor: `${cfg.cor}20`,
                          }}
                        >
                          <Icon size={12} style={{ color: cfg.cor }} strokeWidth={2} />
                          <span className="text-xs font-medium" style={{ color: cfg.cor }}>
                            {cfg.label}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Email */}
                {usuario.email && (
                  <div className="flex items-center gap-2 mb-4">
                    <Mail size={13} className="sf-text-ghost" strokeWidth={1.5} />
                    <span className="text-sm sf-text-dim font-mono">{usuario.email}</span>
                  </div>
                )}

                {/* Permissões de aprovação */}
                {usuario.pode_aprovar && usuario.areas_aprovacao?.length > 0 && (
                  <div className="sf-glass border rounded-xl p-4" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldCheck size={14} className="text-emerald-400" strokeWidth={2} />
                      <p className="text-[10px] text-emerald-400 uppercase tracking-wider font-semibold">
                        Aprovador
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {usuario.areas_aprovacao.map((area: string) => {
                        const cfg = areaConfig[area] || { label: area, icon: Shield }
                        const Icon = cfg.icon
                        return (
                          <div
                            key={area}
                            className="flex items-center gap-1.5 px-2.5 py-1 sf-glass border sf-border rounded-lg"
                          >
                            <Icon size={11} className="sf-text-dim" strokeWidth={1.8} />
                            <span className="text-[11px] sf-text-dim">{cfg.label}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
