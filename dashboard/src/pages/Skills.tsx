/* Skills — Catálogo premium de habilidades dos agentes (zero emojis) */

import { useCallback, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import {
  BookOpen, Search, FileText, Code2, FolderTree, FolderSearch,
  Terminal, Cloud, Globe, Compass, Flame, Dog,
  Sparkles, FileJson, FileSpreadsheet, FileType2,
  Pencil, Send, Mail, Paperclip, FolderArchive,
  GitBranch, Eye, ListTree, SearchCode, SquareTerminal,
  Wrench, User2, LayoutGrid, 
  type LucideIcon,
} from 'lucide-react'

interface Skill {
  id: string; nome: string; descricao: string; categoria: string
  ativa: boolean; icone: string; requer_config: boolean
}

interface Perfil {
  perfil: string; skills: string[]
}

/* Mapeamento de skill ID → ícone lucide */
const skillIconMap: Record<string, LucideIcon> = {
  rag_consultar: BookOpen,
  markdown_buscar: FileText,
  arquivo_ler: Eye,
  diretorio_listar: FolderTree,
  diretorio_buscar: FolderSearch,
  codigo_executar: Terminal,
  e2b_sandbox: Cloud,
  github_buscar: GitBranch,
  web_scrape: Globe,
  web_buscar: Compass,
  tavily_buscar: Sparkles,
  firecrawl_scrape: Flame,
  firecrawl_crawl: Flame,
  exa_buscar: Search,
  scrapingdog_google: Dog,
  json_buscar: FileJson,
  csv_buscar: FileSpreadsheet,
  pdf_buscar: FileType2,
  texto_buscar: SearchCode,
  arquivo_escrever: Pencil,
  email_enviar: Send,
  email_enviar_anexo: Paperclip,
  projeto_criar: FolderArchive,
  zip_criar: FolderArchive,
  sx_ler_arquivo: Eye,
  sx_listar_diretorio: ListTree,
  sx_escrever_arquivo: Pencil,
  sx_buscar: SearchCode,
  sx_git: GitBranch,
  sx_terminal: SquareTerminal,
}

/* Ícone de categoria (lucide) */
const categoriaConfig: Record<string, { icon: LucideIcon; label: string; cor: string }> = {
  conhecimento: { icon: BookOpen, label: 'Conhecimento', cor: '#10b981' },
  codigo: { icon: Code2, label: 'Código', cor: '#3b82f6' },
  web: { icon: Globe, label: 'Web', cor: '#8b5cf6' },
  escrita: { icon: Pencil, label: 'Escrita', cor: '#f59e0b' },
  dados: { icon: FileSpreadsheet, label: 'Dados', cor: '#ec4899' },
  comunicacao: { icon: Mail, label: 'Comunicação', cor: '#14b8a6' },
  syneriumx: { icon: Terminal, label: 'SyneriumX', cor: '#6366f1' },
}

const perfilConfig: Record<string, { label: string; cor: string }> = {
  tech_lead:            { label: '#1 Kenji — Tech Lead',           cor: '#10b981' },
  backend_dev:          { label: '#2 Amara — Backend',             cor: '#3b82f6' },
  frontend_dev:         { label: '#3 Carlos — Frontend',           cor: '#8b5cf6' },
  especialista_ia:      { label: '#4 Yuki — IA',                   cor: '#f59e0b' },
  integracao:           { label: '#5 Rafael — Integrações',        cor: '#ec4899' },
  devops:               { label: '#6 Hans — DevOps',               cor: '#6366f1' },
  qa_seguranca:         { label: '#7 Fatima — QA / Test Master',   cor: '#ef4444' },
  product_manager:      { label: '#8 Marco — PM',                  cor: '#14b8a6' },
  secretaria_executiva: { label: '#9 Sofia — Secretária Exec.',    cor: '#d946ef' },
  diretor:              { label: '#10 — Diretor / Factory Opt.',   cor: '#f97316' },
  arquiteto:            { label: '#11 — Arquiteto de Sistemas',    cor: '#a855f7' },
}

async function fetchSkills(): Promise<{ skills: Skill[]; perfis: Perfil[] }> {
  const token = localStorage.getItem('sf_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const [r1, r2] = await Promise.all([
    fetch('/api/skills', { headers }),
    fetch('/api/skills/perfis', { headers }),
  ])
  return { skills: await r1.json(), perfis: await r2.json() }
}

