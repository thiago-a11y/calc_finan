/* CodeEditor — Editor de código com CodeMirror 6 */

import { useEffect, useRef, useCallback } from 'react'
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import { autocompletion, completionKeymap } from '@codemirror/autocomplete'
import { bracketMatching, foldGutter, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { oneDark } from '@codemirror/theme-one-dark'

// Importações de linguagens
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { html } from '@codemirror/lang-html'
import { css } from '@codemirror/lang-css'
import { json } from '@codemirror/lang-json'
import { markdown } from '@codemirror/lang-markdown'

interface CodeEditorProps {
  conteudo: string
  linguagem: string
  editavel: boolean
  onChange: (novoConteudo: string) => void
  onSave: () => void
}

function obterExtensaoLinguagem(linguagem: string) {
  switch (linguagem) {
    case 'javascript': return javascript({ jsx: true })
    case 'typescript': return javascript({ jsx: true, typescript: true })
    case 'python': return python()
    case 'html': return html()
    case 'css': return css()
    case 'json': return json()
    case 'markdown': return markdown()
    default: return []
  }
}

export default function CodeEditor({ conteudo, linguagem, editavel, onChange, onSave }: CodeEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  const onSaveRef = useRef(onSave)

  onChangeRef.current = onChange
  onSaveRef.current = onSave

  const salvarKeymap = useCallback(() => {
    return keymap.of([{
      key: 'Mod-s',
      run: () => { onSaveRef.current(); return true },
    }])
  }, [])

  useEffect(() => {
    if (!containerRef.current) return

    // Limpar editor anterior
    if (viewRef.current) {
      viewRef.current.destroy()
      viewRef.current = null
    }

    const extensoes = [
      lineNumbers(),
      highlightActiveLine(),
      highlightActiveLineGutter(),
      drawSelection(),
      history(),
      foldGutter(),
      indentOnInput(),
      bracketMatching(),
      highlightSelectionMatches(),
      autocompletion(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      oneDark,
      obterExtensaoLinguagem(linguagem),
      keymap.of([
        ...defaultKeymap,
        ...historyKeymap,
        ...searchKeymap,
        ...completionKeymap,
        indentWithTab,
      ]),
      salvarKeymap(),
      EditorView.editable.of(editavel),
      EditorView.updateListener.of(update => {
        if (update.docChanged) {
          onChangeRef.current(update.state.doc.toString())
        }
      }),
      EditorView.theme({
        '&': {
          height: '100%',
          fontSize: '13px',
          fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
        },
        '.cm-scroller': { overflow: 'auto' },
        '.cm-gutters': {
          background: 'transparent',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        },
      }),
    ]

    const state = EditorState.create({
      doc: conteudo,
      extensions: extensoes,
    })

    viewRef.current = new EditorView({
      state,
      parent: containerRef.current,
    })

    return () => {
      viewRef.current?.destroy()
      viewRef.current = null
    }
  }, [conteudo, linguagem, editavel, salvarKeymap])

  return (
    <div
      ref={containerRef}
      className="h-full w-full overflow-hidden"
      style={{ background: '#282c34' }}
    />
  )
}
