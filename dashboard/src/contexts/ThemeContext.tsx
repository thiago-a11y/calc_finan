/* ThemeContext — Gerenciamento de tema (Dark/Light) */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

type Theme = 'dark' | 'light'

interface ThemeContextType {
  tema: Theme
  isDark: boolean
  toggleTema: () => void
  setTema: (t: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [tema, setTemaState] = useState<Theme>(() => {
    const salvo = localStorage.getItem('sf-theme')
    return (salvo === 'light' ? 'light' : 'dark') as Theme
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema)
    localStorage.setItem('sf-theme', tema)
  }, [tema])

  const toggleTema = () => setTemaState(t => t === 'dark' ? 'light' : 'dark')
  const setTema = (t: Theme) => setTemaState(t)

  return (
    <ThemeContext.Provider value={{ tema, isDark: tema === 'dark', toggleTema, setTema }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme deve estar dentro de ThemeProvider')
  return ctx
}
