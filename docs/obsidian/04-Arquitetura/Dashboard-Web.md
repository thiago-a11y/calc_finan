# Arquitetura — Dashboard Web (Centro de Comando)

> Painel visual para Thiago e o Operations Lead acompanharem squads, aprovações, RAG e standups em tempo real.

---

## Stack do Dashboard

| Camada | Tecnologia | Versão |
|---|---|---|
| **API HTTP** | FastAPI | 0.135 |
| **Servidor ASGI** | uvicorn | 0.34 |
| **Frontend** | React + TypeScript | 18 |
| **Build Tool** | Vite | 6 |
| **Estilização** | Tailwind CSS | 4 |
| **Linguagem** | TypeScript | 5.7 |

## Estrutura de Pastas

```
api/                         # Backend FastAPI
├── main.py                  # App FastAPI com CORS e lifespan
├── dependencias.py          # Singleton do SyneriumFactory
├── schemas.py               # Schemas Pydantic (request/response)
└── routes/
    ├── status.py            # GET /api/status
    ├── squads.py            # GET /api/squads
    ├── aprovacoes.py        # GET/POST /api/aprovacoes
    ├── rag.py               # GET /api/rag/status + POST /api/rag/consultar
    └── standup.py           # POST /api/standup

dashboard/                   # Frontend React
├── vite.config.ts           # Vite + Tailwind + proxy para API
├── src/
│   ├── App.tsx              # Roteamento principal
│   ├── types/index.ts       # Tipos TypeScript
│   ├── services/api.ts      # Comunicação com FastAPI
│   ├── hooks/usePolling.ts  # Polling automático
│   ├── components/          # Sidebar, Card, Badge
│   └── pages/               # PainelGeral, Aprovacoes, Squads, RAG, Standup
```

## Fluxo de Dados

```
Browser (localhost:5173)
    → Vite proxy (/api)
        → FastAPI (localhost:8000)
            → SyneriumFactory (singleton)
                ├── ApprovalGate (historico)
                ├── RAGQuery (ChromaDB)
                ├── Squads (registrados)
                └── DailyStandup (CrewAI)
```

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/status` | Visão geral da fábrica |
| GET | `/api/squads` | Lista de squads com agentes |
| GET | `/api/aprovacoes` | Todas as aprovações (filtro: `?pendentes=true`) |
| POST | `/api/aprovacoes` | Criar nova solicitação |
| POST | `/api/aprovacoes/{id}/acao` | Aprovar ou rejeitar |
| GET | `/api/rag/status` | Config e vaults do RAG |
| POST | `/api/rag/consultar` | Busca semântica na base |
| POST | `/api/standup` | Gerar relatório diário (10-30s) |

## Páginas do Dashboard

1. **Painel Geral** — Cards com métricas, lista de squads e vaults
2. **Aprovações** — Fila do Operations Lead, botões aprovar/rejeitar, formulário
3. **Squads** — Grid de cards com especialidade e agentes
4. **Base de Conhecimento (RAG)** — Config, vaults e campo de consulta
5. **Standup Diário** — Botão gerar + relatório renderizado
6. **Luna** (`/luna`) — Assistente IA com streaming, voz, preview de artefatos

## Decisões Técnicas

- **Por que FastAPI?** Reutiliza o Pydantic já existente no projeto. Performance excelente.
- **Por que Vite?** Build ultra-rápido. HMR instantâneo em desenvolvimento.
- **Por que polling e não WebSocket?** Simplicidade para uso local. Polling de 5-10s é suficiente para o caso de uso.
- **Por que Tailwind?** Produtividade máxima sem CSS customizado. Consistência visual.

## Como Rodar

```bash
# Terminal 1 — API
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2 — Dashboard
cd dashboard && npm run dev
```

Acessar: `http://localhost:5173`

---

> Última atualização: 2026-03-23
