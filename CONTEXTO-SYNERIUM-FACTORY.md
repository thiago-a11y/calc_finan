# Contexto do Projeto Synerium Factory

## Sobre Este Documento
Este documento resume todo o histórico de desenvolvimento do Synerium Factory para servir de contexto em qualquer LLM (Claude, GPT, Llama, Gemini, etc.). Use este arquivo para dar contexto completo a qualquer IA que vá trabalhar neste projeto.

---

## Projeto
**Nome:** Synerium Factory
**URL Produção:** `https://synerium-factory.objetivasolucao.com.br`
**Servidor:** AWS Lightsail (Ubuntu 22.04, 2GB RAM, IP 3.223.92.171)
**Pasta local:** `/Users/thiagoxavier/synerium-factory`
**Pasta servidor:** `/opt/synerium-factory`
**Dashboard local:** `http://localhost:5173`
**API local:** `http://localhost:8000`
**Stack:** Python 3.13 + FastAPI (backend) | React 18 + Vite 6 + TypeScript + Tailwind CSS 4 (frontend) | SQLite + SQLAlchemy (banco) | CrewAI + LangGraph + LangSmith (agentes IA)
**Objetivo:** Fábrica de SaaS impulsionada por agentes IA. Cada funcionário da empresa tem seu próprio squad de agentes para multiplicar eficiência por 10x.

## Empresa
**Nome:** Objetiva Solução Empresarial
**Localização:** Ipatinga, MG
**CEO:** Thiago Xavier (thiago@objetivasolucao.com.br)
**Diretor Técnico / Operations Lead:** Jonatas (jonatas@objetivasolucao.com.br) — irmão do Thiago, aprovação final em tudo crítico
**Funcionários:** 45 pessoas (cada um terá seu próprio squad de agentes)

## Produtos da Objetiva
- **SyneriumX** — CRM completo (PHP 7.4 + React 18 + MySQL) — repositório em `~/propostasap`
- **DiamondOne** — Add-on industrial para SAP B1
- **FinancialOne** — Módulo financeiro (crédito, captação, endividamento)
- **Softwares industriais** — Produção, qualidade, custeio, manutenção

## Visão Estratégica
1. Synerium Factory é o produto para escalar TODOS os serviços da Objetiva
2. Cada um dos 45 funcionários terá seu próprio squad de agentes IA
3. Zero contratação de humanos para trabalho operacional
4. Eficiência multiplicada por 10x ou mais
5. Tudo orquestrado por líderes, diretores e Operations Lead
6. Futuro: licenciar como SaaS multi-tenant para outras empresas

---

## Hierarquia

```
CEO (Thiago)
└── Operations Lead (Jonatas) — aprovação final, override total
    └── PM Agent Central (Alex) — orquestra todos os squads
        ├── Squad CEO — Thiago (9 agentes especializados) ← PILOTO
        ├── Squad Dev Backend (1 agente)
        ├── Squad Dev Frontend (1 agente)
        ├── Squad Marketing (1 agente)
        └── [41 squads pendentes — 1 por funcionário]
```

## Squad do CEO (Piloto) — 9 Agentes

| # | Rosto | Nome | País | Área | Skills |
|---|-------|------|------|------|--------|
| 1 | 👨🏻 | Kenji | 🇰🇷 Coreia | Tech Lead / Arquiteto | RAG, busca web, leitura de código, GitHub |
| 2 | 👩🏿 | Amara | 🇳🇬 Nigéria | Backend PHP/Python | RAG, código, JSON, SQL |
| 3 | 👨🏽 | Carlos | 🇲🇽 México | Frontend React/TS | RAG, web scrape, markdown |
| 4 | 👩🏻 | Yuki | 🇯🇵 Japão | Especialista IA | RAG, busca web, código, CSV |
| 5 | 👨🏾 | Rafael | 🇧🇷 Brasil | Integrações/APIs | RAG, Firecrawl, JSON, código |
| 6 | 👨🏼 | Hans | 🇩🇪 Alemanha | DevOps/Infra | RAG, GitHub, código, terminal |
| 7 | 🧕🏽 | Fatima | 🇸🇦 Arábia | QA/Segurança | RAG, código, busca web |
| 8 | 👨🏻‍🦱 | Marco | 🇮🇹 Itália | Product Manager | RAG, busca web, escrita Obsidian |
| 9 | 👩🏽‍💼 | Sofia | 🇧🇷 Brasil | Secretária Executiva | TODAS (email, .zip, criar projetos, ata) |

