/* PushDialog — Modal de selecao de commits para Push + PR */

import { useState, useEffect, useCallback } from 'react'
import { X, Loader2, GitBranch, Check, ExternalLink, AlertCircle, GitCommitHorizontal } from 'lucide-react'
import { gitLog, gitPush, type GitCommitInfo } from '../../services/codeStudio'

interface PushDialogProps {
  projetoId: number
  projetoNome: string
  onFechar: () => void
}

/** Tempo relativo compacto */
function tempoRelativo(dataStr: string): string {
  if (!dataStr) return ''
  const agora = Date.now()
  const data = new Date(dataStr.replace(' ', 'T')).getTime()
  const diff = agora - data
  if (diff < 0 || isNaN(diff)) return ''
  const min = Math.floor(diff / 60000)
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  return `${d}d`
}

export default function PushDialog({ projetoId, projetoNome, onFechar }: PushDialogProps) {
  const [commits, setCommits] = useState<GitCommitInfo[]>([])
  const [branch, setBranch] = useState('')
  const [branchRemoto, setBranchRemoto] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<{ sucesso: boolean; pr_url: string; mensagem: string } | null>(null)

  // Carregar commits pendentes
  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro('')
    try {
      const dados = await gitLog(projetoId)
      setCommits(dados.commits)
      setBranch(dados.branch)
      setBranchRemoto(dados.branch_remoto)
      // Selecionar todos por padrao
      setSelecionados(new Set(dados.commits.map(c => c.hash)))
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao carregar commits')
    } finally {
      setCarregando(false)
    }
  }, [projetoId])

  useEffect(() => { carregar() }, [carregar])

  const toggleCommit = (hash: string) => {
    setSelecionados(prev => {
      const novo = new Set(prev)
      if (novo.has(hash)) novo.delete(hash)
      else novo.add(hash)
      return novo
    })
  }

  const toggleTodos = () => {
    if (selecionados.size === commits.length) {
      setSelecionados(new Set())
    } else {
      setSelecionados(new Set(commits.map(c => c.hash)))
    }
  }

  const executarPush = async () => {
    if (selecionados.size === 0) return
    setEnviando(true)
    setErro('')
    try {
      const hashes = selecionados.size === commits.length
        ? []  // vazio = todos
        : Array.from(selecionados)
      const res = await gitPush(projetoId, hashes)
      setResultado({ sucesso: res.sucesso, pr_url: res.pr_url, mensagem: res.mensagem })
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro no push')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div className="rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
        style={{ background: 'var(--sf-bg-1)', border: '1px solid var(--sf-border-default)' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
          <div className="flex items-center gap-2">
            <GitBranch size={16} style={{ color: '#10b981' }} />
            <div>
              <h3 className="text-[14px] font-bold" style={{ color: 'var(--sf-text-0)' }}>
                Push & Pull Request
              </h3>
              <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                {projetoNome} · {branch} → {branchRemoto}
              </p>
            </div>
          </div>
          <button onClick={onFechar} className="p-1.5 rounded-lg hover:bg-white/5" style={{ color: 'var(--sf-text-3)' }}>
            <X size={16} />
          </button>
        </div>

        {/* Conteudo */}
        <div className="px-5 py-4 max-h-[60vh] overflow-auto" style={{ scrollbarWidth: 'thin' }}>

          {/* Loading */}
          {carregando && (
            <div className="flex items-center justify-center py-8 gap-2">
              <Loader2 size={16} className="animate-spin" style={{ color: '#10b981' }} />
              <span className="text-[12px]" style={{ color: 'var(--sf-text-3)' }}>Buscando commits...</span>
            </div>
          )}

          {/* Erro */}
          {erro && !carregando && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg mb-3"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <AlertCircle size={14} style={{ color: '#ef4444' }} />
              <span className="text-[11px]" style={{ color: '#ef4444' }}>{erro}</span>
            </div>
          )}

          {/* Sem commits */}
          {!carregando && !erro && commits.length === 0 && (
            <div className="text-center py-8">
              <Check size={28} className="mx-auto mb-2" style={{ color: '#10b981' }} />
              <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>
                Tudo sincronizado!
              </p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
                Nenhum commit pendente de push
              </p>
            </div>
          )}

          {/* Resultado do push */}
          {resultado && (
            <div className="px-4 py-3 rounded-xl mb-3"
              style={{
                background: resultado.sucesso ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                border: `1px solid ${resultado.sucesso ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
              }}>
              <p className="text-[12px] font-semibold" style={{ color: resultado.sucesso ? '#10b981' : '#ef4444' }}>
                {resultado.sucesso ? '✅ PR criada com sucesso!' : '❌ Falhou'}
              </p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-2)' }}>{resultado.mensagem}</p>
              {resultado.pr_url && (
                <a href={resultado.pr_url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all hover:brightness-110"
                  style={{ background: '#10b981', color: '#fff' }}>
                  <ExternalLink size={11} />
                  Abrir PR no GitHub
                </a>
              )}
            </div>
          )}

          {/* Lista de commits */}
          {!carregando && commits.length > 0 && !resultado && (
            <>
              {/* Header da lista */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold" style={{ color: 'var(--sf-text-2)' }}>
                  {commits.length} commit{commits.length !== 1 ? 's' : ''} pendente{commits.length !== 1 ? 's' : ''}
                </span>
                <button onClick={toggleTodos}
                  className="text-[10px] font-medium px-2 py-0.5 rounded hover:bg-white/5"
                  style={{ color: '#818cf8' }}>
                  {selecionados.size === commits.length ? 'Desmarcar todos' : 'Selecionar todos'}
                </button>
              </div>

              {/* Commits */}
              <div className="space-y-1">
                {commits.map(c => {
                  const sel = selecionados.has(c.hash)
                  return (
                    <button
                      key={c.hash}
                      onClick={() => toggleCommit(c.hash)}
                      className="w-full flex items-start gap-2.5 px-3 py-2 rounded-lg text-left transition-all"
                      style={{
                        background: sel ? 'rgba(16,185,129,0.06)' : 'transparent',
                        border: `1px solid ${sel ? 'rgba(16,185,129,0.15)' : 'var(--sf-border-subtle)'}`,
                      }}
                    >
                      {/* Checkbox */}
                      <div className="w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{
                          borderColor: sel ? '#10b981' : 'var(--sf-border-default)',
                          background: sel ? '#10b981' : 'transparent',
                        }}>
                        {sel && <Check size={10} color="#fff" strokeWidth={3} />}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <GitCommitHorizontal size={11} style={{ color: '#f59e0b', flexShrink: 0 }} />
                          <span className="text-[10px] font-mono" style={{ color: '#f59e0b' }}>{c.hash_curto}</span>
                          <span className="text-[11px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>
                            {c.mensagem}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>{c.autor}</span>
                          <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>·</span>
                          <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.6 }}>
                            {tempoRelativo(c.data)}
                          </span>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!carregando && commits.length > 0 && !resultado && (
          <div className="flex items-center justify-between px-5 py-3"
            style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
            <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
              {selecionados.size} de {commits.length} selecionado{selecionados.size !== 1 ? 's' : ''}
            </span>
            <div className="flex items-center gap-2">
              <button onClick={onFechar}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium hover:bg-white/5"
                style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
                Cancelar
              </button>
              <button
                onClick={executarPush}
                disabled={selecionados.size === 0 || enviando}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
                style={{ background: '#10b981', color: '#fff' }}>
                {enviando ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    Criando PR...
                  </>
                ) : (
                  <>
                    <GitBranch size={12} />
                    Criar PR e Push
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Footer resultado */}
        {resultado && (
          <div className="flex justify-end px-5 py-3" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
            <button onClick={onFechar}
              className="px-4 py-1.5 rounded-lg text-[11px] font-medium"
              style={{ background: 'var(--sf-accent)', color: '#fff' }}>
              Fechar
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
