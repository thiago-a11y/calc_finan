/* Mission Control — VERSÃO MINIMALISTA PARA DEBUG
 * v0.58.16-debug
 * Removeu todos os paineis complexos para isolar erro #310
 */

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useParams, useNavigate } from 'react-router-dom'
import { Rocket, Loader2 } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

interface Sessao {
  sessao_id: string; titulo: string; status: string; projeto_id: number | null
  agentes_ativos: Array<{
    id: string; nome: string; status: string; tarefa: string; tipo: string; inicio: string
  }>
  artifacts: Array<{ artifact_id: string; tipo: string; titulo: string }>
  total_artifacts: number; total_comandos: number
}

interface SessaoResumo {
  sessao_id: string; titulo: string; status: string
  total_artifacts: number; total_comandos: number
  atualizado_em: string | null
}

export default function MissionControl() {
  const { token } = useAuth()
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()

  const [sessao, setSessao] = useState<Sessao | null>(null)
  const [sessoes, setSessoes] = useState<SessaoResumo[]>([])
  const [carregandoSessoes, setCarregandoSessoes] = useState(true)
  const [criando, setCriando] = useState(false)
  const [titulo, setTitulo] = useState('')

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  function tempoRelativo(iso: string | null): string {
    if (!iso) return ''
    const diff = Date.now() - new Date(iso).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return 'agora'
    if (min < 60) return `${min}min`
    const h = Math.floor(min / 60)
    if (h < 24) return `${h}h`
    return `${Math.floor(h / 24)}d`
  }

  const carregarSessoes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/mission-control/sessoes`, { headers })
      if (res.ok) setSessoes(await res.json())
    } catch { /* */ } finally { setCarregandoSessoes(false) }
  }, [headers])

  const criarSessao = useCallback(async () => {
    setCriando(true)
    try {
      const res = await fetch(`${API}/api/mission-control/sessao`, {
        method: 'POST', headers,
        body: JSON.stringify({ titulo: titulo || 'Nova Sessao Mission Control' }),
      })
      const data = await res.json()
      navigate(`/mission-control/${data.sessao_id}`, { replace: true })
    } catch { /* */ } finally { setCriando(false) }
  }, [headers, titulo, navigate])

  /* ============================================================
     Startup
   ============================================================ */

  useEffect(() => {
    if (urlSessionId) {
      fetch(`${API}/api/mission-control/sessao/${urlSessionId}`, { headers })
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setSessao(data) })
        .catch(() => {})
        .finally(() => setCarregandoSessoes(false))
    } else {
      carregarSessoes()
    }
  }, [urlSessionId])

  /* ============================================================
     Render: Lista de sessoes
   ============================================================ */

  if (!sessao && !urlSessionId) {
    return (
      <div className="h-full overflow-auto p-8" style={{ background: 'var(--sf-bg-primary)' }}>
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl font-bold mb-6" style={{ color: 'var(--sf-text)' }}>Mission Control</h1>
          <div className="flex gap-2 mb-6">
            <input type="text" placeholder="Nome da sessao" value={titulo}
              onChange={e => setTitulo(e.target.value)} onKeyDown={e => e.key === 'Enter' && criarSessao()}
              className="flex-1 px-4 py-2 rounded-lg text-sm"
              style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)', color: 'var(--sf-text)' }} />
            <button onClick={criarSessao} disabled={criando}
              className="px-4 py-2 rounded-lg font-medium text-white" style={{ background: 'var(--sf-accent)' }}>
              {criando ? '...' : 'Nova'}
            </button>
          </div>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--sf-text-secondary)' }}>Sessoes</h2>
          {carregandoSessoes ? (
            <p style={{ color: 'var(--sf-text-secondary)' }}>Carregando...</p>
          ) : sessoes.length === 0 ? (
            <p style={{ color: 'var(--sf-text-secondary)' }}>Nenhuma sessao.</p>
          ) : (
            <div className="space-y-2">
              {sessoes.map(s => (
                <div key={s.sessao_id} onClick={() => navigate(`/mission-control/${s.sessao_id}`)}
                  className="p-4 rounded-lg cursor-pointer"
                  style={{ background: 'var(--sf-bg-card)', border: '1px solid var(--sf-border-subtle)' }}>
                  <p className="text-sm font-medium" style={{ color: 'var(--sf-text)' }}>{s.titulo}</p>
                  <p className="text-xs" style={{ color: 'var(--sf-text-secondary)' }}>
                    {s.total_artifacts} artifacts - {tempoRelativo(s.atualizado_em)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  /* ============================================================
     Render: Sessao carregando
   ============================================================ */

  if (!sessao && urlSessionId) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: 'var(--sf-bg-primary)' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--sf-accent)' }} />
      </div>
    )
  }

  /* ============================================================
     Render: Painel da sessao — MINIMALISTA
   ============================================================ */

  return (
    <div className="h-full flex flex-col" style={{ background: 'var(--sf-bg-primary)' }}>
      <header className="flex items-center gap-3 px-4 py-3"
        style={{ background: 'var(--sf-bg-card)', borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <button onClick={() => { setSessao(null); navigate('/mission-control') }}>
          <Rocket className="w-5 h-5" style={{ color: 'var(--sf-accent)' }} />
        </button>
        <span className="font-bold text-sm" style={{ color: 'var(--sf-text)' }}>{sessao?.titulo}</span>
      </header>

      <div className="flex-1 p-8">
        <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--sf-text)' }}>
          Sessao: {sessao?.titulo}
        </h2>
        <p style={{ color: 'var(--sf-text-secondary)' }}>
          Agentes: {sessao?.agentes_ativos?.length || 0}
        </p>
        <p style={{ color: 'var(--sf-text-secondary)' }}>
          Artifacts: {sessao?.total_artifacts || 0}
        </p>
        <p style={{ color: 'var(--sf-text-secondary)' }}>
          Comandos: {sessao?.total_comandos || 0}
        </p>
      </div>
    </div>
  )
}
