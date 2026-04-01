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
**Versão Atual:** v0.58.1 (01/Abr/2026)
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
        ├── Catálogo de Agentes (16 templates reutilizáveis — "prateleira")
        ├── Factory Optimizer (ID=16) — Distinguished Engineer, meta-análise PDCA
        ├── Squad CEO — Thiago (9 agentes atribuídos do catálogo)
        ├── Squad Jonatas (3 agentes atribuídos do catálogo)
        ├── Squad Dev Backend, Dev Frontend, Marketing (squads de área)
        ├── Autonomous Squads — Workflows BMAD autônomos com gates
        ├── Vision-to-Product — PM Central gera roadmap + estimativa custo/prazo
    └── [Novos squads criados dinamicamente via atribuição do catálogo]
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

### Smart Router Dinâmico por Mensagem (v0.52.0)

O sistema classifica cada mensagem individualmente e roteia para o provider mais adequado:
- **SIMPLES** → Minimax MiniMax-Text-01 (mais barato)
- **MEDIO** → Groq Llama 3.3 70B (rápido)
- **COMPLEXO** → Claude Sonnet (qualidade premium)
- **TOOLS** → GPT-4o-mini (function calling + system role)

Arquivo: `core/classificador_mensagem.py`

### Roteamento Vision / Multimodal (v0.58.0)

Quando o usuário envia imagem, o classificador detecta automaticamente e roteia para providers com suporte a vision:
- **SIMPLES/MEDIO com imagem** → GPT-4o-mini (mais barato com vision)
- **COMPLEXO com imagem** → GPT-4o (máxima qualidade multimodal)
- **Fallback chain filtrada**: pula Minimax, Groq, Fireworks e Together (sem vision)
- **Rede de segurança**: `llm_fallback.py` detecta `image_url` em mensagens independentemente do classificador

### LLM Providers — Cadeia Definitiva (v0.52.0)

**Cadeia do `core/llm_fallback.py` (operações automatizadas):**
1. 🏆 **MiniMax-Text-01** (Minimax) — **Principal**, mais barato ($0.0004/1K input) — endpoint: `api.minimaxi.chat` (global, com **i**)
2. ⚡ **Llama 3.3 70B via Groq** — Fallback 1, ultra-rápido ($0.00059/1K)
3. 🔥 **Llama via Fireworks** — Fallback 2, custo baixo ($0.0009/1K) — API OpenAI-compatible
4. 🤝 **Llama via Together.ai** — Fallback 3, outra opção open-source ($0.00088/1K) — API OpenAI-compatible
5. 🧠 **Claude Sonnet** (Anthropic) — Fallback 4, qualidade premium ($0.003/1K)
6. 🤖 **GPT-4o** (OpenAI) — Fallback 5, última linha de defesa ($0.005/1K)

**Cadeia da Luna (assistente principal):**
Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together

**Outros providers disponíveis (Smart Router):**
- 💎 **Gemini 2.5 Flash** (Google) — Free tier 1.5M tokens/dia

