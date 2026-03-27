/* Login — Tela de autenticação do Synerium Factory */

import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [entrando, setEntrando] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErro('')
    setEntrando(true)

    try {
      await login(email, senha)
      navigate('/')
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao fazer login')
    } finally {
      setEntrando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--sf-bg-main, #111827)' }}>
      <div className="w-full max-w-md sf-animate-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-emerald-400">Synerium Factory</h1>
          <p className="sf-text-muted mt-2">Centro de Comando — Objetiva Solução</p>
        </div>

        {/* Card de login */}
        <div className="sf-card rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold sf-text mb-6">Entrar</h2>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
              {erro}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium sf-text-secondary mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoFocus
                className="w-full sf-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            </div>

            <div>
              <label className="block text-sm font-medium sf-text-secondary mb-1.5">Senha</label>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="Sua senha"
                required
                className="w-full sf-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            </div>

            <button
              type="submit"
              disabled={entrando}
              className="w-full bg-emerald-600 text-white py-2.5 rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {entrando ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>

        <p className="text-center sf-text-muted text-xs mt-6">
          v0.3.0 — Synerium Factory by Objetiva Solução
        </p>
      </div>
    </div>
  )
}
