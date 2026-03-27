/* Standup — Relatório diário premium dark-mode (zero emojis) */

import { useState } from 'react'
import { gerarStandup } from '../services/api'
import type { StandupRelatorio } from '../types'
import {
  ClipboardList, Play, Loader2, Calendar, Users, XCircle,
  FileText,
} from 'lucide-react'

export default function Standup() {
  const [relatorio, setRelatorio] = useState<StandupRelatorio | null>(null)
  const [gerando, setGerando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const executar = async () => {
    setGerando(true); setErro(null)
    try { setRelatorio(await gerarStandup()) }
    catch (e) { setErro(e instanceof Error ? e.message : 'Erro desconhecido') }
    finally { setGerando(false) }
  }

  return (
    <div className="sf-page">
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-amber-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Standup Diário
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            Relatório compilando status de todos os squads
          </p>
        </div>
        <button
          onClick={executar}
          disabled={gerando}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
            gerando
              ? 'bg-white/5 text-gray-500 border border-white/10 cursor-wait'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/30 hover:shadow-lg hover:shadow-emerald-500/10'
          }`}
        >
          {gerando
            ? <><Loader2 size={14} className="animate-spin" /> Gerando...</>
            : <><Play size={14} /> Gerar Standup</>
          }
        </button>
      </div>

      {/* Loading state — elegante */}
      {gerando && (
        <div className="sf-glass border sf-border rounded-2xl p-8 text-center">
          <div className="relative w-16 h-16 mx-auto mb-5">
            <div className="absolute inset-0 border-2 border-emerald-500/20 rounded-full" />
            <div className="absolute inset-0 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <ClipboardList size={20} className="text-emerald-400" strokeWidth={1.5} />
            </div>
          </div>
          <p className="sf-text-white text-lg font-medium mb-2">Gerando relatório...</p>
          <p className="sf-text-dim text-sm">
            Os agentes estão compilando o status de todos os squads.
            <br />Isso pode levar 10–30 segundos.
          </p>
          <div className="mt-5 w-48 h-1 bg-white/5 rounded-full mx-auto overflow-hidden">
            <div className="h-full bg-emerald-500/50 rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      )}

      {/* Erro */}
      {erro && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
          <XCircle size={16} className="text-red-400 shrink-0" />
          <span className="text-sm text-red-300">Erro ao gerar standup: {erro}</span>
        </div>
      )}

      {/* Relatório gerado */}
      {relatorio && !gerando && (
        <div className="sf-glass border sf-border rounded-2xl overflow-hidden">
          {/* Header do relatório */}
          <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--sf-border-subtle)' }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <FileText size={16} className="text-emerald-400" strokeWidth={1.8} />
              </div>
              <h3 className="text-lg font-semibold sf-text-white">Relatório</h3>
            </div>
            <div className="flex items-center gap-4 text-xs sf-text-dim">
              <span className="flex items-center gap-1.5">
                <Calendar size={12} />
                {relatorio.data_execucao}
              </span>
              <span className="flex items-center gap-1.5">
                <Users size={12} />
                {relatorio.squads_reportados} squad(s)
              </span>
            </div>
          </div>

          {/* Corpo do relatório */}
          <div className="p-6">
            <div className="sf-glass border rounded-xl p-5 font-mono text-sm sf-text-dim whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto" style={{ borderColor: 'var(--sf-border-subtle)' }}>
              {relatorio.relatorio}
            </div>
          </div>
        </div>
      )}

      {/* Estado vazio */}
      {!relatorio && !gerando && !erro && (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl sf-glass border flex items-center justify-center" style={{ borderColor: 'var(--sf-border-subtle)' }}>
            <ClipboardList size={28} className="sf-text-ghost" strokeWidth={1.5} />
          </div>
          <p className="sf-text-dim text-sm">Clique em "Gerar Standup" para compilar o relatório diário.</p>
          <p className="sf-text-ghost text-xs mt-1">O relatório agrega status de todos os squads ativos.</p>
        </div>
      )}
    </div>
  )
}
