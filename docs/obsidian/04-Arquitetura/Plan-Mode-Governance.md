# Plan Mode — Governança Avançada

> Sistema de permissões granulares com modo somente-leitura para planejamento seguro.

**Fase:** 3.2 | **Versão:** v0.61.0 | **Última atualização:** 05/Abr/2026

---

## Visão Geral

O Plan Mode permite que agentes e CEO operem em modo somente-leitura: podem analisar, consultar e gerar planos sem risco de executar ações destrutivas. Ferramentas são classificadas em 5 categorias de risco e bloqueadas conforme o modo ativo.

## Diagrama

```
┌──────────────────────────────────────────────────────────┐
│                   CHAMADA DE FERRAMENTA                    │
│                    (Luna, MC, Agente)                      │
│                          │                                │
│                          ▼                                │
│              ┌───────────────────────┐                    │
│              │   PermissionGuard     │                    │
│              │                       │                    │
│              │  classificar(tool)    │                    │
│              │     │                 │                    │
│              │     ▼                 │                    │
│              │  ┌──────────────┐    │                    │
│              │  │ SAFE         │ ──→ PERMITIDO           │
│              │  │ WRITE        │ ──→ bloqueado (Plan)    │
│              │  │ EXECUTE      │ ──→ bloqueado (Plan)    │
│              │  │ DESTRUCTIVE  │ ──→ bloqueado (Plan)    │
│              │  │ EXTERNAL     │ ──→ bloqueado (Plan)    │
│              │  └──────────────┘    │                    │
│              │                       │                    │
│              │  Se bloqueado:        │                    │
│              │  → PermissionRequest  │                    │
│              │  → CEO aprova/rejeita │                    │
│              └───────────────────────┘                    │
└──────────────────────────────────────────────────────────┘
```

## Modos

| Modo | Categorias Permitidas | Uso |
|------|----------------------|-----|
| Normal | SAFE + WRITE + EXECUTE + DESTRUCTIVE + EXTERNAL | Operação padrão |
| Plan | SAFE apenas | Planejamento somente-leitura |
| Restricted | SAFE apenas | Agentes com escopo limitado |

## Categorias de Risco

| Categoria | Exemplos | Risco |
|-----------|----------|-------|
| SAFE | Read, Grep, Glob, Search | Nenhum — leitura pura |
| WRITE | Write, Edit, salvar | Médio — modifica arquivos |
| EXECUTE | Bash, run, spawn, fork | Alto — executa comandos |
| DESTRUCTIVE | Delete, push --force, restart | Crítico — irreversível |
| EXTERNAL | Deploy, Email, Push, Merge | Alto — afeta sistemas externos |

## Componentes

| Arquivo | Responsabilidade |
|---------|------------------|
| `types.py` | Enums + dataclasses |
| `modes.py` | Definições dos 3 modos |
| `permission_guard.py` | Guard: classificação + verificação + requests |
| `enter_plan_mode.py` | Ativa Plan Mode + sessão + snapshot Kairos |
| `exit_plan_mode.py` | Desativa + resumo + snapshot Kairos |
| `plan_agent.py` | PlanAgent: planos via LLM |
| `service.py` | PlanModeService singleton |

## Integração Luna (v0.61.1)

- `_detectar_plan_mode(mensagem)` — 9 padrões regex (5 entrada + 4 saída)
- `_handle_plan_mode(acao, ...)` — processa entrar/sair com resposta confirmando
- Interceptação em `stream_resposta()` antes do fork de sub-agente
- Snapshot Kairos capturado automaticamente na transição

## Integração Mission Control (v0.61.2)

- `POST /sessao/{id}/plan-mode/entrar` — ativa Plan Mode com motivo
- `POST /sessao/{id}/plan-mode/sair` — desativa e retorna resumo (duração, bloqueios)
- `GET /plan-mode/status` — status atual (modo, sessão, guard stats)
- Helper `_plan_mode_action()` — síncrono via `asyncio.run()` (endpoints não-async)
- Snapshots Kairos automáticos ao entrar/sair

## Dashboard UI (v0.61.3)

- Botão toggle no header do Mission Control (ao lado das métricas)
- Inativo: ShieldOff cinza | Ativo: Shield roxo + dot pulsante
- Loading 600ms + toast verde "Plan Mode ativado" / "Modo Normal restaurado" 2.5s
- Fetch automático do status ao carregar sessão

## Próximos Passos

- [x] Integrar Plan Mode com Luna — v0.61.1
- [x] Integrar com Mission Control (endpoints) — v0.61.2
- [x] Botão visual no Mission Control — v0.61.3
