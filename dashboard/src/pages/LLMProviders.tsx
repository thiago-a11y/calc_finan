/* LLM Providers — Premium dark dashboard inspired by Linear/Vercel */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import {
  Brain, Zap, Flame, Network, ChevronRight, Play,
  Star, Check, X, Clock, Hash, ArrowRight, Loader2,
  ToggleLeft, ToggleRight, AlertCircle, Info, Coins,
} from 'lucide-react'

interface Provider {
  id: string; nome: string; icone: string; modelo: string
  ativo: boolean; configurado: boolean
  total_chamadas: number; total_erros: number; total_tokens: number
  custo_estimado: number; latencia_media_ms: number
  ultimo_uso: string | null; ultimo_erro: string | null
}

interface LLMStatus {
  provider_padrao: string; providers: Provider[]
  total_providers: number; providers_ativos: number
}

interface TesteResult {
  provider: string; modelo: string
  resposta: string | null; erro: string | null
  latencia_ms: number; status: string
}

/* Mapeamento de ícones e cores por provider */
const providerConfig: Record<string, {
  Icon: typeof Brain; cor: string; label: string; num: number
}> = {
  anthropic: { Icon: Brain, cor: '#d97706', label: 'Principal', num: 1 },
  groq: { Icon: Zap, cor: '#10b981', label: 'Fallback 1', num: 2 },
  fireworks: { Icon: Flame, cor: '#ef4444', label: 'Fallback 2', num: 3 },
  together: { Icon: Network, cor: '#8b5cf6', label: 'Fallback 3', num: 4 },
}

