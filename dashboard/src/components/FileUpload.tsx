/* FileUpload — Componente reutilizável de upload com drag & drop */

import { useState, useRef, useCallback } from 'react'
import type { FileAttachment } from '../types'
import { uploadArquivos } from '../services/api'

interface Props {
  onUpload: (arquivos: FileAttachment[]) => void
  compact?: boolean  // modo compacto para chat
}

const iconesPorTipo: Record<string, string> = {
  imagem: '🖼️',
  video: '🎬',
  audio: '🎵',
  pdf: '📕',
  documento: '📄',
}

export function FileUploadArea({ onUpload, compact }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [pendentes, setPendentes] = useState<File[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  const adicionarArquivos = useCallback((files: FileList | File[]) => {
    const novos = Array.from(files)
    setPendentes(prev => [...prev, ...novos])
  }, [])

  const removerPendente = (idx: number) => {
    setPendentes(prev => prev.filter((_, i) => i !== idx))
  }

  const enviar = async () => {
    if (pendentes.length === 0) return
    setEnviando(true)
    try {
      const resultado = await uploadArquivos(pendentes)
      onUpload(resultado.filter(r => !r.erro))
      setPendentes([])
    } catch (e) {
      console.error('Erro no upload:', e)
    } finally {
      setEnviando(false)
    }
  }

  // Auto-enviar em modo compacto
  const handleFilesCompact = async (files: FileList | File[]) => {
    const novos = Array.from(files)
    if (novos.length === 0) return
    setEnviando(true)
    try {
      const resultado = await uploadArquivos(novos)
      onUpload(resultado.filter(r => !r.erro))
    } catch (e) {
      console.error('Erro no upload:', e)
    } finally {
      setEnviando(false)
    }
  }

  if (compact) {
    return (
      <>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFilesCompact(e.target.files)}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={enviando}
          className="p-1.5 text-gray-400 hover:text-emerald-600 transition-colors disabled:opacity-50"
          title="Anexar arquivo"
        >
          {enviando ? (
            <span className="animate-spin">⏳</span>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          )}
        </button>
      </>
    )
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => e.target.files && adicionarArquivos(e.target.files)}
      />

      {/* Área de drop */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          if (e.dataTransfer.files) adicionarArquivos(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          dragOver
            ? 'border-emerald-500 bg-emerald-50'
            : 'border-gray-300 hover:border-emerald-400 hover:bg-gray-50'
        }`}
      >
        <div className="text-3xl mb-2">📎</div>
        <p className="text-sm text-gray-600">
          Arraste arquivos aqui ou <span className="text-emerald-600 font-medium">clique para selecionar</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Imagens, PDFs, documentos, vídeos — máx 50MB por arquivo
        </p>
      </div>

      {/* Arquivos pendentes */}
      {pendentes.length > 0 && (
        <div className="mt-3 space-y-2">
          {pendentes.map((file, idx) => (
            <div key={idx} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
              <span className="text-lg">
                {file.type.startsWith('image/') ? '🖼️' :
                 file.type.startsWith('video/') ? '🎬' :
                 file.type === 'application/pdf' ? '📕' : '📄'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700 truncate">{file.name}</p>
                <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB</p>
              </div>
              {file.type.startsWith('image/') && (
                <img
                  src={URL.createObjectURL(file)}
                  alt=""
                  className="w-10 h-10 rounded object-cover"
                />
              )}
              <button
                onClick={(e) => { e.stopPropagation(); removerPendente(idx) }}
                className="text-gray-400 hover:text-red-500"
              >
                ✕
              </button>
            </div>
          ))}

          <button
            onClick={enviar}
            disabled={enviando}
            className="w-full py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
          >
            {enviando ? 'Enviando...' : `Enviar ${pendentes.length} arquivo(s)`}
          </button>
        </div>
      )}
    </div>
  )
}

/* Preview de arquivos já enviados */
export function FilePreview({ arquivos }: { arquivos: FileAttachment[] }) {
  if (!arquivos || arquivos.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {arquivos.map((arq, idx) => (
        <a
          key={idx}
          href={arq.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 hover:bg-gray-50 transition-colors"
        >
          {arq.tipo === 'imagem' ? (
            <img src={arq.url} alt={arq.nome_original} className="w-8 h-8 rounded object-cover" />
          ) : (
            <span className="text-lg">{iconesPorTipo[arq.tipo] || '📄'}</span>
          )}
          <div className="min-w-0">
            <p className="text-xs text-gray-700 truncate max-w-[120px]">{arq.nome_original}</p>
            <p className="text-[10px] text-gray-400">{(arq.tamanho / 1024).toFixed(0)} KB</p>
          </div>
        </a>
      ))}
    </div>
  )
}