---

## Stack Técnica Completa

### Backend (Python)
- **FastAPI** — API REST (porta 8000)
- **SQLAlchemy 2.0** — ORM para SQLite
- **CrewAI 1.11** — Orquestração de agentes IA
- **LangGraph 1.1** — Fluxos complexos de agentes
- **LangSmith 0.7** — Observabilidade e tracing
- **LangChain 1.2** — Framework de LLM
- **LiteLLM** — Abstração multi-provider
- **JWT (HS256)** + bcrypt — Autenticação
- **Amazon SES** — Envio de email (via boto3)
- **ChromaDB** — Vector store para RAG
- **OpenAI Embeddings** — text-embedding-3-small

### Frontend (React)
- **React 18** + TypeScript + Vite 6
- **Tailwind CSS 4** — Estilização
- **Recharts** — Gráficos (consumo de APIs)
- **React Router v6** — Roteamento SPA

### LLM Providers (Fallback Inteligente)
1. 🧠 **Claude** (Anthropic) — Principal, melhor qualidade
2. ⚡ **Llama via Groq** — Fallback 1, mais rápido
3. 🔥 **Llama via Fireworks** — Fallback 2
4. 🤝 **Llama via Together.ai** — Fallback 3

### Skills/Ferramentas dos Agentes (31 registradas)
- **RAG** — Consulta à base de conhecimento (vault Obsidian)
- **Tavily** — Busca web inteligente (paga)
- **EXA** — Busca semântica web
- **Firecrawl** — Scraping avançado
- **ScrapingDog** — SERP API (Google)
- **GitHub** — Busca em repositórios
- **FileRead/Write** — Leitura e escrita de arquivos
- **CodeInterpreter** — Execução de código Python
- **Email SES** — Envio com e sem anexo
- **Criar Projeto** — Gera múltiplos arquivos de uma vez
- **Criar ZIP** — Compacta arquivos
- **SyneriumX Tools** — Ler/listar/buscar/git/terminal do projeto real
- **gstack** (Y Combinator) — 28 skills profissionais (review, QA, security, ship, etc.)

---

## Estrutura de Pastas

