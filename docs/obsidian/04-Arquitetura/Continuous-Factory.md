# Continuous Factory — Modo Contínuo 24/7

> Versão: v0.54.0 | Data: 31/Mar/2026

## Visão Geral

O Modo Contínuo transforma o Synerium Factory numa empresa virtual que opera 24/7. Quando ativado, workflows autônomos continuam executando, gates são gerenciados automaticamente e o CEO recebe relatórios diários por email.

## Arquitetura

```
CEO ativa Modo Contínuo
  ↓
Worker Background (thread daemon, loop 30s)
  ├─ Auto-aprova gates soft (sempre)
  ├─ Auto-aprova gates hard (se configurado)
  │   └─ Se não auto-aprovar → envia email ao CEO
  ├─ Verifica horário do relatório diário (23:00)
  │   └─ Gera relatório com métricas + resumo LLM
  └─ Atualiza métricas do dia na ContinuousFactoryDB
```

## Componentes

### 1. ContinuousFactoryDB (Singleton por empresa)
- `ativo` — Boolean que controla se o modo está ativo
- `auto_aprovar_hard` — Se True, gates hard são auto-aprovados
- `email_notificacao` — Email para notificações de gates pendentes
- `horario_relatorio` — Horário do relatório diário (default: 23:00)
- `max_workflows_paralelos` — Limite de workflows simultâneos
- Métricas do dia: workflows, custo, fases, erros (resetadas no relatório)

### 2. RelatorioDiarioDB
- Métricas: workflows executados/concluídos/erro, custo, tokens, evoluções
- Resumo gerado por LLM (via Smart Router)
- Próximos passos sugeridos
- Enviado por email automaticamente

### 3. Worker Background
- Thread daemon com loop a cada 30s
- Thread-safe com `_worker_lock`
- Recovery automático no startup do FastAPI
- Encerra sozinho quando modo contínuo é desativado

### 4. Integração com Gates
Em `_executar_workflow_autonomo_bg()` (tarefas.py), antes de pausar para gate hard:
```python
from api.routes.continuous_factory import verificar_auto_aprovacao_gate
if verificar_auto_aprovacao_gate(workflow_id, fase, company_id):
    # Auto-aprovado pelo Modo Contínuo
    fase += 1
    continue
```

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/continuous-factory` | Status + config + métricas |
| POST | `/api/continuous-factory/ativar` | Ativa (CEO/Operations Lead) |
| POST | `/api/continuous-factory/desativar` | Desativa |
| POST | `/api/continuous-factory/config` | Atualiza configurações |
| GET | `/api/continuous-factory/relatorios` | Lista relatórios (30 dias) |
| POST | `/api/continuous-factory/relatorio-agora` | Gera relatório manualmente |

## Como Ativar

```bash
curl -X POST /api/continuous-factory/ativar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"email_notificacao": "ceo@empresa.com", "auto_aprovar_hard": true}'
```

## Exemplo de Relatório

```json
{
  "data": "2026-03-31",
  "workflows_executados": 8,
  "workflows_concluidos": 7,
  "workflows_erro": 1,
  "custo_total_usd": 0.8666,
  "evolucoes_geradas": 15,
  "resumo": "Dia produtivo com 7 workflows concluídos...",
  "proximos_passos": ["Revisar evoluções pendentes", "Otimizar custos"]
}
```

## Segurança

- Apenas CEO ou Operations Lead podem ativar/desativar
- Gates hard com `auto_aprovar_hard=false` (default) requerem aprovação humana
- Email de notificação verificado no Amazon SES
- Worker encerra automaticamente se modo for desativado

## Dependências

- Amazon SES (email) — já configurado
- Smart Router Dinâmico (relatório LLM)
- Self-Evolving Factory (métricas de evoluções)
- Autonomous Squads (workflows)
