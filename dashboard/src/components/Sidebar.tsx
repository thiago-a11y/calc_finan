/* Sidebar — v0.58.4
 *
 * Menu lateral fixo (sticky) com scroll interno e modo colapsavel (mini).
 * Estado gerenciado via Redux (sidebarSlice) com persistencia em localStorage.
 *
 * v0.58.4 — Sidebar Fixo e Colapsavel:
 * - position: fixed, height: 100vh, overflow-y: auto
 * - Card usuario + Sair sempre visiveis no bottom
 * - Modo mini: 64px (icons only)
 * - Modo expandido: 240px (labels visiveis)
 * - Animacao suave ao colapsar/expandir
 * - Mobile: overlay com backdrop
 */

import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { toggleSidebar } from '../store/sidebarSlice'
import {
  LayoutDashboard, ShieldCheck, Users, Building2, FolderKanban,
  BookOpen, ClipboardList, FileText, Coins, Brain, Wrench,
  UserCircle, Settings, LogOut, ChevronRight, Rocket, Bot, UserCog, Code2, Target,
  ChevronLeft, Menu, X,
} from 'lucide-react'
import { useState } from 'react'

const links = [
  { to: '/', label: 'Painel Geral', Icon: LayoutDashboard },
  { to: '/aprovacoes', label: 'Aprovações', Icon: ShieldCheck },
  { to: '/squads', label: 'Squads', Icon: Users },
  { to: '/catalogo', label: 'Catálogo', Icon: Bot },
  { to: '/atribuicoes', label: 'Atribuições', Icon: UserCog },
  { to: '/escritorio', label: 'Escritório', Icon: Building2 },
  { to: '/code-studio', label: 'Code Studio', Icon: Code2 },
  { to: '/mission-control', label: 'Mission Control', Icon: Rocket },
  { to: '/projetos', label: 'Projetos', Icon: FolderKanban },
  { to: '/rag', label: 'Base de Conhecimento', Icon: BookOpen },
  { to: '/standup', label: 'Standup Diário', Icon: ClipboardList },
  { to: '/relatorios', label: 'Relatórios', Icon: FileText },
  { to: '/deploy', label: 'Deploy', Icon: Rocket },
  { to: '/command-center', label: 'Command Center', Icon: Target },
  { to: '/consumo', label: 'Consumo de APIs', Icon: Coins },
  { to: '/llm-providers', label: 'LLM Providers', Icon: Brain },
  { to: '/skills', label: 'Skills', Icon: Wrench },
  { to: '/equipe', label: 'Equipe', Icon: UserCircle },
  { to: '/configuracoes', label: 'Configurações', Icon: Settings },
]

const SIDEBAR_EXPANDED = 240
const SIDEBAR_COLLAPSED = 64
const MOBILE_BREAKPOINT = 768

export default function Sidebar() {
  const collapsed = useAppSelector(s => s.sidebar.collapsed)
  const dispatch = useAppDispatch()
  const [mobileOpen, setMobileOpen] = useState(false)

  const isMobile = typeof window !== 'undefined' && window.innerWidth < MOBILE_BREAKPOINT
  const sidebarWidth = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED

  if (isMobile && !mobileOpen) {
    return (
      <>
        <button
          onClick={() => setMobileOpen(true)}
          className="fixed top-4 left-4 z-50 p-2 rounded-lg shadow-lg"
          style={{
            background: 'var(--sf-bg-1)',
            border: '1px solid var(--sf-border-subtle)',
          }}
        >
          <Menu className="w-5 h-5" style={{ color: 'var(--sf-text-1)' }} />
        </button>
        <SidebarContent
          collapsed={false}
          onClose={() => setMobileOpen(false)}
          isMobile
        />
      </>
    )
  }

  if (isMobile && mobileOpen) {
    return (
      <>
        <div
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.5)' }}
          onClick={() => setMobileOpen(false)}
        />
        <div
          className="fixed inset-y-0 left-0 z-50 flex flex-col"
          style={{
            width: '280px',
            background: 'var(--sf-bg-1)',
            borderRight: '1px solid var(--sf-border-subtle)',
          }}
        >
          <SidebarContent
            collapsed={false}
            onClose={() => setMobileOpen(false)}
            isMobile
          />
        </div>
      </>
    )
  }

  // Desktop: sidebar fixed
  return (
    <>
      <aside
        className="fixed top-0 left-0 z-40 flex flex-col flex-shrink-0 transition-all duration-300 ease-in-out"
        style={{
          width: `${sidebarWidth}px`,
          height: '100vh',
          background: 'var(--sf-bg-1)',
          borderRight: '1px solid var(--sf-border-subtle)',
        }}
      >
        <SidebarContent
          collapsed={collapsed}
          onToggle={() => dispatch(toggleSidebar())}
          isMobile={false}
        />
      </aside>

      {/* Spacer for main content (desktop only) */}
      <div style={{ width: `${sidebarWidth}px`, flexShrink: 0 }} />
    </>
  )
}