```
~/synerium-factory/
├── orchestrator.py              # Ponto de entrada principal
├── requirements.txt             # Dependências Python
├── .env                         # Variáveis de ambiente (NUNCA commitar)
├── CLAUDE.md                    # Regras permanentes do projeto
├── agents/                      # Definições de agentes
│   ├── pm_central.py            # Alex — PM Agent Central
│   └── operations_lead.py       # Jonatas — Diretor Técnico
├── squads/                      # Squads pessoais
│   ├── squad_template.py        # Template para novos squads
│   └── squad_ceo_thiago.py      # Squad piloto do CEO (9 agentes)
├── flows/                       # Fluxos automatizados
│   └── daily_standup.py         # Standup diário
├── gates/                       # Portões de aprovação
│   └── approval_gates.py        # Human-in-the-loop
├── config/                      # Configurações
│   ├── settings.py              # Settings centralizadas (pydantic-settings)
│   ├── llm_providers.py         # Multi-provider LLM com fallback
│   ├── usuarios.py              # Cadastro de usuários
│   └── permissoes.py            # Permissões granulares (13 módulos x 5 ações)
├── rag/                         # Base de conhecimento
│   ├── config.py                # RAGConfig
│   ├── store.py                 # ChromaDB store
│   ├── indexer.py               # Indexador de vaults Obsidian
│   ├── query.py                 # Consulta semântica
│   └── assistant.py             # Assistente IA (Claude responde com RAG)
├── tools/                       # Skills/ferramentas dos agentes
│   ├── registry.py              # Catálogo de skills
│   ├── skills_setup.py          # Inicialização e perfis
│   ├── rag_tool.py              # Ferramenta de consulta RAG
│   ├── email_tool.py            # Envio de email (SES)
│   ├── projeto_tool.py          # Criar projetos (múltiplos arquivos)
│   ├── zip_tool.py              # Compactar em .zip
│   ├── syneriumx_tools.py       # Ler/editar código do SyneriumX
│   └── gstack/                  # 28 skills do Y Combinator
├── api/                         # API REST (FastAPI)
│   ├── main.py                  # App principal
│   ├── security.py              # JWT + bcrypt
│   ├── dependencias.py          # Singleton + auth middleware
│   ├── schemas.py               # Schemas Pydantic
│   └── routes/                  # Endpoints
│       ├── auth.py              # Login, refresh, registro, trocar senha
│       ├── status.py            # Painel geral
│       ├── squads.py            # Gestão de squads
│       ├── aprovacoes.py        # Approval gates
│       ├── rag.py               # Base de conhecimento
│       ├── standup.py           # Standup diário
│       ├── usuarios.py          # CRUD de usuários
│       ├── convites.py          # Convites por email
│       ├── tarefas.py           # Chat individual + reuniões
│       ├── skills.py            # Catálogo de skills
│       ├── projetos.py          # Gestão de projetos
│       ├── propostas.py         # Propostas de edição (aprovação)
│       ├── uploads.py           # Upload de arquivos
│       ├── consumo.py           # Dashboard de consumo
│       └── llm.py               # Gestão de LLM providers
├── dashboard/                   # Frontend React
│   └── src/
│       ├── App.tsx              # Roteamento principal
│       ├── contexts/AuthContext.tsx  # Autenticação
│       ├── components/
│       │   ├── Sidebar.tsx      # Navegação lateral
│       │   ├── ChatManager.tsx  # Gerenciador de chats flutuantes
│       │   ├── ChatFloating.tsx # Chat individual (messenger)
│       │   └── ReuniaoModal.tsx # Modal de reunião com rodadas
│       └── pages/
│           ├── PainelGeral.tsx  # Dashboard principal
│           ├── Aprovacoes.tsx   # Fila de aprovações
│           ├── Squads.tsx       # Grid de squads
│           ├── Escritorio.tsx   # Escritório virtual (bonequinhos)
│           ├── RAG.tsx          # Base de conhecimento
│           ├── Standup.tsx      # Standup diário
│           ├── Relatorios.tsx   # Histórico de tarefas/reuniões
│           ├── Skills.tsx       # Catálogo de skills
│           ├── Projetos.tsx     # Gestão de projetos
│           ├── Consumo.tsx      # Dashboard de consumo (Recharts)
│           ├── LLMProviders.tsx # Gestão de LLM providers
│           ├── Equipe.tsx       # Liderança
│           ├── Perfil.tsx       # Perfil do usuário
│           ├── Configuracoes.tsx # Configurações do sistema
│           └── Login.tsx        # Tela de login
├── database/                    # Banco de dados
│   ├── models.py                # Modelos SQLAlchemy
│   ├── session.py               # Engine + sessão
│   └── seed.py                  # Seed (Thiago + Jonatas)
├── data/                        # Dados persistidos
│   ├── synerium.db              # Banco SQLite
│   ├── chromadb/                # Vector store RAG
│   ├── uploads/chat/            # Arquivos enviados no chat
│   └── propostas_edicao/        # Propostas pendentes de aprovação
└── logs/                        # Logs do sistema
    └── synerium.log
```

---

## Autenticação
- JWT HS256 com access token (1h) + refresh token (30d)
- bcrypt cost 12 para senhas
- Bloqueio de conta após 10 tentativas (30 min)
- Audit log de todos os logins (LGPD)
- Senha seed: `SyneriumFactory@2026`
- Permissões granulares: 13 módulos x 5 ações (view/create/edit/delete/export)

## Approval Gates
Ações críticas que requerem aprovação do Operations Lead:
- Deploy em produção
- Gasto de IA acima de R$50
- Mudança de arquitetura
- Campanha de marketing
- Outreach em massa

