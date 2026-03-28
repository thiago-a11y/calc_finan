# Arquitetura — Visão Geral

> Stack, estrutura e fluxos do Synerium Factory.

---

## Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| **Runtime** | Python | 3.13 |
| **Agentes** | CrewAI | 1.11 |
| **Orquestração** | LangGraph | 1.1 |
| **Observabilidade** | LangSmith | 0.7 |
| **LLM Framework** | LangChain | 1.2 |
| **LLM Principal** | Claude (Anthropic) | Claude 4 |
| **LLM Fallback** | OpenAI GPT-4o | — |
| **API HTTP** | FastAPI | 0.135 |
| **Servidor ASGI** | uvicorn | 0.34 |
| **Frontend** | React + TypeScript | 18 |
| **Build Tool** | Vite | 6 |
| **Estilização** | Tailwind CSS | 4 |
| **Configuração** | pydantic-settings | 2.10 |
| **Ambiente** | virtualenv (.venv) | — |

## Estrutura de Pastas

```
synerium-factory/
├── orchestrator.py          # Ponto de entrada principal
├── requirements.txt         # Dependências
├── .env                     # Variáveis de ambiente (NÃO commitar)
├── CLAUDE.md                # Regras permanentes do projeto
├── agents/                  # Definições de agentes
│   ├── pm_central.py        # Alex — PM Agent Central
│   └── operations_lead.py   # Diretor de Serviços
├── squads/                  # Squads pessoais (45 funcionários)
│   └── squad_template.py    # Template para novos squads
├── flows/                   # Fluxos automatizados
│   └── daily_standup.py     # Standup diário às 7h30
├── gates/                   # Portões de aprovação
│   └── approval_gates.py    # Human-in-the-loop
├── config/                  # Configurações
│   └── settings.py          # Settings centralizadas
├── tools/                   # Ferramentas customizadas
│   └── rag_tool.py          # Ferramenta RAG para agentes
├── rag/                     # RAG com vault Obsidian
│   ├── config.py, loader.py, splitter.py
│   ├── embeddings.py, store.py, indexer.py, query.py
├── api/                     # Backend FastAPI (Dashboard)
│   ├── main.py              # App FastAPI + CORS
│   ├── schemas.py           # Schemas Pydantic
│   └── routes/              # status, squads, aprovações, rag, standup
├── dashboard/               # Frontend React + Vite + Tailwind
│   ├── src/pages/           # PainelGeral, Aprovações, Squads, RAG, Standup
│   └── src/components/      # Sidebar, Card, Badge
├── logs/                    # Logs do sistema
└── docs/                    # Documentação adicional
```

## Fluxo Principal

```
Thiago/Líder define tarefa
    → PM Central (Alex) recebe
        → Verifica se precisa de Approval Gate
            → Se sim: Operations Lead aprova/rejeita
            → Se não: prossegue
        → Delega para o Squad adequado
            → Squad executa com seus agentes
                → Resultado volta ao PM Central
                    → PM Central reporta no standup diário
```

## Hierarquia de Agentes

```
PM Central (Alex) — Hierarchical Process
├── Operations Lead — override total
├── Squad Dev Backend — PHP/Python, APIs, migrations
├── Squad Dev Frontend — React, UI/UX
├── Squad Marketing — campanhas, growth
├── Squad Financeiro — crédito, captação
├── Squad Industrial — softwares industriais
└── Squad [Funcionário N] — personalizado
```

---

> Última atualização: 2026-03-23
