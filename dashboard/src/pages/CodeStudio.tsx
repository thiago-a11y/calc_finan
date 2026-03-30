/* Code Studio — Editor de codigo integrado ao Synerium Factory (multi-projeto) */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Code2, Loader2, Eye, EyeOff, FolderKanban, ChevronDown, GitBranch, AlertCircle, RefreshCw, Download, Upload } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import FileTree from '../components/code-studio/FileTree'
import EditorTabs, { type TabInfo } from '../components/code-studio/EditorTabs'
import CodeEditor from '../components/code-studio/CodeEditor'
import Toolbar from '../components/code-studio/Toolbar'
import AgentPanel from '../components/code-studio/AgentPanel'
import HistoricoPanel from '../components/code-studio/HistoricoPanel'
import PushDialog from '../components/code-studio/PushDialog'
import { buscarArvore, lerArquivo, salvarArquivo, gitPull, type ArquivoArvore } from '../services/codeStudio'

interface ProjetoInfo {
  id: number
  nome: string
  stack: string
  caminho: string
  icone: string
  repositorio: string
}

const STORAGE_KEY = 'sf_code_studio_projeto'

export default function CodeStudio() {
  const { token } = useAuth()

  // Ler agente da URL (quando vem do Escritorio Virtual)
  const [searchParams] = useSearchParams()
  const agenteNome = useMemo(() => searchParams.get('agente') || '', [searchParams])

  // Estado de projetos
  const [projetos, setProjetos] = useState<ProjetoInfo[]>([])
  const [projetoAtivo, setProjetoAtivo] = useState<ProjetoInfo | null>(null)
  const [dropProjeto, setDropProjeto] = useState(false)
  const [carregandoProjetos, setCarregandoProjetos] = useState(true)

  // Estado da arvore
  const [arvore, setArvore] = useState<ArquivoArvore[]>([])
  const [carregando, setCarregando] = useState(false)
  const [erroArvore, setErroArvore] = useState('')

  // Estado do editor
  const [abas, setAbas] = useState<TabInfo[]>([])
  const [abaAtiva, setAbaAtiva] = useState('')
  const [conteudos, setConteudos] = useState<Map<string, string>>(new Map())
  const [conteudosOriginal, setConteudosOriginal] = useState<Map<string, string>>(new Map())
  const [linguagens, setLinguagens] = useState<Map<string, string>>(new Map())
  const [editaveis, setEditaveis] = useState<Map<string, boolean>>(new Map())
  const [modificados, setModificados] = useState<Set<string>>(new Set())
  const [salvando, setSalvando] = useState(false)

  // Estado dos paineis laterais (mutuamente exclusivos)
  const [agentePainel, setAgentePainel] = useState(!!agenteNome)
  const [historicoPainel, setHistoricoPainel] = useState(false)

  // Toggle mutuamente exclusivo
  const toggleAgente = useCallback(() => {
    setAgentePainel(prev => {
      if (!prev) setHistoricoPainel(false)
      return !prev
    })
  }, [])

  const toggleHistorico = useCallback(() => {
    setHistoricoPainel(prev => {
      if (!prev) setAgentePainel(false)
      return !prev
    })
  }, [])

  // Estado do preview
  const [previewAberto, setPreviewAberto] = useState(false)

  // Linguagens que suportam preview
  const suportaPreview = (lang: string) =>
    ['html', 'javascript', 'typescript', 'markdown'].includes(lang)

  // Gerar conteudo do preview
  const gerarPreviewHtml = useCallback((conteudo: string, lang: string): string => {
    if (lang === 'html') return conteudo
    if (lang === 'markdown') {
      let html = conteudo
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:#333;padding:2px 6px;border-radius:4px;font-size:13px">$1</code>')
        .replace(/^- (.*$)/gm, '<li>$1</li>')
        .replace(/\n/g, '<br>')
      return `<div style="font-family:system-ui;padding:24px;color:#e2e8f0;max-width:700px">${html}</div>`
    }
    return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body{font-family:system-ui;padding:24px;background:#1e1e2e;color:#cdd6f4;margin:0}
  pre{background:#181825;padding:16px;border-radius:8px;overflow:auto;font-size:13px;line-height:1.6}
  h3{color:#a6e3a1;margin-bottom:8px}
</style></head><body>
<h3>${abaAtiva?.split('/').pop() || 'arquivo'}</h3>
<pre>${conteudo.replace(/</g,'&lt;').replace(/>/g,'&gt;').slice(0, 5000)}</pre>
</body></html>`
  }, [abaAtiva])

  // ============================================================
  // Carregar projetos ao montar
  // ============================================================
  useEffect(() => {
    const carregarProjetos = async () => {
      setCarregandoProjetos(true)
      try {
        const res = await fetch('/api/projetos', { headers: { Authorization: `Bearer ${token}` } })
        if (!res.ok) throw new Error('Erro')
        const lista: ProjetoInfo[] = await res.json()
        setProjetos(lista)

        // Restaurar ultimo projeto selecionado
        const salvo = localStorage.getItem(STORAGE_KEY)
        const salvoId = salvo ? parseInt(salvo, 10) : 0
        const encontrado = lista.find(p => p.id === salvoId)

        if (encontrado) {
          setProjetoAtivo(encontrado)
        } else if (lista.length > 0) {
          // Usar primeiro projeto como padrao
          setProjetoAtivo(lista[0])
        }
      } catch {
        // Fallback: sem projetos, usar Synerium Factory padrao
        setProjetoAtivo(null)
      } finally {
        setCarregandoProjetos(false)
      }
    }
    carregarProjetos()
  }, [token])

  // ============================================================
  // Carregar arvore quando projeto muda
  // ============================================================
  // Estado de git pull
  const [fazendoPull, setFazendoPull] = useState(false)
  const [mensagemPull, setMensagemPull] = useState('')
  const [mostrarPushDialog, setMostrarPushDialog] = useState(false)

  const carregarArvore = useCallback(async () => {
    setCarregando(true)
    setErroArvore('')
    try {
      const projetoId = projetoAtivo?.id || 0
      const dados = await buscarArvore('', projetoId)
      setArvore(dados.arvore)
    } catch (e) {
      setErroArvore(e instanceof Error ? e.message : 'Erro ao carregar arvore')
    } finally {
      setCarregando(false)
    }
  }, [projetoAtivo])

  // Git pull — atualizar repositorio remoto
  const executarPull = useCallback(async () => {
    setFazendoPull(true)
    setMensagemPull('')
    try {
      const resultado = await gitPull(projetoAtivo?.id || 0)
      setMensagemPull(resultado.sucesso ? `Pull OK (${resultado.branch})` : resultado.mensagem)
      // Recarregar arvore apos pull
      if (resultado.sucesso) {
        await carregarArvore()
        // Limpar mensagem apos 3s
        setTimeout(() => setMensagemPull(''), 3000)
      }
    } catch (e) {
      setMensagemPull(e instanceof Error ? e.message : 'Erro no pull')
    } finally {
      setFazendoPull(false)
    }
  }, [projetoAtivo, carregarArvore])

  useEffect(() => {
    if (!carregandoProjetos) {
      carregarArvore()
    }
  }, [carregarArvore, carregandoProjetos])

  // ============================================================
  // Trocar projeto
  // ============================================================
  const trocarProjeto = useCallback((projeto: ProjetoInfo) => {
    setProjetoAtivo(projeto)
    localStorage.setItem(STORAGE_KEY, String(projeto.id))
    setDropProjeto(false)
    // Limpar estado do editor
    setAbas([])
    setAbaAtiva('')
    setConteudos(new Map())
    setConteudosOriginal(new Map())
    setLinguagens(new Map())
    setEditaveis(new Map())
    setModificados(new Set())
    setPreviewAberto(false)
  }, [])

  // Usar projeto padrao (Synerium Factory — sem project_id)
  const usarPadrao = useCallback(() => {
    setProjetoAtivo(null)
    localStorage.removeItem(STORAGE_KEY)
    setDropProjeto(false)
    setAbas([])
    setAbaAtiva('')
    setConteudos(new Map())
    setConteudosOriginal(new Map())
    setLinguagens(new Map())
    setEditaveis(new Map())
    setModificados(new Set())
    setPreviewAberto(false)
  }, [])

  // ============================================================
  // Operacoes de arquivo (passam projetoId)
  // ============================================================
  const projetoId = projetoAtivo?.id || 0

  const abrirArquivo = useCallback(async (caminho: string) => {
    if (abas.some(a => a.caminho === caminho)) {
      setAbaAtiva(caminho)
      return
    }

    try {
      const arquivo = await lerArquivo(caminho, projetoId)
      const nome = caminho.split('/').pop() || caminho

      setConteudos(prev => new Map(prev).set(caminho, arquivo.conteudo))
      setConteudosOriginal(prev => new Map(prev).set(caminho, arquivo.conteudo))
      setLinguagens(prev => new Map(prev).set(caminho, arquivo.linguagem))
      setEditaveis(prev => new Map(prev).set(caminho, arquivo.editavel))
      setAbas(prev => [...prev, { caminho, nome, modificado: false, linguagem: arquivo.linguagem }])
      setAbaAtiva(caminho)
    } catch {
      // Erro silencioso
    }
  }, [abas, projetoId])

  const fecharAba = useCallback((caminho: string) => {
    setAbas(prev => {
      const novas = prev.filter(a => a.caminho !== caminho)
      if (abaAtiva === caminho && novas.length > 0) {
        setAbaAtiva(novas[novas.length - 1].caminho)
      } else if (novas.length === 0) {
        setAbaAtiva('')
      }
      return novas
    })
    setConteudos(prev => { const m = new Map(prev); m.delete(caminho); return m })
    setConteudosOriginal(prev => { const m = new Map(prev); m.delete(caminho); return m })
    setModificados(prev => { const s = new Set(prev); s.delete(caminho); return s })
  }, [abaAtiva])

  const handleChange = useCallback((novoConteudo: string) => {
    if (!abaAtiva) return
    setConteudos(prev => new Map(prev).set(abaAtiva, novoConteudo))

    const original = conteudosOriginal.get(abaAtiva)
    const ehModificado = novoConteudo !== original
    setModificados(prev => {
      const s = new Set(prev)
      ehModificado ? s.add(abaAtiva) : s.delete(abaAtiva)
      return s
    })
    setAbas(prev => prev.map(a =>
      a.caminho === abaAtiva ? { ...a, modificado: ehModificado } : a
    ))
  }, [abaAtiva, conteudosOriginal])

  const handleSalvar = useCallback(async () => {
    if (!abaAtiva || !modificados.has(abaAtiva)) return
    const conteudo = conteudos.get(abaAtiva)
    if (conteudo === undefined) return

    setSalvando(true)
    try {
      await salvarArquivo(abaAtiva, conteudo, projetoId)
      setConteudosOriginal(prev => new Map(prev).set(abaAtiva, conteudo))
      setModificados(prev => { const s = new Set(prev); s.delete(abaAtiva); return s })
      setAbas(prev => prev.map(a =>
        a.caminho === abaAtiva ? { ...a, modificado: false } : a
      ))
    } catch {
      // Erro silencioso
    } finally {
      setSalvando(false)
    }
  }, [abaAtiva, modificados, conteudos, projetoId])

  const conteudoAtivo = conteudos.get(abaAtiva) || ''
  const linguagemAtiva = linguagens.get(abaAtiva) || 'text'
  const editavelAtivo = editaveis.get(abaAtiva) ?? false
  const modificadoAtivo = modificados.has(abaAtiva)

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 64px)', margin: '-24px', overflow: 'hidden' }}>
      {/* Header com seletor de projeto */}
      <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)', background: 'var(--sf-bg-0)' }}>
        <Code2 size={20} style={{ color: 'var(--sf-accent)' }} />
        <h1 className="text-[15px] font-bold" style={{ color: 'var(--sf-text-0)' }}>
          Code Studio
        </h1>

        {/* Separador */}
        <div className="w-px h-5 bg-white/10" />

        {/* Seletor de projeto */}
        <div className="relative">
          <button
            onClick={() => setDropProjeto(!dropProjeto)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all hover:border-white/20"
            style={{
              background: 'rgba(255,255,255,0.03)',
              borderColor: 'var(--sf-border-subtle)',
              color: 'var(--sf-text-0)',
            }}
          >
            <FolderKanban size={14} style={{ color: projetoAtivo ? '#818cf8' : 'var(--sf-accent)' }} />
            <span className="max-w-[200px] truncate">
              {projetoAtivo ? projetoAtivo.nome : 'Synerium Factory'}
            </span>
            {projetoAtivo?.stack && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5" style={{ color: 'var(--sf-text-3)' }}>
                {projetoAtivo.stack.slice(0, 25)}
              </span>
            )}
            {projetoAtivo?.repositorio && (
              <GitBranch size={10} className="text-emerald-400" />
            )}
            <ChevronDown size={12} style={{ color: 'var(--sf-text-3)' }} />
          </button>

          {/* Dropdown de projetos */}
          {dropProjeto && (
            <div
              className="absolute top-full left-0 mt-1 rounded-xl border shadow-2xl overflow-hidden"
              style={{
                background: 'var(--sf-bg-tooltip)',
                borderColor: 'var(--sf-border-subtle)',
                minWidth: '280px',
                zIndex: 50,
              }}
            >
              {/* Opcao padrao: Synerium Factory */}
              <button
                onClick={usarPadrao}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-white/5 ${
                  !projetoAtivo ? 'bg-emerald-500/5 border-l-2 border-emerald-500' : ''
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(16,185,129,0.1)' }}>
                  <Code2 size={14} className="text-emerald-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold truncate" style={{ color: 'var(--sf-text-0)' }}>
                    Synerium Factory
                  </p>
                  <p className="text-[10px]" style={{ color: 'var(--sf-text-3)' }}>
                    Projeto principal (padrao)
                  </p>
                </div>
              </button>

              {/* Separador */}
              {projetos.length > 0 && (
                <div className="px-4 py-1.5" style={{ borderTop: '1px solid var(--sf-border-subtle)' }}>
                  <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--sf-text-3)' }}>
                    Projetos cadastrados
                  </p>
                </div>
              )}

              {/* Lista de projetos */}
              <div className="max-h-60 overflow-y-auto">
                {projetos.map(p => (
                  <button
                    key={p.id}
                    onClick={() => trocarProjeto(p)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-white/5 ${
                      projetoAtivo?.id === p.id ? 'bg-indigo-500/5 border-l-2 border-indigo-500' : ''
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: 'rgba(129,140,248,0.1)' }}>
                      <FolderKanban size={14} className="text-indigo-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-[12px] font-semibold truncate" style={{ color: 'var(--sf-text-0)' }}>
                          {p.nome}
                        </p>
                        {p.repositorio && <GitBranch size={10} className="text-emerald-400 flex-shrink-0" />}
                      </div>
                      <p className="text-[10px] truncate" style={{ color: 'var(--sf-text-3)' }}>
                        {p.stack || p.caminho || 'Sem stack definida'}
                      </p>
                    </div>
                    {!p.caminho && (
                      <AlertCircle size={12} className="text-amber-400 flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Indicador do projeto ativo */}
        {projetoAtivo && !projetoAtivo.caminho && !projetoAtivo.repositorio && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <AlertCircle size={11} className="text-amber-400" />
            <span className="text-[10px] text-amber-400 font-medium">Caminho nao configurado</span>
          </div>
        )}

        {/* Botoes git pull + push */}
        {projetoAtivo?.repositorio && (
          <>
            <button
              onClick={executarPull}
              disabled={fazendoPull}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium border transition-all hover:bg-white/5 disabled:opacity-50"
              style={{ borderColor: 'var(--sf-border-subtle)', color: 'var(--sf-text-2)' }}
              title="Atualizar repositorio (git pull)"
            >
              {fazendoPull ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <Download size={11} />
              )}
              Pull
            </button>
            <button
              onClick={() => setMostrarPushDialog(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium border transition-all hover:bg-white/5"
              style={{ borderColor: 'var(--sf-border-subtle)', color: '#10b981' }}
              title="Enviar commits e criar Pull Request"
            >
              <Upload size={11} />
              Push
            </button>
          </>
        )}

        {/* Mensagem do pull */}
        {mensagemPull && (
          <span className="text-[10px] px-2 py-0.5 rounded"
            style={{ color: mensagemPull.includes('OK') ? '#34d399' : '#f87171', background: 'rgba(255,255,255,0.03)' }}>
            {mensagemPull.slice(0, 60)}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Botao recarregar arvore */}
        <button
          onClick={carregarArvore}
          disabled={carregando}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all hover:bg-white/5 disabled:opacity-50"
          style={{ color: 'var(--sf-text-3)' }}
          title="Recarregar arvore de arquivos"
        >
          <RefreshCw size={11} className={carregando ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Fechar dropdown ao clicar fora */}
      {dropProjeto && (
        <div className="fixed inset-0 z-40" onClick={() => setDropProjeto(false)} />
      )}

      {/* Layout principal: 3 paineis */}
      <div className="flex-1 flex overflow-hidden">
        {/* Painel esquerdo: Arvore de arquivos */}
        <div className="flex-shrink-0" style={{ width: '240px', borderRight: '1px solid var(--sf-border-subtle)' }}>
          {carregando || carregandoProjetos ? (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <Loader2 size={20} className="animate-spin" style={{ color: 'var(--sf-accent)' }} />
              <span className="text-[11px] text-center px-4" style={{ color: 'var(--sf-text-3)' }}>
                {projetoAtivo?.repositorio && !projetoAtivo?.caminho
                  ? 'Clonando repositorio...\nIsso pode levar alguns segundos'
                  : 'Carregando arquivos...'}
              </span>
            </div>
          ) : erroArvore ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 px-4 text-center">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(239,68,68,0.1)' }}>
                <Code2 size={18} style={{ color: '#ef4444' }} />
              </div>
              <p className="text-[11px]" style={{ color: '#ef4444' }}>{erroArvore}</p>
              <button
                onClick={carregarArvore}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium"
                style={{ background: 'var(--sf-accent)', color: '#fff' }}
              >
                Tentar novamente
              </button>
            </div>
          ) : arvore.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 px-4 text-center">
              <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>Nenhum arquivo encontrado</p>
              <button
                onClick={carregarArvore}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium"
                style={{ background: 'var(--sf-accent)', color: '#fff' }}
              >
                Recarregar
              </button>
            </div>
          ) : (
            <FileTree arvore={arvore} arquivoAtivo={abaAtiva} onSelect={abrirArquivo} />
          )}
        </div>

        {/* Painel central: Editor */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <EditorTabs abas={abas} abaAtiva={abaAtiva} onSelect={setAbaAtiva} onClose={fecharAba} />

          <Toolbar
            caminho={abaAtiva || undefined}
            linguagem={abaAtiva ? linguagemAtiva : undefined}
            modificado={modificadoAtivo}
            salvando={salvando}
            editavel={editavelAtivo}
            onSalvar={handleSalvar}
            onToggleAgente={toggleAgente}
            agentePainelAberto={agentePainel}
            onToggleHistorico={toggleHistorico}
            historicoPainelAberto={historicoPainel}
            onTogglePreview={() => setPreviewAberto(!previewAberto)}
            previewAberto={previewAberto}
            suportaPreview={abaAtiva ? suportaPreview(linguagemAtiva) : false}
          />

          <div className="flex-1 flex flex-col overflow-hidden">
            {abaAtiva ? (
              <>
                <div style={{ height: previewAberto && suportaPreview(linguagemAtiva) ? '55%' : '100%' }}
                  className="overflow-hidden">
                  <CodeEditor
                    key={abaAtiva}
                    conteudo={conteudoAtivo}
                    linguagem={linguagemAtiva}
                    editavel={editavelAtivo}
                    onChange={handleChange}
                    onSave={handleSalvar}
                  />
                </div>

                {previewAberto && suportaPreview(linguagemAtiva) && (
                  <div className="overflow-hidden" style={{
                    height: '45%',
                    borderTop: '1px solid var(--sf-border-subtle)',
                  }}>
                    <div className="flex items-center justify-between px-3 py-1" style={{
                      background: 'rgba(16,185,129,0.05)',
                      borderBottom: '1px solid var(--sf-border-subtle)',
                    }}>
                      <div className="flex items-center gap-2">
                        <Eye size={12} style={{ color: 'var(--sf-accent)' }} />
                        <span className="text-[10px] font-semibold" style={{ color: 'var(--sf-accent)' }}>Preview</span>
                      </div>
                      <button onClick={() => setPreviewAberto(false)} className="p-0.5 rounded hover:bg-white/5"
                        style={{ color: 'var(--sf-text-3)' }}>
                        <EyeOff size={12} />
                      </button>
                    </div>
                    <iframe
                      srcDoc={gerarPreviewHtml(conteudoAtivo, linguagemAtiva)}
                      sandbox="allow-scripts"
                      className="w-full border-0"
                      style={{ height: 'calc(100% - 28px)', background: '#1e1e2e' }}
                      title="Preview"
                    />
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Code2 size={48} className="mx-auto mb-4" style={{ color: 'var(--sf-text-3)', opacity: 0.2 }} />
                  <p className="text-[14px] font-medium" style={{ color: 'var(--sf-text-2)' }}>
                    Selecione um arquivo
                  </p>
                  <p className="text-[11px] mt-1" style={{ color: 'var(--sf-text-3)' }}>
                    Clique em um arquivo na arvore a esquerda para abrir
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Painel direito: Agente IA ou Historico */}
        {agentePainel && (
          <div className="flex-shrink-0" style={{ width: '320px' }}>
            <AgentPanel
              caminhoAtivo={abaAtiva || undefined}
              conteudoAtivo={abaAtiva ? conteudoAtivo : undefined}
              linguagem={linguagemAtiva}
              onFechar={() => setAgentePainel(false)}
              agenteNome={agenteNome || undefined}
              projetoId={projetoId}
              projetoNome={projetoAtivo?.nome}
              projetoStack={projetoAtivo?.stack}
              onArquivoAtualizado={abaAtiva ? () => {
                lerArquivo(abaAtiva, projetoId).then(arq => {
                  setConteudos(prev => new Map(prev).set(abaAtiva, arq.conteudo))
                  setConteudosOriginal(prev => new Map(prev).set(abaAtiva, arq.conteudo))
                }).catch(() => {})
              } : undefined}
            />
          </div>
        )}
        {historicoPainel && (
          <div className="flex-shrink-0" style={{ width: '320px' }}>
            <HistoricoPanel
              projetoId={projetoId}
              onFechar={() => setHistoricoPainel(false)}
              onAbrirArquivo={abrirArquivo}
            />
          </div>
        )}
      </div>

      {/* PushDialog modal */}
      {mostrarPushDialog && projetoAtivo && (
        <PushDialog
          projetoId={projetoAtivo.id}
          projetoNome={projetoAtivo.nome}
          onFechar={() => setMostrarPushDialog(false)}
        />
      )}
    </div>
  )
}