Gastos de IA abaixo de R$50 são auto-aprovados.

## Sistema de Projetos
- Cada projeto tem: proprietário (nomeado pelo CEO), líder técnico, membros
- Mudança pequena → líder aprova
- Mudança grande → proprietário aprova
- Mudança crítica → proprietário + líder
- SyneriumX cadastrado como primeiro projeto (proprietário: Thiago, líder: Jonatas)

## Ferramentas de Edição do SyneriumX
- **Leitura**: livre (qualquer agente lê, lista, busca, git status/log/diff)
- **Escrita**: gera solicitação → proprietário aprova no dashboard → aplica no arquivo real
- Path restrito a `~/propostasap` — impossível acessar fora
- Comandos destrutivos bloqueados (rm -rf, drop, push, merge)

---

## Vaults Obsidian
1. **SyneriumX-notes** (`~/Documents/SyneriumX-notes/`) — Documentação do CRM
2. **SyneriumFactory-notes** (`~/Documents/SyneriumFactory-notes/`) — Documentação da fábrica

### Estrutura do Vault Factory
```
SyneriumFactory-notes/
├── 00-Home.md
├── 01-Roadmap/Roadmap.md
├── 02-Backlog/
├── 03-Changelog/Changelog.md
├── 04-Arquitetura/
│   ├── Autenticacao.md
│   ├── Dashboard-Web.md
│   ├── Gestao-Usuarios.md
│   ├── LLM-Providers.md
│   ├── Permissoes-Granulares.md
│   ├── Projetos.md
│   └── RAG.md
├── 09-Squads/
│   ├── Mapa-Squads.md
│   └── Squad-CEO-Thiago.md
└── CONTEXTO-SYNERIUM-FACTORY.md (este arquivo)
```

---

## Variáveis de Ambiente (.env)
```
LANGSMITH_API_KEY=lsv2_sk_...
LANGSMITH_PROJECT=synerium-factory
LANGSMITH_TRACING=true
CREWAI_TRACING_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
FIREWORKS_API_KEY=fw_...
TOGETHER_API_KEY=tgp_v1_...
TAVILY_API_KEY=tvly-dev-...
EXA_API_KEY=cffe...
FIRECRAWL_API_KEY=fc-...
SCRAPINGDOG_API_KEY=69c...
GITHUB_TOKEN=ghp_...
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAT...
AWS_SECRET_ACCESS_KEY=pS6...
AWS_SES_SENDER=noreply@objetivasolucao.com.br
JWT_SECRET_KEY=synerium-factory-jwt-secret-...
RAG_VAULT_SYNERIUMX=/Users/thiagoxavier/Documents/SyneriumX-notes
RAG_VAULT_FACTORY=/Users/thiagoxavier/Documents/SyneriumFactory-notes
```

---

## Acessos

### Produção (qualquer lugar)
- **URL:** https://synerium-factory.objetivasolucao.com.br
- **Login:** thiago@objetivasolucao.com.br / SyneriumFactory@2026

### Servidor (SSH)
```bash
ssh -i ~/Downloads/LightsailDefaultKey-us-east-1.pem ubuntu@3.223.92.171
# Logs: sudo journalctl -u synerium-factory -f
# Restart: sudo systemctl restart synerium-factory
# Deploy: cd /opt/synerium-factory && git pull && sudo systemctl restart synerium-factory
```

### Local (desenvolvimento)
```bash
# Terminal 1 — API
cd ~/synerium-factory && source .venv/bin/activate && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Dashboard
cd ~/synerium-factory/dashboard && npm run dev -- --host 0.0.0.0

# Acessar: http://localhost:5173
```

---

## Histórico de Versões

