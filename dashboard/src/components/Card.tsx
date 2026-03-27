/* Card — Componente reutilizável de card com ícone e valor */

interface CardProps {
  titulo: string
  valor: string | number
  icone: string
  cor?: string
  subtitulo?: string
}

export default function Card({ titulo, valor, icone, cor = 'emerald', subtitulo }: CardProps) {
  const cores: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  }

  return (
    <div className={`rounded-xl border p-5 ${cores[cor] || cores.emerald}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium opacity-80">{titulo}</span>
        <span className="text-2xl">{icone}</span>
      </div>
      <p className="text-3xl font-bold">{valor}</p>
      {subtitulo && <p className="text-xs mt-1 opacity-60">{subtitulo}</p>}
    </div>
  )
}