### Smart Router — Perfis de Uso
- `consultora_estrategica` (peso 0.4) — Perfil da Luna: padrão Sonnet, Opus para tarefas complexas

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
│   ├── squad_ceo_thiago.py      # Squad piloto do CEO (9 agentes)
│   └── regras.py                # Regras anti-alucinação compartilhadas
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
├── core/                        # Motores e lógica central
│   ├── luna_engine.py           # Motor da Luna: streaming + fallback (Opus→Sonnet→Groq→Fireworks→Together)
│   ├── llm_router.py            # Smart Router multi-provider
│   ├── classificador_mensagem.py # Smart Router Dinâmico — classifica por complexidade (SIMPLES/MEDIO/COMPLEXO/TOOLS)
│   ├── llm_fallback.py          # LLM Fallback centralizado (Minimax → Groq → Anthropic → OpenAI)
│   └── vcs_service.py           # Serviço VCS (GitHub/GitBucket) com Fernet + Build Gate (validação pré-push)
├── api/                         # API REST (FastAPI)
│   ├── main.py                  # App principal
│   ├── security.py              # JWT + bcrypt
│   ├── dependencias.py          # Singleton + auth middleware
│   ├── schemas.py               # Schemas Pydantic
│   └── routes/                  # Endpoints
│       ├── auth.py              # Login, refresh, registro, trocar senha
│       ├── luna.py              # 11 endpoints REST + SSE streaming + supervisão
│       ├── catalogo.py          # CRUD catálogo de agentes + atribuições + solicitações
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
│       ├── uploads.py           # Upload de arquivos (UPLOAD_DIR relativo ao projeto)
│       ├── consumo.py           # Dashboard de consumo
│       ├── llm.py               # Gestão de LLM providers
│       ├── continuous_factory.py # Modo Contínuo 24/7 (v0.54.0)
│       └── mission_control.py   # Code Studio 2.0 — Mission Control (v0.55.0)
├── dashboard/                   # Frontend React
│   └── src/
│       ├── App.tsx              # Roteamento principal
│       ├── contexts/AuthContext.tsx  # Autenticação
│       ├── components/
│       │   ├── Sidebar.tsx      # Navegação lateral
│       │   ├── ChatManager.tsx  # Gerenciador de chats flutuantes
│       │   ├── ChatFloating.tsx # Chat individual (messenger)
│       │   ├── ReuniaoModal.tsx # Modal de reunião com rodadas
│       │   └── luna/            # 7 componentes da Luna
│       │       ├── MarkdownRenderer.tsx
│       │       ├── LunaWelcome.tsx
│       │       ├── LunaInput.tsx
│       │       ├── LunaChat.tsx
│       │       ├── LunaSidebar.tsx
│       │       ├── LunaPreview.tsx
│       │       └── LunaAdminView.tsx
│       ├── services/
│       │   └── luna.ts          # Serviço API com streaming SSE
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
│           ├── Catalogo.tsx      # Catálogo de agentes (prateleira)
│           ├── Atribuicoes.tsx   # Atribuição de agentes a usuários
│           ├── Configuracoes.tsx # Configurações do sistema
│           ├── Luna.tsx         # Assistente IA (ChatGPT/Claude interno)
│           ├── CodeStudio.tsx   # Editor de código integrado (v1)
│           ├── CommandCenter.tsx # Centro de Comando (Vision-to-Product)
│           ├── MissionControl.tsx # Code Studio 2.0 — painel triplo (v0.55.0)
│           └── Login.tsx        # Tela de login
├── database/                    # Banco de dados
│   ├── models.py                # Modelos SQLAlchemy
│   ├── session.py               # Engine + sessão
│   ├── seed.py                  # Seed (Thiago — Jonatas entra via convite)
│   ├── seed_catalogo.py         # Seed dos 16 agentes no catálogo
│   └── (tabelas Luna: luna_conversas, luna_mensagens)
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
- JWT HS256 com access token (8h) + refresh token (30d) + auto-refresh transparente
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
- **Hierarquia editável** — Proprietário, líder técnico e membros podem ser alterados diretamente na interface com dropdowns inline (v0.36.0)
- **Regras de aprovação customizáveis por projeto** — Campo JSON `regras_aprovacao` em `ProjetoDB` permite definir fluxo de aprovação diferente para cada projeto
- Endpoint `PUT /projetos/{id}/regras` para atualizar regras de aprovação
- Padrão (se não customizado): mudança pequena → líder aprova | mudança grande → proprietário aprova | mudança crítica → proprietário + líder
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
│   ├── RAG.md
│   ├── Code-Studio.md
│   ├── VCS-Integration.md
│   ├── Autonomous-Squads.md
│   ├── Self-Evolving-Factory.md
│   ├── Command-Center.md
│   ├── LLM-Fallback.md
│   └── Build-Gate.md
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
ssh synerium-aws   # Alias configurado em ~/.ssh/config
# Logs: sudo journalctl -u synerium-factory -f
# Restart: sudo systemctl restart synerium-factory
# Deploy completo (do Mac): bash scripts/deploy_producao.sh
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
- **v0.16.0** — **Luna: Assistente IA Integrada** — ChatGPT/Claude dentro do Factory, streaming SSE, voz, preview de artefatos, supervisão LGPD, fallback multi-provider
- **v0.16.1** — Redesign Premium Completo (Dark Mode obsessivo, lucide-react, zero emojis, visual Stripe/Vercel)
- **v0.16.4** — Fix download de arquivos Luna em produção (UPLOAD_DIR corrigido para AWS)
- **v0.16.5** — Exclusão permanente de usuários (hard delete, libera email para reconvite)
- **v0.17.0** — Light Mode completo + Escritório Virtual imersivo com Framer Motion + Correções
- **v0.18.0** — BMAD Workflow Engine (4 fases, PRD, Sprint Status, Story BDD, Readiness Gate)
- **v0.19.0** — Deploy Pipeline com progresso 0→100% + Squad Jonatas (3 agentes) + CI corrigido
- **v0.20.0** — Isolamento de Squads por usuário + Visão Geral + Toggle de permissões
- **v0.21.0** — LiveKit Video Call + Escritório estilo Sowork + Auto-timeout de reuniões
- **v0.22.0** — Guia de Deploy + LiveKit no Consumo + Sala de Reunião Premium
- **v0.23.0** — **Deploy em produção AWS Lightsail** (https://synerium-factory.objetivasolucao.com.br)
- **v0.24.0** — Esquema de cores corrigido, melhorias visuais
- **v0.25.0** — Commit inicial no GitHub (estrutura completa)
- **v0.26.0** — Tracking automático de consumo em TODOS os agentes
- **v0.27.0** — Convite por email ao adicionar novo membro
- **v0.28.0** — Bootstrap AWS completo (RAG, seeds, providers, deploy script)
- **v0.29.0** — **Catálogo de Agentes + Atribuição Dinâmica** — Prateleira de agentes reutilizáveis, admin atribui a usuários, hot-reload de squads, solicitações com aprovação
- **v0.30.0** — **Escritório Virtual Revolucionário** — Canvas 1600×750, janelas com Rio de Janeiro, ciclo dia/noite real, mesas premium, sala de reunião com vidro, avatares com micro-animações, Framer Motion walk animations
- **v0.32.0** — **Avatares Reais dos Agentes** — 10 avatares JPG, config centralizada, AgentAvatar reutilizável
- **v0.33.0** — **Smart Router Global** — Roteamento multi-provider (7 LLMs) + multi-ferramenta (8 integrações), 13 categorias de intenção
- **v0.33.1** — **Gemini 2.0 Flash + GPT-4o** — Cadeia completa: Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
- **v0.34.0** — **Code Studio** — Editor de código integrado com CodeMirror 6, 4 endpoints, árvore de arquivos, abas, agente IA, syntax highlighting, audit log LGPD
- **v0.35.0** — **Version Control (VCS)** — Integração GitHub/GitBucket por projeto, token criptografado (Fernet), 4 endpoints VCS, commit+push automático no Code Studio
- **v0.35.1** — **Fix PDF (Luna)** — Corrigido erro 400 ao gerar PDF; nova função `_sanitizar_para_pdf()` remove tags HTML antes do ReportLab
- **v0.36.0** — **Hierarquia Editável + Regras de Aprovação** — Projetos com hierarquia editável (owner, tech lead, membros) e regras de aprovação customizáveis por projeto (JSON), endpoint PUT, dropdowns inline no frontend
- **v0.36.1** — **Fix Rotas VCS** — Corrigido prefixo de rotas VCS (404 → `/api/projetos/{id}/vcs`)
- **v0.36.2** — **Fix AuditLogDB** — Corrigido campos inexistentes no endpoint VCS (`usuario_id`/`detalhes` → `user_id`/`descricao`)
- **v0.36.3** — **JWT Auto-Refresh + Bloqueio de Binários** — Token 8h + auto-refresh transparente + bloqueio de 19 extensões binárias no Code Studio
- **v0.37.0** — **Code Studio Multi-Projeto** — Code Studio project-aware com seletor de projeto no header, `project_id` em todos os endpoints, VCS auto-commit por projeto, contexto de projeto no agente IA, audit log com nome do projeto, persistência em localStorage
- **v0.37.1** — **Auto-Clone VCS** — Code Studio clona automaticamente repositório quando diretório não existe + botão Pull + refresh de árvore
- **v0.38.0** — **Histórico de Atividades + Feedback Detalhado** — Endpoint de histórico com paginação, diff no apply-action, HistoricoPanel, toast detalhado, confirmação inline
- **v0.39.0** — **Company Context Total** — 3 níveis (minimal/standard/full), RAG integrado, toggle no frontend, cache inteligente, budget 4000 chars
- **v0.40.0** — **Chat Resiliente** — Timeout 30min, retomar conversa, git pull com token VCS, GIT_TERMINAL_PROMPT=0
- **v0.41.0** — **One-Click Apply+Deploy** — Pipeline: backup → aplicar → Test Master (bloqueante) → commit → push, rollback automático
- **v0.42.0** — **Push & PR & Merge** — Push, PR e merge direto do Code Studio via GitHub API, seleção de commits
- **v0.43.0** — **Live Agents** — Progresso rotativo no AgentPanel, balão status no Escritório, shimmer no ChatFloating
- **v0.44.0** — **Painéis Redimensionáveis** — Drag handle entre painéis do Code Studio, persistência em localStorage
- **v0.45.0** — **Conversas Separadas** — Sistema de conversas no AgentPanel, novo chat, histórico, scroll inteligente, persistência localStorage
- **v0.46.0** — **3 Agentes Elite + BMAD** — Test Master, GitHub Master, GitBucket Master + 15 agentes mapeados no BMAD
- **v0.47.0** — **Novo Projeto** — Botão Novo Projeto na página Projetos + modal de criação (CEO only)
- **v0.48.0** — **Preview por Commit** — Preview de arquivos alterados por commit no PushDialog + horário Brasília
- **v0.49.0** — **Autonomous Squads + Self-Evolving Factory + Command Center** — Workflows BMAD autônomos (4 fases, gates soft/hard), Factory Optimizer (PDCA), Command Center CEO, LLM Fallback robusto (Anthropic→Groq→OpenAI), recovery de workflows travados
- **v0.50.0** — **Vision-to-Product + Session Isolada + Fila de Workflows** — PM Central gera roadmap com estimativa de custo/prazo, session SQLite isolada por fase (fix crítico), fila automática de workflows, 16 agentes no catálogo, teste end-to-end aprovado (Fase 2→3→4 sem crash)
- **Vision-to-Product testado e aprovado em produção** (30/03/2026) — 4 fases BMAD completas, gates soft/hard, review com 3 sugestões reais via Groq, fila automática de workflows em sequência
- **Self-Evolving Factory** gerando 3 sugestões reais de melhoria após cada workflow concluído
- **v0.51.0** — **Minimax como LLM Principal** — MiniMax-Text-01 como provider principal ($0.0004/1K input), nova cadeia Minimax→Groq→Anthropic→OpenAI, Smart Router com Provider.MINIMAX, config/settings.py e config/llm_providers.py atualizados
- **v0.52.0** — **Smart Router Dinâmico por Mensagem** — Classificação por complexidade (SIMPLES→Minimax, MEDIO→Groq, COMPLEXO→Sonnet, TOOLS→GPT-4o-mini), classificador regex em `core/classificador_mensagem.py`, adaptador system→user para Minimax
- **v0.52.2** — **Build Gate** — Validação obrigatória de build antes de push (`core/vcs_service.py`), revert automático se build falhar, prevenção de código quebrado em produção (motivado pelo Bug #43)
- **v0.53.0→v0.53.3** — **Pipeline Completo + Correções** — Agente→Proposta→Aprovação→Build→Deploy, tool schemas Pydantic no CrewAI, retry com backoff exponencial, throttle Fase 4
- **v0.54.0** — **Continuous Factory (24/7)** — Modo contínuo com toggle CEO/Ops Lead, auto-aprovação gates soft/hard, notificações SES, relatório diário LLM às 23h, worker background com recovery
- **v0.55.0** — **Mission Control** — Painel triplo Editor+Terminal+Artifacts, agentes live animados, comentários inline estilo Google Docs, 8 endpoints REST, ArtifactDB + MissionControlSessaoDB
- **v0.55.1** — **Fix Mission Control Produção** — URL relativa para API (`VITE_API_URL || ''`), systemd service para dashboard, diagnóstico porta 5173 bloqueada pelo Lightsail
- **v0.56.0** — **Suporte Completo Novos Agentes** — Ícones GitBranch/TrendingUp/FlaskConical, categorias qualidade/infraestrutura/otimizacao com cores nos filtros, perfis diretor/arquiteto na Skills, CATEGORIAS_DISPONIVEIS expandido, Escritório DK 9→16 posições (agentes 10–16 têm mesa própria), 3 bugs críticos resolvidos (Aprovação 500, Git Pull conflito, Command Center reiniciar workflow)
- **v0.57.0** — **Mission Control Session Persistence** — Auto-save a cada 10s (editor+terminal), tela de sessões recentes com "Retomar", URL `/mission-control/:sessionId`, endpoint PATCH /save, editor `<pre>`→`<textarea>`, indicador "Salvo HH:MM"
- **v0.57.1** — **Team Chat Multi-Agente + Artifact Modal** — TeamChatDB, 4 fases multi-agente (Tech Lead+Backend+Frontend+QA), polling GET /chat a cada 2s, Painel 3 com abas Team Chat|Artifacts, modal estável (não fecha sozinho) com botões Aplicar/Copiar/Download, 3 bugs corrigidos (#49 metadata reservado, #50 string como ProviderRecomendado, #51 import TypeScript desnecessário), teste integração APROVADO (14 mensagens, 3 artifacts)
- **v0.57.2** — **Visible Execution** — 3 novos helpers no backend (fase/progresso, código no editor, terminal do agente), barra de progresso animada por fase (10%→35%→60%→85%→100%), código aparece ao vivo no editor com badge "agente", terminal distingue entradas do agente (ícone Bot verde) vs usuário ($), proteção de edições manuais do CEO no editor, botão "Rodar Testes" no modal
- **v0.57.3** — **Modo LIVE + Recovery de Agentes Órfãos** — Botão toggle LIVE (verde, default on) na barra de progresso, streaming progressivo de código no editor (4 linhas/flush, 350ms delay), polling dinâmico 1s em LIVE vs 5s normal, badge LIVE vermelho pulsante durante streaming, indicador "escrevendo..." com cursor pulsante, proteção contra sobrescrita de edições manuais. **Bug #52 corrigido**: `_recovery_agentes_orfaos()` executada no import do módulo — varre sessões ativas no startup e marca como erro agentes que ficaram travados em "executando" após `systemctl restart`
- **v0.57.4** — **Fix Crítico Streaming ao Vivo** — 3 root causes corrigidas: session isolada por helper + flag_modified (Bug #53), auto-save protegido contra race condition com agente (Bug #54), polling estável sem restart a cada poll (Bug #55). Streaming ao vivo finalmente funciona.
- **v0.58.1** — **Vision Real para Agentes de Squad** — Pré-processamento de imagens com GPT-4o-mini vision (`_analisar_imagens_com_vision()`), ChatFloating envia URLs reais de upload, Luna Engine com path resolution absoluto e fallback não-silencioso
- **v0.58.0** — **Agentes Multimodais (Vision)** — Flag `vision` em todos os providers, novo parâmetro `tem_imagem` no classificador, roteamento SIMPLES/MEDIO→GPT-4o-mini e COMPLEXO→GPT-4o quando imagem presente, fallback chain filtra providers sem vision, `_mensagens_tem_imagem()` no LLM Fallback
- **v0.57.5** — **Visible Live Execution** — Efeito typewriter no editor (caracteres graduais), barra de progresso com shimmer + texto descritivo + %, ícone do agente pulsante, badge "Em execução" no Team Chat, cursor piscante no terminal. Backend: chunks 2 linhas/200ms (era 4/350ms), progresso granular dentro das fases, comandos reais no terminal (npm run build, pytest, eslint, tsc), editor com conteúdo desde Fase 1 (scaffold→plan→code), mais entradas de terminal em todas as fases.

---

## Video Call (novo em v0.21.0)

- **LiveKit Cloud** integrado: áudio + vídeo em tempo real
- URL: `wss://synerium-factory-rhayv819.livekit.cloud`
- Free tier: 100 participantes simultâneos
- Sofia entra automaticamente como transcritora
- Botão "Video Call" no Escritório Virtual

## Auto-Timeout de Reuniões

- Reuniões/tarefas executando há +30 minutos são resetadas automaticamente
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

## Catálogo de Agentes (novo em v0.29.0, expandido v0.46.0)

Sistema de "prateleira" de agentes reutilizáveis:
- **16 templates** no catálogo (9 do squad CEO + 3 do squad Jonatas + 3 Agentes Elite + Factory Optimizer)
- Admin (CEO, Diretor, Operations Lead) atribui agentes do catálogo a qualquer usuário
- Usuários podem solicitar agentes → aprovação pelo admin
- Hot-reload: atribuir/remover agente recarrega o squad em memória sem restart
- Tabelas: `AgenteCatalogoDB`, `AgenteAtribuidoDB`, `SolicitacaoAgenteDB`
- Endpoints: `/api/catalogo`, `/api/atribuicoes`, `/api/solicitacoes-agente`
- Dashboard: `/catalogo` (prateleira), `/atribuicoes` (gerenciar por usuário), aba "Agentes" em Aprovações
- **3 Agentes Elite** (v0.46.0): Test Master (testes automatizados), GitHub Master (operações GitHub), GitBucket Master (operações GitBucket)
- **Factory Optimizer** (v0.49.0): Distinguished Engineer, meta-análise PDCA, review sessions automáticas
- **BMAD mapeamento completo**: 16 agentes mapeados com fases, palavras-chave e especialidades

## Luna — Assistente IA Integrada (novo em v0.16.0)

Assistente inteligente estilo ChatGPT/Claude dentro do Synerium Factory:
- **Rota:** `/luna` no dashboard
- **Streaming SSE** — Respostas em tempo real token a token
- **Reconhecimento de voz** — Web Speech API integrada no input
- **Markdown rendering** com syntax highlighting
- **Preview de artefatos** — Visualização de código e conteúdo gerado
- **Gestão de conversas** — Criar, listar, renomear, excluir
- **Supervisão de proprietários** — CEO/admin pode visualizar chats de funcionários (audit log LGPD)
- **Fallback multi-provider:** Opus → Sonnet → Groq → Fireworks → Together
- **11 endpoints REST** + SSE streaming
- **Banco:** `luna_conversas` (id, usuario_id, titulo, modelo_preferido, company_id, timestamps) + `luna_mensagens` (conversa_id, papel, conteudo, modelo_usado, provider_usado, tokens, custo)

## Escritório Virtual (reescrito em v0.30.0)

Escritório premium com imersão cinematográfica:
- Canvas 1600×750 full-bleed
- **Janelas com vista do Rio de Janeiro** (Pão de Açúcar, Cristo Redentor, montanhas)
- **Ciclo dia/noite real** baseado na hora do sistema (amanhecer, dia, entardecer, noite com estrelas)
- Mesas com monitor + glow, café com vapor, planta pessoal, objetos únicos
- Sala de reunião com paredes de vidro transparente, mesa oval, telão
- Animações Framer Motion: agente caminha ao CEO (click) e reunião com stagger
- Micro-animações CSS: breathing, typing, thinking com bolha
- Elementos: relógio, quadros, bebedouro, máquina de café, luminárias que respondem ao dia/noite

## Code Studio Avançado (v0.34.0 → v0.48.0)

Editor de código completo integrado ao dashboard com funcionalidades avançadas:

- **Editor CodeMirror 6** com syntax highlighting, abas, árvore de arquivos
- **Multi-Projeto** (v0.37.0) — Seletor de projeto no header, cada projeto com sua árvore e VCS
- **Auto-Clone VCS** (v0.37.1) — Clona repositório automaticamente quando diretório não existe
- **Company Context Total** (v0.39.0) — 3 níveis de contexto (minimal/standard/full) com RAG integrado
- **One-Click Apply+Deploy** (v0.41.0) — Pipeline: backup → aplicar → Test Master → commit → push
- **Push & PR & Merge** (v0.42.0) — Operações Git completas via GitHub API direto do dashboard
- **Live Agents** (v0.43.0) — Animações visuais de status dos agentes (rotativo, shimmer, balão)
- **Painéis redimensionáveis** (v0.44.0) — Drag handle entre painéis com persistência
- **Conversas separadas** (v0.45.0) — Múltiplas conversas no AgentPanel com scroll inteligente
- **Preview por commit** (v0.48.0) — Arquivos alterados por commit no PushDialog com horário Brasília
- **Rota:** `/code-studio` no dashboard

## Autonomous Squads (novo em v0.49.0, consolidado v0.50.0)

Workflow BMAD completo automatizado:
- **4 fases**: Business → Marketing → Architecture → Development
- **Gates soft/hard**: Soft prossegue automaticamente, hard aguarda CEO/OpsLead
- **Session isolada por fase** (v0.50.0) — Cada fase cria e fecha sua própria `SessionLocal()` SQLite, evitando crash em threads longas
- **Fila automática** (v0.50.0) — Ao concluir/falhar, verifica e inicia o próximo workflow da fila
- **Dynamic Team Assembly** — Detecção automática de tipo de tarefa + seleção de agentes por LLM
- **Teste end-to-end aprovado** — Fase 2→3→4 sem crash
- **Modelo**: `WorkflowAutonomoDB` com status, fase atual e resultado JSON
- **Endpoints**: `POST /api/autonomo`, `GET /api/autonomo/{id}`, aprovar-gate, cancelar
- **Recovery**: Workflows travados >30min são marcados como erro no startup
- **Gate approval**: `threading.Lock` para evitar race condition

## Self-Evolving Factory (novo em v0.49.0)

Sistema de auto-evolução contínua:
- **Factory Optimizer** (ID=16) — Distinguished Engineer com ciclo PDCA
- **Review session automática** — Após cada workflow concluído, analisa e gera sugestões
- **Modelo**: `EvolucaoFactoryDB` com tipo, impacto, status, aprovação
- **Fluxo**: workflow conclui → review → sugestões → CEO aprova → implementação
- **Endpoints**: `/api/evolucao` (listar, aprovar, rejeitar)

## Command Center (novo em v0.49.0, expandido v0.50.0)

Painel estratégico do CEO:
- **KPIs em tempo real** — Workflows ativos, concluídos, taxa de sucesso
- **Comando estratégico** — Disparar workflows autônomos com features priorizadas e complexidade
- **Vision-to-Product** (v0.50.0) — PM Central gera roadmap com estimativa de dias e custo a partir de uma visão de produto
- **Barra de progresso %** em cada card de squad no Command Center
- **Spawn de squads** — Criar squads sob demanda
- **Gates pendentes** — Visualização e aprovação de gates
- **Fila automática de workflows** — Próximo inicia ao concluir/falhar o anterior
- **Endpoints**: `GET /command-center` (KPIs, workflows, evoluções), `POST /command-center/estrategia` (PM Central quebra em features)

## LLM Fallback Robusto (novo em v0.49.0, consolidado v0.50.0, Minimax principal em v0.51.0)

Cadeia centralizada em `core/llm_fallback.py`:
- **Minimax** (MiniMax-Text-01) → **Groq** (Llama) → **Anthropic** (Claude) → **OpenAI** (GPT-4o)
- Minimax como LLM principal: $0.0004/1K input, $0.0016/1K output
- Integrado via MiniMaxChat (langchain_community)
- config/settings.py com minimax_api_key e minimax_group_id
- config/llm_providers.py com ProviderID.MINIMAX
- Smart Router Global com Provider.MINIMAX + PROVIDER_CONFIG
- Qualquer módulo chama `obter_llm_fallback()` e recebe o provider disponível
- **6 pontos de chamada** atualizados para usar fallback centralizado
- Detecção automática de erro de crédito/quota/rate limit
- Nunca mais para por falta de créditos ou rate limit

---

> Ultima atualizacao: 2026-04-01