- **v0.1.0** — Fundação (estrutura, orchestrator, agentes, gates, standup)
- **v0.2.0** — Dashboard Web (FastAPI + React + Tailwind)
- **v0.3.0** — Autenticação (JWT, bcrypt, perfil, convites, audit log)
- **v0.4.0** — Gestão de Usuários e Permissões
- **v0.5.0** — RAG Completo com IA (ChromaDB + Claude)
- **v0.6.0** — Squad do CEO com 8 Agentes
- **v0.7.0** — Chat Individual e Reuniões com Rodadas
- **v0.8.0** — Skills Reais (20+ ferramentas: Tavily, Firecrawl, EXA, etc.)
- **v0.9.0** — Sofia (Secretária Executiva) + gstack (28 skills Y Combinator)
- **v0.10.0** — Escritório Virtual com Diversidade
- **v0.11.0** — Email com Anexo (Amazon SES)
- **v0.12.0** — Ferramentas de Edição do SyneriumX (leitura livre + escrita com aprovação)
- **v0.13.0** — Sistema de Projetos com Proprietário e Governança
- **v0.14.0** — Permissões Granulares + Upload de Arquivos + Isolamento de Sessão
- **v0.15.0** — Multi-Provider LLM (Claude + Groq + Fireworks + Together) + Dashboard de Consumo
- **v0.16.0** — Redesign Premium Completo (Dark Mode obsessivo, lucide-react, zero emojis, visual Stripe/Vercel)
- **v0.17.0** — Light Mode completo + Escritório Virtual imersivo com Framer Motion + Correções
- **v0.18.0** — BMAD Workflow Engine (4 fases, PRD, Sprint Status, Story BDD, Readiness Gate)
- **v0.19.0** — Deploy Pipeline com progresso 0→100% + Squad Jonatas (3 agentes) + CI corrigido
- **v0.20.0** — Isolamento de Squads por usuário + Visão Geral + Toggle de permissões
- **v0.21.0** — LiveKit Video Call + Escritório estilo Sowork + Auto-timeout de reuniões
- **v0.22.0** — Guia de Deploy + LiveKit no Consumo + Sala de Reunião Premium
- **v0.23.0** — **Deploy em produção AWS Lightsail** (https://synerium-factory.objetivasolucao.com.br)

---

## Video Call (novo em v0.21.0)

- **LiveKit Cloud** integrado: áudio + vídeo em tempo real
- URL: `wss://synerium-factory-rhayv819.livekit.cloud`
- Free tier: 100 participantes simultâneos
- Sofia entra automaticamente como transcritora
- Botão "Video Call" no Escritório Virtual

## Auto-Timeout de Reuniões

- Reuniões executando há +10 minutos são resetadas automaticamente
- Verificação silenciosa a cada consulta de histórico
- Endpoint manual: `POST /api/tarefas/limpar-travadas`

## Deploy Pipeline (novo em v0.19.0)

Pipeline de 8 etapas executado pelo dashboard com barra de progresso em tempo real:
1. Git Status → 2. Git Add → 3. Git Commit → 4. Build → 5. Testes → 6. Branch → 7. Push+PR → 8. Merge

Acesso: `/deploy` no dashboard. Tudo automatizado — 1 clique do CEO.

---

## Design System

### Dark Mode (principal)
- Fundo: `#0a0a0f` | Cards: `from-white/[0.04]` | Bordas: `white/[0.08]`
- Textos: `#f8f8f8` (principal), `#9ca3af` (secundário), `#4b5563` (ghost)
- Ícones: lucide-react (stroke 1.5-2) — zero emojis em todo o dashboard
- Hover: `-translate-y-0.5` + `border-white/15` + glow sutil
- Classes: `sf-page`, `sf-glass`, `sf-border`, `sf-text-white`, `sf-text-dim`, `sf-text-ghost`

### Light Mode
- Fundo: `#f8f9fa` | Cards: `#ffffff` | Bordas: `#e2e8f0`
- Textos: `#111827` (principal), `#4b5563` (secundário)
- Toggle ☀️/🌙 na sidebar
- Glows desativados (opacity 0)

---

## Como Usar Este Contexto

1. **Para dar contexto a qualquer LLM:** Cole este arquivo inteiro no início da conversa
2. **Para revisar código:** Peça à IA ler os arquivos via tools/syneriumx_tools.py
3. **Para planejar features:** Discuta usando este contexto + vault Obsidian
4. **Para debug:** Consulte os logs em `logs/synerium.log`
5. **Para verificar status:** Rode `python orchestrator.py --status`

---

> Última atualização: 2026-03-26
