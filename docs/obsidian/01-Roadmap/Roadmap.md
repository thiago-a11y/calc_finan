# Roadmap — Synerium Factory

> Fases de desenvolvimento da fábrica de SaaS da Objetiva.
> Atualizado em: 30/03/2026

---

## Fase 1 — Fundação (✅ concluída)

- [x] Estrutura de pastas do projeto
- [x] Dependências instaladas (CrewAI, LangGraph, LangSmith, LangChain)
- [x] Orchestrator principal (`orchestrator.py`)
- [x] PM Agent Central (Alex)
- [x] Operations Lead (Jonatas) com poderes especiais
- [x] Approval Gates (human-in-the-loop)
- [x] Daily Standup automático
- [x] Squad Template (duplicável)
- [x] Configurações via .env + pydantic-settings
- [x] Vault Obsidian criado (SyneriumFactory-notes)
- [x] Premissas estratégicas definidas (45 funcionários, multi-tenant, multi-produto)
- [x] RAG completo com vault Obsidian do SyneriumX (ChromaDB + embeddings OpenAI)
- [x] RAG com Assistente IA (Claude responde baseado nos chunks)
- [x] Testes automatizados (32 testes: ApprovalGate, JWT, bcrypt, SyneriumX Tools, Auth API)
- [ ] Evolução para multi-tenant real

## Fase 1.5 — Dashboard Web (✅ concluída)

- [x] Backend FastAPI (`api/`) com endpoints REST
- [x] Frontend React 18 + Vite 6 + Tailwind CSS 4 (`dashboard/`)
- [x] Painel geral com métricas da fábrica
- [x] Fila de aprovações para o Operations Lead
- [x] Status do RAG e consulta via web
- [x] Relatório de standup diário via web
- [x] Persistência de usuários (SQLite + SQLAlchemy)
- [x] Autenticação JWT + bcrypt (login, refresh, perfil)
- [x] Tela de login no dashboard
- [x] Perfil editável com avatar + trocar senha
- [x] Sistema de convites por email (Amazon SES)
- [x] Audit log de ações (LGPD)
- [x] Bloqueio de conta (10 tentativas)
- [x] Gestão de usuários (criar, editar, desativar) via Configurações
- [x] Permissões granulares (13 módulos x 5 ações: view/create/edit/delete/export)
- [x] Isolamento de sessão por usuário (bug crítico corrigido)
- [x] Deploy em servidor (produção) — v0.28.0 Bootstrap AWS completo
- [ ] Autenticação 2FA

## Fase 2 — Squads e Agentes (🟡 em andamento)

- [x] Squad piloto do CEO (Thiago) com 9 agentes especializados
- [x] Agentes com diversidade (Kenji 🇰🇷, Amara 🇳🇬, Carlos 🇲🇽, Yuki 🇯🇵, Rafael 🇧🇷, Hans 🇩🇪, Fatima 🇸🇦, Marco 🇮🇹, Sofia 🇧🇷)
- [x] Sofia — Secretária Executiva (ata + execução de pedidos nas reuniões)
- [x] 20+ skills reais por agente (Tavily, Firecrawl, EXA, ScrapingDog, GitHub, etc.)
- [x] Chat individual por agente (messenger flutuante)
- [x] Reuniões com rodadas + feedback do CEO + Sofia fazendo ata
- [x] Escritório Virtual com bonequinhos animados e status em tempo real
- [x] Skills/ferramentas com página visual de catálogo
- [x] gstack do Y Combinator (28 skills profissionais instaladas)
- [x] Catálogo de Agentes — prateleira de templates reutilizáveis (v0.29.0)
- [x] Atribuição dinâmica — admin atribui agentes do catálogo a usuários
- [x] Solicitação de agentes — usuário pede, admin aprova/rejeita
- [x] Hot-reload de squads ao atribuir/remover agentes
- [x] 3 Agentes Elite: Test Master, GitHub Master, GitBucket Master (v0.46.0)
- [x] BMAD mapeamento completo — 15 agentes com fases e palavras-chave (v0.46.0)
- [x] Live Agents — progresso rotativo, balão de status, shimmer (v0.43.0)
- [ ] Mapear os 45 funcionários da Objetiva
- [ ] Criar squad personalizado para cada um
- [ ] Sistema de registro e gestão escalável de squads

## Fase 2.5 — Multi-Provider LLM (✅ concluída)

- [x] Claude (Anthropic) como provider principal
- [x] Groq Llama como Fallback 1 (mais rápido)
- [x] Fireworks Llama como Fallback 2
- [x] Together.ai Llama como Fallback 3
- [x] LiteLLM como camada de abstração
- [x] Fallback automático na cadeia
- [x] Dashboard visual de gestão de providers (ativar/desativar/testar/trocar padrão)
- [x] Dashboard de Consumo de APIs (Recharts: Line, Pie, Bar + tabela detalhada)

