/* Calculadora de Financiamento Imobiliario — React 18 + TypeScript + Tailwind CSS
 * Projeto gerado pelo Synerium Factory (Mission Control)
 */

import { useState, useCallback } from 'react'

interface Resultado {
  parcela: number
  totalPago: number
  totalJuros: number
  tabela: { mes: number; parcela: number; juros: number; amortizacao: number; saldo: number }[]
}

export default function App() {
  const [valor, setValor] = useState('')
  const [entrada, setEntrada] = useState('')
  const [taxa, setTaxa] = useState('')
  const [meses, setMeses] = useState('')
  const [sistema, setSistema] = useState<'price' | 'sac'>('price')
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [mostrarTabela, setMostrarTabela] = useState(false)

  const calcular = useCallback(() => {
    const v = parseFloat(valor.replace(/\./g, '').replace(',', '.')) || 0
    const e = parseFloat(entrada.replace(/\./g, '').replace(',', '.')) || 0
    const t = parseFloat(taxa.replace(',', '.')) || 0
    const n = parseInt(meses) || 0

    if (v <= 0 || t <= 0 || n <= 0) return

    const financiado = v - e
    if (financiado <= 0) return

    const taxaMensal = t / 100

    const tabela: Resultado['tabela'] = []
    let totalPago = e
    let totalJuros = 0

    if (sistema === 'price') {
      // Tabela Price: parcelas fixas
      const parcela = financiado * (taxaMensal * Math.pow(1 + taxaMensal, n)) / (Math.pow(1 + taxaMensal, n) - 1)
      let saldo = financiado

      for (let i = 1; i <= n; i++) {
        const juros = saldo * taxaMensal
        const amortizacao = parcela - juros
        saldo -= amortizacao
        totalJuros += juros
        tabela.push({
          mes: i,
          parcela: parcela,
          juros,
          amortizacao,
          saldo: Math.max(0, saldo),
        })
      }
      totalPago += parcela * n

      setResultado({ parcela, totalPago, totalJuros, tabela })
    } else {
      // SAC: amortizacao constante
      const amortizacao = financiado / n
      let saldo = financiado

      for (let i = 1; i <= n; i++) {
        const juros = saldo * taxaMensal
        const parcela = amortizacao + juros
        saldo -= amortizacao
        totalJuros += juros
        totalPago += parcela
        tabela.push({
          mes: i,
          parcela,
          juros,
          amortizacao,
          saldo: Math.max(0, saldo),
        })
      }

      setResultado({ parcela: tabela[0]?.parcela || 0, totalPago, totalJuros, tabela })
    }
  }, [valor, entrada, taxa, meses, sistema])

  const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">

        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-zinc-200">Financiamento Imobiliario</h1>
          <p className="text-[11px] text-zinc-500">Simule Price ou SAC — Synerium Factory</p>
        </div>

        {/* Formulario */}
        <div className="bg-zinc-900 rounded-2xl p-5 mb-4 border border-zinc-800 space-y-4">

          <div>
            <label className="text-[11px] text-zinc-500 mb-1 block">Valor do Imovel (R$)</label>
            <input type="text" placeholder="500.000" value={valor}
              onChange={e => setValor(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl text-sm bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 focus:border-purple-500 focus:outline-none" />
          </div>

          <div>
            <label className="text-[11px] text-zinc-500 mb-1 block">Entrada (R$)</label>
            <input type="text" placeholder="100.000" value={entrada}
              onChange={e => setEntrada(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl text-sm bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 focus:border-purple-500 focus:outline-none" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] text-zinc-500 mb-1 block">Taxa Mensal (%)</label>
              <input type="text" placeholder="0.75" value={taxa}
                onChange={e => setTaxa(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 focus:border-purple-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-[11px] text-zinc-500 mb-1 block">Prazo (meses)</label>
              <input type="text" placeholder="360" value={meses}
                onChange={e => setMeses(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 focus:border-purple-500 focus:outline-none" />
            </div>
          </div>

          {/* Sistema */}
          <div className="flex gap-2">
            <button onClick={() => setSistema('price')}
              className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                sistema === 'price'
                  ? 'bg-purple-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}>
              Price
            </button>
            <button onClick={() => setSistema('sac')}
              className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                sistema === 'sac'
                  ? 'bg-purple-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}>
              SAC
            </button>
          </div>

          {/* Calcular */}
          <button onClick={calcular}
            className="w-full py-3 rounded-xl text-sm font-bold bg-purple-600 hover:bg-purple-500 text-white transition-all active:scale-[0.98]">
            Calcular
          </button>
        </div>

        {/* Resultado */}
        {resultado && (
          <div className="bg-zinc-900 rounded-2xl p-5 border border-zinc-800 space-y-4">
            <h2 className="text-sm font-bold text-zinc-200">Resultado ({sistema.toUpperCase()})</h2>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-zinc-800 rounded-xl p-3 text-center">
                <div className="text-[10px] text-zinc-500 mb-1">
                  {sistema === 'price' ? 'Parcela Fixa' : '1a Parcela'}
                </div>
                <div className="text-sm font-bold text-purple-400">{fmt(resultado.parcela)}</div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-3 text-center">
                <div className="text-[10px] text-zinc-500 mb-1">Total Pago</div>
                <div className="text-sm font-bold text-zinc-200">{fmt(resultado.totalPago)}</div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-3 text-center">
                <div className="text-[10px] text-zinc-500 mb-1">Total Juros</div>
                <div className="text-sm font-bold text-red-400">{fmt(resultado.totalJuros)}</div>
              </div>
            </div>

            {/* Tabela */}
            <button onClick={() => setMostrarTabela(!mostrarTabela)}
              className="w-full text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors">
              {mostrarTabela ? 'Esconder tabela' : `Ver tabela completa (${resultado.tabela.length} meses)`}
            </button>

            {mostrarTabela && (
              <div className="max-h-60 overflow-y-auto rounded-xl border border-zinc-800">
                <table className="w-full text-[11px]">
                  <thead className="sticky top-0 bg-zinc-800">
                    <tr className="text-zinc-500">
                      <th className="py-1.5 px-2 text-left">Mes</th>
                      <th className="py-1.5 px-2 text-right">Parcela</th>
                      <th className="py-1.5 px-2 text-right">Juros</th>
                      <th className="py-1.5 px-2 text-right">Amort.</th>
                      <th className="py-1.5 px-2 text-right">Saldo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.tabela.map(r => (
                      <tr key={r.mes} className="border-t border-zinc-800/50 text-zinc-400">
                        <td className="py-1 px-2">{r.mes}</td>
                        <td className="py-1 px-2 text-right text-zinc-200">{fmt(r.parcela)}</td>
                        <td className="py-1 px-2 text-right text-red-400/70">{fmt(r.juros)}</td>
                        <td className="py-1 px-2 text-right text-green-400/70">{fmt(r.amortizacao)}</td>
                        <td className="py-1 px-2 text-right">{fmt(r.saldo)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <p className="text-center text-[10px] text-zinc-600 mt-4">
          Feito com React + TypeScript + Tailwind CSS
        </p>
      </div>
    </div>
  )
}
