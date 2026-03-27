/* ReuniaoVideo — Vídeo chamada real com LiveKit */

import { useState, useCallback, useEffect } from 'react'
import { LiveKitRoom, VideoConference, RoomAudioRenderer } from '@livekit/components-react'
import '@livekit/components-styles'
import { useAuth } from '../contexts/AuthContext'
import { Phone, PhoneOff, Video, X, Users, AlertCircle } from 'lucide-react'

interface Props {
  sala: string
  participantes: string[]
  onFechar: () => void
}

export default function ReuniaoVideo({ sala, participantes, onFechar }: Props) {
  const { token: authToken, usuario } = useAuth()
  const [livekitToken, setLivekitToken] = useState<string>('')
  const [livekitUrl, setLivekitUrl] = useState<string>('')
  const [fase, setFase] = useState<'lobby' | 'conectando' | 'sala' | 'erro'>('lobby')
  const [erro, setErro] = useState<string>('')
  const [permissaoMedia, setPermissaoMedia] = useState<boolean | null>(null)

  // Verificar permissão de câmera/microfone ao abrir
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ audio: true, video: true })
      .then(stream => {
        setPermissaoMedia(true)
        // Parar tracks imediatamente (só testando permissão)
        stream.getTracks().forEach(t => t.stop())
      })
      .catch(() => {
        setPermissaoMedia(false)
      })
  }, [])

  const entrar = useCallback(async () => {
    setFase('conectando')
    setErro('')

    try {
      const res = await fetch('/api/videocall/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ sala, participante: usuario?.nome || 'Participante' }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
        throw new Error(data.detail || 'Erro ao gerar token')
      }

      const data = await res.json()

      if (!data.token || !data.url) {
        throw new Error('Token ou URL do LiveKit não retornado pelo servidor')
      }

      console.log('[LiveKit] Conectando:', { url: data.url, sala: data.sala, participante: data.participante })

      setLivekitUrl(data.url)
      setLivekitToken(data.token)
      setFase('sala')

    } catch (e) {
      console.error('[LiveKit] Erro:', e)
      setErro(e instanceof Error ? e.message : 'Erro desconhecido')
      setFase('erro')
    }
  }, [sala, authToken, usuario])

  const sair = () => {
    setLivekitToken('')
    setLivekitUrl('')
    setFase('lobby')
    onFechar()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,.9)', backdropFilter: 'blur(12px)' }}>

      <div className="relative w-full max-w-5xl mx-4 rounded-2xl overflow-hidden"
        style={{ background: 'var(--sf-bg-1, #111)', border: '1px solid var(--sf-border-default, #222)', maxHeight: '90vh' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3"
          style={{ borderBottom: '1px solid var(--sf-border-subtle, #1a1a1a)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
              <Video size={14} className="text-emerald-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--sf-text-0, #f8f8f8)' }}>
                Reunião: {sala.replace(/^sf-\d+$/, 'Nova Reunião')}
              </h3>
              <p className="text-[10px]" style={{ color: 'var(--sf-text-3, #888)' }}>
                {participantes.join(', ')} · Sofia (transcritora)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {fase === 'sala' && (
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-lg border border-emerald-500/20">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                Ao vivo
              </span>
            )}
            <button onClick={sair}
              className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-red-500/20 transition-colors"
              title="Sair da reunião">
              <X size={14} style={{ color: '#ef4444' }} />
            </button>
          </div>
        </div>

        {/* === LOBBY === */}
        {fase === 'lobby' && (
          <div className="flex flex-col items-center justify-center py-16 px-8">
            <div className="w-20 h-20 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-6">
              <Users size={32} className="text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--sf-text-0, #f8f8f8)' }}>Entrar na reunião</h3>
            <p className="text-sm mb-1" style={{ color: 'var(--sf-text-2, #aaa)' }}>
              Sala: <span className="font-mono text-emerald-400">{sala}</span>
            </p>
            <p className="text-xs mb-6" style={{ color: 'var(--sf-text-3, #666)' }}>
              {participantes.join(', ')}
            </p>

            {/* Status de permissão */}
            {permissaoMedia === false && (
              <div className="mb-4 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs flex items-center gap-2 max-w-md">
                <AlertCircle size={14} />
                <div>
                  <p className="font-medium">Permissão de câmera/microfone necessária</p>
                  <p className="text-amber-500/70 mt-0.5">Clique no ícone de cadeado na barra de endereço e permita câmera e microfone.</p>
                </div>
              </div>
            )}
            {permissaoMedia === true && (
              <div className="mb-4 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] flex items-center gap-1.5">
                <Video size={10} /> Câmera e microfone disponíveis
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={entrar}
                className="flex items-center gap-2 px-6 py-3 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-xl text-sm font-medium hover:bg-emerald-500/30 transition-all">
                <Phone size={14} /> Entrar com áudio e vídeo
              </button>
              <button onClick={onFechar}
                className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm transition-all"
                style={{ background: 'var(--sf-bg-hover, #1a1a1a)', color: 'var(--sf-text-3, #888)', border: '1px solid var(--sf-border-default, #222)' }}>
                <PhoneOff size={14} /> Cancelar
              </button>
            </div>

            <p className="text-[10px] mt-6" style={{ color: 'var(--sf-text-4, #555)' }}>
              Sofia entrará automaticamente para transcrever e gerar a ata
            </p>
          </div>
        )}

        {/* === CONECTANDO === */}
        {fase === 'conectando' && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-12 h-12 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
            <p className="text-sm" style={{ color: 'var(--sf-text-2, #aaa)' }}>Conectando ao LiveKit...</p>
            <p className="text-[10px] mt-1" style={{ color: 'var(--sf-text-4, #555)' }}>Aguarde enquanto entramos na sala</p>
          </div>
        )}

        {/* === SALA LIVEKIT === */}
        {fase === 'sala' && livekitToken && livekitUrl && (
          <div style={{ height: 520 }}>
            <LiveKitRoom
              serverUrl={livekitUrl}
              token={livekitToken}
              connect={true}
              connectOptions={{
                autoSubscribe: true,
              }}
              options={{
                adaptiveStream: true,
                dynacast: true,
                publishDefaults: {
                  simulcast: true,
                },
              }}
              onConnected={() => {
                console.log('[LiveKit] Conectado com sucesso!')
              }}
              onDisconnected={() => {
                console.log('[LiveKit] Desconectado')
                sair()
              }}
              onError={(error) => {
                console.error('[LiveKit] Erro na sala:', error)
                setErro(error?.message || 'Erro na conexão')
                setFase('erro')
              }}
              style={{ height: '100%' }}
              data-lk-theme="default"
            >
              <VideoConference />
              <RoomAudioRenderer />
            </LiveKitRoom>
          </div>
        )}

        {/* === ERRO === */}
        {fase === 'erro' && (
          <div className="flex flex-col items-center justify-center py-16 px-8">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
              <AlertCircle size={24} style={{ color: '#ef4444' }} />
            </div>
            <h3 className="text-sm font-semibold mb-2" style={{ color: '#ef4444' }}>Erro na conexão</h3>
            <p className="text-xs text-center max-w-md mb-6" style={{ color: 'var(--sf-text-3, #888)' }}>
              {erro || 'Não foi possível conectar ao servidor de vídeo.'}
            </p>
            <div className="flex gap-3">
              <button onClick={() => { setFase('lobby'); setErro('') }}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/30 transition-all">
                Tentar novamente
              </button>
              <button onClick={onFechar}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs transition-all"
                style={{ background: 'var(--sf-bg-hover, #1a1a1a)', color: 'var(--sf-text-3, #888)', border: '1px solid var(--sf-border-default, #222)' }}>
                Fechar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
