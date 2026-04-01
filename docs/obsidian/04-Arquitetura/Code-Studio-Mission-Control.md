# Code Studio 2.0 — Mission Control

> Versão: v0.57.0 | Data: 01/Abr/2026

## Visão Geral

O Mission Control é o Code Studio 2.0 — um ambiente de desenvolvimento imersivo com painel triplo simultâneo (Editor + Terminal + Artifacts/Navegador). Agentes IA trabalham em tempo real, gerando entregáveis tangíveis que o CEO pode revisar e comentar inline.

## Persistência de Sessões (v0.57.0)

### Fluxo do usuário
1. Acessa `/mission-control` → vê **lista de sessões recentes** (titulo, status, metricas, tempo relativo)
2. Clica "Retomar" → navega para `/mission-control/{sessionId}` → carrega estado completo
3. Ou clica "Nova Sessão" → cria sessão e navega automaticamente para ela
4. Enquanto trabalha, **auto-save a cada 10s** persiste: conteúdo do editor, arquivo ativo, histórico do terminal
5. Fecha aba/navega para outra página → ao voltar, tudo restaurado exatamente

### Endpoints de persistência
- `GET /api/mission-control/sessoes` — Últimas 20 sessões do usuário
- `PATCH /api/mission-control/sessao/{id}/save` — Auto-save (chamado a cada 10s pelo frontend)

### O que é persistido
- **Editor**: conteúdo completo (`painel_editor.conteudo`), arquivo ativo (`arquivo_ativo`)
- **Terminal**: últimos 50 comandos com output, sucesso/falha, timestamp
- **Artifacts**: todos os artifacts gerados por agentes (ArtifactDB)
- **Comentários inline**: `ArtifactDB.comentarios_inline` (JSON)
- **Agentes**: estado de cada agente (executando/concluído/erro)

## Arquitetura

```
Dashboard (/mission-control)
  ├─ Painel 1: Editor (código, preview)
  ├─ Painel 2: Terminal (comandos sandboxed)
  └─ Painel 3: Artifacts (planos, checklists, código)
       ├─ Gerados por agentes em background
       ├─ Comentários inline (estilo Google Docs)
       └─ Status: gerado → revisado → aprovado
```

## Componentes

### Backend (api/routes/mission_control.py)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/mission-control/sessoes` | GET | Lista sessões ativas |
| `/api/mission-control/sessao` | POST | Cria nova sessão |
| `/api/mission-control/sessao/{id}` | GET | Detalhes com artifacts |
| `/api/mission-control/sessao/{id}/comando` | POST | Executa no terminal |
| `/api/mission-control/sessao/{id}/agente` | POST | Dispara agente |
| `/api/mission-control/artifacts/{sessao_id}` | GET | Lista artifacts |
| `/api/mission-control/artifacts/{id}/comentar` | POST | Comentário inline |
| `/api/mission-control/artifacts/{id}/status` | POST | Atualizar status |

### Frontend (dashboard/src/pages/MissionControl.tsx)

- Painel triplo com ResizableHandle (redimensionável)
- Terminal com histórico e input inline
- Barra de instrução de agente no topo
- Agentes vivos com animação pulse no header
- Artifacts expansíveis com comentários

### Models

- **ArtifactDB** — tipo, titulo, conteudo, dados (JSON), comentarios_inline (JSON array)
- **MissionControlSessaoDB** — estado dos 3 painéis, agentes ativos, métricas

## Tipos de Artifacts

| Tipo | Descrição | Ícone |
|------|-----------|-------|
| plano | Plano de implementação gerado por LLM | FileText |
| checklist | Lista de tarefas com items verificáveis | CheckSquare |
| codigo | Trecho de código gerado | Code2 |
| terminal | Output significativo de comando | Terminal |
| screenshot | Captura de tela do navegador | Eye |
| markdown | Documentação ou notas | FileText |

## Segurança

- Comandos destrutivos bloqueados (rm -rf, mkfs, shutdown, etc)
- Timeout de 30s por comando
- Sessões isoladas por usuário (usuario_id)
- Multi-tenant (company_id)

## Diferencial vs Antigravity

| Feature | Antigravity | Mission Control |
|---------|-------------|-----------------|
| Painéis simultâneos | 2 (editor + preview) | 3 (editor + terminal + artifacts) |
| Terminal integrado | Não | Sim, sandboxed |
| Artifacts tangíveis | Não | Sim, com checklist e planos |
| Comentários inline | Não | Sim, estilo Google Docs |
| Agentes vivos animados | Não | Sim, com pulse animation |
| Background execution | Limitado | Full async com polling 5s |
