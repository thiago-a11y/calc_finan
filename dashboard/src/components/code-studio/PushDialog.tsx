/* PushDialog — Modal de selecao de commits para Push + PR + Merge */
/* v2: Preview expandivel + horario Brasilia + arquivos alterados */

import { useState, useEffect, useCallback } from 'react'
import { X, Loader2, GitBranch, Check, ExternalLink, AlertCircle, GitCommitHorizontal, GitMerge, ChevronDown, ChevronRight, FileEdit, FilePlus, FileX } from 'lucide-react'
import { gitLog, gitPush, gitMerge, type GitCommitInfo } from '../../services/codeStudio'

interface PushDialogProps {
  projetoId: number
  projetoNome: string
  onFechar: () => void
}

/** Converte data ISO/git para horario de Brasilia formatado */
function formatarBrasilia(dataStr: string): string {
  if (!dataStr) return ''
  try {
    // Suporta ISO 8601 (2026-03-30T13:45:01-03:00) e formato git (2026-03-30 13:45:01 -0300)
    let str = dataStr.trim()
    // Converter formato git "2026-03-30 13:45:01 -0300" para ISO
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$/.test(str)) {
      str = str.replace(' ', 'T').replace(/ ([+-]\d{2})(\d{2})$/, '$1:$2')
    }
    const d = new Date(str)
    if (isNaN(d.getTime())) return dataStr
    return d.toLocaleString('pt-BR', {
      timeZone: 'America/Sao_Paulo',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return dataStr }
}

/** Icone e cor por status do arquivo */
function statusArquivo(status: string) {
  switch (status.toUpperCase()) {
    case 'A': return { icon: FilePlus, cor: '#10b981', label: 'Adicionado' }
    case 'D': return { icon: FileX, cor: '#ef4444', label: 'Removido' }
    default: return { icon: FileEdit, cor: '#f59e0b', label: 'Modificado' }
  }
}

type Etapa = 'selecao' | 'enviando' | 'pr_criada' | 'fazendo_merge' | 'merge_concluido' | 'erro'

export default function PushDialog({ projetoId, projetoNome, onFechar }: PushDialogProps) {
  const [commits, setCommits] = useState<GitCommitInfo[]>([])
  const [branch, setBranch] = useState('')
  const [branchRemoto, setBranchRemoto] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set())
  const [etapa, setEtapa] = useState<Etapa>('selecao')
  const [erro, setErro] = useState('')

  // Dados da PR criada
  const [prUrl, setPrUrl] = useState('')
  const [prNumber, setPrNumber] = useState(0)
  const [mergeSha, setMergeSha] = useState('')

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro('')
    try {
      const dados = await gitLog(projetoId)
      setCommits(dados.commits)
      setBranch(dados.branch)
      setBranchRemoto(dados.branch_remoto)
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

  const toggleExpandido = (hash: string) => {
    setExpandidos(prev => {
      const novo = new Set(prev)
      if (novo.has(hash)) novo.delete(hash)
      else novo.add(hash)
      return novo
    })
  }

  const toggleTodos = () => {
    if (selecionados.size === commits.length) setSelecionados(new Set())
    else setSelecionados(new Set(commits.map(c => c.hash)))
  }

  // Etapa 1: Criar PR e Push
  const executarPush = async () => {
    if (selecionados.size === 0) return
    setEtapa('enviando')
    setErro('')
    try {
      const hashes = selecionados.size === commits.length ? [] : Array.from(selecionados)
      const res = await gitPush(projetoId, hashes)
      if (res.sucesso) {
        setPrUrl(res.pr_url)
        setPrNumber(res.pr_number)
        setEtapa('pr_criada')
      } else {
        setErro(res.mensagem || 'Falha ao criar PR')
        setEtapa('erro')
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro no push')
      setEtapa('erro')
    }
  }

  // Etapa 2: Fazer Merge
  const executarMerge = async () => {
    if (!prNumber) return
    setEtapa('fazendo_merge')
    setErro('')
    try {
      const res = await gitMerge(projetoId, prNumber)
      if (res.sucesso) {
        setMergeSha(res.merge_sha)
        setEtapa('merge_concluido')
      } else {
        setErro(res.mensagem || 'Falha no merge')
        setEtapa('erro')
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro no merge')
      setEtapa('erro')
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
                {projetoNome} · {branch || '...'} → {branchRemoto || 'main'}
              </p>
            </div>
          </div>
          <button onClick={onFechar} className="p-1.5 rounded-lg hover:bg-white/5" style={{ color: 'var(--sf-text-3)' }}>
            <X size={16} />
          </button>
        </div>

        {/* Conteudo */}
        <div className="px-5 py-4 max-h-[60vh] overflow-auto" style={{ scrollbarWidth: 'thin' }}>

          {/* Loading inicial */}
          {carregando && (
            <div className="flex items-center justify-center py-8 gap-2">
              <Loader2 size={16} className="animate-spin" style={{ color: '#10b981' }} />
              <span className="text-[12px]" style={{ color: 'var(--sf-text-3)' }}>Buscando commits...</span>
            </div>
          )}

          {/* Erro */}
          {erro && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg mb-3"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <AlertCircle size={14} style={{ color: '#ef4444' }} />
              <span className="text-[11px]" style={{ color: '#ef4444' }}>{erro}</span>
            </div>
          )}

          {/* Sem commits */}
          {!carregando && !erro && commits.length === 0 && etapa === 'selecao' && (
            <div className="text-center py-8">
              <Check size={28} className="mx-auto mb-2" style={{ color: '#10b981' }} />
              <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>Tudo sincronizado!</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>Nenhum commit pendente de push</p>
            </div>
          )}

          {/* === ETAPA: PR CRIADA — mostrar botao de Merge === */}
          {etapa === 'pr_criada' && (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                style={{ background: 'rgba(16,185,129,0.1)' }}>
                <Check size={24} style={{ color: '#10b981' }} />
              </div>
              <p className="text-[14px] font-bold" style={{ color: '#10b981' }}>PR criada com sucesso!</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
                PR #{prNumber} pronta para merge
              </p>
              {prUrl && (
                <a href={prUrl} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 mt-2 text-[10px] transition-colors hover:underline"
                  style={{ color: '#818cf8' }}>
                  <ExternalLink size={10} /> Ver no GitHub
                </a>
              )}
            </div>
          )}

          {/* === ETAPA: FAZENDO MERGE === */}
          {etapa === 'fazendo_merge' && (
            <div className="text-center py-8">
              <Loader2 size={24} className="animate-spin mx-auto mb-3" style={{ color: '#8b5cf6' }} />
              <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>Fazendo merge...</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>Unindo as alteracoes na branch {branchRemoto}</p>
            </div>
          )}

          {/* === ETAPA: MERGE CONCLUIDO === */}
          {etapa === 'merge_concluido' && (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                style={{ background: 'rgba(139,92,246,0.1)' }}>
                <GitMerge size={24} style={{ color: '#8b5cf6' }} />
              </div>
              <p className="text-[14px] font-bold" style={{ color: '#8b5cf6' }}>Merge concluido!</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
                PR #{prNumber} merged na {branchRemoto}
                {mergeSha && <span className="font-mono"> ({mergeSha.slice(0, 8)})</span>}
              </p>
              {prUrl && (
                <a href={prUrl} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 mt-2 text-[10px] transition-colors hover:underline"
                  style={{ color: '#818cf8' }}>
                  <ExternalLink size={10} /> Ver PR no GitHub
                </a>
              )}
            </div>
          )}

          {/* === ETAPA: SELECAO DE COMMITS (com preview) === */}
          {!carregando && commits.length > 0 && etapa === 'selecao' && (
            <>
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
              <div className="space-y-1.5">
                {commits.map(c => {
                  const sel = selecionados.has(c.hash)
                  const exp = expandidos.has(c.hash)
                  const arquivos = c.arquivos || []
                  return (
                    <div key={c.hash} className="rounded-lg overflow-hidden transition-all"
                      style={{
                        background: sel ? 'rgba(16,185,129,0.06)' : 'transparent',
                        border: `1px solid ${sel ? 'rgba(16,185,129,0.15)' : 'var(--sf-border-subtle)'}`,
                      }}>
                      {/* Linha principal do commit */}
                      <div className="flex items-start gap-2.5 px-3 py-2">
                        {/* Checkbox */}
                        <button onClick={() => toggleCommit(c.hash)}
                          className="w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 mt-0.5"
                          style={{ borderColor: sel ? '#10b981' : 'var(--sf-border-default)', background: sel ? '#10b981' : 'transparent' }}>
                          {sel && <Check size={10} color="#fff" strokeWidth={3} />}
                        </button>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <GitCommitHorizontal size={11} style={{ color: '#f59e0b', flexShrink: 0 }} />
                            <span className="text-[10px] font-mono" style={{ color: '#f59e0b' }}>{c.hash_curto}</span>
                            <span className="text-[11px] font-medium truncate" style={{ color: 'var(--sf-text-1)' }}>{c.mensagem}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>{c.autor}</span>
                            <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>·</span>
                            <span className="text-[9px]" style={{ color: 'var(--sf-text-3)' }}>{formatarBrasilia(c.data)}</span>
                            {arquivos.length > 0 && (
                              <>
                                <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.5 }}>·</span>
                                <span className="text-[9px]" style={{ color: 'var(--sf-text-3)', opacity: 0.7 }}>
                                  {arquivos.length} arquivo{arquivos.length !== 1 ? 's' : ''}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Botão preview */}
                        {arquivos.length > 0 && (
                          <button onClick={() => toggleExpandido(c.hash)}
                            className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium hover:bg-white/5 flex-shrink-0"
                            style={{ color: '#818cf8' }}
                            title="Ver arquivos alterados neste commit">
                            {exp ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                            Detalhes
                          </button>
                        )}
                      </div>

                      {/* Preview expandido — lista de arquivos */}
                      {exp && arquivos.length > 0 && (
                        <div className="px-3 pb-2.5 pt-0.5 ml-6" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
                          <div className="max-h-40 overflow-auto space-y-0.5" style={{ scrollbarWidth: 'thin' }}>
                            {arquivos.map((a, ai) => {
                              const st = statusArquivo(a.status)
                              const Icon = st.icon
                              return (
                                <div key={ai} className="flex items-center gap-2 py-0.5">
                                  <Icon size={11} style={{ color: st.cor, flexShrink: 0 }} />
                                  <span className="text-[10px] font-mono truncate" style={{ color: 'var(--sf-text-2)' }}>
                                    {a.arquivo}
                                  </span>
                                  <span className="text-[8px] px-1.5 py-0.5 rounded flex-shrink-0" style={{
                                    background: `${st.cor}15`,
                                    color: st.cor,
                                  }}>
                                    {st.label}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {/* === ETAPA: ENVIANDO === */}
          {etapa === 'enviando' && (
            <div className="text-center py-8">
              <Loader2 size={24} className="animate-spin mx-auto mb-3" style={{ color: '#10b981' }} />
              <p className="text-[13px] font-medium" style={{ color: 'var(--sf-text-1)' }}>Criando PR e Push...</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>Enviando commits para o GitHub</p>
            </div>
          )}
        </div>

        {/* Footer — muda conforme etapa */}
        <div className="flex items-center justify-between px-5 py-3"
          style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>

          {/* Selecao */}
          {etapa === 'selecao' && commits.length > 0 && (
            <>
              <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                {selecionados.size} de {commits.length} selecionado{selecionados.size !== 1 ? 's' : ''}
              </span>
              <div className="flex items-center gap-2">
                <button onClick={onFechar}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-medium hover:bg-white/5"
                  style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
                  Cancelar
                </button>
                <button onClick={executarPush} disabled={selecionados.size === 0}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
                  style={{ background: '#10b981', color: '#fff' }}>
                  <GitBranch size={12} />
                  Criar PR e Push
                </button>
              </div>
            </>
          )}

          {/* PR criada — botao Merge */}
          {etapa === 'pr_criada' && (
            <>
              <span className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                PR #{prNumber} pronta
              </span>
              <div className="flex items-center gap-2">
                <button onClick={onFechar}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-medium hover:bg-white/5"
                  style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
                  Fazer depois
                </button>
                <button onClick={executarMerge}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all hover:brightness-110"
                  style={{ background: '#8b5cf6', color: '#fff' }}>
                  <GitMerge size={12} />
                  Fazer Merge
                </button>
              </div>
            </>
          )}

          {/* Merge concluido ou sem commits */}
          {(etapa === 'merge_concluido' || (etapa === 'selecao' && commits.length === 0 && !carregando)) && (
            <div className="flex-1 flex justify-end">
              <button onClick={onFechar}
                className="px-4 py-1.5 rounded-lg text-[11px] font-medium"
                style={{ background: 'var(--sf-accent)', color: '#fff' }}>
                Fechar
              </button>
            </div>
          )}

          {/* Erro — botao tentar novamente */}
          {etapa === 'erro' && (
            <>
              <span />
              <div className="flex items-center gap-2">
                <button onClick={onFechar}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-medium hover:bg-white/5"
                  style={{ color: 'var(--sf-text-3)', border: '1px solid var(--sf-border-subtle)' }}>
                  Fechar
                </button>
                <button onClick={() => { setErro(''); setEtapa('selecao') }}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-medium"
                  style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>
                  Tentar novamente
                </button>
              </div>
            </>
          )}

          {/* Enviando / fazendo merge — footer vazio */}
          {(etapa === 'enviando' || etapa === 'fazendo_merge') && <span />}
        </div>
      </div>
    </div>
  )
}
