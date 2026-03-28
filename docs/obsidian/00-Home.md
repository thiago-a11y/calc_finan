# Synerium Factory — Central de Conhecimento

> Vault Obsidian para organização completa do Synerium Factory.
> Fábrica de SaaS da Objetiva Solução impulsionada por agentes IA.
> Criado em: 2026-03-23

---

## Navegação Rápida

- [[01-Roadmap/Roadmap]] — Fases, prioridades e cronograma
- [[02-Backlog/Backlog]] — Tarefas e features pendentes
- [[03-Changelog/Changelog]] — Histórico de mudanças e versões
- [[04-Arquitetura/Visao-Geral]] — Stack, estrutura e fluxos
- [[04-Arquitetura/Multi-Tenant]] — Arquitetura multi-tenant
- [[04-Arquitetura/Dashboard-Web]] — Dashboard Web (Centro de Comando)
- [[04-Arquitetura/Autenticacao]] — Autenticação JWT + Perfil de Usuário
- [[04-Arquitetura/Gestao-Usuarios]] — Gestão de Usuários e Permissões (RBAC)
- [[04-Arquitetura/RAG]] — Base de Conhecimento com IA (RAG)
- [[04-Arquitetura/Escritorio-Virtual]] — Escritório Virtual Isométrico
- [[04-Arquitetura/Luna]] — Luna — Assistente Inteligente
- [[04-Arquitetura/Skills]] — Skills e Ferramentas dos Agentes
- [[05-Deploy/Guia-Deploy]] — Como rodar e fazer deploy
- [[06-Decisoes/Decisoes-Tecnicas]] — Por que escolhemos X e não Y
- [[06-Decisoes/Premissas]] — Premissas estratégicas do projeto
- [[07-Bugs/Bugs-Conhecidos]] — Issues abertas e workarounds
- [[08-Daily/Pendencias-Ultimo-Chat]] — O que ficou pendente do último chat
- [[09-Squads/Mapa-Squads]] — Mapa dos 45 squads da Objetiva
- [[10-Produtos/Catalogo-Produtos]] — Todos os produtos da Objetiva

---

## Dados do Projeto

| Campo | Valor |
|---|---|
| **Empresa** | Objetiva Solução |
| **Diretório** | `~/synerium-factory/` |
| **Stack** | Python 3.13 + CrewAI + LangGraph + LangSmith + Claude + FastAPI + React |
| **Ponto de entrada** | `orchestrator.py` |
| **Ambiente** | development |
| **Funcionários** | 45 pessoas (cada uma com squad próprio) |
| **CEO** | Thiago |
| **Operations Lead** | Jonatas (Diretor Técnico e Operations Lead) |
| **Banco de Dados** | SQLite (data/synerium.db) + SQLAlchemy 2.0 |
| **Autenticação** | JWT (HS256) + bcrypt |
| **PM Central** | Alex (agente IA) |

---

## Status Atual (2026-03-27)

**Concluído:**
- Estrutura base, agentes, approval gates, daily standup, squad template
- RAG completo com Obsidian (461 chunks indexados)
- Dashboard Web com login JWT, perfil editável, convites, audit log
- Gestão de usuários e permissões (RBAC), Configurações com 3 abas
- Squad CEO com 8 agentes turbinados (20 skills reais)
- Chat messenger flutuante + Reuniões interativas com rodadas
- Relatórios persistidos em SQLite com reabrir/continuar
- Escritório Virtual isométrico com status em tempo real
- Skills: Tavily, EXA, Firecrawl, ScrapingDog, GitHub, CodeInterpreter, RAG
- Luna — Assistente inteligente com streaming SSE, voz, preview de artefatos e supervisão LGPD (v0.16.0)

**Em andamento:** Evolução do escritório virtual, multi-tenant, cadastro dos 45 funcionários.

**Próximo:** Deploy Luna na AWS, integrar histórico Luna ao RAG, mapear os 45 funcionários, testes automatizados, 2FA.
