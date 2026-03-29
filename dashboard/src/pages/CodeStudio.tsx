/* Code Studio — Editor de código integrado ao Synerium Factory */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Code2, Loader2, Eye, EyeOff } from 'lucide-react'
import FileTree from '../components/code-studio/FileTree'
import EditorTabs, { type TabInfo } from '../components/code-studio/EditorTabs'
import CodeEditor from '../components/code-studio/CodeEditor'
import Toolbar from '../components/code-studio/Toolbar'
import AgentPanel from '../components/code-studio/AgentPanel'
import { buscarArvore, lerArquivo, salvarArquivo, type ArquivoArvore } from '../services/codeStudio'

export default function CodeStudio() {
  // Ler agente da URL (quando vem do Escritório Virtual)
  const [searchParams] = useSearchParams()
  const agenteNome = useMemo(() => searchParams.get('agente') || '', [searchParams])

  // Estado da árvore
  const [arvore, setArvore] = useState<ArquivoArvore[]>([])
  const [carregando, setCarregando] = useState(true)
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

  // Estado do painel de agente — abre automaticamente se veio do Escritório
  const [agentePainel, setAgentePainel] = useState(!!agenteNome)

  // Estado do preview
  const [previewAberto, setPreviewAberto] = useState(false)

  // Linguagens que suportam preview
  const suportaPreview = (lang: string) =>
    ['html', 'javascript', 'typescript', 'markdown'].includes(lang)

  // Gerar conteúdo do preview
  const gerarPreviewHtml = useCallback((conteudo: string, lang: string): string => {
    if (lang === 'html') return conteudo
    if (lang === 'markdown') {
      // Preview simples de markdown → HTML via regex básico
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
    // Para JS/TS, mostrar o código em uma estrutura básica
    return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body{font-family:system-ui;padding:24px;background:#1e1e2e;color:#cdd6f4;margin:0}
  pre{background:#181825;padding:16px;border-radius:8px;overflow:auto;font-size:13px;line-height:1.6}
  h3{color:#a6e3a1;margin-bottom:8px}
</style></head><body>
<h3>📄 ${abaAtiva?.split('/').pop() || 'arquivo'}</h3>
<pre>${conteudo.replace(/</g,'&lt;').replace(/>/g,'&gt;').slice(0, 5000)}</pre>
</body></html>`
  }, [abaAtiva])

  // Carregar árvore ao montar
  const carregarArvore = useCallback(async () => {
    setCarregando(true)
    setErroArvore('')
    try {
      const dados = await buscarArvore()
      setArvore(dados)
    } catch (e) {
      setErroArvore(e instanceof Error ? e.message : 'Erro ao carregar árvore')
      console.error('[CodeStudio] Erro ao carregar árvore:', e)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => { carregarArvore() }, [carregarArvore])

  // Abrir arquivo
  const abrirArquivo = useCallback(async (caminho: string) => {
    // Se já está aberto, só ativa
    if (abas.some(a => a.caminho === caminho)) {
      setAbaAtiva(caminho)
      return
    }

    try {
      const arquivo = await lerArquivo(caminho)
      const nome = caminho.split('/').pop() || caminho

      setConteudos(prev => new Map(prev).set(caminho, arquivo.conteudo))
      setConteudosOriginal(prev => new Map(prev).set(caminho, arquivo.conteudo))
      setLinguagens(prev => new Map(prev).set(caminho, arquivo.linguagem))
      setEditaveis(prev => new Map(prev).set(caminho, arquivo.editavel))
      setAbas(prev => [...prev, { caminho, nome, modificado: false, linguagem: arquivo.linguagem }])
      setAbaAtiva(caminho)
    } catch {
      // Erro silencioso — poderia mostrar toast
    }
  }, [abas])

  // Fechar aba
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

  // Alterar conteúdo
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

  // Salvar arquivo
  const handleSalvar = useCallback(async () => {
    if (!abaAtiva || !modificados.has(abaAtiva)) return
    const conteudo = conteudos.get(abaAtiva)
    if (conteudo === undefined) return

    setSalvando(true)
    try {
      await salvarArquivo(abaAtiva, conteudo)
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
  }, [abaAtiva, modificados, conteudos])

  const conteudoAtivo = conteudos.get(abaAtiva) || ''
  const linguagemAtiva = linguagens.get(abaAtiva) || 'text'
  const editavelAtivo = editaveis.get(abaAtiva) ?? false
  const modificadoAtivo = modificados.has(abaAtiva)

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 64px)', margin: '-24px', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--sf-border-subtle)', background: 'var(--sf-bg-0)' }}>
        <Code2 size={20} style={{ color: 'var(--sf-accent)' }} />
        <h1 className="text-[15px] font-bold" style={{ color: 'var(--sf-text-0)' }}>
          Code Studio
        </h1>
        <span className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
          Editor de código integrado
        </span>
      </div>

      {/* Layout principal: 3 painéis */}
      <div className="flex-1 flex overflow-hidden">
        {/* Painel esquerdo: Árvore de arquivos */}
        <div className="flex-shrink-0" style={{ width: '240px', borderRight: '1px solid var(--sf-border-subtle)' }}>
          {carregando ? (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <Loader2 size={20} className="animate-spin" style={{ color: 'var(--sf-accent)' }} />
              <span className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>Carregando arquivos...</span>
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
          {/* Tabs */}
          <EditorTabs abas={abas} abaAtiva={abaAtiva} onSelect={setAbaAtiva} onClose={fecharAba} />

          {/* Toolbar */}
          <Toolbar
            caminho={abaAtiva || undefined}
            linguagem={abaAtiva ? linguagemAtiva : undefined}
            modificado={modificadoAtivo}
            salvando={salvando}
            editavel={editavelAtivo}
            onSalvar={handleSalvar}
            onToggleAgente={() => setAgentePainel(!agentePainel)}
            agentePainelAberto={agentePainel}
            onTogglePreview={() => setPreviewAberto(!previewAberto)}
            previewAberto={previewAberto}
            suportaPreview={abaAtiva ? suportaPreview(linguagemAtiva) : false}
          />

          {/* Editor + Preview */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {abaAtiva ? (
              <>
                {/* Editor */}
                <div className={previewAberto && suportaPreview(linguagemAtiva) ? 'flex-1 overflow-hidden' : 'flex-1 overflow-hidden'}
                  style={{ height: previewAberto && suportaPreview(linguagemAtiva) ? '55%' : '100%' }}>
                  <CodeEditor
                    key={abaAtiva}
                    conteudo={conteudoAtivo}
                    linguagem={linguagemAtiva}
                    editavel={editavelAtivo}
                    onChange={handleChange}
                    onSave={handleSalvar}
                  />
                </div>

                {/* Preview */}
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
                        <span className="text-[10px] font-semibold" style={{ color: 'var(--sf-accent)' }}>
                          Preview
                        </span>
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
                    Clique em um arquivo na árvore à esquerda para abrir
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Painel direito: Agente IA */}
        {agentePainel && (
          <div className="flex-shrink-0" style={{ width: '320px' }}>
            <AgentPanel
              caminhoAtivo={abaAtiva || undefined}
              conteudoAtivo={abaAtiva ? conteudoAtivo : undefined}
              linguagem={linguagemAtiva}
              onFechar={() => setAgentePainel(false)}
              agenteNome={agenteNome || undefined}
            />
          </div>
        )}
      </div>
    </div>
  )
}
