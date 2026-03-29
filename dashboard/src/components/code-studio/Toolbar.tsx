/* Toolbar — Barra de ferramentas do Code Studio */

import { Save, Undo2, Redo2, Bot, Check, Loader2 } from 'lucide-react'

interface ToolbarProps {
  caminho?: string
  linguagem?: string
  modificado: boolean
  salvando: boolean
  editavel: boolean
  onSalvar: () => void
  onToggleAgente: () => void
  agentePainelAberto: boolean
}

export default function Toolbar({
  caminho, linguagem, modificado, salvando, editavel,
  onSalvar, onToggleAgente, agentePainelAberto,
}: ToolbarProps) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5 flex-shrink-0"
      style={{
        borderBottom: '1px solid var(--sf-border-subtle)',
        background: 'var(--sf-bg-0)',
      }}>
      {/* Breadcrumb do arquivo */}
      <div className="flex items-center gap-2 min-w-0">
        {caminho ? (
          <span className="text-[11px] font-mono truncate" style={{ color: 'var(--sf-text-2)' }}>
            {caminho}
          </span>
        ) : (
          <span className="text-[11px] italic" style={{ color: 'var(--sf-text-3)' }}>
            Selecione um arquivo na árvore
          </span>
        )}
        {linguagem && (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
            style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--sf-accent)' }}>
            {linguagem}
          </span>
        )}
        {modificado && (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold"
            style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
            Não salvo
          </span>
        )}
      </div>

      {/* Ações */}
      <div className="flex items-center gap-1">
        {/* Salvar */}
        <button
          onClick={onSalvar}
          disabled={!editavel || !modificado || salvando}
          className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all disabled:opacity-30"
          style={{
            color: modificado ? '#fff' : 'var(--sf-text-3)',
            background: modificado ? 'var(--sf-accent)' : 'transparent',
          }}
          title="Salvar (Ctrl+S)"
        >
          {salvando ? <Loader2 size={12} className="animate-spin" /> : modificado ? <Save size={12} /> : <Check size={12} />}
          {salvando ? 'Salvando...' : modificado ? 'Salvar' : 'Salvo'}
        </button>

        {/* Desfazer / Refazer (visuais, CodeMirror já tem) */}
        <button className="p-1 rounded hover:bg-white/5 transition-colors"
          style={{ color: 'var(--sf-text-3)' }} title="Desfazer (Ctrl+Z)">
          <Undo2 size={13} />
        </button>
        <button className="p-1 rounded hover:bg-white/5 transition-colors"
          style={{ color: 'var(--sf-text-3)' }} title="Refazer (Ctrl+Shift+Z)">
          <Redo2 size={13} />
        </button>

        {/* Separador */}
        <div className="w-px h-4 mx-1" style={{ background: 'var(--sf-border-subtle)' }} />

        {/* Toggle Agente */}
        <button
          onClick={onToggleAgente}
          className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all"
          style={{
            color: agentePainelAberto ? '#fff' : 'var(--sf-text-3)',
            background: agentePainelAberto ? 'rgba(139,92,246,0.2)' : 'transparent',
          }}
          title="Painel do Agente IA"
        >
          <Bot size={13} />
          Agente IA
        </button>
      </div>
    </div>
  )
}
