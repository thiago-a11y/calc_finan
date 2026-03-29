/* EditorTabs — Abas de arquivos abertos */

import { X } from 'lucide-react'

export interface TabInfo {
  caminho: string
  nome: string
  modificado: boolean
  linguagem: string
}

interface EditorTabsProps {
  abas: TabInfo[]
  abaAtiva: string
  onSelect: (caminho: string) => void
  onClose: (caminho: string) => void
}

export default function EditorTabs({ abas, abaAtiva, onSelect, onClose }: EditorTabsProps) {
  if (abas.length === 0) return null

  return (
    <div className="flex items-center overflow-x-auto flex-shrink-0"
      style={{
        borderBottom: '1px solid var(--sf-border-subtle)',
        background: 'var(--sf-bg-0)',
        scrollbarWidth: 'none',
      }}>
      {abas.map(aba => {
        const ativo = aba.caminho === abaAtiva
        return (
          <div
            key={aba.caminho}
            onClick={() => onSelect(aba.caminho)}
            className="flex items-center gap-1.5 px-3 py-2 cursor-pointer text-[12px] font-medium transition-colors relative select-none flex-shrink-0"
            style={{
              color: ativo ? 'var(--sf-text-0)' : 'var(--sf-text-3)',
              background: ativo ? 'var(--sf-bg-1)' : 'transparent',
              borderRight: '1px solid var(--sf-border-subtle)',
            }}
          >
            {aba.modificado && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
            )}
            <span className="truncate max-w-[140px]">{aba.nome}</span>
            <button
              onClick={e => { e.stopPropagation(); onClose(aba.caminho) }}
              className="p-0.5 rounded hover:bg-white/10 transition-colors flex-shrink-0"
              style={{ color: 'var(--sf-text-3)' }}
            >
              <X size={11} />
            </button>
            {ativo && (
              <div className="absolute bottom-0 left-0 right-0 h-[2px]"
                style={{ background: 'var(--sf-accent)' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
