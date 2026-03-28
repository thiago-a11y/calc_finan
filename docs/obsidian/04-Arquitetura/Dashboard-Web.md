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

## Sistema de Avatares dos Agentes

### Arquitetura

```
dashboard/src/config/agents.ts       # Config centralizada de todos os agentes
dashboard/src/components/AgentAvatar.tsx  # Componente reutilizável de avatar
dashboard/public/avatars/            # Imagens JPG dos 10 agentes
```

### `agents.ts` — Config Centralizada

Arquivo único com dados de todos os agentes IA do sistema:
- **id** — Identificador único (ex: `kenji`, `luna`)
- **nome** — Nome completo do agente
- **cargo** — Função no sistema (ex: "Arquiteto de Soluções")
- **avatar** — Path do JPG em `public/avatars/`
- **cor** — Cor temática do agente (para badges e bordas)
- **especialidade** — Área de atuação

Função exportada: `getAgentConfig(id)` retorna a config completa do agente.

### `AgentAvatar.tsx` — Componente Reutilizável

Props principais:
- **agentId** — ID do agente para buscar config automaticamente
- **size** — `sm` (32px), `md` (40px), `lg` (48px), `xl` (64px), `2xl` (80px)
- **showStatus** — Indicador de online/offline
- **fallback** — Iniciais do nome quando imagem não carrega

Componente auxiliar `AgentAvatarGroup` empilha múltiplos avatares com sobreposição (estilo participantes de reunião).

### Telas que usam AgentAvatar
- **ChatFloating** — Avatar do agente no cabeçalho do chat
- **ReuniaoModal** — Grupo de avatares dos participantes
- **Escritório Virtual** — Avatares nos assentos de cada agente
- **Catálogo de Agentes** — Cards com avatar grande
- **Luna Chat** — Avatar da Luna nas mensagens
- **Luna Welcome** — Avatar destaque na tela inicial

---

> Última atualização: 2026-03-28
