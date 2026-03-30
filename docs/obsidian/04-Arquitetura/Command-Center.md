# Command Center — Arquitetura

> Painel estrategico do CEO para comando e controle da fabrica.
> Criado em v0.49.0, expandido em v0.50.0.

---

## Visao Geral

O Command Center e o painel central do CEO para monitorar e comandar toda a fabrica de agentes. Reune KPIs em tempo real, workflows autonomos, gates pendentes e a funcionalidade Vision-to-Product.

## Endpoints

### GET /command-center

Retorna dados consolidados para o painel:
- **KPIs**: workflows ativos, concluidos, falhos, taxa de sucesso %
- **Workflows**: lista de WorkflowAutonomoDB com status, fase atual, progresso %
- **Evolucoes**: sugestoes do Factory Optimizer (EvolucaoFactoryDB)
- **Gates pendentes**: gates aguardando aprovacao do CEO/OpsLead

### POST /command-center/estrategia

Recebe uma visao de produto em linguagem natural e:
1. PM Central (Alex) processa a visao via LLM
2. Gera roadmap de features com prioridade e complexidade
3. Estima dias por feature e custo total
4. Cria workflows autonomos para cada feature
5. Retorna roadmap completo para exibicao no dashboard

## Vision-to-Product (v0.50.0)

Fluxo completo de uma visao de produto ate a execucao:

```
CEO descreve visao → PM Central analisa via LLM → Roadmap gerado
    → Features com prioridade/complexidade
    → Estimativa de dias e custo por feature
    → Workflows autonomos criados (um por feature)
    → Fila automatica: execucao sequencial
    → Progresso % em tempo real no dashboard
```

### Dados do roadmap gerado:
- Nome da feature
- Descricao
- Prioridade (alta, media, baixa)
- Complexidade (1-5)
- Estimativa de dias
- Custo estimado (baseado em tokens LLM)

## Progresso %

Cada card de squad no Command Center exibe uma barra de progresso calculada por:
- Fase 1 (Business) = 25%
- Fase 2 (Marketing) = 50%
- Fase 3 (Architecture) = 75%
- Fase 4 (Development) = 100%
- Status `erro` ou `cancelado` = mantém ultimo %

## Fila de Workflows

- Workflows sao enfileirados com status `aguardando_fila`
- Ao concluir ou falhar um workflow, o sistema verifica e inicia o proximo
- CEO pode enfileirar multiplos via comando estrategico
- Execucao sequencial para evitar estouro de rate limits

## Spawn de Squads

O Command Center permite criar squads sob demanda:
- Selecao de agentes do catalogo (16 disponiveis)
- Atribuicao a usuarios especificos
- Hot-reload sem restart do servidor

## Dependencias

- `api/routes/tarefas.py` — Endpoints do Command Center
- `agents/pm_central.py` — PM Central processa visao e gera roadmap
- `core/llm_fallback.py` — Fallback de LLM para chamadas
- `database/models.py` — WorkflowAutonomoDB, EvolucaoFactoryDB

---

> Ultima atualizacao: 2026-03-30