export default function LLMProviders() {
  const { token } = useAuth()
  const [testando, setTestando] = useState<string | null>(null)
  const [resultadoTeste, setResultadoTeste] = useState<TesteResult | null>(null)
  const [trocando, setTrocando] = useState(false)

  const fetcher = useCallback(async () => {
    const res = await fetch('/api/llm/status', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Erro')
    return res.json() as Promise<LLMStatus>
  }, [token])

  const { dados, carregando, recarregar } = usePolling(fetcher, 30000)

  const testarProvider = async (providerId: string) => {
    setTestando(providerId)
    setResultadoTeste(null)
    try {
      const res = await fetch('/api/llm/testar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          provider_id: providerId,
          prompt: 'Responda em uma frase curta em portugues: Quem e voce e qual seu modelo?',
        }),
      })
      setResultadoTeste(await res.json() as TesteResult)
    } catch {
      setResultadoTeste({ provider: providerId, modelo: '', resposta: null, erro: 'Erro de conexao', latencia_ms: 0, status: 'erro' })
    } finally {
      setTestando(null)
    }
  }

  const trocarPadrao = async (providerId: string) => {
    setTrocando(true)
    try {
      await fetch('/api/llm/provider-padrao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ provider_id: providerId }),
      })
      recarregar()
    } finally { setTrocando(false) }
  }

  const toggleAtivo = async (providerId: string, ativo: boolean) => {
    await fetch('/api/llm/ativar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ provider_id: providerId, ativo }),
    })
    recarregar()
  }

  if (carregando || !dados) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={20} className="animate-spin" style={{ color: 'var(--sf-text-3)' }} />
      </div>
    )
  }

  return (
    <div className="sf-animate">
      {/* Header */}
      <div className="mb-8">
        <h1 className="sf-h1">LLM Providers</h1>
        <p className="sf-caption mt-1">
          {dados.providers_ativos}/{dados.total_providers} ativos · Padrao: {dados.provider_padrao}
        </p>
      </div>

      {/* Fallback Chain */}
      <div className="sf-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <ArrowRight size={14} strokeWidth={1.8} style={{ color: 'var(--sf-text-3)' }} />
          <h2 className="sf-h3">Cadeia de Fallback</h2>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {dados.providers.map((p, idx) => {
            const cfg = providerConfig[p.id] || providerConfig.anthropic
            const isPadrao = p.id === dados.provider_padrao
            const IconComp = cfg.Icon
            return (
              <div key={p.id} className="flex items-center gap-2">
                <div
                  className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl transition-all"
                  style={{
                    background: isPadrao ? `${cfg.cor}12` : 'var(--sf-bg-3)',
                    border: `1px solid ${isPadrao ? `${cfg.cor}30` : 'var(--sf-border-subtle)'}`,
                    opacity: p.ativo && p.configurado ? 1 : 0.4,
                  }}
                >
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: `${cfg.cor}18` }}
                  >
                    <IconComp size={14} strokeWidth={1.8} style={{ color: cfg.cor }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[12px] font-medium" style={{ color: 'var(--sf-text-1)' }}>
                        {p.nome.split('(')[0].split('via')[0].trim()}
                      </span>
                      {isPadrao && (
                        <span
                          className="sf-badge"
                          style={{ background: `${cfg.cor}20`, color: cfg.cor, border: `1px solid ${cfg.cor}25` }}
                        >
                          Padrao
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                        #{cfg.num} {cfg.label}
                      </span>
                      {p.configurado
                        ? <Check size={10} style={{ color: '#10b981' }} />
                        : <X size={10} style={{ color: '#ef4444' }} />
                      }
                    </div>
                  </div>
                </div>
                {idx < dados.providers.length - 1 && (
                  <ChevronRight size={14} style={{ color: 'var(--sf-text-4)' }} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Provider Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        {dados.providers.map(p => {
          const cfg = providerConfig[p.id] || providerConfig.anthropic
          const isPadrao = p.id === dados.provider_padrao
          const IconComp = cfg.Icon

          return (
            <div
              key={p.id}
              className="sf-card p-5 transition-all"
              style={{
                borderColor: isPadrao ? `${cfg.cor}30` : undefined,
              }}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: `${cfg.cor}12` }}
                  >
                    <IconComp size={18} strokeWidth={1.8} style={{ color: cfg.cor }} />
                  </div>
                  <div>
                    <h3 className="text-[14px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
                      {p.nome}
                    </h3>
                    <p className="text-[11px] sf-mono" style={{ color: 'var(--sf-text-3)' }}>
                      {p.modelo}
                    </p>
                  </div>
                </div>
                {/* Toggle */}
                <button
                  onClick={() => toggleAtivo(p.id, !p.ativo)}
                  style={{ color: p.ativo ? '#10b981' : 'var(--sf-text-4)' }}
                >
                  {p.ativo
                    ? <ToggleRight size={28} strokeWidth={1.5} />
                    : <ToggleLeft size={28} strokeWidth={1.5} />
                  }
                </button>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                {[
                  { label: 'Chamadas', valor: p.total_chamadas, Icon: Hash },
                  { label: 'Latencia', valor: p.latencia_media_ms > 0 ? `${p.latencia_media_ms.toFixed(0)}ms` : '—', Icon: Clock },
                  { label: 'Custo', valor: `$${p.custo_estimado.toFixed(4)}`, Icon: Coins },
                ].map(m => (
                  <div
                    key={m.label}
                    className="rounded-lg p-2.5 text-center"
                    style={{ background: 'var(--sf-bg-3)' }}
                  >
                    <p className="text-[15px] font-semibold sf-mono" style={{ color: 'var(--sf-text-0)' }}>
                      {m.valor}
                    </p>
                    <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>{m.label}</p>
                  </div>
                ))}
              </div>

              {/* Status */}
              <div className="flex items-center gap-2 mb-4">
                {p.configurado ? (
                  <span className="sf-badge" style={{ background: 'rgba(16,185,129,0.1)', color: '#34d399', border: '1px solid rgba(16,185,129,0.15)' }}>
                    <div className="sf-dot sf-dot-green" /> API Key OK
                  </span>
                ) : (
                  <span className="sf-badge" style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.15)' }}>
                    <div className="sf-dot sf-dot-red" /> Sem Key
                  </span>
                )}
                {p.total_erros > 0 && (
                  <span className="sf-badge" style={{ background: 'rgba(239,68,68,0.08)', color: '#f87171', border: '1px solid rgba(239,68,68,0.12)' }}>
                    <AlertCircle size={10} /> {p.total_erros} erros
                  </span>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => testarProvider(p.id)}
                  disabled={testando === p.id || !p.configurado || !p.ativo}
                  className="sf-btn sf-btn-ghost flex-1 text-[12px]"
                >
                  {testando === p.id
                    ? <><Loader2 size={12} className="animate-spin" /> Testando...</>
                    : <><Play size={12} /> Testar</>
                  }
                </button>
                {!isPadrao && p.configurado && p.ativo ? (
                  <button
                    onClick={() => trocarPadrao(p.id)}
                    disabled={trocando}
                    className="sf-btn sf-btn-primary flex-1 text-[12px]"
                  >
                    <Star size={12} /> Definir Padrao
                  </button>
                ) : isPadrao ? (
                  <span
                    className="sf-btn flex-1 text-[12px] cursor-default"
                    style={{
                      background: `${cfg.cor}12`,
                      color: cfg.cor,
                      border: `1px solid ${cfg.cor}20`,
                    }}
                  >
                    <Star size={12} /> Padrao Atual
                  </span>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>

      {/* Test Result */}
      {resultadoTeste && (
        <div
          className="sf-card p-5 mb-6"
          style={{
            borderColor: resultadoTeste.status === 'ok' ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)',
          }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {resultadoTeste.status === 'ok'
                ? <Check size={16} style={{ color: '#10b981' }} />
                : <X size={16} style={{ color: '#ef4444' }} />
              }
              <h3 className="sf-h3">
                {resultadoTeste.status === 'ok' ? 'Teste OK' : 'Teste Falhou'} — {resultadoTeste.provider}
              </h3>
            </div>
            {resultadoTeste.latencia_ms > 0 && (
              <span className="sf-caption sf-mono">{resultadoTeste.latencia_ms.toFixed(0)}ms</span>
            )}
          </div>
          {resultadoTeste.resposta && (
            <div className="rounded-lg p-3 text-[13px]" style={{ background: 'var(--sf-bg-3)', color: 'var(--sf-text-2)' }}>
              <p className="sf-caption mb-1">Resposta:</p>
              {resultadoTeste.resposta}
            </div>
          )}
          {resultadoTeste.erro && (
            <div className="rounded-lg p-3 text-[13px]" style={{ background: 'rgba(239,68,68,0.06)', color: '#f87171' }}>
              <p className="sf-caption mb-1" style={{ color: '#ef4444' }}>Erro:</p>
              {resultadoTeste.erro}
            </div>
          )}
          <button onClick={() => setResultadoTeste(null)} className="sf-caption mt-3 hover:underline" style={{ color: 'var(--sf-text-3)' }}>
            Fechar
          </button>
        </div>
      )}

      {/* Info */}
      <div className="sf-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <Info size={14} strokeWidth={1.8} style={{ color: 'var(--sf-text-3)' }} />
          <h2 className="sf-h3">Como funciona</h2>
        </div>
        <div className="space-y-1.5">
          {[
            'O sistema tenta usar o provider padrao configurado',
            'Se falhar (timeout, erro, rate limit), tenta o proximo na cadeia',
            'Providers Llama (Groq, Fireworks, Together) sao mais baratos para tarefas simples',
            'Claude (Anthropic) oferece melhor qualidade para tarefas complexas',
            'Voce pode trocar o padrao ou desativar providers a qualquer momento',
          ].map((text, i) => (
            <p key={i} className="text-[12px] flex items-start gap-2" style={{ color: 'var(--sf-text-2)' }}>
              <span className="sf-mono text-[10px] mt-0.5" style={{ color: 'var(--sf-text-3)' }}>{i + 1}.</span>
              {text}
            </p>
          ))}
        </div>
      </div>
    </div>
  )
}
