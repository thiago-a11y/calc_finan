/* HistoricoPanel — Painel de historico de atividades do Code Studio */

import { useState, useEffect, useCallback } from 'react'
import { History, X, RefreshCw, Loader2, Pencil, Sparkles, FilePlus, FileCode, Clock, ChevronDown } from 'lucide-react'
import { buscarHistorico, type AtividadeHistorico } from '../../services/codeStudio'

interface HistoricoPanelProps {
  projetoId: number
  onFechar: () => void
  onAbrirArquivo?: (caminho: string) => void
}

/** Calcula tempo relativo em PT-BR (sem dependencia externa) */
function tempoRelativo(dataISO: string): string {
  if (!dataISO) return ''
  const agora = Date.now()
  const data = new Date(dataISO).getTime()
  const diff = agora - data
  if (diff < 0) return 'agora'

  const seg = Math.floor(diff / 1000)
  if (seg < 60) return 'agora'
  const min = Math.floor(seg / 60)
  if (min < 60) return `ha ${min} min`
  const horas = Math.floor(min / 60)
  if (horas < 24) return `ha ${horas}h`
  const dias = Math.floor(horas / 24)
  if (dias < 30) return `ha ${dias}d`
  const meses = Math.floor(dias / 30)
  return `ha ${meses} mes${meses > 1 ? 'es' : ''}`
}

/** Icone e cor por tipo de acao */
function iconeAcao(acao: string) {
  if (acao.includes('criar')) return { Icon: FilePlus, cor: '#3b82f6' }
  if (acao.includes('apply') || acao.includes('substituir')) return { Icon: Sparkles, cor: '#a78bfa' }
  if (acao === 'CODE_STUDIO_WRITE') return { Icon: Pencil, cor: '#10b981' }
  return { Icon: FileCode, cor: 'var(--sf-text-3)' }
}

export default function HistoricoPanel({ projetoId, onFechar, onAbrirArquivo }: HistoricoPanelProps) {
  const [atividades, setAtividades] = useState<AtividadeHistorico[]>([])
  const [carregando, setCarregando] = useState(false)
  const [pagina, setPagina] = useState(1)
  const [total, setTotal] = useState(0)
  const [erro, setErro] = useState('')

  const carregar = useCallback(async (pag = 1, acumular = false) => {
    setCarregando(true)
    setErro('')
    try {
      const dados = await buscarHistorico(projetoId, 30, pag)
      setAtividades(prev => acumular ? [...prev, ...dados.atividades] : dados.atividades)
      setTotal(dados.total)
      setPagina(pag)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao carregar')
    } finally {
      setCarregando(false)
    }
  }, [projetoId])

  useEffect(() => {
    carregar(1, false)
  }, [carregar])

  const temMais = atividades.length < total

  return (
    <div className="h-full flex flex-col" style={{ borderLeft: '1px solid var(--sf-border-subtle)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <div className="flex items-center gap-2">
          <History size={16} style={{ color: '#f59e0b' }} />
          <div>
            <span className="text-[12px] font-semibold" style={{ color: 'var(--sf-text-0)' }}>
              Historico
            </span>
            <p className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>
              {total} atividade{total !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => carregar(1, false)}
            disabled={carregando}
            className="p-1 rounded hover:bg-white/5 transition-colors"
            style={{ color: 'var(--sf-text-3)' }}
            title="Recarregar"
          >
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} />
          </button>
          <button onClick={onFechar} className="p-1 rounded hover:bg-white/5"
            style={{ color: 'var(--sf-text-3)' }}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Lista de atividades */}
      <div className="flex-1 overflow-auto px-2 py-2 space-y-1" style={{ scrollbarWidth: 'thin' }}>
        {erro && (
          <div className="text-center py-4">
            <p className="text-[11px]" style={{ color: '#ef4444' }}>{erro}</p>
            <button onClick={() => carregar(1, false)} className="text-[10px] mt-2 underline" style={{ color: 'var(--sf-text-3)' }}>
              Tentar novamente
            </button>
          </div>
        )}

        {!erro && atividades.length === 0 && !carregando && (
          <div className="text-center py-8">
            <Clock size={28} className="mx-auto mb-3" style={{ color: 'var(--sf-text-3)', opacity: 0.3 }} />
            <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
              Nenhuma atividade registrada
            </p>
            <p className="text-[10px] mt-1" style={{ color: 'var(--sf-text-3)', opacity: 0.6 }}>
              As acoes do Code Studio aparecerão aqui
            </p>
          </div>
        )}

        {atividades.map(ativ => {
          const { Icon, cor } = iconeAcao(ativ.acao)
          const nomeArquivo = ativ.arquivo.split('/').pop() || ativ.arquivo
          return (
            <div
              key={ativ.id}
              className="flex items-start gap-2.5 px-2.5 py-2 rounded-lg transition-colors hover:bg-white/3 group"
              style={{ background: 'rgba(255,255,255,0.01)' }}
            >
              {/* Icone */}
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{ background: `${cor}15` }}>
                <Icon size={13} style={{ color: cor }} />
              </div>

              {/* Conteudo */}
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-medium leading-snug" style={{ color: 'var(--sf-text-1)' }}>
                  {ativ.acao_label}
                </p>

                {ativ.arquivo && (
                  <button
                    onClick={() => onAbrirArquivo?.(ativ.arquivo)}
                    className="text-[10px] font-mono truncate block max-w-full text-left transition-colors hover:underline mt-0.5"
                    style={{ color: '#818cf8' }}
                    title={ativ.arquivo}
                  >
                    {nomeArquivo}
                  </button>
                )}

                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>
                    {ativ.usuario_nome}
                  </span>
                  <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>
                    ·
                  </span>
                  <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.6 }}>
                    {tempoRelativo(ativ.criado_em)}
                  </span>
                </div>
              </div>
            </div>
          )
        })}

        {/* Carregar mais */}
        {temMais && !carregando && (
          <button
            onClick={() => carregar(pagina + 1, true)}
            className="w-full flex items-center justify-center gap-1.5 py-2 mt-2 rounded-lg text-[10px] font-medium transition-all hover:bg-white/5"
            style={{ color: 'var(--sf-text-3)', border: '1px dashed var(--sf-border-subtle)' }}
          >
            <ChevronDown size={11} />
            Carregar mais ({total - atividades.length} restantes)
          </button>
        )}

        {carregando && (
          <div className="flex items-center justify-center py-4 gap-2">
            <Loader2 size={14} className="animate-spin" style={{ color: '#f59e0b' }} />
            <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>Carregando...</span>
          </div>
        )}
      </div>
    </div>
  )
}
