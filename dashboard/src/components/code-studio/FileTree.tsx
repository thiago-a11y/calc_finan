/* FileTree — Árvore de arquivos recursiva com busca */

import { useState, useMemo } from 'react'
import { ChevronRight, ChevronDown, FileCode, FileJson, FileText, Folder, FolderOpen, Search, File } from 'lucide-react'
import type { ArquivoArvore } from '../../services/codeStudio'

interface FileTreeProps {
  arvore: ArquivoArvore[]
  arquivoAtivo?: string
  onSelect: (caminho: string) => void
}

const ICONES_EXT: Record<string, typeof FileCode> = {
  '.py': FileCode, '.tsx': FileCode, '.ts': FileCode, '.jsx': FileCode, '.js': FileCode,
  '.json': FileJson, '.md': FileText, '.txt': FileText, '.env': FileText,
  '.html': FileCode, '.css': FileCode, '.sql': FileCode, '.sh': FileCode,
}

function filtrarArvore(arvore: ArquivoArvore[], termo: string): ArquivoArvore[] {
  if (!termo) return arvore
  const lower = termo.toLowerCase()
  return arvore.reduce<ArquivoArvore[]>((acc, item) => {
    if (item.tipo === 'pasta') {
      const filhosFiltrados = filtrarArvore(item.filhos || [], termo)
      if (filhosFiltrados.length > 0 || item.nome.toLowerCase().includes(lower)) {
        acc.push({ ...item, filhos: filhosFiltrados })
      }
    } else if (item.nome.toLowerCase().includes(lower)) {
      acc.push(item)
    }
    return acc
  }, [])
}

function ItemArvore({ item, nivel, ativo, onSelect, buscaAtiva }: {
  item: ArquivoArvore; nivel: number; ativo?: string
  onSelect: (c: string) => void; buscaAtiva: boolean
}) {
  const [aberto, setAberto] = useState(nivel < 1 || buscaAtiva)
  const Icon = item.tipo === 'pasta'
    ? (aberto ? FolderOpen : Folder)
    : (ICONES_EXT[item.extensao || ''] || File)

  const ehAtivo = item.caminho === ativo

  if (item.tipo === 'pasta') {
    return (
      <div>
        <button
          onClick={() => setAberto(!aberto)}
          className="w-full flex items-center gap-1.5 px-2 py-[3px] text-[12px] rounded transition-colors hover:bg-white/5"
          style={{ paddingLeft: `${12 + nivel * 14}px`, color: 'var(--sf-text-2)' }}
        >
          {aberto ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <Icon size={14} style={{ color: '#f59e0b', flexShrink: 0 }} />
          <span className="truncate">{item.nome}</span>
        </button>
        {aberto && item.filhos?.map(filho => (
          <ItemArvore key={filho.caminho} item={filho} nivel={nivel + 1}
            ativo={ativo} onSelect={onSelect} buscaAtiva={buscaAtiva} />
        ))}
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelect(item.caminho)}
      className="w-full flex items-center gap-1.5 px-2 py-[3px] text-[12px] rounded transition-all"
      style={{
        paddingLeft: `${26 + nivel * 14}px`,
        color: ehAtivo ? 'var(--sf-accent)' : 'var(--sf-text-3)',
        background: ehAtivo ? 'rgba(16,185,129,0.08)' : 'transparent',
      }}
    >
      <Icon size={13} style={{ flexShrink: 0 }} />
      <span className="truncate">{item.nome}</span>
    </button>
  )
}

export default function FileTree({ arvore, arquivoAtivo, onSelect }: FileTreeProps) {
  const [busca, setBusca] = useState('')
  const arvoreFiltrada = useMemo(() => filtrarArvore(arvore, busca), [arvore, busca])

  return (
    <div className="h-full flex flex-col" style={{ borderRight: '1px solid var(--sf-border-subtle)' }}>
      {/* Busca */}
      <div className="px-2 py-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--sf-border-subtle)' }}>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg"
          style={{ background: 'var(--sf-bg-1)' }}>
          <Search size={12} style={{ color: 'var(--sf-text-3)', flexShrink: 0 }} />
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar arquivo..."
            className="bg-transparent border-none outline-none text-[11px] w-full"
            style={{ color: 'var(--sf-text-1)' }}
          />
        </div>
      </div>

      {/* Árvore */}
      <div className="flex-1 overflow-auto py-1" style={{ scrollbarWidth: 'thin' }}>
        {arvoreFiltrada.length === 0 ? (
          <p className="text-center text-[11px] py-8" style={{ color: 'var(--sf-text-3)' }}>
            {busca ? 'Nenhum arquivo encontrado' : 'Carregando...'}
          </p>
        ) : (
          arvoreFiltrada.map(item => (
            <ItemArvore key={item.caminho} item={item} nivel={0}
              ativo={arquivoAtivo} onSelect={onSelect} buscaAtiva={!!busca} />
          ))
        )}
      </div>
    </div>
  )
}
