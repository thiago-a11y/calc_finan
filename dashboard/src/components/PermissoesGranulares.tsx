/* PermissoesGranulares — Tabela de toggles dark-mode aware */

import { useState, useEffect } from 'react'
import { buscarModulosDisponiveis, atualizarPermissoes } from '../services/api'
import type { Usuario, ModuloDisponivel } from '../types'
import { Save, RotateCcw, Eye } from 'lucide-react'

interface Props {
  usuario: Usuario
  onSalvo: () => void
}

const acaoLabels: Record<string, string> = {
  view: 'Ver', create: 'Criar', edit: 'Editar', delete: 'Excluir', export: 'Exportar',
}

const acaoIcones: Record<string, string> = {
  view: '👁', create: '＋', edit: '✎', delete: '🗑', export: '⬆',
}

export default function PermissoesGranulares({ usuario, onSalvo }: Props) {
  const [modulos, setModulos] = useState<ModuloDisponivel[]>([])
  const [acoes, setAcoes] = useState<string[]>([])
  const [permsPorPapel, setPermsPorPapel] = useState<Record<string, Record<string, Record<string, boolean>>>>({})
  const [overrides, setOverrides] = useState<Record<string, Record<string, boolean>>>(
    usuario.permissoes_granulares || {}
  )
  const [salvando, setSalvando] = useState(false)
  const [mensagem, setMensagem] = useState('')
  const PAPEIS_VISAO_GERAL = ['ceo', 'diretor_tecnico', 'operations_lead']
  const temVisaoGeralPorPapel = (usuario.papeis || []).some(p => PAPEIS_VISAO_GERAL.includes(p))

  const [visaoGeral, setVisaoGeral] = useState<boolean>(
    (usuario.permissoes_granulares as any)?.squads?.visao_geral ?? temVisaoGeralPorPapel
  )

  useEffect(() => {
    buscarModulosDisponiveis().then(data => {
      setModulos(data.modulos)
      setAcoes(data.acoes)
      setPermsPorPapel(data.permissoes_por_papel)
    })
  }, [])

  const permissaoBase = (modulo: string, acao: string): boolean => {
    for (const papel of (usuario.papeis || [])) {
      if (permsPorPapel[papel]?.[modulo]?.[acao]) return true
    }
    return false
  }

  const temOverride = (modulo: string, acao: string): boolean => {
    return overrides[modulo]?.[acao] !== undefined
  }

  const valorEfetivo = (modulo: string, acao: string): boolean => {
    if (temOverride(modulo, acao)) return overrides[modulo][acao]
    return permissaoBase(modulo, acao)
  }

  const togglePermissao = (modulo: string, acao: string) => {
    const novoValor = !valorEfetivo(modulo, acao)
    setOverrides(prev => ({
      ...prev,
      [modulo]: { ...(prev[modulo] || {}), [acao]: novoValor },
    }))
  }

  const resetarOverride = (modulo: string, acao: string) => {
    setOverrides(prev => {
      const novo = { ...prev }
      if (novo[modulo]) {
        delete novo[modulo][acao]
        if (Object.keys(novo[modulo]).length === 0) delete novo[modulo]
      }
      return novo
    })
  }

  const salvar = async () => {
    setSalvando(true)
    setMensagem('')
    try {
      const overridesLimpos: Record<string, Record<string, boolean>> = {}
      for (const [modulo, acoesMod] of Object.entries(overrides)) {
        for (const [acao, valor] of Object.entries(acoesMod)) {
          if (valor !== permissaoBase(modulo, acao)) {
            if (!overridesLimpos[modulo]) overridesLimpos[modulo] = {}
            overridesLimpos[modulo][acao] = valor
          }
        }
      }
      // Incluir visao_geral no override de squads
      if (visaoGeral && !temVisaoGeralPorPapel) {
        if (!overridesLimpos['squads']) overridesLimpos['squads'] = {}
        ;(overridesLimpos as any)['squads']['visao_geral'] = true
      }

      await atualizarPermissoes(usuario.id, {
        permissoes_granulares: Object.keys(overridesLimpos).length > 0 ? overridesLimpos : null,
      })
      setMensagem('Permissões salvas com sucesso!')
      onSalvo()
    } catch {
      setMensagem('Erro ao salvar permissões.')
    } finally {
      setSalvando(false)
    }
  }

  if (modulos.length === 0) return <p className="text-sm sf-text-dim">Carregando módulos...</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-emerald-400">
            Permissões de {usuario.nome}
          </h4>
          <p className="text-xs sf-text-dim">
            Papéis: {(usuario.papeis || []).join(', ') || 'Nenhum'} — overrides em destaque
          </p>
        </div>
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/25 rounded-xl text-xs font-medium hover:bg-emerald-500/30 disabled:opacity-40 transition-all"
        >
          <Save size={12} />
          {salvando ? 'Salvando...' : 'Salvar Permissões'}
        </button>
      </div>

      {mensagem && (
        <div className={`mb-3 px-3 py-2 rounded-lg text-xs ${
          mensagem.includes('sucesso')
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {mensagem}
        </div>
      )}

      {/* Toggle Visão Geral */}
      <div className="mb-4 p-4 rounded-xl flex items-center justify-between" style={{ background: 'var(--sf-bg-2)', border: '1px solid var(--sf-border-default)' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-purple-500/15 border border-purple-500/25 flex items-center justify-center">
            <Eye size={16} className="text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-semibold sf-text-white">Visão Geral</p>
            <p className="text-[10px] sf-text-dim">
              Permite ver todos os squads, escritórios e agentes da empresa
              {temVisaoGeralPorPapel && <span className="text-purple-400 ml-1">(ativa por padrão pelo papel)</span>}
            </p>
          </div>
        </div>
        <button
          onClick={() => setVisaoGeral(!visaoGeral)}
          className={`w-11 h-6 rounded-full transition-all relative cursor-pointer ${
            visaoGeral ? 'bg-purple-500' : 'bg-gray-600'
          }`}
          title={visaoGeral ? 'Desativar visão geral' : 'Ativar visão geral'}
        >
          <span
            className="absolute top-0.5 w-5 h-5 rounded-full shadow transition-all"
            style={{
              background: 'var(--sf-bg-0)',
              left: visaoGeral ? '22px' : '2px',
            }}
          />
        </button>
      </div>

      {/* Tabela de permissões */}
      <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid var(--sf-border-default)' }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: 'var(--sf-bg-2)', borderBottom: '1px solid var(--sf-border-default)' }}>
              <th className="text-left py-3 px-4 font-medium sf-text-dim w-48">Módulo</th>
              {acoes.map(acao => (
                <th key={acao} className="text-center py-3 px-2 font-medium sf-text-dim w-20">
                  <span title={acaoLabels[acao]}>{acaoIcones[acao]} {acaoLabels[acao]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {modulos.map((modulo, idx) => (
              <tr
                key={modulo.id}
                style={{
                  background: idx % 2 === 0 ? 'var(--sf-bg-1)' : 'var(--sf-bg-2)',
                  borderBottom: '1px solid var(--sf-border-subtle)',
                }}
              >
                <td className="py-2.5 px-4">
                  <span className="mr-1.5 text-sm">{modulo.icone}</span>
                  <span className="font-medium sf-text-white">{modulo.nome}</span>
                </td>
                {acoes.map(acao => {
                  const ativo = valorEfetivo(modulo.id, acao)
                  const isOverride = temOverride(modulo.id, acao)
                  const baseVal = permissaoBase(modulo.id, acao)

                  // Cores do toggle
                  const bgToggle = ativo
                    ? isOverride ? 'bg-blue-500' : 'bg-emerald-500'
                    : isOverride ? 'bg-red-500/60' : 'bg-gray-600'

                  return (
                    <td key={acao} className="text-center py-2.5 px-2">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => togglePermissao(modulo.id, acao)}
                          className={`w-9 h-5 rounded-full transition-all relative ${bgToggle}`}
                          title={
                            isOverride
                              ? `Override: ${ativo ? 'permitido' : 'negado'} (base: ${baseVal ? 'permitido' : 'negado'})`
                              : `Base do papel: ${ativo ? 'permitido' : 'negado'}`
                          }
                        >
                          <span
                            className={`absolute top-0.5 w-4 h-4 rounded-full shadow transition-all ${
                              ativo ? 'left-[18px]' : 'left-0.5'
                            }`}
                            style={{ background: 'var(--sf-bg-0)' }}
                          />
                        </button>
                        {isOverride && (
                          <button
                            onClick={() => resetarOverride(modulo.id, acao)}
                            className="sf-text-ghost hover:text-red-400 transition-colors"
                            title="Remover override (voltar ao padrão)"
                          >
                            <RotateCcw size={10} />
                          </button>
                        )}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legenda */}
      <div className="mt-3 flex flex-wrap gap-4 text-[10px] sf-text-dim">
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 bg-emerald-500 rounded-full" /> Permitido (base do papel)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 bg-blue-500 rounded-full" /> Permitido (override)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 bg-red-500/60 rounded-full" /> Negado (override)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 bg-gray-600 rounded-full" /> Negado (base do papel)
        </span>
        <span className="flex items-center gap-1">
          <RotateCcw size={9} /> Remover override
        </span>
      </div>
    </div>
  )
}
