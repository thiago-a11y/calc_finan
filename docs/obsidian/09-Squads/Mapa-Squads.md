# Mapa de Squads — Objetiva Solução

> Cada um dos 45 funcionários da Objetiva terá seu próprio squad de agentes IA.
> Este documento mapeia todos os squads.

---

## Status

- **Total de funcionários:** 45
- **Squads configurados:** 4 (1 piloto + 3 de área)
- **Squads pendentes:** 41
- **Total de agentes ativos:** 12

## Liderança

| # | Nome | Cargo | Papel no Sistema | Pode Aprovar |
|---|---|---|---|---|
| 1 | **Thiago** | CEO | CEO | ✅ Sim (tudo) |
| 2 | **Jonatas** | Diretor Técnico e Operations Lead | Aprovação final + override técnico | ✅ Sim (tudo) |
| — | **Alex** | PM Agent Central (agente IA) | Orquestra todos os squads | — |

## Squad Piloto — CEO Thiago (9 agentes)

> 🏆 **Primeiro squad completo.** Serve como modelo para os demais.
> Documentação completa: [[Squad-CEO-Thiago]]

| # | Agente | Área | Prioridade Imediata |
|---|--------|------|---------------------|
| 1 | Tech Lead / Arquiteto | Arquitetura e padrões | Sync dev→main |
| 2 | Backend Developer | PHP, MySQL, APIs | 4 bugs do dashboard |
| 3 | Frontend Developer | React, TypeScript, UX | Dark mode, PWA |
| 4 | Especialista IA | Prompts, RAG, scoring | Copilot proativo |
| 5 | Especialista Integrações | OAuth, APIs externas | WhatsApp API |
| 6 | DevOps & Infra | Deploy, CI/CD, cloud | Migração domínio |
| 7 | QA & Segurança | Testes, LGPD | Criar testes (zero hoje) |
| 8 | Product Manager | Roadmap, backlog | Priorizar 30+ itens |
| 9 | Sofia — Secretária Executiva 🇧🇷 | Atas, entregáveis, emails | Atas + execução em reuniões |

## Squads de Área

| # | Squad | Especialidade | Agentes | Status |
|---|---|---|---|---|
| 1 | Dev Backend | Desenvolvimento Backend PHP/Python | 1 | Ativo |
| 2 | Dev Frontend | Desenvolvimento Frontend React | 1 | Ativo |
| 3 | Marketing | Marketing Digital e Growth | 1 | Ativo |

## Squads Pendentes de Mapeamento

Para mapear os 41 squads restantes, precisamos:

1. **Lista dos 45 funcionários** com nome e cargo
2. **Área de atuação** de cada um (dev, financeiro, industrial, comercial, etc.)
3. **Quem são os líderes/diretores** que orquestram os squads
4. **Quais agentes** cada pessoa precisa (dev, análise, redação, atendimento, etc.)

## Como Criar um Novo Squad

### Opção 1: Squad simples (1 agente)
Editar `orchestrator.py` e adicionar na função `main()`:

```python
fabrica.registrar_squad(
    nome="Nome do Funcionário",
    especialidade="Área de atuação",
    contexto="Detalhes sobre o foco e ferramentas usadas.",
)
```

### Opção 2: Squad completo (múltiplos agentes)
Usar como base o `squads/squad_ceo_thiago.py` — duplicar o arquivo, ajustar os agentes e registrar no orchestrator.

---

> Última atualização: 2026-03-24
