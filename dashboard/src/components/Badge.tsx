/* Badge — Indicador de status (pendente, aprovado, rejeitado) */

interface BadgeProps {
  status: boolean | null
}

export default function Badge({ status }: BadgeProps) {
  if (status === null) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
        Pendente
      </span>
    )
  }

  if (status) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
        Aprovado
      </span>
    )
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
      Rejeitado
    </span>
  )
}
