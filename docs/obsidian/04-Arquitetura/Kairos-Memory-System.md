# Kairos — Sistema de Memória Auto-Evolutiva

> Memória de longo prazo para agentes IA do Synerium Factory.

**Fase:** 3.1 | **Versão:** v0.60.0 | **Última atualização:** 05/Abr/2026

---

## Visão Geral

O Kairos é o sistema de memória auto-evolutiva do Synerium Factory. Inspirado no padrão AutoDream, ele captura fragmentos brutos de interações (snapshots) e periodicamente os consolida em memórias estruturadas usando LLM — como o processo de "sonho" que organiza experiências.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FONTES DE SNAPSHOT                              │
│                                                                         │
│   Luna        Mission Control     Reunião       Workflow     Agente     │
│   (chat)      (sessão)            (escritório)  (BMAD)       (tarefa)  │
│     │              │                   │            │            │      │
│     └──────────────┴───────────────────┴────────────┴────────────┘      │
│                                    │                                    │
│                                    ▼                                    │
│                         ┌──────────────────┐                            │
│                         │  SnapshotManager  │                           │
│                         │  (captura bruta)  │                           │
│                         └────────┬─────────┘                            │
│                                  │                                      │
│                                  ▼                                      │
│                    ┌─────────────────────────┐                          │
│                    │  MemorySnapshotDB        │                         │
│                    │  (snapshots pendentes)   │                         │
│                    └─────────────┬───────────┘                          │
└──────────────────────────────────│──────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        AUTO DREAM            │
                    │  (consolidação background)   │
                    │                              │
                    │  1. Adquirir lock             │
                    │  2. Buscar pendentes          │
                    │  3. Agrupar por agente        │
                    │  4. LLM consolida → JSON      │
                    │  5. Criar MemoryEntry          │
                    │  6. Marcar consolidados        │
                    │  7. Limpar expirados          │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     MemoryEntryDB             │
                    │  (memórias consolidadas)      │
                    │                              │
                    │  • 4 tipos: episódica,       │
                    │    semântica, procedural,     │
                    │    estratégica                │
                    │  • Tags para busca           │
                    │  • Relevância 0.0–1.0        │
                    │  • Tracking de acessos       │
                    └──────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       MemoryRegistry          │
                    │  (consulta + busca textual)   │
                    │                              │
                    │  Agentes, Luna, Mission       │
                    │  Control consultam memórias   │
                    │  consolidadas por tipo,       │
                    │  agente, tags, relevância     │
                    └──────────────────────────────┘
```

## Componentes

| Arquivo | Responsabilidade |
|---------|------------------|
| `types.py` | Dataclasses e enums (MemoryType, SnapshotSource, etc.) |
| `consolidation_lock.py` | Lock por arquivo com TTL 10min + detecção de PID morto |
| `memory_snapshot.py` | Captura, listagem e limpeza de snapshots |
| `consolidation_prompt.py` | Prompts para consolidação e mesclagem via LLM |
| `auto_dream.py` | Motor de consolidação: ciclo único + loop background |
| `registry.py` | CRUD de memórias + busca textual + tracking de acessos |
| `service.py` | KairosService singleton — ponto de entrada único |

## Tipos de Memória

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| Episódica | Evento específico | "Reunião de 03/04: decidimos migrar para PostgreSQL" |
| Semântica | Conhecimento geral | "SyneriumX usa PHP 7.4 + React 18 + MySQL" |
| Procedural | Como fazer algo | "Para deploy: git push → ssh → git pull → build → restart" |
| Estratégica | Decisão de alto nível | "Prioridade: Fase 3.1 Kairos antes de multi-tenant" |

## Fontes de Snapshot

| Source | Quando captura |
|--------|---------------|
| `luna` | Conversas relevantes na Luna |
| `mission_control` | Sessões de desenvolvimento |
| `reuniao` | Reuniões no Escritório Virtual |
| `workflow` | Workflows BMAD autônomos |
| `agente` | Tarefas executadas por agentes |
| `manual` | Registrado manualmente |

## Configuração

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `dream_interval_min` | 60 | Intervalo entre ciclos de dream |
| `max_snapshots_por_dream` | 50 | Máximo de snapshots por ciclo |
| `max_memoria_por_agente` | 200 | Máximo de memórias por agente |
| `ttl_snapshot_horas` | 72 | TTL de snapshots consolidados |
| `modelo_consolidacao` | sonnet | Modelo LLM para consolidação |

## Uso

```python
from core.memory.kairos import kairos_service

# Capturar snapshot
await kairos_service.criar_snapshot(
    agente_id="tech_lead",
    source="luna",
    conteudo="Decidimos usar PostgreSQL para produção",
    contexto={"conversa_id": "abc123"},
)

# Consultar memórias
resultados = kairos_service.consultar(
    agente_id="tech_lead",
    query="banco de dados",
    limite=5,
)

# Disparar dream manualmente
resultado = await kairos_service.dream()

# Status do sistema
status = kairos_service.status()
```

## Próximos Passos

- [ ] Integrar com Luna (capturar snapshots automaticamente)
- [ ] Integrar com Mission Control
- [ ] API REST para dashboard
- [ ] Auto-dream no startup da API
- [ ] Embeddings para busca semântica (ChromaDB)
