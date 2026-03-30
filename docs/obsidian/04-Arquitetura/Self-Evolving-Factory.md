# Arquitetura: Self-Evolving Factory

> Sistema de auto-evolução da fábrica com review sessions e Factory Optimizer.

---

## Visão Geral

A Self-Evolving Factory é o mecanismo pelo qual o Synerium Factory melhora a si mesmo continuamente. Após cada workflow autônomo concluído, uma review session analisa o resultado e gera sugestões de melhoria. O CEO aprova as sugestões relevantes, que são então implementadas.

---

## Modelo de Dados

### EvolucaoFactoryDB

```python
class EvolucaoFactoryDB(Base):
    __tablename__ = "evolucoes_factory"

    id                # PK auto-increment
    workflow_id       # FK para WorkflowAutonomoDB (origem)
    tipo              # performance | qualidade | processo | arquitetura
    titulo            # Título curto da sugestão
    descricao         # Descrição detalhada da melhoria proposta
    impacto_estimado  # baixo | medio | alto | critico
    status            # pendente | aprovada | implementada | rejeitada
    aprovado_por      # ID do usuário que aprovou (NULL se pendente)
    criado_em         # Timestamp
    atualizado_em     # Timestamp
```

---

## Factory Optimizer (ID=16)

O Factory Optimizer é o 16o agente no catálogo, com papel de **Distinguished Engineer**:

- **Nome:** Factory Optimizer
- **Papel:** Distinguished Engineer (meta-análise)
- **Metodologia:** Ciclo PDCA (Plan-Do-Check-Act)
- **Função:** Analisa workflows concluídos e propõe melhorias estruturais
- **Não executa tarefas operacionais** — apenas observa e sugere

---

## Fluxo: Review Session

### `_executar_review_session()`

Executada automaticamente após a conclusão de cada workflow autônomo:

```
1. WORKFLOW CONCLUÍDO
   │
   ▼
2. REVIEW SESSION (automática)
   ├── Factory Optimizer analisa:
   │   ├── Tempo de execução por fase
   │   ├── Qualidade dos resultados
   │   ├── Erros ou retrabalho
   │   ├── Uso de recursos (tokens, chamadas API)
   │   └── Padrões recorrentes
   │
   ▼
3. SUGESTÕES GERADAS
   ├── Registradas em EvolucaoFactoryDB
   ├── Status: "pendente"
   ├── Tipos: performance, qualidade, processo, arquitetura
   │
   ▼
4. CEO REVISA E APROVA
   ├── Via Command Center ou endpoint dedicado
   ├── Aprovar → status = "aprovada"
   ├── Rejeitar → status = "rejeitada"
   │
   ▼
5. IMPLEMENTAÇÃO
   └── Sugestões aprovadas entram no backlog ou são aplicadas automaticamente
```

---

## Endpoints de Evolução

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/evolucao` | Listar sugestões de evolução (filtros por status, tipo) |
| `GET` | `/api/evolucao/{id}` | Detalhe de uma sugestão |
| `POST` | `/api/evolucao/{id}/aprovar` | Aprovar sugestão (CEO/OpsLead) |
| `POST` | `/api/evolucao/{id}/rejeitar` | Rejeitar sugestão com justificativa |

---

## Ciclo PDCA

O Factory Optimizer aplica o ciclo PDCA em cada review:

1. **Plan** — Identifica áreas de melhoria com base nos dados do workflow
2. **Do** — Propõe ações concretas (sugestões registradas no banco)
3. **Check** — Após implementação, verifica se a melhoria teve efeito (próxima review)
4. **Act** — Consolida melhorias bem-sucedidas como padrão da fábrica

---

> Última atualização: 2026-03-30
