/* LunaFileBlock — Detecta e renderiza blocos :::arquivo[...] nas respostas da Luna */

import { useState, useCallback, useEffect, useRef } from 'react'
import { FileDown, FileSpreadsheet, FileText, Presentation, File, Loader2, Eye, ExternalLink } from 'lucide-react'
import { gerarArquivo } from '../../services/luna'
import type { LunaArquivoGerado } from '../../services/luna'

interface LunaFileBlockProps {
  nome: string       // ex: "planilha_vendas.xlsx"
  conteudo: string   // conteúdo dentro do bloco :::arquivo
  conversaId?: string
  onPreview?: (url: string, formato: string, nome: string) => void
}

const iconesPorFormato: Record<string, typeof FileText> = {
  xlsx: FileSpreadsheet,
  csv: FileSpreadsheet,
  docx: FileText,
  pptx: Presentation,
  pdf: File,
  txt: FileText,
  md: FileText,
  json: FileText,
  html: FileText,
}

const coresPorFormato: Record<string, string> = {
  xlsx: '#10B981',   // emerald
  csv: '#10B981',
  docx: '#3B82F6',   // blue
  pptx: '#F59E0B',   // amber
  pdf: '#EF4444',    // red
  txt: '#8B5CF6',    // purple
  md: '#8B5CF6',
  json: '#6366F1',   // indigo
  html: '#EC4899',   // pink
}

const labelsPorFormato: Record<string, string> = {
  xlsx: 'Planilha Excel',
  csv: 'Planilha CSV',
  docx: 'Documento Word',
  pptx: 'Apresentação PowerPoint',
  pdf: 'Documento PDF',
  txt: 'Arquivo de Texto',
  md: 'Markdown',
  json: 'Dados JSON',
  html: 'Página HTML',
}

export default function LunaFileBlock({ nome, conteudo, conversaId, onPreview }: LunaFileBlockProps) {
  const [gerando, setGerando] = useState(false)
  const [arquivo, setArquivo] = useState<LunaArquivoGerado | null>(null)
  const [erro, setErro] = useState('')
  // Extrair formato do nome
  const partes = nome.split('.')
  const formato = partes.length > 1 ? partes[partes.length - 1].toLowerCase() : 'txt'
  const nomeBase = partes.slice(0, -1).join('.') || nome

  const Icone = iconesPorFormato[formato] || File
  const cor = coresPorFormato[formato] || '#10B981'
  const label = labelsPorFormato[formato] || 'Arquivo'

  const handleGerar = useCallback(async () => {
    setGerando(true)
    setErro('')
    try {
      const resultado = await gerarArquivo({
        formato,
        conteudo,
        nome: nomeBase,
        titulo: nomeBase.replace(/_/g, ' '),
        conversa_id: conversaId,
      })
      setArquivo(resultado)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao gerar arquivo')
    } finally {
      setGerando(false)
    }
  }, [formato, conteudo, nomeBase, conversaId])

  // Auto-gerar o arquivo assim que o componente montar
  // Assim o usuário já vê o botão de download pronto
  const autoGeradoRef = useRef(false)
  useEffect(() => {
    if (!autoGeradoRef.current && !arquivo && conteudo) {
      autoGeradoRef.current = true
      handleGerar()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleDownload = useCallback(() => {
    if (arquivo?.url) {
      const a = document.createElement('a')
      a.href = arquivo.url
      a.download = arquivo.nome
      a.click()
    }
  }, [arquivo])

  const handlePreview = useCallback(() => {
    if (arquivo?.url && onPreview) {
      onPreview(arquivo.url, formato, arquivo.nome)
    }
  }, [arquivo, formato, onPreview])

  return (
    <div
      className="rounded-xl overflow-hidden my-3 transition-all"
      style={{
        border: `1px solid ${cor}33`,
        background: `${cor}08`,
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3"
        style={{ borderBottom: `1px solid ${cor}20` }}
      >
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${cor}15` }}
        >
          <Icone size={20} style={{ color: cor }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold truncate" style={{ color: 'var(--sf-text-0)' }}>
            {nome}
          </p>
          <p className="text-[11px]" style={{ color: 'var(--sf-text-3)' }}>
            {label}
            {arquivo && ` · ${(arquivo.tamanho / 1024).toFixed(0)} KB`}
          </p>
        </div>
      </div>

      {/* Ações */}
      <div className="flex items-center gap-2 px-4 py-2.5">
        {!arquivo ? (
          <button
            onClick={handleGerar}
            disabled={gerando}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold transition-all hover:brightness-110 disabled:opacity-50"
            style={{
              background: gerando ? `${cor}80` : cor,
              color: '#fff',
            }}
          >
            {gerando ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Preparando arquivo...
              </>
            ) : (
              <>
                <FileDown size={14} />
                Baixar {formato.toUpperCase()}
              </>
            )}
          </button>
        ) : (
          <>
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold transition-all hover:brightness-110"
              style={{ background: cor, color: '#fff' }}
            >
              <FileDown size={14} />
              Baixar {formato.toUpperCase()}
            </button>

            {onPreview && ['html', 'pdf', 'md', 'txt'].includes(formato) && (
              <button
                onClick={handlePreview}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] font-medium transition-all hover:brightness-110"
                style={{
                  background: `${cor}15`,
                  color: cor,
                  border: `1px solid ${cor}30`,
                }}
              >
                <Eye size={14} />
                Preview
              </button>
            )}

            <a
              href={arquivo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] transition-all hover:brightness-110"
              style={{ color: 'var(--sf-text-3)' }}
            >
              <ExternalLink size={12} />
              Abrir
            </a>
          </>
        )}
      </div>

      {/* Erro */}
      {erro && (
        <div className="px-4 pb-3">
          <p className="text-[11px] text-red-400">{erro}</p>
        </div>
      )}
    </div>
  )
}

/**
 * Utilitário: Extrai blocos :::arquivo[nome] do texto da Luna.
 * Retorna { textoLimpo, arquivos: [{nome, conteudo}] }
 */
export function extrairBlocosArquivo(texto: string): {
  textoLimpo: string
  arquivos: { nome: string; conteudo: string }[]
} {
  const regex = /:::arquivo\[([^\]]+)\]\n([\s\S]*?):::/g
  const arquivos: { nome: string; conteudo: string }[] = []
  let textoLimpo = texto

  let match
  while ((match = regex.exec(texto)) !== null) {
    arquivos.push({
      nome: match[1].trim(),
      conteudo: match[2].trim(),
    })
  }

  // Remover os blocos do texto
  textoLimpo = texto.replace(regex, '').trim()

  return { textoLimpo, arquivos }
}