interface SidebarContentProps {
  collapsed: boolean
  onToggle?: () => void
  onClose?: () => void
  isMobile: boolean
}

function SidebarContent({ collapsed, onToggle, onClose, isMobile }: SidebarContentProps) {
  const { usuario, logout } = useAuth()

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--sf-accent)' }}
          >
            <span className="text-white text-xs font-bold">S</span>
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <p className="text-[13px] font-semibold truncate" style={{ color: 'var(--sf-text-0)' }}>
                Synerium
              </p>
              <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Factory</p>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" style={{ color: 'var(--sf-text-2)' }} />
            </button>
          )}
          {onToggle && !isMobile && (
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
              title={collapsed ? 'Expandir menu' : 'Colapsar menu'}
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" style={{ color: 'var(--sf-text-2)' }} />
              ) : (
                <ChevronLeft className="w-4 h-4" style={{ color: 'var(--sf-text-2)' }} />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Luna — Destaque especial */}
      <div className="px-2 pt-2 pb-1">
        <NavLink
          to="/luna"
          className="group flex items-center gap-2.5 px-2.5 py-[9px] rounded-lg text-[13px] transition-all duration-200"
          style={({ isActive }) => ({
            background: isActive
              ? 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(99,102,241,0.1))'
              : 'linear-gradient(135deg, rgba(16,185,129,0.06), rgba(99,102,241,0.04))',
            color: isActive ? '#10b981' : 'var(--sf-text-1)',
            fontWeight: 500,
            border: isActive ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(16,185,129,0.1)',
          })}
          onClick={onClose}
        >
          {({ isActive }) => (
            <>
              <img
                src="/avatars/luna.jpg"
                alt="Luna"
                className="w-5 h-5 rounded-full object-cover flex-shrink-0"
                style={{
                  border: isActive ? '2px solid #10b981' : '1.5px solid rgba(16,185,129,0.4)',
                  boxShadow: isActive ? '0 0 8px rgba(16,185,129,0.3)' : 'none',
                }}
              />
              {!collapsed && (
                <>
                  <span className="truncate">Luna</span>
                  <span
                    className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full font-bold flex-shrink-0"
                    style={{ background: 'linear-gradient(135deg, #10b981, #6366f1)', color: '#fff' }}
                  >
                    IA
                  </span>
                </>
              )}
            </>
          )}
        </NavLink>
      </div>

      {/* Navigation — scrollavel internamente */}
      <nav
        className="flex-1 px-2 py-1 space-y-[2px] overflow-y-auto"
        style={{ minHeight: 0 }}
      >
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
            onClick={onClose}
            title={collapsed ? label : undefined}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={16}
                  strokeWidth={isActive ? 2 : 1.5}
                  className="flex-shrink-0"
                  style={{
                    color: isActive ? 'var(--sf-accent-text)' : 'var(--sf-text-3)',
                    transition: 'color 0.15s ease',
                  }}
                />
                {!collapsed && (
                  <>
                    <span className="truncate">{label}</span>
                    {isActive && (
                      <ChevronRight
                        size={12}
                        className="ml-auto opacity-40 flex-shrink-0"
                        style={{ color: 'var(--sf-accent-text)' }}
                      />
                    )}
                  </>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User card — sempre no bottom do sidebar visivel */}
      {usuario && (
        <div
          className="mx-2 mb-2 rounded-lg overflow-hidden flex-shrink-0"
          style={{
            background: 'var(--sf-bg-2)',
            border: '1px solid var(--sf-border-subtle)',
          }}
        >
          <NavLink
            to="/perfil"
            className="flex items-center gap-2.5 px-3 py-2.5 transition-colors"
            style={{ color: 'var(--sf-text-2)' }}
            onClick={onClose}
          >
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              {usuario.nome?.[0] || 'U'}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 overflow-hidden">
                <p className="text-[12px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                  {usuario.nome}
                </p>
                <p className="text-[10px] truncate" style={{ color: 'var(--sf-text-3)' }}>
                  {usuario.email}
                </p>
              </div>
            )}
          </NavLink>
          <button
            onClick={() => { logout(); onClose?.() }}
            className="w-full flex items-center gap-2 px-3 py-2 text-[11px] transition-colors"
            style={{
              color: 'var(--sf-text-3)',
              borderTop: '1px solid var(--sf-border-subtle)',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#ef4444' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--sf-text-3)' }}
          >
            <LogOut size={12} className="flex-shrink-0" />
            {!collapsed && <span>Sair</span>}
          </button>
        </div>
      )}

      {/* Version */}
      <div className="px-4 pb-3 flex-shrink-0">
        <p className="text-[10px]" style={{ color: 'var(--sf-text-4)' }}>v0.58.4</p>
      </div>
    </div>
  )
}
