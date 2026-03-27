/* AuthContext — Contexto de autenticação JWT do Synerium Factory */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { Usuario, PermissaoAcao, PermissoesEfetivas } from '../types'

interface AuthContextValue {
  usuario: Usuario | null
  token: string | null
  autenticado: boolean
  carregando: boolean
  permissoes: PermissoesEfetivas
  temPermissao: (modulo: string, acao: PermissaoAcao) => boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
  atualizarUsuario: (dados: Partial<Usuario>) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>')
  return ctx
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('sf_token'))
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem('sf_refresh'))
  const [carregando, setCarregando] = useState(true)

  /* --- Validar token ao iniciar --- */
  useEffect(() => {
    if (token) {
      validarToken(token)
    } else {
      setCarregando(false)
    }
  }, [])

  async function validarToken(t: string) {
    try {
      const res = await fetch('/api/status', {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (res.ok) {
        // Token válido — extrair dados do JWT
        const payload = JSON.parse(atob(t.split('.')[1]))
        setUsuario({
          id: payload.sub,
          nome: payload.nome,
          email: payload.email,
          cargo: '',
          papeis: payload.papeis || [],
          pode_aprovar: false,
          areas_aprovacao: [],
          ativo: true,
        })
      } else if (res.status === 401 && refreshToken) {
        // Token expirado — tentar refresh
        await tentarRefresh()
      } else {
        limparAuth()
      }
    } catch {
      limparAuth()
    } finally {
      setCarregando(false)
    }
  }

  async function tentarRefresh() {
    if (!refreshToken) return
    try {
      const res = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (res.ok) {
        const data = await res.json()
        salvarToken(data.access_token, refreshToken)
        await validarToken(data.access_token)
      } else {
        limparAuth()
      }
    } catch {
      limparAuth()
    }
  }

  /* --- Login --- */
  const login = useCallback(async (email: string, senha: string) => {
    // Limpar estado antigo ANTES do novo login
    limparAuth()

    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, senha }),
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Erro ao fazer login')
    }

    const data = await res.json()
    salvarToken(data.access_token, data.refresh_token)

    const novoUsuario = {
      id: data.usuario.id,
      nome: data.usuario.nome,
      email: data.usuario.email,
      cargo: data.usuario.cargo,
      papeis: data.usuario.papeis,
      pode_aprovar: data.usuario.pode_aprovar,
      areas_aprovacao: [],
      ativo: true,
      permissoes_efetivas: data.usuario.permissoes_efetivas || {},
    }

    setUsuario(novoUsuario)

    console.log(`[AUTH] Login: ${novoUsuario.nome} (${novoUsuario.email}) — ID: ${novoUsuario.id}`)

    // Forçar reload completo dos dados para o novo usuário
    window.dispatchEvent(new Event('sf-user-changed'))
  }, [])

  /* --- Logout --- */
  const logout = useCallback(() => {
    console.log(`[AUTH] Logout: ${usuario?.nome}`)
    limparAuth()
    // Forçar reload para limpar todo cache de componentes
    window.location.href = '/login'
  }, [usuario])

  /* --- Atualizar dados do usuário localmente --- */
  const atualizarUsuario = useCallback((dados: Partial<Usuario>) => {
    setUsuario((prev) => prev ? { ...prev, ...dados } : null)
  }, [])

  /* --- Permissões efetivas --- */
  const permissoes: PermissoesEfetivas = usuario?.permissoes_efetivas || {}

  const temPermissao = useCallback((modulo: string, acao: PermissaoAcao): boolean => {
    if (!usuario) return false
    // CEO/Diretor/Ops Lead sempre tem tudo
    const papeis = usuario.papeis || []
    if (papeis.some(p => ['ceo', 'diretor_tecnico', 'operations_lead'].includes(p))) return true
    // Verificar permissões efetivas
    const permsModulo = usuario.permissoes_efetivas?.[modulo]
    if (!permsModulo) return false
    return permsModulo[acao] === true
  }, [usuario])

  /* --- Helpers --- */
  function salvarToken(access: string, refresh: string | null) {
    setToken(access)
    localStorage.setItem('sf_token', access)
    if (refresh) {
      setRefreshToken(refresh)
      localStorage.setItem('sf_refresh', refresh)
    }
  }

  function limparAuth() {
    setToken(null)
    setRefreshToken(null)
    setUsuario(null)
    localStorage.removeItem('sf_token')
    localStorage.removeItem('sf_refresh')
  }

  return (
    <AuthContext.Provider
      value={{
        usuario,
        token,
        autenticado: !!usuario,
        carregando,
        permissoes,
        temPermissao,
        login,
        logout,
        atualizarUsuario,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
