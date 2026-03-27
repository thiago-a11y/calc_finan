/* Perfil — Página de perfil do usuário autenticado */

import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function Perfil() {
  const { usuario, token, atualizarUsuario } = useAuth()
  const [editando, setEditando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [mensagem, setMensagem] = useState('')

  const [nome, setNome] = useState(usuario?.nome || '')
  const [cargo, setCargo] = useState(usuario?.cargo || '')

  // Trocar senha
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [salvandoSenha, setSalvandoSenha] = useState(false)

  if (!usuario) return null

  const papelLabel: Record<string, string> = {
    ceo: 'CEO',
    diretor_tecnico: 'Diretor Técnico',
    operations_lead: 'Operations Lead',
    pm_central: 'PM Central',
    lider: 'Líder',
    membro: 'Membro',
  }

  const salvar = async () => {
    setSalvando(true)
    setMensagem('')
    try {
      const res = await fetch('/api/usuarios/perfil', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ nome, cargo }),
      })

      if (res.ok) {
        atualizarUsuario({ nome, cargo })
        setEditando(false)
        setMensagem('Perfil atualizado com sucesso!')
      } else {
        setMensagem('Erro ao salvar perfil.')
      }
    } catch {
      setMensagem('Erro de conexão.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="sf-animate-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold sf-text">Meu Perfil</h2>
        <p className="text-sm sf-text-muted">Gerencie suas informações pessoais</p>
      </div>

      {mensagem && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${
          mensagem.includes('sucesso')
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {mensagem}
        </div>
      )}

      <div className="sf-card sf-border rounded-xl p-6 max-w-2xl">
        {/* Avatar + Nome */}
        <div className="flex items-center gap-5 mb-6 pb-6" style={{ borderBottom: '1px solid var(--sf-border)' }}>
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center text-3xl font-bold text-emerald-700">
            {usuario.nome[0]}
          </div>
          <div>
            <h3 className="text-xl font-semibold sf-text">{usuario.nome}</h3>
            <p className="text-sm sf-text-muted">{usuario.email}</p>
            <div className="flex gap-1.5 mt-2">
              {usuario.papeis.map((papel) => (
                <span
                  key={papel}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700"
                >
                  {papelLabel[papel] || papel}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Dados editáveis */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium sf-text-secondary mb-1">Nome</label>
            {editando ? (
              <input
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                className="w-full sf-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            ) : (
              <p className="sf-text">{usuario.nome}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium sf-text-secondary mb-1">Cargo</label>
            {editando ? (
              <input
                value={cargo}
                onChange={(e) => setCargo(e.target.value)}
                className="w-full sf-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            ) : (
              <p className="sf-text">{usuario.cargo || 'Não definido'}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium sf-text-secondary mb-1">Email</label>
            <p className="sf-text font-mono text-sm">{usuario.email}</p>
          </div>

          <div>
            <label className="block text-sm font-medium sf-text-secondary mb-1">Pode aprovar</label>
            <p className="sf-text">{usuario.pode_aprovar ? 'Sim' : 'Não'}</p>
          </div>
        </div>

        {/* Botões */}
        <div className="mt-6 pt-4 flex gap-3" style={{ borderTop: '1px solid var(--sf-border)' }}>
          {editando ? (
            <>
              <button
                onClick={salvar}
                disabled={salvando}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                {salvando ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                onClick={() => { setEditando(false); setNome(usuario.nome); setCargo(usuario.cargo) }}
                className="px-4 py-2 sf-text rounded-lg text-sm" style={{ background: 'var(--sf-bg-input)' }}
              >
                Cancelar
              </button>
            </>
          ) : (
            <button
              onClick={() => setEditando(true)}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700"
            >
              Editar Perfil
            </button>
          )}
        </div>
      </div>

      {/* Trocar Senha */}
      <div className="sf-card sf-border rounded-xl p-6 max-w-2xl mt-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold sf-text">Segurança</h3>
            <p className="text-sm sf-text-muted">Altere sua senha de acesso</p>
          </div>
          {!mostrarSenha && (
            <button
              onClick={() => setMostrarSenha(true)}
              className="px-4 py-2 sf-text rounded-lg text-sm" style={{ background: 'var(--sf-bg-input)' }}
            >
              Trocar Senha
            </button>
          )}
        </div>

        {mostrarSenha && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium sf-text-secondary mb-1">Senha atual</label>
              <input
                type="password"
                value={senhaAtual}
                onChange={(e) => setSenhaAtual(e.target.value)}
                placeholder="Digite sua senha atual"
                className="w-full sf-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium sf-text-secondary mb-1">Nova senha</label>
              <input
                type="password"
                value={novaSenha}
                onChange={(e) => setNovaSenha(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="w-full sf-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium sf-text-secondary mb-1">Confirmar nova senha</label>
              <input
                type="password"
                value={confirmarSenha}
                onChange={(e) => setConfirmarSenha(e.target.value)}
                placeholder="Repita a nova senha"
                className="w-full sf-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
                style={{ background: 'var(--sf-bg-input)' }}
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={async () => {
                  if (novaSenha !== confirmarSenha) {
                    setMensagem('As senhas não coincidem.')
                    return
                  }
                  if (novaSenha.length < 8) {
                    setMensagem('A nova senha deve ter no mínimo 8 caracteres.')
                    return
                  }
                  setSalvandoSenha(true)
                  setMensagem('')
                  try {
                    const res = await fetch('/auth/trocar-senha', {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify({
                        senha_atual: senhaAtual,
                        nova_senha: novaSenha,
                      }),
                    })
                    const data = await res.json()
                    if (res.ok) {
                      setMensagem('Senha alterada com sucesso!')
                      setMostrarSenha(false)
                      setSenhaAtual('')
                      setNovaSenha('')
                      setConfirmarSenha('')
                    } else {
                      setMensagem(data.detail || 'Erro ao trocar senha.')
                    }
                  } catch {
                    setMensagem('Erro de conexão.')
                  } finally {
                    setSalvandoSenha(false)
                  }
                }}
                disabled={salvandoSenha || !senhaAtual || !novaSenha || !confirmarSenha}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                {salvandoSenha ? 'Salvando...' : 'Alterar Senha'}
              </button>
              <button
                onClick={() => {
                  setMostrarSenha(false)
                  setSenhaAtual('')
                  setNovaSenha('')
                  setConfirmarSenha('')
                }}
                className="px-4 py-2 sf-text rounded-lg text-sm" style={{ background: 'var(--sf-bg-input)' }}
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
