/* App principal — Roteamento com autenticação */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import PainelGeral from './pages/PainelGeral'
import Aprovacoes from './pages/Aprovacoes'
import Squads from './pages/Squads'
import RAG from './pages/RAG'
import Standup from './pages/Standup'
import Equipe from './pages/Equipe'
import Perfil from './pages/Perfil'
import Configuracoes from './pages/Configuracoes'
import Agente from './pages/Agente'
import Registrar from './pages/Registrar'
import ThemeToggle from './components/ThemeToggle'
import { ChatProvider } from './components/ChatManager'
import Relatorios from './pages/Relatorios'
import Escritorio from './pages/Escritorio'
import Skills from './pages/Skills'
import Projetos from './pages/Projetos'
import Consumo from './pages/Consumo'
import Deploy from './pages/Deploy'
import LLMProviders from './pages/LLMProviders'

/* Rota protegida — redireciona para /login se não autenticado */
function RotaProtegida({ children }: { children: React.ReactNode }) {
  const { autenticado, carregando } = useAuth()

  if (carregando) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
      </div>
    )
  }

  if (!autenticado) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

/* Layout principal com sidebar — usa tema dinâmico */
function LayoutPrincipal({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen" style={{ background: 'var(--sf-bg-primary)' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header com ThemeToggle */}
        <header
          className="flex items-center justify-end px-6 py-3 shrink-0"
          style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}
        >
          <ThemeToggle />
        </header>
        <main
          className="flex-1 p-6 overflow-y-auto transition-colors duration-300"
          style={{ color: 'var(--sf-text-primary)' }}
        >
          {children}
        </main>
      </div>
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      {/* Rotas públicas */}
      <Route path="/login" element={<Login />} />
      <Route path="/registrar" element={<Registrar />} />

      {/* Rotas protegidas */}
      <Route
        path="/"
        element={
          <RotaProtegida>
            <LayoutPrincipal><PainelGeral /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/aprovacoes"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Aprovacoes /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/squads"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Squads /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/rag"
        element={
          <RotaProtegida>
            <LayoutPrincipal><RAG /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/standup"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Standup /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/equipe"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Equipe /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/perfil"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Perfil /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/configuracoes"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Configuracoes /></LayoutPrincipal>
          </RotaProtegida>
        }
      />

      <Route
        path="/escritorio"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Escritorio /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/projetos"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Projetos /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/deploy"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Deploy /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/consumo"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Consumo /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/llm-providers"
        element={
          <RotaProtegida>
            <LayoutPrincipal><LLMProviders /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/relatorios"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Relatorios /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/skills"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Skills /></LayoutPrincipal>
          </RotaProtegida>
        }
      />
      <Route
        path="/agente"
        element={
          <RotaProtegida>
            <LayoutPrincipal><Agente /></LayoutPrincipal>
          </RotaProtegida>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <ChatProvider>
            <AppRoutes />
          </ChatProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
