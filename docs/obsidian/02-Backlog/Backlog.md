# Backlog — Synerium Factory

> Tarefas pendentes organizadas por prioridade.

---

## Prioridade Alta

### Manual Completo do Synerium Factory
**Prioridade:** Alta
**Estimativa:** 2-3 sessões
**Descrição:** Documentação completa para usuários e administradores do Synerium Factory.

**Estrutura planejada:**
1. **Introdução** — O que é o Synerium Factory, visão, objetivo
2. **Primeiros Passos** — Login, dashboard, navegação
3. **Escritório Virtual** — Como usar agentes, enviar mensagens, reuniões
4. **Code Studio** — Editar código, apply, push, PR, merge
5. **Command Center** — KPIs, comando estratégico, Vision-to-Product, Autonomous Squads
6. **Luna (Assistente IA)** — Conversas, streaming, RAG
7. **Squads e Agentes** — Catálogo de 16 agentes, papéis, BMAD
8. **Administração** — Usuários, convites, permissões, projetos
9. **VCS (Controle de Versão)** — GitHub/GitBucket, tokens, Build Gate
10. **Consumo de APIs** — Monitoramento, Smart Router, providers
11. **Arquitetura Técnica** — Stack, LLM Fallback, Smart Router, Deploy
12. **Troubleshooting** — Erros comuns, logs, fallback

**Formato:** Markdown no vault Obsidian (`docs/obsidian/10-Manual/`)
**Público:** CEO, Operations Lead, desenvolvedores, usuários comuns da Objetiva

---

- [ ] Implementar RAG com vault Obsidian do SyneriumX
- [ ] Evoluir arquitetura para multi-tenant (company_id)
- [ ] Mapear os 45 funcionários e criar squads reais
- [ ] Testes automatizados do core (orchestrator, gates, squads)

## Prioridade Média

- [ ] Integrar Kairos com Luna (capturar snapshots automaticamente das conversas)
- [ ] Integrar Kairos com Mission Control (snapshots de sessões de desenvolvimento)
- [ ] API REST para consulta/status do Kairos no dashboard
- [ ] Auto-dream no startup da API (iniciar_auto_dream no main.py)
- [ ] Embeddings para busca semântica no Kairos (ChromaDB)
- [ ] Dashboard web para acompanhar status dos squads
- [ ] Integração com WhatsApp Business para notificações
- [ ] Integração com Telegram Bot
- [ ] Sistema de billing por tenant
- [ ] Relatórios de custo de IA por squad/produto
- [ ] Deploy Luna na AWS
- [ ] Integrar histórico Luna ao RAG

## Prioridade Baixa

- [ ] API pública para integrações externas
- [ ] Onboarding self-service para novos tenants
- [ ] PWA/app mobile para acompanhamento
- [ ] Marketplace de agentes customizados

## Concluído

- [x] Luna — Assistente inteligente com streaming, voz, preview e supervisão LGPD (v0.16.0)

---

> Última atualização: 2026-03-27
