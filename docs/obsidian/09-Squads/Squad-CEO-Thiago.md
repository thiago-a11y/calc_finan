# Squad do CEO — Thiago Xavier

> **Status:** ✅ Ativo (Piloto)
> **Arquivo:** `squads/squad_ceo_thiago.py`
> **Total de agentes:** 9

## Visão Geral

Squad pessoal do CEO, desenhado a partir de uma varredura completa do SyneriumX:
- 14 módulos em produção
- 136+ PRs mergeados
- 61 migrations
- 10 integrações externas
- 3 providers de IA
- 30+ itens no backlog

Cada agente cobre uma área crítica para garantir visão 360° e execução 10x mais rápida.

---

## Agentes

### #1 — Tech Lead / Arquiteto de Software
- **Responsabilidades:** Decisões técnicas, revisão de arquitetura, padrões de código, planejamento de migrations
- **Prioridade imediata:** Sync dev→main, padronizar código
- **Contexto:** 15 decisões arquiteturais documentadas, PHP 7.4, company_id obrigatório, audit log

### #2 — Desenvolvedor Backend PHP/Python
- **Responsabilidades:** 50+ endpoints PHP, migrations, queries SQL, correção de bugs backend
- **Prioridade imediata:** Corrigir 4 bugs do dashboard (Invalid Date, Ticket Médio R$0, Funil sem barras, Evolução Mensal)
- **Contexto:** PDO sem ORM, prepared statements obrigatórios, multi-tenant

### #3 — Desenvolvedor Frontend React/TypeScript
- **Responsabilidades:** 20+ páginas React, componentes shadcn/ui, apiClient.ts (~3500 linhas)
- **Prioridade imediata:** Dark mode, PWA, bugs de UI
- **Contexto:** React 18 + TypeScript + Vite + shadcn/ui + TailwindCSS + 12 bibliotecas

### #4 — Especialista em Inteligência Artificial
- **Responsabilidades:** 12+ endpoints IA, 3 providers com fallback, RAG, Lead Scoring, AI Chat, anomalias
- **Prioridade imediata:** Copilot proativo, embeddings semânticos (pgvector)
- **Contexto:** Claude primário + GPT-4o + Gemini, LGPD masking, cache SHA-256

### #5 — Especialista em Integrações e APIs
- **Responsabilidades:** 10 integrações (Google Calendar OAuth, WordPress, Autentique GraphQL, Amazon SES, etc.)
- **Prioridade imediata:** WhatsApp Business API, migração de domínio (OAuth)
- **Contexto:** Amazon SES com Signature V4 puro PHP, Google Calendar gerou 17 PRs de fix

### #6 — Engenheiro DevOps e Infraestrutura
- **Responsabilidades:** Deploy GitHub Actions→FTP→cPanel, CI/CD, DNS, SSL, cloud
- **Prioridade imediata:** Migração de domínio (Fase 8.5), planejar AWS (Fase 9)
- **Contexto:** 7 etapas na migração de domínio, 13 arquivos para alterar

### #7 — Engenheiro de QA e Segurança
- **Responsabilidades:** Testes automatizados, LGPD, segurança, correção de bugs
- **Prioridade imediata:** Criar testes (hoje: zero), corrigir 4 bugs ativos
- **Contexto:** JWT puro, 2FA TOTP, audit log diff, rate limiting, risco SQL injection no AI Chat

### #8 — Product Manager e Analista de Negócios
- **Responsabilidades:** Roadmap (9 fases), backlog (30+ itens), documentação estratégica, multi-tenant
- **Prioridade imediata:** Priorizar backlog, documentar decisões
- **Contexto:** Vault Obsidian com modelo de advocacia do diabo, princípios acumulados

### #9 — Sofia — Secretária Executiva 🇧🇷
- **Responsabilidades:** Atas de reunião, execução de pedidos práticos (criar arquivos, .zip, enviar emails), mensageria
- **Prioridade imediata:** Garantir que toda reunião gere ata + entregáveis reais
- **Contexto:** Brasileira, organizada, direta. Tem TODAS as skills. Última a falar em reuniões.

---

## Métricas do Projeto Coberto

| Métrica | Valor |
|---------|-------|
| Módulos em produção | 14 |
| PRs mergeados | 136+ |
| Migrations | 61 |
| Integrações externas | 10 |
| Providers de IA | 3 |
| Páginas React | 20+ |
| Endpoints PHP | 50+ |
| Bugs ativos | 4 |
| Backlog | 30+ itens |

---

## Próximos Passos
1. Testar cada agente com uma tarefa real
2. Definir métricas de performance por agente
3. Replicar modelo para squads dos outros 44 funcionários
4. Integrar com sistema de aprovações do Operations Lead

---

*Criado em: 23/03/2026*
*Última atualização: 24/03/2026*
