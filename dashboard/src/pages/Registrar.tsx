/* Registrar — Página de aceitar convite e criar senha */

import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { UserPlus, AlertCircle, CheckCircle2, Lock, Eye, EyeOff } from 'lucide-react'

export default function Registrar() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') || ''

  const [fase, setFase] = useState<'validando' | 'form' | 'sucesso' | 'erro'>('validando')
  const [convite, setConvite] = useState<{ email: string; nome: string; cargo: string } | null>(null)
  const [erro, setErro] = useState('')

  const [nome, setNome] = useState('')
  const [senha, setSenha] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [salvando, setSalvando] = useState(false)

  // Validar token ao carregar
  useEffect(() => {
    if (!token) { setErro('Token não fornecido.'); setFase('erro'); return }

    fetch(`/api/convites/${token}`)
      .then(async r => {
        if (!r.ok) {
          const d = await r.json().catch(() => ({ detail: 'Convite inválido' }))
          throw new Error(d.detail)
        }
        return r.json()
      })
      .then(data => {
        setConvite(data)
        setNome(data.nome || '')
        setFase('form')
      })
      .catch(e => {
        setErro(e.message)
        setFase('erro')
      })
  }, [token])

  const registrar = async () => {
    if (senha.length < 8) { setErro('A senha deve ter no mínimo 8 caracteres.'); return }
    if (senha !== confirmar) { setErro('As senhas não coincidem.'); return }

    setSalvando(true)
    setErro('')

    try {
      const res = await fetch('/auth/registrar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, nome, senha }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: 'Erro ao registrar' }))
        throw new Error(data.detail)
      }

      setFase('sucesso')
      setTimeout(() => navigate('/login'), 3000)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro desconhecido')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ background: 'var(--sf-bg-primary, #0a0a0f)' }}>

      {/* Logo */}
      <h1 className="text-3xl font-bold text-emerald-400 mb-2">Synerium Factory</h1>
      <p className="text-sm mb-8" style={{ color: 'var(--sf-text-3, #888)' }}>
        Centro de Comando — Objetiva Solução
      </p>

      <div className="w-full max-w-md rounded-2xl p-8"
        style={{ background: 'var(--sf-bg-1, #111)', border: '1px solid var(--sf-border-default, #222)' }}>

        {/* VALIDANDO */}
        {fase === 'validando' && (
          <div className="flex flex-col items-center py-8">
            <div className="w-10 h-10 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
            <p style={{ color: 'var(--sf-text-2, #aaa)' }} className="text-sm">Validando convite...</p>
          </div>
        )}

        {/* ERRO */}
        {fase === 'erro' && (
          <div className="flex flex-col items-center py-8">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
              <AlertCircle size={28} className="text-red-400" />
            </div>
            <h2 className="text-lg font-semibold text-red-400 mb-2">Convite inválido</h2>
            <p className="text-sm text-center" style={{ color: 'var(--sf-text-3, #888)' }}>{erro}</p>
            <button onClick={() => navigate('/login')}
              className="mt-6 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm border border-emerald-500/20 hover:bg-emerald-500/30 transition-all">
              Ir para Login
            </button>
          </div>
        )}

        {/* FORMULÁRIO */}
        {fase === 'form' && convite && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
                <UserPlus size={18} className="text-emerald-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--sf-text-0, #f8f8f8)' }}>
                  Criar sua conta
                </h2>
                <p className="text-xs" style={{ color: 'var(--sf-text-3, #888)' }}>
                  Convite para {convite.email}
                </p>
              </div>
            </div>

            {erro && (
              <div className="mb-4 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertCircle size={12} /> {erro}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--sf-text-2, #aaa)' }}>Nome</label>
                <input value={nome} onChange={e => setNome(e.target.value)}
                  placeholder="Seu nome completo"
                  className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-colors"
                  style={{ background: 'var(--sf-bg-hover, #1a1a1a)', border: '1px solid var(--sf-border-default, #222)', color: 'var(--sf-text-0, #f8f8f8)' }} />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--sf-text-2, #aaa)' }}>Email</label>
                <input value={convite.email} disabled
                  className="w-full px-4 py-2.5 rounded-xl text-sm opacity-60 cursor-not-allowed"
                  style={{ background: 'var(--sf-bg-hover, #1a1a1a)', border: '1px solid var(--sf-border-default, #222)', color: 'var(--sf-text-0, #f8f8f8)' }} />
              </div>

              <div className="relative">
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--sf-text-2, #aaa)' }}>Senha</label>
                <div className="relative">
                  <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--sf-text-4, #555)' }} />
                  <input type={mostrarSenha ? 'text' : 'password'} value={senha} onChange={e => setSenha(e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl text-sm outline-none transition-colors"
                    style={{ background: 'var(--sf-bg-hover, #1a1a1a)', border: '1px solid var(--sf-border-default, #222)', color: 'var(--sf-text-0, #f8f8f8)' }} />
                  <button type="button" onClick={() => setMostrarSenha(!mostrarSenha)}
                    className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--sf-text-4, #555)' }}>
                    {mostrarSenha ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--sf-text-2, #aaa)' }}>Confirmar senha</label>
                <input type="password" value={confirmar} onChange={e => setConfirmar(e.target.value)}
                  placeholder="Repita a senha"
                  className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-colors"
                  style={{ background: 'var(--sf-bg-hover, #1a1a1a)', border: '1px solid var(--sf-border-default, #222)', color: 'var(--sf-text-0, #f8f8f8)' }} />
              </div>

              <button onClick={registrar} disabled={salvando || !nome || !senha || !confirmar}
                className="w-full py-3 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
                {salvando ? 'Criando conta...' : 'Criar conta e entrar'}
              </button>
            </div>
          </div>
        )}

        {/* SUCESSO */}
        {fase === 'sucesso' && (
          <div className="flex flex-col items-center py-8">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
              <CheckCircle2 size={28} className="text-emerald-400" />
            </div>
            <h2 className="text-lg font-semibold text-emerald-400 mb-2">Conta criada!</h2>
            <p className="text-sm text-center" style={{ color: 'var(--sf-text-3, #888)' }}>
              Redirecionando para o login em 3 segundos...
            </p>
          </div>
        )}
      </div>

      <p className="text-[10px] mt-6" style={{ color: 'var(--sf-text-4, #444)' }}>
        Synerium Factory by Objetiva Solução
      </p>
    </div>
  )
}
