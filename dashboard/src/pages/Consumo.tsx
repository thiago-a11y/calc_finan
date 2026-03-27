/* Consumo — Dashboard premium dark-mode (estilo OpenAI / Vercel / Stripe) */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { useAuth } from '../contexts/AuthContext'
import {
  DollarSign, Gauge, ArrowUpRight, Hexagon,
} from 'lucide-react'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Area, AreaChart,
} from 'recharts'

interface ApiDados {
  id: string; nome: string; icone: string; cor: string
  requests: number; tokens_input: number; tokens_output: number
  tokens_total: number; custo_estimado: number; percentual_custo: number
  plano?: string; modelo?: string
}

interface ConsumoData {
  periodo_dias: number; custo_total: number; custo_total_brl: number
  total_requests: number; total_tokens: number; total_registros: number
  apis: ApiDados[]
  historico_diario: { data: string; total_requests: number; total_tokens: number; custo_total: number }[]
  orcamento_mensal_usd: number; orcamento_restante_usd: number; percentual_orcamento: number
  atualizado_em: string
}

const periodos = [
  { label: '7d', valor: 7 },
  { label: '30d', valor: 30 },
  { label: '90d', valor: 90 },
  { label: 'Tudo', valor: 365 },
]

/* Tooltip premium — ultra clean, sem sombra feia */
const PremiumTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: 'var(--sf-bg-tooltip)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--sf-border-default)',
        borderRadius: '12px',
        padding: '12px 16px',
        boxShadow: 'none',
        minWidth: '140px',
      }}
    >
      <p style={{ fontSize: '11px', color: '#6b7280', marginBottom: '8px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
        {label}
      </p>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: i < payload.length - 1 ? '4px' : 0 }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: p.color, flexShrink: 0 }} />
          <span style={{ fontSize: '13px', fontFamily: 'monospace', color: '#f3f4f6', fontWeight: 600 }}>
            {typeof p.value === 'number' && p.value < 1
              ? `$${p.value.toFixed(4)}`
              : typeof p.value === 'number'
              ? p.value.toLocaleString()
              : p.value}
          </span>
          <span style={{ fontSize: '11px', color: '#4b5563' }}>{p.name}</span>
        </div>
      ))}
    </div>
  )
}