### Fase 2.6 — Redesign Premium Completo ✅
- [x] Dark mode verdadeiro em TODAS as páginas (#0a0a0f)
- [x] Zero emojis — lucide-react em todo o dashboard
- [x] Visual Stripe/Vercel/Linear consistency
- [x] Escritório Virtual imersivo com animações
- [x] Toggle Light/Dark Mode
- [x] 15 páginas redesenhadas

### Fase 2.7 — Deploy Pipeline + Isolamento + Video Call ✅
- [x] Deploy para produção pelo dashboard (8 etapas com progresso 0→100%)
- [x] Build + commit + branch + PR + merge automático
- [x] Squad do Jonatas (Diretor Técnico) com 3 agentes
- [x] Isolamento de squads por usuário (cada um vê só o seu)
- [x] Permissão visão_geral (CEO/Diretor veem todos)
- [x] LiveKit Video Call integrado (áudio + vídeo em tempo real)
- [x] Escritório Visual estilo Sowork (madeira, vidro, plantas, luminárias)
- [x] Auto-timeout de reuniões travadas (10 min)
- [x] Chat expandível (maximize/minimize)
- [x] CI corrigido (JSDoc + lint)

### Fase 2.8 — Deploy em Produção AWS ✅
- [x] AWS Lightsail criado (Ubuntu 22.04, 2GB RAM, Virginia)
- [x] IP estático: 3.223.92.171
- [x] DNS: synerium-factory.objetivasolucao.com.br
- [x] Python 3.13 + Node 20 + Nginx instalados
- [x] SSL HTTPS (Let's Encrypt) com redirect automático
- [x] Systemd: API como serviço permanente
- [x] Frontend buildado e servido pelo Nginx
- [x] Acessível de qualquer lugar: https://synerium-factory.objetivasolucao.com.br
- [x] Custo: $12/mês (90 dias grátis)

## Fase 2.9 — Luna: Assistente IA Integrada (✅ concluída)

- [x] Luna — Assistente estilo ChatGPT/Claude dentro do dashboard (v0.16.0)
- [x] Backend: modelos LunaConversaDB e LunaMensagemDB
- [x] Motor de IA com streaming SSE + fallback chain (Opus→Sonnet→Groq→Fireworks→Together)
- [x] 7 componentes frontend (MarkdownRenderer, LunaWelcome, LunaInput, LunaChat, LunaSidebar, LunaPreview, LunaAdminView)
- [x] Entrada por voz (Web Speech API)
- [x] Markdown rendering com syntax highlighting
- [x] Preview de artefatos (código e conteúdo gerado)
- [x] Gestão de conversas (criar, listar, renomear, excluir)
- [x] Supervisão do CEO com audit log LGPD
- [x] Smart Router perfil consultora_estrategica (peso 0.4)
- [x] Deploy Luna em produção (AWS) — 27/Mar/2026
- [x] Fix download de arquivos Luna em produção (UPLOAD_DIR) — v0.16.4
- [x] Exclusão permanente de usuários (libera email para reconvite) — v0.16.5
- [x] Syncthing removido (redundante com rsync do deploy)
- [ ] Integrar histórico Luna ao RAG

## Fase 3 — Multi-Produto e Governança (🟡 em andamento)

- [x] Sistema de Projetos com proprietário, líder técnico e membros
- [x] Hierarquia de aprovação (pequena → líder, grande → proprietário, crítica → ambos)
- [x] CEO pode nomear proprietários para qualquer projeto
- [x] SyneriumX cadastrado como primeiro projeto
- [x] Ferramentas de edição do SyneriumX (leitura livre + escrita com aprovação)
- [x] Propostas de edição com diff (agente propõe → proprietário aprova no dashboard)
- [x] Upload de arquivos no chat e reuniões
- [x] Email com anexo (Amazon SES)
- [ ] Gestão de múltiplos produtos (CRM, industrial, financeiro)
- [ ] PM Central gerencia squads por produto
- [ ] Contexto RAG separado por produto
- [ ] Relatórios por produto

## Fase 4 — Multi-Tenant (planejada)

- [ ] Isolamento por company_id (padrão SyneriumX)
- [ ] Configuração por tenant
- [ ] Billing e licenciamento
- [ ] Onboarding self-service para novos tenants
- [ ] Dashboard white-label por tenant

## Fase 5 — Integrações e Escala (🟡 parcial)

- [x] Email via Amazon SES (envio simples + anexo)
- [ ] WhatsApp Business API
- [ ] Telegram Bot
- [ ] Webhooks para sistemas externos
- [ ] API pública para integrações
- [x] Deploy em servidor cloud (AWS Lightsail) — v0.28.0

---

## Próximas Prioridades (por impacto)

| # | Item | Impacto | Esforço | Status |
|---|------|---------|---------|--------|
| 1 | ✅ Testes automatizados | Alto — 32 testes passando | Médio | Concluído |
| 2 | 🔴 Mapear 45 funcionários | Alto — escala real | Baixo | Próximo |
| 3 | ✅ Deploy em servidor | Alto — sair da rede local | Médio | Concluído (AWS Lightsail) |
| 4 | 🟡 Multi-tenant real | Alto — licenciamento | Alto | Planejado |
| 5 | 🟡 WhatsApp Business API | Médio — notificações | Médio | Planejado |
| 6 | 🟢 2FA | Médio — segurança | Baixo | Planejado |
| 7 | 🟢 RAG separado por produto | Médio — multi-produto | Médio | Planejado |

---

> Última atualização: 2026-03-27
