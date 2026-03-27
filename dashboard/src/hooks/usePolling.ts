/* Hook de polling — busca dados periodicamente com reset ao trocar usuário */

import { useEffect, useState, useCallback } from 'react'

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervaloMs = 10000,
) {
  const [dados, setDados] = useState<T | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(true)

  const buscar = useCallback(async () => {
    try {
      const resultado = await fetcher()
      setDados(resultado)
      setErro(null)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro desconhecido')
    } finally {
      setCarregando(false)
    }
  }, [fetcher])

  useEffect(() => {
    buscar()
    const timer = setInterval(buscar, intervaloMs)

    // Resetar dados quando o usuário muda
    const handleUserChanged = () => {
      setDados(null)
      setCarregando(true)
      setErro(null)
      buscar()
    }
    window.addEventListener('sf-user-changed', handleUserChanged)

    return () => {
      clearInterval(timer)
      window.removeEventListener('sf-user-changed', handleUserChanged)
    }
  }, [buscar, intervaloMs])

  return { dados, erro, carregando, recarregar: buscar }
}