export default function Consumo() {
  const { token } = useAuth()
  const [periodo, setPeriodo] = useState(30)

  const fetcher = useCallback(async () => {
    const res = await fetch(`/api/consumo?periodo=${periodo}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Erro')
    return res.json() as Promise<ConsumoData>
  }, [periodo, token])

  const { dados, carregando } = usePolling(fetcher, 60000)

  if (carregando || !dados) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }

  const alertaNivel = dados.percentual_orcamento > 80 ? 'critical' : dados.percentual_orcamento > 50 ? 'warning' : 'healthy'

  return (
    <div className="sf-page">
      {/* Glow sutil no fundo */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-emerald-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Consumo de APIs
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            Monitoramento em tempo real · Atualizado {new Date(dados.atualizado_em).toLocaleTimeString('pt-BR')}
          </p>
        </div>
        <div className="flex gap-1 bg-white/5 backdrop-blur-sm border sf-border rounded-xl p-1">
          {periodos.map(p => (
            <button
              key={p.valor}
              onClick={() => setPeriodo(p.valor)}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-300 ${
                periodo === p.valor
                  ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                  : 'sf-text-dim hover:sf-text-dim hover:bg-white/5'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cards KPI */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {/* Custo Total */}
        <div className="group relative sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6 hover:border-emerald-500/30 transition-all duration-500">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <DollarSign size={14} className="text-emerald-400" strokeWidth={2} />
              </div>
              <p className="text-xs sf-text-dim uppercase tracking-wider">Custo Total</p>
            </div>
            <p className="text-4xl font-bold sf-text-white font-mono tracking-tight">
              ${dados.custo_total.toFixed(2)}
            </p>
            <p className="text-sm sf-text-dim mt-2 font-mono">≈ R${dados.custo_total_brl.toFixed(2)}</p>
          </div>
        </div>

        {/* Gauge Orçamento */}
        <div className={`group relative sf-glass backdrop-blur-sm border rounded-2xl p-6 transition-all duration-500 ${
          alertaNivel === 'critical' ? 'border-red-500/30' :
          alertaNivel === 'warning' ? 'border-amber-500/30' : 'border-white/10 hover:border-emerald-500/30'
        }`}>
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                alertaNivel === 'critical' ? 'bg-red-500/10' :
                alertaNivel === 'warning' ? 'bg-amber-500/10' : 'bg-emerald-500/10'
              }`}>
                <Gauge size={14} className={
                  alertaNivel === 'critical' ? 'text-red-400' :
                  alertaNivel === 'warning' ? 'text-amber-400' : 'text-emerald-400'
                } strokeWidth={2} />
              </div>
              <p className="text-xs sf-text-dim uppercase tracking-wider">Orçamento</p>
            </div>

            {/* Gauge circular mini */}
            <div className="flex items-center gap-4">
              <svg width="64" height="36" viewBox="0 0 64 36" className="overflow-visible">
                <path d="M 6 32 A 26 26 0 0 1 58 32" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" strokeLinecap="round" />
                <path d="M 6 32 A 26 26 0 0 1 58 32" fill="none"
                  stroke={alertaNivel === 'critical' ? '#ef4444' : alertaNivel === 'warning' ? '#f59e0b' : '#10b981'}
                  strokeWidth="5" strokeLinecap="round"
                  strokeDasharray={`${(dados.percentual_orcamento / 100) * 82} 82`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div>
                <p className={`text-3xl font-bold font-mono ${
                  alertaNivel === 'critical' ? 'text-red-400' :
                  alertaNivel === 'warning' ? 'text-amber-400' : 'text-emerald-400'
                }`}>
                  {dados.percentual_orcamento}%
                </p>
                <p className="text-xs sf-text-dim">de ${dados.orcamento_mensal_usd}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Requests */}
        <div className="group relative sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-500">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <ArrowUpRight size={14} className="text-blue-400" strokeWidth={2} />
              </div>
              <p className="text-xs sf-text-dim uppercase tracking-wider">Requests</p>
            </div>
            <p className="text-4xl font-bold sf-text-white font-mono tracking-tight">
              {dados.total_requests.toLocaleString()}
            </p>
            <p className="text-sm sf-text-dim mt-2">{dados.apis.length} providers configurados</p>
          </div>
        </div>

        {/* Tokens */}
        <div className="group relative sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6 hover:border-purple-500/30 transition-all duration-500">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <Hexagon size={14} className="text-purple-400" strokeWidth={2} />
              </div>
              <p className="text-xs sf-text-dim uppercase tracking-wider">Tokens</p>
            </div>
            <p className="text-4xl font-bold sf-text-white font-mono tracking-tight">
              {dados.total_tokens.toLocaleString()}
            </p>
            <p className="text-sm sf-text-dim mt-2">Últimos {dados.periodo_dias} dias</p>
          </div>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Area Chart — Custo por dia (span 2) */}
        <div className="lg:col-span-2 sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-medium sf-text-dim">Custo Diário</h3>
            <span className="text-xs sf-text-ghost font-mono">{dados.periodo_dias} dias</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={dados.historico_diario}>
              <defs>
                <linearGradient id="gradCusto" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="data" tick={{ fontSize: 10, fill: '#4b5563' }} tickFormatter={d => d.slice(5)} axisLine={{ stroke: 'rgba(255,255,255,0.06)' }} />
              <YAxis tick={{ fontSize: 10, fill: '#4b5563' }} tickFormatter={v => `$${v}`} axisLine={{ stroke: 'rgba(255,255,255,0.06)' }} />
              <Tooltip content={<PremiumTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Area type="monotone" dataKey="custo_total" name="Custo" stroke="#10b981" strokeWidth={2} fill="url(#gradCusto)" dot={false} activeDot={{ r: 4, fill: '#10b981', stroke: '#0a0a0f', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart — Distribuição */}
        <div className="sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6">
          <h3 className="text-sm font-medium sf-text-dim mb-6">Distribuição</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={dados.apis}
                dataKey="requests"
                nameKey="nome"
                cx="50%"
                cy="50%"
                outerRadius={80}
                innerRadius={50}
                paddingAngle={3}
                strokeWidth={0}
              >
                {dados.apis.map(api => (
                  <Cell key={api.id} fill={api.cor} />
                ))}
              </Pie>
              <Tooltip content={<PremiumTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            </PieChart>
          </ResponsiveContainer>
          {/* Legenda custom */}
          <div className="flex flex-wrap gap-3 mt-4 justify-center">
            {dados.apis.map(api => (
              <div key={api.id} className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: api.cor }} />
                <span className="text-xs sf-text-dim">{api.nome.split('(')[0].trim()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bar Chart — Requests por Provider (premium) */}
      <div className="sf-glass backdrop-blur-sm border sf-border rounded-2xl p-6 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-sm font-medium sf-text-dim">Requests por Provider</h3>
          <span className="text-xs sf-text-ghost font-mono">{dados.apis.length} providers</span>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={dados.apis} barCategoryGap="15%" barSize={32}>
            <defs>
              {dados.apis.map(api => (
                <linearGradient key={api.id} id={`grad-${api.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={api.cor} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={api.cor} stopOpacity={0.4} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis
              dataKey="nome"
              tick={{ fontSize: 10, fill: '#6b7280' }}
              tickFormatter={n => n.split('(')[0].split(' ')[0].trim()}
              axisLine={false}
              tickLine={false}
              dy={8}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#4b5563' }}
              axisLine={false}
              tickLine={false}
              dx={-4}
            />
            <Tooltip content={<PremiumTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)', radius: 6 }} />
            <Bar dataKey="requests" name="Requests" radius={[8, 8, 2, 2]}>
              {dados.apis.map(api => (
                <Cell key={api.id} fill={`url(#grad-${api.id})`} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Tabela detalhada */}
      <div className="sf-glass backdrop-blur-sm border sf-border rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--sf-border-subtle)' }}>
          <h3 className="text-sm font-medium sf-text-dim">Relatório Detalhado</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs sf-text-ghost uppercase tracking-wider">
                <th className="text-left py-3 px-6">Provider</th>
                <th className="text-right py-3 px-4">Requests</th>
                <th className="text-right py-3 px-4">Tokens In</th>
                <th className="text-right py-3 px-4">Tokens Out</th>
                <th className="text-right py-3 px-4">Total</th>
                <th className="text-right py-3 px-4">Custo</th>
                <th className="text-right py-3 px-4">% Uso</th>
                <th className="text-left py-3 px-4">Modelo</th>
              </tr>
            </thead>
            <tbody>
              {dados.apis.map(api => (
                <tr key={api.id} className="border-t border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
                        style={{ backgroundColor: `${api.cor}15` }}>
                        {api.icone}
                      </div>
                      <div>
                        <p className="font-medium sf-text-white text-sm">{api.nome}</p>
                        <p className="text-xs sf-text-ghost">{api.plano || ''}</p>
                      </div>
                    </div>
                  </td>
                  <td className="text-right py-4 px-4 font-mono sf-text-dim">
                    {api.requests.toLocaleString()}
                  </td>
                  <td className="text-right py-4 px-4 font-mono sf-text-dim text-xs">
                    {api.tokens_input.toLocaleString()}
                  </td>
                  <td className="text-right py-4 px-4 font-mono sf-text-dim text-xs">
                    {api.tokens_output.toLocaleString()}
                  </td>
                  <td className="text-right py-4 px-4 font-mono sf-text-dim">
                    {api.tokens_total.toLocaleString()}
                  </td>
                  <td className="text-right py-4 px-4">
                    <span className="font-mono font-semibold sf-text-white">
                      ${api.custo_estimado.toFixed(4)}
                    </span>
                  </td>
                  <td className="text-right py-4 px-4">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-20 bg-white/5 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full transition-all duration-700"
                          style={{ width: `${Math.min(api.percentual_custo, 100)}%`, backgroundColor: api.cor }}
                        />
                      </div>
                      <span className="text-xs sf-text-dim w-10 text-right font-mono">{api.percentual_custo}%</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className="text-xs sf-text-ghost font-mono">{api.modelo || '-'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t sf-border sf-glass">
                <td className="py-4 px-6 font-semibold sf-text-white">Total</td>
                <td className="text-right py-4 px-4 font-mono sf-text-white font-semibold">{dados.total_requests.toLocaleString()}</td>
                <td colSpan={2}></td>
                <td className="text-right py-4 px-4 font-mono sf-text-white font-semibold">{dados.total_tokens.toLocaleString()}</td>
                <td className="text-right py-4 px-4 font-mono font-bold text-emerald-400">${dados.custo_total.toFixed(4)}</td>
                <td className="text-right py-4 px-4 text-xs sf-text-dim">{dados.percentual_orcamento}%</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Rodapé */}
      <p className="text-xs sf-text-faint mt-6 text-center font-mono">
        Câmbio: $1 = R$5,10 · Orçamento: ${dados.orcamento_mensal_usd}/mês · Restante: ${dados.orcamento_restante_usd.toFixed(2)}
      </p>
    </div>
  )
}
