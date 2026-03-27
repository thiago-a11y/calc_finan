/* Sidebar — Premium navigation inspired by Linear/Vercel */

import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard, ShieldCheck, Users, Building2, FolderKanban,
  BookOpen, ClipboardList, FileText, Coins, Brain, Wrench,
  UserCircle, Settings, LogOut, ChevronRight, Rocket, Bot, UserCog,
} from 'lucide-react'

const links = [
  { to: '/', label: 'Painel Geral', Icon: LayoutDashboard },
  { to: '/aprovacoes', label: 'Aprovacoes', Icon: ShieldCheck },
  { to: '/squads', label: 'Squads', Icon: Users },
  { to: '/catalogo', label: 'Catálogo de Agentes', Icon: Bot },
  { to: '/atribuicoes', label: 'Atribuições', Icon: UserCog },
  { to: '/escritorio', label: 'Escritorio', Icon: Building2 },
  { to: '/projetos', label: 'Projetos', Icon: FolderKanban },
  { to: '/rag', label: 'Base de Conhecimento', Icon: BookOpen },
  { to: '/standup', label: 'Standup Diario', Icon: ClipboardList },
  { to: '/relatorios', label: 'Relatorios', Icon: FileText },
  { to: '/deploy', label: 'Deploy', Icon: Rocket },
  { to: '/consumo', label: 'Consumo de APIs', Icon: Coins },
  { to: '/llm-providers', label: 'LLM Providers', Icon: Brain },
  { to: '/skills', label: 'Skills', Icon: Wrench },
  { to: '/equipe', label: 'Equipe', Icon: UserCircle },
  { to: '/configuracoes', label: 'Configuracoes', Icon: Settings },
]

export default function Sidebar() {
  const { usuario, logout } = useAuth()
  // Theme toggle movido para Header

  return (
    <aside
      className="w-[240px] min-h-screen flex flex-col flex-shrink-0 transition-colors duration-200"
      style={{
        background: 'var(--sf-bg-1)',
        borderRight: '1px solid var(--sf-border-subtle)',
      }}
    >
      {/* Header */}
      <div className="px-4 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--sf-accent)' }}
          >
            <span className="text-white text-xs font-bold">S</span>
          </div>
          <div>
            <p className="text-[13px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
              Synerium
            </p>
            <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Factory</p>
          </div>
        </div>

        {/* Theme toggle movido para o Header (App.tsx) */}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-1 space-y-[2px] overflow-y-auto">
        {links.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className="group flex items-center gap-2.5 px-2.5 py-[7px] rounded-lg text-[13px] transition-all duration-150"
            style={({ isActive }) => ({
              background: isActive ? 'var(--sf-accent-dim)' : 'transparent',
              color: isActive ? 'var(--sf-accent-text)' : 'var(--sf-text-2)',
              fontWeight: isActive ? 500 : 400,
            })}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={16}
                  strokeWidth={isActive ? 2 : 1.5}
                  style={{
                    color: isActive ? 'var(--sf-accent-text)' : 'var(--sf-text-3)',
                    transition: 'color 0.15s ease',
                  }}
                />
                <span className="truncate">{label}</span>
                {isActive && (
                  <ChevronRight
                    size={12}
                    className="ml-auto opacity-40"
                    style={{ color: 'var(--sf-accent-text)' }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      {usuario && (
        <div
          className="mx-2 mb-2 rounded-lg overflow-hidden"
          style={{
            background: 'var(--sf-bg-2)',
            border: '1px solid var(--sf-border-subtle)',
          }}
        >
          <NavLink
            to="/perfil"
            className="flex items-center gap-2.5 px-3 py-2.5 transition-colors"
            style={{ color: 'var(--sf-text-2)' }}
          >
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              {usuario.nome[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                {usuario.nome}
              </p>
              <p className="text-[10px] truncate" style={{ color: 'var(--sf-text-3)' }}>
                {usuario.email}
              </p>
            </div>
          </NavLink>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 text-[11px] transition-colors"
            style={{
              color: 'var(--sf-text-3)',
              borderTop: '1px solid var(--sf-border-subtle)',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#ef4444' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--sf-text-3)' }}
          >
            <LogOut size={12} />
            <span>Sair</span>
          </button>
        </div>
      )}

      {/* Version */}
      <div className="px-4 pb-3">
        <p className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>v0.15.0</p>
      </div>
    </aside>
  )
}