export default function Skills() {
  const fetcher = useCallback(() => fetchSkills(), [])
  const { dados, erro, carregando } = usePolling(fetcher, 30000)
  const [vista, setVista] = useState<'catalogo' | 'perfis'>('catalogo')

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    )
  }
  if (erro) return <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">Erro: {erro}</div>

  const skills = dados?.skills || []
  const perfis = dados?.perfis || []

  const porCategoria: Record<string, Skill[]> = {}
  for (const s of skills) {
    if (!porCategoria[s.categoria]) porCategoria[s.categoria] = []
    porCategoria[s.categoria].push(s)
  }

  return (
    <div className="sf-page">
      {/* Glow sutil */}
      <div className="fixed top-0 left-1/3 w-[600px] h-[300px] bg-blue-500/5 blur-[120px] pointer-events-none sf-glow" style={{ opacity: 'var(--sf-glow-opacity)' }} />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent sf-text-white">
            Skills dos Agentes
          </h2>
          <p className="text-sm sf-text-dim mt-1">
            {skills.length} skills disponíveis · {perfis.length} perfis configurados
          </p>
        </div>
        <div className="flex gap-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-1">
          <button
            onClick={() => setVista('catalogo')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-300 ${
              vista === 'catalogo'
                ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                : 'sf-text-dim hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            <LayoutGrid size={14} />
            Catálogo
          </button>
          <button
            onClick={() => setVista('perfis')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-300 ${
              vista === 'perfis'
                ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                : 'sf-text-dim hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            <User2 size={14} />
            Por Agente
          </button>
        </div>
      </div>

      {vista === 'catalogo' ? (
        <div className="space-y-8">
          {Object.entries(porCategoria).map(([cat, catSkills]) => {
            const cfg = categoriaConfig[cat] || { icon: Wrench, label: cat, cor: '#6b7280' }
            const CatIcon = cfg.icon

            return (
              <div key={cat}>
                {/* Categoria header */}
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${cfg.cor}15` }}
                  >
                    <CatIcon size={16} style={{ color: cfg.cor }} strokeWidth={2} />
                  </div>
                  <h3 className="text-sm font-semibold sf-text-dim uppercase tracking-wider">
                    {cfg.label}
                  </h3>
                  <span className="text-xs sf-text-ghost">{catSkills.length}</span>
                </div>

                {/* Grid de skills */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {catSkills.map(skill => {
                    const IconComp = skillIconMap[skill.id] || Wrench
                    const usadoPor = perfis.filter(p => p.skills.includes(skill.id)).length

                    return (
                      <div
                        key={skill.id}
                        className={`group relative sf-glass backdrop-blur-sm border rounded-xl p-4 transition-all duration-300 hover:-translate-y-0.5 ${
                          skill.ativa
                            ? 'sf-border hover:border-white/20'
                            : 'border-red-500/20 opacity-50'
                        }`}
                      >
                        {/* Hover glow */}
                        <div
                          className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                          style={{ background: `radial-gradient(ellipse at top, ${cfg.cor}08, transparent 70%)` }}
                        />

                        <div className="relative">
                          {/* Header da skill */}
                          <div className="flex items-start gap-3 mb-3">
                            <div
                              className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300 group-hover:scale-110"
                              style={{ backgroundColor: `${cfg.cor}12`, border: `1px solid ${cfg.cor}20` }}
                            >
                              <IconComp size={16} style={{ color: cfg.cor }} strokeWidth={1.8} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium sf-text-white text-sm leading-tight">
                                {skill.nome}
                              </h4>
                              {!skill.ativa && (
                                <span className="inline-block mt-1 text-[10px] bg-red-500/15 text-red-400 px-2 py-0.5 rounded-full border border-red-500/20">
                                  Inativa
                                </span>
                              )}
                              {skill.requer_config && skill.ativa && (
                                <span className="inline-block mt-1 text-[10px] bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded-full border border-amber-500/20">
                                  Requer config
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Descrição */}
                          <p className="text-xs sf-text-dim leading-relaxed mb-3 line-clamp-2">
                            {skill.descricao}
                          </p>

                          {/* Footer */}
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] sf-text-ghost font-mono px-2 py-0.5 sf-glass rounded border" style={{ borderColor: 'var(--sf-border-subtle)' }}>
                              {skill.id}
                            </span>
                            {usadoPor > 0 && (
                              <span className="text-[10px] font-medium" style={{ color: cfg.cor }}>
                                {usadoPor} agente{usadoPor > 1 ? 's' : ''}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        /* Vista por perfil/agente */
        <div className="space-y-4">
          {perfis.map(perfil => {
            const cfg = perfilConfig[perfil.perfil] || { label: perfil.perfil, cor: '#6b7280' }

            return (
              <div
                key={perfil.perfil}
                className="group sf-glass backdrop-blur-sm border sf-border rounded-xl p-5 transition-all duration-300 hover:border-white/15"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${cfg.cor}15`, border: `1px solid ${cfg.cor}25` }}
                  >
                    <User2 size={18} style={{ color: cfg.cor }} strokeWidth={1.8} />
                  </div>
                  <div>
                    <h3 className="font-semibold sf-text-white">{cfg.label}</h3>
                    <p className="text-xs sf-text-ghost">{perfil.skills.length} skills atribuídas</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {perfil.skills.map(sid => {
                    const skill = skills.find(s => s.id === sid)
                    const IconComp = skillIconMap[sid] || Wrench
                    const cat = skill?.categoria || ''
                    const catCfg = categoriaConfig[cat] || { cor: '#6b7280' }

                    return (
                      <div
                        key={sid}
                        className="flex items-center gap-2 px-3 py-1.5 sf-glass border rounded-lg transition-all duration-200 hover:border-white/15" style={{ borderColor: 'var(--sf-border-subtle)' }}
                      >
                        <IconComp size={12} style={{ color: catCfg.cor }} strokeWidth={2} />
                        <span className="text-xs sf-text-dim">{skill?.nome || sid}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
