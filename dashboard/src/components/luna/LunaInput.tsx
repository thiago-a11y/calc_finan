/* LunaInput — Area de entrada de texto com voz (Web Speech API) */

import { useState, useRef, useCallback, useEffect, type KeyboardEvent, type ChangeEvent } from 'react'
import { ArrowUp, Mic, Loader2 } from 'lucide-react'

interface LunaInputProps {
  onEnviar: (texto: string) => void
  carregando: boolean
  disabled?: boolean
}

/** Verifica se Web Speech API esta disponivel */
function getSpeechRecognition(): unknown {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

export default function LunaInput({ onEnviar, carregando, disabled = false }: LunaInputProps) {
  const [texto, setTexto] = useState('')
  const [gravando, setGravando] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)
  const speechDisponivel = useRef(!!getSpeechRecognition())

  /* Ajustar altura automaticamente */
  const ajustarAltura = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = '48px'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [])

  useEffect(() => {
    ajustarAltura()
  }, [texto, ajustarAltura])

  /* Enviar mensagem */
  const enviar = useCallback(() => {
    const trimmed = texto.trim()
    if (!trimmed || carregando || disabled) return
    onEnviar(trimmed)
    setTexto('')
    // Resetar altura
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px'
    }
  }, [texto, carregando, disabled, onEnviar])

  /* Teclado: Enter envia, Shift+Enter nova linha */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        enviar()
      }
    },
    [enviar],
  )

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      setTexto(e.target.value)
    },
    [],
  )

  /* --- Web Speech API --- */
  const toggleGravacao = useCallback(() => {
    if (gravando) {
      recognitionRef.current?.stop()
      setGravando(false)
      return
    }

    const SpeechRecClass = getSpeechRecognition() as any
    if (!SpeechRecClass) return

    const recognition = new SpeechRecClass()
    recognition.lang = 'pt-BR'
    recognition.continuous = true
    recognition.interimResults = false

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          transcript += event.results[i][0].transcript
        }
      }
      if (transcript) {
        setTexto((prev) => {
          const separador = prev && !prev.endsWith(' ') ? ' ' : ''
          return prev + separador + transcript
        })
      }
    }

    recognition.onerror = () => {
      setGravando(false)
    }

    recognition.onend = () => {
      setGravando(false)
    }

    recognitionRef.current = recognition
    recognition.start()
    setGravando(true)
  }, [gravando])

  /* Limpar recognition ao desmontar */
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

  const podeEnviar = texto.trim().length > 0 && !carregando && !disabled

  return (
    <div className="px-4 pb-4 pt-2">
      {/* Indicador de "pensando" */}
      {carregando && (
        <div
          className="flex items-center gap-2 mb-2 px-3 py-1.5 rounded-lg text-[12px]"
          style={{ color: 'var(--sf-accent)', background: 'rgba(16,185,129,0.06)' }}
        >
          <Loader2 size={14} className="animate-spin" />
          Luna esta pensando...
        </div>
      )}

      {/* Container do input */}
      <div
        className="relative flex items-end gap-2 rounded-2xl px-4 py-2 transition-all duration-200"
        style={{
          background: 'var(--sf-bg-2)',
          border: '1px solid var(--sf-border-subtle)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        {/* Textarea auto-expansivel */}
        <textarea
          ref={textareaRef}
          value={texto}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Envie uma mensagem para a Luna..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent outline-none text-[14px] leading-relaxed py-2 placeholder:opacity-40 disabled:opacity-50"
          style={{
            color: 'var(--sf-text-1)',
            minHeight: '48px',
            maxHeight: '200px',
            scrollbarWidth: 'thin',
          }}
        />

        {/* Botoes */}
        <div className="flex items-center gap-1.5 pb-1.5">
          {/* Microfone */}
          {speechDisponivel.current && (
            <button
              onClick={toggleGravacao}
              disabled={disabled}
              className="relative flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200 hover:scale-105 disabled:opacity-40"
              style={{
                background: gravando ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.05)',
                color: gravando ? '#ef4444' : 'var(--sf-text-3)',
              }}
              title={gravando ? 'Parar gravacao' : 'Entrada por voz'}
            >
              <Mic size={16} />
              {/* Pulsacao vermelha durante gravacao */}
              {gravando && (
                <span
                  className="absolute inset-0 rounded-full animate-ping"
                  style={{ background: 'rgba(239,68,68,0.25)' }}
                />
              )}
            </button>
          )}

          {/* Enviar */}
          <button
            onClick={enviar}
            disabled={!podeEnviar}
            className="flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200 hover:scale-105 disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: podeEnviar ? 'var(--sf-accent)' : 'rgba(255,255,255,0.06)',
              color: podeEnviar ? '#fff' : 'var(--sf-text-4)',
            }}
            title="Enviar mensagem"
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </div>
      </div>

      {/* Dica */}
      <p
        className="text-[11px] mt-1.5 text-center"
        style={{ color: 'var(--sf-text-4)' }}
      >
        Enter para enviar &middot; Shift+Enter para nova linha
      </p>
    </div>
  )
}
