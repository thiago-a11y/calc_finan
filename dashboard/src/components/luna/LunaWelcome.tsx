/* LunaWelcome — Tela de boas-vindas da Luna (quando nenhuma conversa esta selecionada) */

import { Moon } from 'lucide-react'
import { motion } from 'framer-motion'

interface LunaWelcomeProps {
  onSugestao: (texto: string) => void
}

const sugestoes = [
  { emoji: '\u{1F4A1}', texto: 'Me ajude a pensar em uma estrategia para...' },
  { emoji: '\u{1F4CA}', texto: 'Analise os pros e contras de...' },
  { emoji: '\u{1F527}', texto: 'Como posso formular um pedido para o agente...' },
  { emoji: '\u{1F4DD}', texto: 'Revise e melhore este texto...' },
]

export default function LunaWelcome({ onSugestao }: LunaWelcomeProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 sf-animate-in">
      {/* Icone principal com brilho emerald */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative mb-6"
      >
        <div
          className="absolute inset-0 rounded-full blur-2xl opacity-30"
          style={{ background: 'var(--sf-accent)', transform: 'scale(1.8)' }}
        />
        <div
          className="relative w-20 h-20 rounded-full flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, var(--sf-accent), #059669)',
            boxShadow: '0 0 40px rgba(16,185,129,0.3)',
          }}
        >
          <Moon size={36} color="#fff" strokeWidth={1.5} />
        </div>
      </motion.div>

      {/* Titulo */}
      <motion.h1
        initial={{ y: 12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.15, duration: 0.4 }}
        className="text-2xl font-bold mb-2"
        style={{ color: 'var(--sf-text-0)' }}
      >
        Ola! Sou a Luna {'\u{1F319}'}
      </motion.h1>

      <motion.p
        initial={{ y: 12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.25, duration: 0.4 }}
        className="text-[15px] font-medium mb-3"
        style={{ color: 'var(--sf-accent)' }}
      >
        Sua consultora estrategica e assistente geral
      </motion.p>

      <motion.p
        initial={{ y: 12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.35, duration: 0.4 }}
        className="text-[14px] text-center max-w-md mb-8 leading-relaxed"
        style={{ color: 'var(--sf-text-3)' }}
      >
        Posso ajudar com estrategia, analises, revisao de textos, brainstorming,
        formulacao de pedidos para agentes e muito mais. Pergunte o que quiser!
      </motion.p>

      {/* Grid de sugestoes */}
      <motion.div
        initial={{ y: 16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.45, duration: 0.4 }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg"
      >
        {sugestoes.map((s, i) => (
          <button
            key={i}
            onClick={() => onSugestao(s.texto)}
            className="group sf-card px-4 py-3.5 rounded-xl text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              border: '1px solid var(--sf-border-subtle)',
              cursor: 'pointer',
            }}
          >
            <span className="text-lg mb-1 block">{s.emoji}</span>
            <span
              className="text-[13px] leading-snug block group-hover:brightness-110 transition-colors"
              style={{ color: 'var(--sf-text-2)' }}
            >
              {s.texto}
            </span>
          </button>
        ))}
      </motion.div>
    </div>
  )
}
