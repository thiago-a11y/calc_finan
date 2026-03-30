# Arquitetura: Autonomous Squads

> Workflow BMAD completo automatizado com 4 fases, gates e execução paralela.

---

## Visão Geral

Os Autonomous Squads permitem que o CEO dispare um workflow completo via Command Center. O sistema executa automaticamente as 4 fases do BMAD (Business, Marketing, Architecture, Development) com gates de aprovação entre fases.

---

## Modelo de Dados

### WorkflowAutonomoDB

```python
class WorkflowAutonomoDB(Base):
    __tablename__ = "workflows_autonomos"

    id              # PK auto-increment
    titulo          # Nome do workflow
    descricao       # Descrição detalhada
    status          # pendente | executando | aguardando_gate | concluido | erro | cancelado
    fase_atual      # business | marketing | architecture | development
    resultado_json  # JSON com resultados de cada fase
    criado_por      # ID do usuário que disparou
    criado_em       # Timestamp de criação
    atualizado_em   # Timestamp da última atualização
```

---

## Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/autonomo` | Criar e disparar workflow autônomo |
| `GET` | `/api/autonomo/{id}` | Consultar status e resultado do workflow |
| `POST` | `/api/autonomo/{id}/aprovar-gate` | Aprovar gate entre fases (CEO/OpsLead) |
| `POST` | `/api/autonomo/{id}/cancelar` | Cancelar workflow em execução |

---

## Fluxo de Execução

### `_executar_workflow_autonomo_bg()`

Função executada em background (thread separada) que orquestra as 4 fases:

```
1. BUSINESS (Análise de negócio)
   ├── Agentes: Marco (PM), Sofia (Secretária)
   ├── Saída: PRD, análise de mercado, requisitos
   └── Gate SOFT → prossegue automaticamente (CEO pode revisar depois)

2. MARKETING (Estratégia e posicionamento)
   ├── Agentes: selecionados por palavra-chave
   ├── Saída: plano de marketing, personas, canais
   └── Gate SOFT → prossegue automaticamente

3. ARCHITECTURE (Arquitetura técnica)
   ├── Agentes: Kenji (Tech Lead), Yuki (IA)
   ├── Saída: design técnico, stack, diagramas
   └── Gate HARD → AGUARDA aprovação do CEO/OpsLead

4. DEVELOPMENT (Implementação)
   ├── Agentes: Amara (Backend), Carlos (Frontend), Hans (DevOps)
   ├── Saída: código, testes, deploy plan
   └── Gate HARD → AGUARDA aprovação para deploy
```

### Gates Soft vs Hard

- **Gate Soft**: O workflow prossegue automaticamente. O CEO pode revisar os resultados a qualquer momento, mas não bloqueia a execução.
- **Gate Hard**: O workflow PARA e aguarda aprovação explícita do CEO ou Operations Lead. Apenas após aprovação a próxima fase inicia.

---

## Integração com Command Center

O Command Center (`/command-center` no dashboard) exibe:

- **KPIs em tempo real** — Workflows ativos, concluídos, taxa de sucesso
- **Comando estratégico** — Formulário para disparar novo workflow autônomo
- **Spawn de squads** — Criar squads sob demanda para projetos específicos
- **Status dos gates** — Visualização de gates pendentes para aprovação

---

## Gate Approval com threading.Lock

```python
_gate_lock = threading.Lock()

def aprovar_gate(workflow_id, usuario):
    with _gate_lock:
        workflow = db.get(workflow_id)
        if workflow.status != "aguardando_gate":
            raise HTTPException(400, "Workflow não está aguardando gate")
        if usuario.papel not in ["ceo", "operations_lead"]:
            raise HTTPException(403, "Apenas CEO/OpsLead podem aprovar gates")
        workflow.status = "executando"
        db.commit()
```

---

## Session SQLite Isolada por Fase

A partir da v0.50.0, cada fase do workflow cria sua própria `SessionLocal()` em vez de compartilhar uma única session entre todas as fases. Isso resolve o crash `commit() can't be called` que ocorria em threads longas.

```python
def _executar_fase(fase, workflow_id):
    db = SessionLocal()  # Session isolada por fase
    try:
        # ... execução da fase ...
        db.commit()
    finally:
        db.close()
```

---

## Fila de Workflows Automática

Quando um workflow conclui ou falha, o sistema verifica automaticamente se há workflows com status `aguardando_fila` e inicia o próximo. Isso evita que workflows fiquem presos aguardando início manual.

```
Workflow A (executando) → conclui/falha
    └── Verifica fila → Workflow B (aguardando_fila) → inicia automaticamente
```

---

## Progresso Percentual por Fase

Cada fase do BMAD representa 25% do progresso total. O Command Center exibe uma barra de progresso em cada card de squad:

| Fase | Progresso |
|------|-----------|
| Business | 25% |
| Marketing | 50% |
| Architecture | 75% |
| Development | 100% |

O progresso é atualizado em tempo real conforme o workflow avança pelas fases.

---

## Recovery de Workflows Travados

No startup do servidor (`api/main.py`), uma verificação automática:

1. Busca workflows com `status = "executando"` e `atualizado_em < agora - 30min`
2. Marca como `status = "erro"` com mensagem explicativa
3. Registra em audit log

---

> Última atualização: 2026-03-30
