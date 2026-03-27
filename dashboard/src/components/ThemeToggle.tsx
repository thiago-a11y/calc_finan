/* ThemeToggle — Componente premium de toggle Light/Dark Mode */

import { Sun, Moon } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTheme } from '../contexts/ThemeContext'

export default function ThemeToggle() {
  const { isDark, toggleTema } = useTheme()

  return (
    <button
      onClick={toggleTema}
      className="relative w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-300 hover:scale-105"
      style={{
        background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}`,
      }}
      aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
      title={isDark ? 'Modo Claro' : 'Modo Escuro'}
    >
      <motion.div
        key={isDark ? 'moon' : 'sun'}
        initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        exit={{ rotate: 90, opacity: 0, scale: 0.5 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        {isDark ? (
          <Moon size={15} className="text-gray-400" strokeWidth={1.5} />
        ) : (
          <Sun size={15} className="text-amber-500" strokeWidth={1.5} />
        )}
      </motion.div>
    </button>
  )
}
