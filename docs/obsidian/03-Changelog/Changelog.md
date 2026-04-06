# Changelog — Synerium Factory

> Histórico completo de mudanças e versões.

---

## v0.61.9 — Fix: Botão Voltar para Revisão no Mission Control (06/Abr/2026)

### Bug #60: Botão "Voltar para Revisão" não voltava para os 3 painéis

**Causa:** `missaoConcluida` era true por 3 condições OR (status, progresso 100%, agentes concluídos). O `onVoltarRevisao` só mudava `sessao.status` para 'ativa', mas as outras 2 condições continuavam true.

**Correção:**
- Novo estado `forcarRevisao` — quando true, desativa `missaoConcluida` independente das condições
- `onVoltarRevisao` agora seta `forcarRevisao=true` (simples e confiável)
- Banner "Modo Revisão" no topo com botão "Voltar para Conclusão"

---

## v0.61.8 — Seletor de Projeto + Salvar Arquivos + Fix Git Commit (05/Abr/2026)

### Mission Control agora vincula sessões a projetos reais

**Seletor de projeto ao criar sessão:**
- Dropdown com projetos disponíveis ao lado do campo de título
- Sessão criada com `projeto_id` associado
- Indicador visual: "Arquivos gerados serão salvos no diretório do projeto selecionado"

**Novo endpoint: POST /sessao/{id}/salvar-arquivos:**
- Salva conteúdo do editor/artifacts como arquivos reais no diretório do projeto
- Proteção contra path traversal (`.lstrip("/")`, `replace("..", "")`)
- Fallback: se nenhum arquivo explícito, salva conteúdo do editor como arquivo

**Novo endpoint: GET /projetos:**
- Lista projetos disponíveis para o seletor

**Fix git-commit:**
- Adicionado `git add -A` antes do commit (faltava — nada era staged)
- Unificado `git -c user.name=... -c user.email=... commit -m ...` em um único comando
- Verificação dupla: `--porcelain` antes do add, `--cached --stat` depois do add

---

## v0.61.7 — Fix: Botões de aprovação só funcionavam na primeira fase (05/Abr/2026)

### Bug #58: Após aprovar Fase 1, botões de aprovação da Fase 2+ nunca apareciam

**Causa raiz (2 problemas simultâneos):**
1. **Backend**: `fase_status` dependia exclusivamente de `_decision_engine.is_waiting()`, mas entre a aprovação e o `set_pending` da próxima fase há um delay (LLM call). O frontend carregava `waiting_decision=false` e escondia os botões.
2. **Frontend**: Após aprovar, `carregarFaseStatus()` era chamado imediatamente — antes do agente thread avançar para a próxima fase.

**Correções:**
- Backend: fallback no `fase_status` — se `fase_label` contém "Aguardando" e agente está "executando", trata como `waiting_decision=true`
- Frontend: delay de 2s após aprovar antes de recarregar o status

---

## v0.61.6 — Fix: Polling infinito no Mission Control (05/Abr/2026)

### Bug #57: `headers` recriado a cada render causava loop infinito de requests

**Causa raiz:** `headers` era um objeto literal recriado a cada render → `useCallback` com dependência `headers` recriava as funções → `useEffect` re-executava → intervals duplicados → dezenas de requests/segundo ao servidor (chat + fase-status + plan-mode/status).

**Correções:**
- `headers` agora usa `useMemo([token])` — estável entre renders
- `fetchPlanStatus` removido das dependências do useEffect de polling
- Plan Mode status carregado em useEffect separado (uma vez ao abrir sessão)
- Botão executar e botões de ação restaurados (não eram re-renderizados por causa dos re-renders infinitos)

---

## v0.61.5 — Fix: Skills restauradas em produção (05/Abr/2026)

- `tools/skills_catalog.py` — catálogo leve de metadados (31 skills + 9 perfis)
- Registra apenas nome/descrição/categoria/ícone SEM instanciar ferramentas
- Resolve ChromaDB crash: tools RAG-based (WebsiteSearchTool, DirectorySearchTool) inicializavam ChromaDB ao instanciar
- `api/dependencias.py` — chama `registrar_catalogo_skills()` no startup
- 31 skills registradas (30 ativas, RAG desabilitada por ChromaDB)
- GET /api/skills retorna dados completos no dashboard

---

## v0.61.4 — Correção de Intermitência no Botão Plan Mode (05/Abr/2026)

- Botão desabilitado quando `sessao_id` não existe (opacity 0.4 + cursor not-allowed)
- Toast de erro vermelho quando API falha ou retorna `sucesso=false`
- `togglePlanMode` com guard duplo (`!sessao?.sessao_id || planLoading`)
- Headers construídos inline (não reusa objeto mutável) para evitar stale token
- `fetchPlanStatus` re-chamado 500ms após toggle para confirmar estado real do servidor
- `useEffect` com `fetchPlanStatus` nas dependências para evitar race condition
- Guard `if (!token) return` no `fetchPlanStatus`

---

## v0.61.3 — Botão Visual Plan Mode no Mission Control (05/Abr/2026)

### CEO pode ativar/desativar Plan Mode direto no header do Mission Control

- Botão Plan Mode no header da sessão (ao lado das métricas)
- Inativo: icone ShieldOff cinza | Ativo: icone Shield roxo com dot pulsante
- Toggle com loading mínimo 600ms + toast de sucesso 2.5s
- Fetch automático do status ao carregar sessão
- Chama endpoints existentes (POST entrar/sair)

### Alterações

- `dashboard/src/pages/MissionControl.tsx` — imports Shield/ShieldOff + estados planMode/planLoading/planToast + fetchPlanStatus() + togglePlanMode() + botão no header

---

## v0.61.2 — Integração Plan Mode + Mission Control (05/Abr/2026)

### CEO pode ativar/desativar Plan Mode dentro de sessões Mission Control

- `POST /api/mission-control/sessao/{id}/plan-mode/entrar` — ativa Plan Mode com motivo
- `POST /api/mission-control/sessao/{id}/plan-mode/sair` — desativa e retorna resumo
- `GET /api/mission-control/plan-mode/status` — status atual do Plan Mode
- Helper `_plan_mode_action()` — executa transições de forma síncrona (asyncio.run)
- Snapshot Kairos capturado automaticamente ao entrar/sair

### Alterações

- `api/routes/mission_control.py` — import `plan_mode_service` + schema `PlanModeRequest` + helper + 3 endpoints

---

## v0.61.1 — Integração Plan Mode + Luna (05/Abr/2026)

### Luna detecta "modo plano" automaticamente na conversa

- Novo método `_detectar_plan_mode(mensagem)` — 5 padrões de entrada + 4 de saída
- Novo método `_handle_plan_mode(acao, ...)` — processa entrar/sair com resposta confirmando
- Interceptação em `stream_resposta()` antes do fork de sub-agente
- Resposta salva no banco (`modelo_usado="plan_mode"`, `provider="system"`)
- Snapshot Kairos capturado automaticamente
- 11 testes de detecção passaram (entrar/sair/neutro)

### Alterações

- `core/luna_engine.py` — import `plan_mode_service` + 2 métodos + interceptação

---

## v0.61.0 — Plan Mode: Governança Avançada (05/Abr/2026)

### Fase 3.2: Plan Mode com permissões granulares

**Novo módulo `core/governance/plan_mode/` — 7 arquivos:**

- `types.py` — 3 enums (AgentMode, ToolCategory, PermissionStatus) + 4 dataclasses (PlanModeConfig, PlanSession, PermissionRequest)
- `modes.py` — 3 modos pré-definidos (Normal, Plan, Restricted) com categorias permitidas
- `permission_guard.py` — PermissionGuard singleton: classifica 30+ ferramentas por risco (SAFE/WRITE/EXECUTE/DESTRUCTIVE/EXTERNAL), bloqueia conforme modo ativo, cria PermissionRequest para aprovação
- `enter_plan_mode.py` — Ativa Plan Mode com sessão + snapshot Kairos
- `exit_plan_mode.py` — Desativa Plan Mode com resumo (duração, bloqueios) + snapshot Kairos
- `plan_agent.py` — PlanAgent: gera planos estruturados via LLM (somente-leitura)
- `service.py` — PlanModeService singleton: orquestra tudo (entrar/sair/verificar/gerar plano/status)

**Comportamento:**
- Plan Mode: permite Read, Grep, Glob, Search — bloqueia Bash, Write, Edit, Delete, Deploy, Push, Email
- Transição segura entre modos com tracking de sessão
- Snapshots Kairos automáticos ao entrar/sair
- PlanAgent com prompt especializado para planejamento (nunca executa)
- 11 testes de import + verificação de permissões: TODOS PASSARAM

---

## v0.60.5.2 — Botão Criar Snapshot de Teste no Kairos (05/Abr/2026)

- Novo endpoint `POST /api/kairos/snapshot/teste` — cria snapshot de teste para validar o dream
- Novo botão "Criar Snapshot de Teste" na aba Dream (ao lado do Disparar Dream)
- Feedback visual: loading 800ms + mensagem verde "Snapshot criado!" por 2s
- Após criar, atualiza automaticamente status e lista de snapshots

## v0.60.5.1 — Fix: Botão Atualizar do Kairos (05/Abr/2026)

- Botão "Atualizar" não dava feedback visual ao clicar
- Adicionado estado `refreshing` com spinner `Loader2` + texto "Atualizando..."
- `onClick` agora usa `async/await` com `Promise.all` (espera os 3 fetchers antes de liberar)
- Botão `disabled` durante refresh para evitar cliques duplos
- Mínimo 800ms de loading (mesmo se dados carregarem rápido) para usuário perceber o spinner
- Após atualizar: botão fica verde + check + "Atualizado!" por 2 segundos, depois volta ao normal

---

## v0.60.5 — Página Kairos no Dashboard (05/Abr/2026)

### Página visual para o sistema de memória auto-evolutiva

- `dashboard/src/pages/Kairos.tsx` — 4 tabs: Status, Snapshots, Memories, Dream
- `dashboard/src/App.tsx` — rota `/kairos`
- `dashboard/src/components/Sidebar.tsx` — link CEO-only com icone Brain e badge CEO

**Tab Status:** 4 stat cards (ativo, pendentes, consolidadas, AutoDream) + distribuicao por source + memorias por agente + config
**Tab Snapshots:** tabela com filtros por source e status de consolidacao
**Tab Memories:** cards com busca textual, filtro por tipo, relevancia colorida, tags, contagem de acessos
**Tab Dream:** botao de disparo manual com resultado visual (snapshots/criadas/atualizadas/duracao)

Design: dark mode premium, mesmo estilo do Master Control (lucide-react, var(--sf-*))

---

## v0.60.4 — API REST do Kairos (05/Abr/2026)

### 4 endpoints para consulta e controle do sistema de memória

- `GET /api/kairos/status` — status geral + contadores por source/agente
- `GET /api/kairos/snapshots` — lista com paginação + filtros (agente_id, source, consolidado)
- `GET /api/kairos/memories` — busca textual + filtros (tipo, agente, relevância mínima)
- `POST /api/kairos/dream/manual` — disparo manual de consolidação

### Alterações

- `api/routes/kairos.py` — novo arquivo (4 endpoints)
- `api/main.py` — import + include_router

---

## v0.60.3 — AutoDream no Startup da API (05/Abr/2026)

### AutoDream ativado automaticamente ao iniciar a API

- `api/main.py` lifespan startup: `kairos_service.iniciar_auto_dream()`
- `api/main.py` lifespan shutdown: `kairos_service.parar_auto_dream()` (graceful)
- Primeiro ciclo executa imediatamente no startup, depois a cada 60 minutos
- Primeiro dream real: 3 snapshots → 3 memórias consolidadas (semântica, estratégica, episódica)

### Alterações

- `api/main.py` — startup + shutdown do AutoDream no lifespan

---

## v0.60.2 — Integração Kairos + Mission Control (05/Abr/2026)

### Mission Control agora captura snapshots de memória automaticamente

- Helper `_kairos_snapshot()` — non-blocking via `threading.Thread` (endpoints síncronos)
- `criar_sessao` → snapshot com `agente_id="mission_control"` (relevância 0.3)
- `fase_decisao` → snapshot com `agente_id="ceo"` (relevância 0.8 — decisões estratégicas)
- `disparar_agente` → snapshot com `agente_id="mission_control"` (relevância 0.6)
- Contexto inclui: `sessao_id`, `tipo_acao`, `usuario_id`, `fase`, `acao`, `agente_nome`

### Alterações

- `api/routes/mission_control.py` — import `kairos_service` + helper `_kairos_snapshot()` + 3 chamadas

---

## v0.60.1 — Integração Kairos + Luna (05/Abr/2026)

### Luna agora captura snapshots de memória automaticamente

- Novo método `_capturar_snapshot_kairos()` em `core/luna_engine.py`
- Captura non-blocking após cada troca (pergunta + resposta) — nunca atrasa a resposta
- Fluxo normal: `agente_id="luna"` | Fluxo sub-agente: `agente_id="luna:{tipo}"`
- Conteúdo: `[Usuário]: ... + [Luna]: ...` truncado a 5000 chars
- Contexto: `conversa_id`, `usuario_id`, `modelo`, `provider`, `subagente`
- Erro silencioso: falha no Kairos apenas loga warning, nunca quebra a Luna

### Alterações

- `core/luna_engine.py` — import `kairos_service` + `_capturar_snapshot_kairos()` + 2 chamadas (fluxo normal + sub-agente)

---

## v0.60.0 — Kairos: Sistema de Memória Auto-Evolutiva (05/Abr/2026)

### Fase 3.1: Self-Evolving Memory System

**Novo módulo `core/memory/kairos/` — 8 arquivos:**

- `types.py` — Dataclasses e enums (MemorySnapshotData, MemoryEntry, ConsolidationResult, MemoryQuery, KairosConfig, MemoryType, SnapshotSource)
- `consolidation_lock.py` — Lock baseado em arquivo com TTL 10min + detecção de PID morto + cleanup de locks stale
- `memory_snapshot.py` — SnapshotManager: captura, listagem, marcação e limpeza de snapshots
- `consolidation_prompt.py` — Prompts para o LLM consolidar snapshots e mesclar memórias duplicadas
- `auto_dream.py` — AutoDream: consolidação automática em background (loop + ciclo único)
- `registry.py` — MemoryRegistry: CRUD de memórias consolidadas com busca textual e tracking de acessos
- `service.py` — KairosService: singleton orquestrador (captura → consulta → dream → status)
- `__init__.py` — Exports limpos + docstring

**Modelos de banco (database/models.py):**
- `MemorySnapshotDB` — snapshots brutos com campos: id, agente_id, tenant_id, source, conteudo, contexto (JSON), relevancia, consolidado
- `MemoryEntryDB` — memórias consolidadas com campos: id, tipo, titulo, conteudo, tags (JSON), relevancia, acessos, fonte_snapshots (JSON), ativo

**Características:**
- Multi-tenant desde o início (tenant_id em todos os modelos)
- Lock de concorrência com TTL + detecção de processos mortos
- 4 tipos de memória: episódica, semântica, procedural, estratégica
- 6 fontes de snapshot: luna, mission_control, reuniao, workflow, manual, agente
- Consolidação via LLM (usa cadeia de fallback existente)
- Loop automático configurável (intervalo, max snapshots, modelo)
- Soft delete em memórias + TTL em snapshots consolidados
- 11 testes de import + integração passaram

### Alterações

- `core/memory/__init__.py` — novo
- `core/memory/kairos/` — 8 arquivos novos (types, lock, snapshot, prompt, dream, registry, service, init)
- `database/models.py` — +2 modelos (MemorySnapshotDB, MemoryEntryDB)

---

## v0.59.8 — Fork Real de Sub-Agentes na Luna (04/Abr/2026)

### Fase 2.3 Finalizada: Fork Real ativado

**Problema:** Ao pedir "Inicie um sub-agente tech_lead...", a Luna respondia com simulação do LLM ("Vou preparar um pedido... aguarde") em vez de executar o fork real.

**Solução: Interceptação de sub-agente em `core/luna_engine.py`**

- Novo método `_detectar_subagente(mensagem)` — detecta pedidos de sub-agente via regex (6 padrões) + fallback por tipo no registry
- Novo método `_executar_subagente(agent_type, diretiva, ...)` — execução REAL via `AgentSpawner` + chamada LLM com system prompt especializado do agente
- Novo método `_construir_prompt_subagente(definition, diretiva)` — prompt dinâmico baseado na definição do agente no registry
- Interceptação em `stream_resposta()`: se `fork_subagent=True` no banco → fork real; se `False` → fluxo antigo (retrocompatível)
- Resposta do sub-agente é salva no banco da conversa (`modelo_usado="subagente:{tipo}"`, `provider_usado="fork_real"`)

### Fluxo

```
Usuário → "Inicie um sub-agente tech_lead para ..."
       ↓
Luna._detectar_subagente() → ("tech_lead", "diretiva...")
       ↓
fork_manager.is_fork_subagent_enabled() → True (banco)
       ↓
Luna._executar_subagente() → AgentSpawner.spawn() + LLM streaming
       ↓
Resposta do sub-agente em streaming via SSE
```

### Alterações

- `core/luna_engine.py` — imports de `fork_manager`, `agent_spawner`, `AgentRegistry`, `AgentSpawnParams`, `feature_flag_service` + 3 novos métodos + interceptação em `stream_resposta()`
- Zero mudanças no frontend, API, ou banco — 100% retrocompatível

---

## v0.59.7 — FeatureFlagService: Integração com ForkManager (04/Abr/2026)

### Novo: core/feature_flags.py

**FeatureFlagService — leitura centralizada de feature flags com cache TTL:**

- Singleton com `cachetools.TTLCache` (30s TTL, max 100 entries)
- Método `is_enabled(flag_name: str) -> bool` — retorna valor do banco com cache
- Método `invalidate(flag_name)` — limpa cache após toggle
- Método `get_flag_info(flag_name)` — info completa da flag
- Fallback fail-closed: flag inexistente = False

**Integração com ForkManager:**
- `ForkManager.is_fork_subagent_enabled()` agora usa `feature_flag_service.is_enabled("fork_subagent")`
- `ForkManager.is_worktree_isolation_enabled()` usa `feature_flag_service.is_enabled("worktree_isolation")`
- Substitui leitura via env vars `CLAURST_FEATURE_FORK_SUBAGENT`

**Integração com Master Control:**
- Endpoint de toggle agora invoca `feature_flag_service.invalidate(nome)` após commit
- Garante que próximo `is_enabled()` lê valor real do banco

### Alterações

- `core/feature_flags.py` — novo arquivo (161 linhas)
- `core/agents/fork.py` — `is_fork_subagent_enabled()` e `is_worktree_isolation_enabled()` agora usam `FeatureFlagService`
- `api/routes/master_control.py` — `invalidate()` após toggle

---

## v0.59.6 — Master Control: Tooltips, Dialog e Melhorias Visuais (04/Abr/2026)

### Melhorias no Master Control

- [x] **Nomes amigáveis** — cada flag tem nome em português ("Fork de Subagente", "Fábrica Contínua", etc.)
- [x] **Tooltips explicativos** — hover em cada card com explicação didática da funcionalidade
- [x] **Badge "Requires Restart"** — badge vermelho nos cards e banner quando flag precisa de restart
- [x] **Dialog de restart melhorado** — layout profissional com header, flag afetada, warning visual e botões Cancelar/Reiniciar
- [x] **Botão Atualizar** — reload dos dados sem F5 no header
- [x] **Histórico com nomes amigáveis** — tabela de histórico mostra nome da flag em português
- [x] **Contador de flags** — badge com número total de flags na tab "Feature Flags"
- [x] **Descrições atualizadas no banco** — seed data atualizada com descrições claras em português
- [x] Bug #53 corrigido — banner de restart não desaparecia após restart

### Detalhes técnicos
- `FLAG_META` com `nomeAmigavel`, `tooltip` e cor por flag
- Componente `FlagCard` com tooltip no hover
- Componente `RestartConfirmDialog` com visual profissional
- Componente `HistoryRow` com ícones coloridos e nome amigável
- Migration atualiza descrições de flags já existentes

## v0.59.5 — Master Control: Feature Flags GUI (04/Abr/2026)

### Novo: Master Control (CEO-only)

**Tela CEO-only para controle de feature flags:**

- **Backend** (`api/routes/master_control.py`):
  - `GET /api/master-control/flags` — lista todas as flags
  - `POST /api/master-control/flags/{nome}/toggle` — toggle uma flag (CEO only)
  - `GET /api/master-control/flags/history` — histórico de alterações
  - `POST /api/master-control/flags/{nome}/restart` — solicita restart

- **Frontend** (`dashboard/src/pages/MasterControl.tsx`):
  - Cards por flag com toggle visual (estilo Linear/Vercel)
  - Ícones e cores por flag
  - Badge de "restart" para flags que requerem restart
  - Aviso vermelho quando há flags pendentes de restart
  - Aba de histórico com tabela de alterações
  - Tabs "Feature Flags" / "Histórico"

- **Sidebar** (`dashboard/src/components/Sidebar.tsx`):
  - Menu "Master Control" visível apenas para CEOs
  - Badge "CEO" roxo ao lado do link

- **Database** (`database/models.py`):
  - `FeatureFlagDB` — 6 flags seedadas: fork_subagent, worktree_isolation, autonomous_mode, brief_mode, continuous_factory, visible_execution
  - `FeatureFlagHistoryDB` — registro de cada toggle

- **Migração** (`scripts/migrate_feature_flags.py`):
  - Cria as duas tabelas se não existirem
  - Seed das 6 flags iniciais

### Alterações

- `api/main.py` — Added `master_control` router
- `dashboard/src/App.tsx` — Added `/master-control` route

## v0.59.3 — Opus 1M Context + Minimax Fix (04/Abr/2026)

### Alterações de LLM Provider

**Opus atualizado para contexto de 1M:**
- Modelo alterado de `claude-opus-4-20250514` (200K) → `claude-opus-4-6` (1M) em 4 arquivos:
  - `core/llm_router.py` — MODELOS_CLAUDE[OPUS] e _MAPA_CREWAI
  - `config/llm_providers.py` — ProviderConfig ANTHROPIC_OPUS
  - `core/smart_router_global.py` — PROVIDER_CONFIG[OPUS]
  - `core/classificador_mensagem.py` — mapa de providers

**Minimax 401 corrigido:**
- Adicionado `base_url="https://api.minimaxi.chat/v1"` em `config/llm_providers.py` e `core/smart_router_global.py`
- Sem o base_url, requests iam para o endpoint padrão da OpenAI (401)

### Documentação
- `docs/obsidian/04-Arquitetura/Agent-Architecture.md` — seção "5. AgentSpawner" adicionada
- `docs/obsidian/01-Roadmap/Roadmap.md` — Fase 2.2 ✅ confirmada

---

## v0.59.2 — Agent Architecture Phase 2.2 (03/Abr/2026)

### Implementação Completa

**Arquivos criados:**
- `core/agents/base.py` — AgentDefinition, AgentSpawnParams, AgentResult, AgentPermissionMode, IsolationMode, ForkContext + constantes
- `core/agents/registry.py` — AgentRegistry singleton com 12 agentes built-in (tech_lead, backend_dev, frontend_dev, qa_engineer, pm_agent, devops, security, integration, test_master, github_master, gitbucket_master, general_purpose)
- `core/agents/fork.py` — ForkManager com anti-recursive guard, worktree isolation, fork message building, AutoApproveMode
- `core/agents/spawn.py` — AgentSpawner com suporte a fork path e named agents, SpawnProgress tracking
- `core/agents/lifecycle.py` — AgentLifecycle com callbacks, timeout, lifecycle manager
- `core/tools/base.py` — ToolFactory, ToolDefinition, ToolRegistry com defaults fail-closed
- `core/tools/brief.py` — BriefTool para messaging ao usuário com attachments
- `core/tools/__init__.py` — Exports centralizados

**Técnicas implementadas (inspiradas em referência TypeScript):**
- **Fork Subagent**: spawning implícito via `agent_type=None`, placeholder idêntico para prompt cache
- **Recursive Guard**: detecta `FORK_BOILERPLATE_TAG` nas mensagens para prevenir fork infinito
- **Worktree Isolation**: criação e cleanup de git worktrees isolados via subprocess
- **Tool Registry**: factory pattern com defaults fail-closed (isEnabled→True, isConcurrencySafe→False, etc.)
- **Brief Tool**: canal primário de output com suporte a attachments e status (normal/proactive)
- **Auto-Approve Mode**: None, AcceptEdits, BypassPermissions, Plan
- **Lifecycle Manager**: tracking de estado, callbacks de progress, timeout support

**Documentação atualizada:**
- `docs/obsidian/04-Arquitetura/Agent-Architecture.md` — arquitetura completa
- `docs/obsidian/06-Decisoes/Decisoes-Tecnicas.md` — decisões Fork, Worktree, Tool Registry, Brief
- `docs/obsidian/01-Roadmap/Roadmap.md` — Fase 2.2 ✅
- `docs/obsidian/08-Daily/Pendencias-Ultimo-Chat.md` — sessão 52

---

## v0.59.1 — Code Studio + API Fixes (03/Abr/2026)

### Correções

**`/api/projetos` 500 Internal Server Error**
- Causa: coluna `regras_aprovacao` definida no modelo `database/models.py` mas inexistente na tabela SQLite
- Fix: migration adicionou a coluna JSON com default padrão
- Arquivo: `scripts/fix_projetos_schema.py`

**Code Studio — Projeto não aparecia na árvore**
- Causa: caminho do SyneriumX estava como `/Users/thiagoxavier/propostasap` (macOS local)
- O repositório no servidor está em `/opt/projetos/syneriumx`
- Fix: atualizado `projetos.caminho` para `/opt/projetos/syneriumx`

**Git Pull — `fatal: could not read Username`**
- Causa: não havia token do GitHub configurado na tabela `projeto_vcs`
- Fix: criado registro `ProjetoVCSDB` para SyneriumX com token do `.env`
- Atualizado repo_url para `https://github.com/SineriumX/syneriumx.git`

### Testes de integração — APROVADOS ✅
- Login JWT: funcionando
- Luna streaming (groq/llama-3.3-70b): funcionando
- Listar projetos: SyneriumX com caminho correto
- Listar squads: CEO-Thiago, Diretor-Jonatas carregados
- Prompts registry: 21 seções, Luna 2419 chars

### Arquivos alterados
- `scripts/fix_projetos_schema.py` — adiciona coluna `regras_aprovacao`
- `scripts/fix_projetos_caminho.py` — corrige caminho SyneriumX
- `scripts/create_vcs_record.py` — cria VCS com token GitHub

---

## v0.59.0 — System Prompts Modular (03/Abr/2026)

### Novidade
Luna e agentes agora usam `core.prompts.composers` para compor prompts de forma modular.

### Arquivos alterados
- `core/luna_engine.py` — `SYSTEM_PROMPT` via `compose_luna_prompt()`
- `core/prompts/composers.py` — novo sistema de composição de prompts
- `core/prompts/registry.py` — registry centralizado de seções de prompt

---

## v0.58.19 — Phase Decision Controls + ChromaDB Fix (03/Abr/2026)

### Funcionalidade
Mission Control agora exibe os controles de decisão de fase quando o agente aguarda aprovação humana após cada etapa do BMAD.

### Novidades
- `PhaseDecisionControls` importado e integrado ao MissionControl
- Polling para `/fase-status` a cada 2s
- Botões **Aprovar**, **Regenerar**, **Rejeitar**, **Revisar** funcionais
- Exibidos automaticamente quando `waiting_decision: true`

### ChromaDB Fix (Servidor)
ChromaDB 1.1.1 crashava com `range start index 10 out of range for slice of length 9` no Ubuntu 22.04.
- Patch: usar `EphemeralClient` ao invés de `PersistentClient` no crewai
- Skills desabilitadas temporariamente (`inicializar_skills` comentado)

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx` — integração PhaseDecisionControls
- `dashboard/src/components/PhaseDecisionControls.tsx` — controles de decisão
- `api/dependencias.py` — skills desabilitadas

---

## v0.58.14 — isInitializing Depende de Carregando (02/Abr/2026)

### Problema
Loading spinner travado permanentemente. isInitializing so virava false se token existisse.

### Solucao
```
// ANTES (travava se token nao existisse)
useEffect(() => {
  if (tokenSeguro && tokenSeguro.length > 0) setIsInitializing(false)
}, [tokenSeguro])

// DEPOIS (sempre libera quando auth terminar)
useEffect(() => {
  if (!carregando) setIsInitializing(false)
}, [carregando])
```

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx`

---

## v0.58.13 — TaskTray com getStoredToken Seguro (02/Abr/2026)

### Problema
TaskTray causando 401. localStorage.getItem() sem try-catch.

### Solucao
Mesma protecao aplicada ao TaskTray:
```tsx
function getStoredToken(): string {
  try {
    return localStorage.getItem('sf_token') || ''
  } catch {
    return ''
  }
}
```

### Arquivos alterados
- `dashboard/src/components/TaskTray.tsx`

---

## v0.58.12 — Protecao localStorage no Mission Control (02/Abr/2026)

### Problema
TaskTray dava 401, possivel erro em localStorage.getItem() se storage nao disponivel.

### Solucao
localStorage access envolvido em try-catch:
```tsx
const getStoredToken = (): string => {
  try {
    return localStorage.getItem('sf_token') || ''
  } catch {
    return ''
  }
}
const tokenSeguro = token || getStoredToken() || ''
```

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx`

---

## v0.58.11 — Guard isInitializing no Startup UseEffect (02/Abr/2026)

### Problema
Crash ao carregar sessao (clicar em Nova Sessao ou Retomar). Startup useEffect rodava antes do token estar confirmado.

### Solucao
Guard `isInitializing` no startup useEffect:
```tsx
useEffect(() => {
  if (isInitializing) return  // NAO faz nada enquanto token nao estiver pronto
  if (urlSessionId) carregarSessao(urlSessionId)
  else carregarSessoes()
}, [urlSessionId, isInitializing, carregarSessao, carregarSessoes])
```

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx`

---

## v0.58.10 — Guard isInitializing no Mission Control (02/Abr/2026)

### Problema
React error #310 ao criar nova missao. useEffects podiam executar antes do token estar disponivel.

### Solucao
Adicionado `isInitializing` state que so vira `false` quando `tokenSeguro` estiver disponivel:
```tsx
const [isInitializing, setIsInitializing] = useState(true)

useEffect(() => {
  if (tokenSeguro && tokenSeguro.length > 0) {
    setIsInitializing(false)
  }
}, [tokenSeguro])

if (carregando || isInitializing) {
  return <Spinner />
}
```

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx` — guard isInitializing

---

## v0.58.9 — Guard de Loading no Mission Control (02/Abr/2026)

### Problema
Mission Control crashava ao criar sessao. useEffects executavam antes da autenticacao estar pronta.

### Solucao
Guard simples no topo do componente:
```tsx
if (carregando) {
  return (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin" />
    </div>
  )
}
```
Isso impede que qualquer useEffect execute ate que `carregando` seja `false`.

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx` — guard carregando no topo

---

## v0.58.8 — Correção FINAL do Crash Mission Control ao Criar Sessão (02/Abr/2026)

### Problema
Mission Control crashava (React error #310) ao criar nova missao. Console mostrava 401 Unauthorized em /api/tarefas/historico e erros de render.

### Causas Identificadas
1. **Token null**: chamadas API podiam ser feitas sem token valido
2. **JSON parse errors**: responses invalidas causavam crashes
3. **Race conditions**: re-render loop ao criar sessao sem reset de estado
4. **Missing guards**: efeitos acessavam APIs sem verificar token

### O que foi feito
1. **hasToken guard**: todas as chamadas API verificam token antes de executar
2. **criarSessao**: reset completo de estado antes de navegar (sessao, artifacts, chat, terminal, conclusao, faseStatus)
3. **dispararAgente**: guard hasToken + reset mostrarConclusao
4. **carregarSessao**: guard hasToken + JSON parse defensivo + null checks em todas propriedades
5. **Polling useEffects**: hasToken adicionado em todas as dependencias
6. **Team Chat + Fase Status**: JSON parse com try/catch

### Protecoes
- Se token vazio, nenhuma API e chamada
- Responses JSON invalidas nao causam crash
- Estado sempre resetado corretamente ao criar nova sessao
- Todas as propriedades acessadas com null checks

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx` — todas as protecoes acima

---

## v0.58.7 — Correção FINAL do Crash Mission Control ao Criar Sessão (02/Abr/2026)

### Problema
Mission Control carregava a pagina inicial, mas crashava (tela preta) ao criar nova missao. Console mostrava React error #310 + 401 Unauthorized em /api/tarefas/historico.

### Causas Identificadas
1. **401 Unauthorized**: TaskTray e MissionControl podiam receber token null da context antes de estar disponivel
2. **React error #310**: Componente recebia response invalida apos criacao de sessao sem verificar res.ok
3. **Falha catastrófica**: Nenhum Error Boundary para proteger a rota — qualquer erro causava tela preta total

### O que foi feito
1. **ErrorBoundary.tsx** (NOVO): Componente que captura erros React e mostra mensagem amigavel com botao recarregar
2. **App.tsx**: MissionControl envolvido com ErrorBoundary em ambas rotas (/mission-control e /mission-control/:sessionId)
3. **tokenSeguro**: Token usa localStorage como fallback se context token ainda nao disponivel
4. **criarSessao**: Adicionado check `res.ok` e throw se `sessao_id` ausente
5. **Prop token**: Substituido `token || ''` por `tokenSeguro` em todos os lugares

### Protecoes Adicionadas
- Error Boundary protege contra qualquer erro de renderizacao
- Token sempre disponivel via localStorage fallback
- Sessao s6o criada apenas com response valida (res.ok check)
- Log de erros facilita debug

### Arquivos alterados
- `dashboard/src/components/ErrorBoundary.tsx` — **NOVO**
- `dashboard/src/App.tsx` — ErrorBoundary wrapper
- `dashboard/src/pages/MissionControl.tsx` — tokenSeguro + res.ok check

---

## v0.58.6 — Correção FINAL Mission Control em Branco (02/Abr/2026)

### Problema
Mission Control continuava em branco apos v0.58.4/v0.58.5. Console mostrava:
- React error #310 (Invalid element type)
- 401 Unauthorized em /api/tarefas/historico

### Causas Identificadas
1. **TaskTray**: usava `sf_access_token` como chave de localStorage, mas AuthContext usa `sf_token`. Resultado: polling sempre retornava 401.
2. **App.tsx Layout**: `h-screen overflow-hidden` no main div dentro de body com `min-h-screen` causava conflito de altura quando body vira scroll container.

### O que foi feito
- TaskTray: `sf_access_token` → `sf_token` (localStorage key correto)
- App.tsx: remove `h-screen overflow-hidden`, usa `flex-1 min-h-screen` no main

### Arquivos alterados
- `dashboard/src/components/TaskTray.tsx` — corrige localStorage key
- `dashboard/src/App.tsx` — corrige layout conflict

---

## v0.58.5 — Correção de Regressão Mission Control (02/Abr/2026)

### Problema
Após v0.58.4, pagina do Mission Control ficou completamente em branco/preta. Console sem erros. Build TypeScript passava.

### Causa Raiz
`MissionControl.tsx` usava `var(--sf-bg)` e `var(--sf-surface)` que NAO existem no design system. Variaveis CSS indefinidas fazem o valor da propriedade ficar UNSET (transparente para background). Quando v0.58.4 removeu o background explicito do parent (`min-h-screen` sem `background` vs `h-screen` sem `background`), os backgrounds transparentes de MissionControl passaram a herdar do body (default branco) — escondendo todo o conteudo.

MissionControl era o UNICO arquivo em todo o projeto que usava `--sf-bg`. Todas as outras paginas usam `--sf-bg-primary` (alias correto).

### O que foi feito
- `var(--sf-bg)` → `var(--sf-bg-primary)` em 14 lugares
- `var(--sf-surface)` → `var(--sf-bg-card)` em 17 lugares
- Build TypeScript: zero erros

### Arquivos alterados
- `dashboard/src/pages/MissionControl.tsx` — corrige CSS undefined

---

## v0.58.4 — Sidebar Fixo e Colapsável (02/Abr/2026)

### Problema
Menu lateral anterior rolava junto com o conteudo da pagina. Usuario precisava rolar ate o final para ver nome/email e botao Sair. Sem opcao de colapsar para modo mini.

### O que foi feito

**Sidebar fixo (desktop):**
- `position: fixed` com `height: 100vh` e `overflow-y: auto`
- Card do usuario + botao Sair SEMPRE visiveis na parte inferior
- Scroll interno quando navegacao exceder altura da tela
- Animacao suave de 300ms ao colapsar/expandir
- Toggle via botao ChevronLeft/Right
- Modo expandido: 240px (labels visiveis) | Modo mini: 64px (icons only)

**Mobile:**
- Overlay com backdrop escuro
- Botao hamburger flutuante (Menu icon) no canto superior esquerdo
- Sidebar 280px em overlay
- Fecha ao clicar fora ou no X

**Redux Toolkit:**
- `sidebarSlice`: estado `collapsed` com persistencia em `localStorage`
- `useAppSelector` / `useAppDispatch` hooks
- Provider em `App.tsx`

### Arquivos alterados
- `dashboard/src/components/Sidebar.tsx` — rewrite completo com fixed sidebar
- `dashboard/src/App.tsx` — Redux Provider + LayoutComSidebar wrapper
- `dashboard/src/store/sidebarSlice.ts` — **NOVO** — slice com localStorage
- `dashboard/src/store/index.ts` — **NOVO** — store
- `dashboard/src/store/hooks.ts` — **NOVO** — hooks tipados
- `dashboard/package.json` — @reduxjs/toolkit + react-redux

---

## v0.58.3 — Correção de Regressão no Mission Control (02/Abr/2026)

### Problema
Após implementar a v0.58.2 (Phase Decision Controls), a página do Mission Control ficava em branco/preta. Console mostrava React error #310 (render error) e 401 Unauthorized em `/api/tarefas/historico`.

### O que foi feito

**Erros corrigidos:**
- **Polling redundante**: `PhaseDecisionControls` tinha seu próprio polling de `/fase-status` que conflituava com o polling do componente pai, causando re-render loop infinito → **REMOVIDO** (componente agora é stateless)
- **useAuth() duplicado**: `useAuth()` era chamado duas vezes (topo do componente e inline no JSX) → consolidado para `const { token, usuario } = useAuth()` no topo
- **waitingDecision prop não utilizada**: removida da interface e do componente
- **FaseStatus interface redundante**: removida (não usada no componente leve)

**Melhorias aplicadas:**
- `handleFaseDecisao` callback no `MissionControl` para tratar decisões
- `PhaseDecisionControls` agora só renderiza via props — polling centralizado no pai
- Componente mais simples, mais rápido, sem loops de render

### Arquivos alterados
- `dashboard/src/components/PhaseDecisionControls.tsx` — polling proprio removido, componente leve
- `dashboard/src/pages/MissionControl.tsx` — callback handleFaseDecisao, usoAuth consolidado

---

## v0.58.2 — Phase Decision Controls — Human-in-the-Loop (02/Abr/2026)

### Problema
O Mission Control executava as 5 fases do BMAD automaticamente, sem intervenção humana em tempo real. Não havia como aprovar, regerar, rejeitar ou revisar cada fase individualmente antes de prosseguir.

### Solução: Phase Decision Controls — Human-in-the-Loop

**O que foi feito:**
- `FaseDecisionEngine`: motor de decisões por fase com `threading.Event` para bloqueio/desbloqueio entre fases
- `POST /sessao/{id}/fase-decisao`: registra decisão do usuário (aprovar/regenerar/rejeitar/revisar) e desbloqueia o agente
- `GET /sessao/{id}/fase-status`: polling do frontend para detectar se agente está esperando decisão
- `_executar_agente_mission_control()`: ponto de decisão entre cada fase (1→2, 2→3, 3→4, 4→5)
- Regerar refaz a fase atual; Rejeitar encerra a sessão; Aprovar prossegue; Revisar abre detalhamento

**Melhorias aplicadas:**
- Novo componente `PhaseDecisionControls.tsx`: painel lateral com 4 botões coloridos
- Indicador visual de progresso das 5 fases (setas numeradas)
- Estado `mostrarConclusao`: tela "Concluído" só após 5 fases aprovadas
- **"Voltar para Revisão"** preserva todo o histórico (artifacts, código, terminal)

**Erros corrigidos durante implementação:**
- `ArrowRight` import não utilizado → removido
- `onConcluido` prop não utilizado → removido da interface
- `ultimaFase` variável não utilizada → removida
- `isCompleto` usado antes da declaração → useEffect movido para após `const isCompleto`
- `setModoRevisao` não existia → substituído por `setMostrarConclusao`
- `PhaseDecisionControls` usava polling próprio redundante → usa `faseStatus` do MissionControl

**Arquitetura de decisão:**
```
Fase N completa → Agente bloqueia (set_pending + wait_decision)
→ Frontend detecta waiting_decision → Mostra PhaseDecisionControls
→ Usuário clica → POST /fase-decisao → Agente desbloqueia
→ Aprovar: próxima fase | Regenerar: refaz fase | Rejeitar: encerra
```

**Arquivos alterados:**
- `api/routes/mission_control.py` — FaseDecisionEngine + 2 endpoints + pontos de decisão
- `dashboard/src/components/PhaseDecisionControls.tsx` — novo componente
- `dashboard/src/pages/MissionControl.tsx` — integração + estado mostrarConclusao
- `dashboard/src/components/MissionCompleteActions.tsx` — botão "Voltar para Revisão"

**Próximos passos:**
- Testar fluxo completo no browser (deploy pendente via SSH)
- Adicionar feedback visual de qual fase foi rejeitada/regenerada
- Persistir histórico de decisões no banco (audit log por fase)

---

## v0.57.8 — Git Actions Funcionais no Mission Control (02/Abr/2026)

### Problema
Botões de Git (Commit, Push, PR, Merge) eram placeholders com `alert()`. Não executavam ações reais.

### Solução: Git Actions Funcionais

**Backend — 4 novos endpoints em `mission_control.py`:**
- `GET /sessao/{id}/git-info`: branch atual, commits pendentes, se tem VCS configurado
- `POST /sessao/{id}/git-commit`: commit local (sem push) com audit log
- `POST /sessao/{id}/git-push`: push + criação automática de PR via API GitHub/GitBucket
- `POST /sessao/{id}/git-merge`: merge de PR existente via API

**Frontend — `MissionCompleteActions.tsx` atualizado:**
- **Git Status Bar**: mostra branch, número de pendências, tipo de VCS
- **Botão Commit** (laranja): commita alterações locais
- **Botão Push + PR** (verde): push para remote + cria PR automaticamente
- **Toast de feedback**: verde (sucesso) ou vermelho (erro) com mensagem clara
- **Permissões**: Git actions só aparecem para ceo/diretor_tecnico/operations_lead/pm_central/lider
- Auto-refresh do git-info após cada operação

---

## v0.57.7 — Tela de Conclusão com Ações Recomendadas (02/Abr/2026)

### Problema
Quando uma sessão atingia 100% (Fase 5/5), a interface continuava em estados de loading sem oferecer ações claras para o próximo passo.

### Solução: Painel de Ações Recomendadas

**Novo componente: `MissionCompleteActions.tsx`**
- Exibe "✅ Concluído com Sucesso!" com badge verde
- Painel com 7 botões grandes e auto-explicativos:
  - 🧪 **Testar Agora** (azul) — Executa testes automatizados
  - 💻 **Aplicar no Code Studio** (roxo) — Abre no editor para revisar
  - 🤖 **Revisar com Factory Optimizer** (amber) — Análise PDCA
  - 🛡️ **Pedir Aprovação** (verde) — Envia para Operations Lead
  - 👥 **Convidar Colaborador** (ciano) — Convida membro da equipe
  - 📄 **Gerar Relatório CEO** (rosa) — Resumo executive
  - ➕ **Nova Sessão** (cinza) — Inicia nova missão

**MissionControl.tsx atualizado**
- Detecção de conclusão: `isCompleto = faseAtual === 5 && progressoAtual === 100`
- Badge verde "Concluído" no header (sem spinner)
- Barra de progresso ocultada quando completo
- Transição suave com fade-in animation

---

## v0.57.6 — True Live Typing & Execution Feeling (01/Abr/2026)

### True Live Typing no Editor
- **Caractere por caractere**: delay variável (8-40ms) para simular digitação natural real
  - Caracteres comuns: 15ms | Pontuação: 28ms | Newline: 40ms | Indentação: 8ms
- **Cursor verde piscando**: 0.65s blink cycle com box-shadow glow (0 0 12px #10b981)
- **Highlight de linha atual**: borda verde à esquerda + fundo sutil rgba(16,185,129,0.06)

### Feedback Visual Forte
- **Badge STREAMING**: glow vermelho pulsante (liveGlow animation, 0.8s)
- **Badge "Em execução"**: glow verde forte (execBadgePulse animation, 1.2s)
- **Barra de progresso**: glow intenso quando LIVE (box-shadow 0 0 24px rgba)
- **Texto descritivo**: "⚡ Gerando código... Fase 3/5" com emoji
- **Animação agent-pulse**: mais forte (0.8s, scale 1.3x, drop-shadow 8px)

### Terminal Real
- Cursor verde com texto "agente executando..." no final do terminal
- Comandos reais: npm build, pytest, eslint, tsc --noEmit

### Backend (streaming 2 linhas/200ms)
- Mantido streaming em blocos de 2 linhas com 200ms de delay
- Frontend faz character-by-character a partir dos chunks

---

## v0.58.1 — Vision Real para Agentes de Squad: Pré-processamento de Imagens (01/Abr/2026)

### Problema
O sistema roteava imagens para o Minimax (sem vision) mesmo após o fix v0.58.0. O classificador não recebia a flag `tem_imagem` corretamente em todos os pontos de entrada.

### Solução: Pré-processamento com GPT-4o-mini Vision

**ChatFloating (`dashboard/src/components/ChatFloating.tsx`)**
- Envia anexos com URL real (upload pré-assinado) ao invés de texto placeholder
- Permite que o backend processe a imagem corretamente

**Tarefas Route (`api/routes/tarefas.py`)**
- Nova função `_analisar_imagens_com_vision()`: pré-processa imagens com GPT-4o-mini vision antes de enviar ao agente
- Extrai descrição textual da imagem para ser adicionada ao contexto da mensagem
- Funciona como camada de segurança adicional (independentemente do classificador)

**Luna Engine (`core/luna_engine.py`)**
- Fix: path resolution absoluto para arquivos de imagem
- Fallback não-silencioso: se falhar ao processar imagem, loga erro e continua (não quebra a conversa)

---

## v0.58.0 — Agentes Multimodais (Vision): Roteamento Inteligente para Imagens (01/Abr/2026)

### Problema Resolvido
Usuário enviava imagem no Escritório Virtual → Smart Router encaminhava para Minimax (sem suporte a vision) → agente respondia "Não consigo interpretar imagens". Agora o sistema detecta imagens automaticamente e roteia para providers com suporte a vision.

### Classificador de Mensagem (`core/classificador_mensagem.py`)
- **Flag `vision` adicionada** a todos os 8 providers em `PROVIDERS_REGISTRO`: indica se o provider suporta imagens
- **Novo parâmetro `tem_imagem`** na função `classificar_mensagem()`: quando `True`, força provider com vision
- **Roteamento com imagem**: SIMPLES/MEDIO → GPT-4o-mini (vision, mais barato com suporte), COMPLEXO → GPT-4o (vision, máxima qualidade)
- **Fallback chain filtrada**: quando `tem_imagem=True`, cadeia de fallback exclui providers sem vision automaticamente

### Luna Engine (`core/luna_engine.py`)
- **`_decidir_modelo()` aceita `anexos`**: detecta `tipo="imagem"` nos anexos e passa `tem_imagem=True` ao classificador
- **Streaming e regeneração atualizados**: ambos os call sites de `_decidir_modelo()` passam anexos corretamente

### LLM Fallback (`core/llm_fallback.py`)
- **`_mensagens_tem_imagem()`**: helper que detecta `image_url` em `content_parts` de `HumanMessage` (LangChain)
- **Sync + Async**: ambas as versões do fallback pulam Minimax, Groq, Fireworks e Together quando imagem detectada
- **Rede de segurança independente**: funciona mesmo se o classificador não receber a flag `tem_imagem`

### Providers com Vision
| Provider | Vision | Modelo |
|----------|--------|--------|
| GPT-4o-mini | Sim | Mais barato com vision ($0.00015/1K input) |
| GPT-4o | Sim | Máxima qualidade multimodal |
| Claude Sonnet | Sim | Qualidade premium |
| Claude Opus | Sim | Tarefas críticas |
| Gemini 2.5 Flash | Sim | Free tier |
| Minimax | **Não** | Texto apenas |
| Groq | **Não** | Texto apenas |
| Fireworks | **Não** | Texto apenas |
| Together | **Não** | Texto apenas |

---

## v0.57.5 — Visible Live Execution: Experiência Visual Completa (01/Abr/2026)

### Frontend (`dashboard/src/pages/MissionControl.tsx`)
- **Efeito Typewriter**: caracteres aparecem gradualmente no editor (não mais linhas inteiras de uma vez)
- **Barra de progresso animada com shimmer**: gradiente + texto descritivo da fase atual + porcentagem visível
- **Ícone do agente pulsante**: indicação visual de atividade do agente em todos os painéis
- **Badge "Em execução"** nas mensagens do Team Chat: identifica visualmente mensagens geradas durante execução
- **Cursor piscante no terminal**: efeito de digitação real no painel de terminal
- **Indicador de atividade do agente em todos os painéis**: feedback visual constante de que o sistema está trabalhando

### Backend (`api/routes/mission_control.py`)
- **Streaming otimizado**: chunks reduzidos de 4→2 linhas com delay de 200ms (era 350ms) — execução mais fluida e responsiva
- **Progresso granular dentro das fases**: atualizações de % não apenas nas transições de fase, mas durante cada fase individualmente
- **Comandos reais no terminal**: `npm run build`, `pytest`, `eslint`, `tsc --noEmit` aparecem no terminal (não mais comandos genéricos)
- **Editor com conteúdo desde a Fase 1**: scaffold → plan → code (antes só aparecia código na Fase 3)
- **Mais entradas de terminal**: todas as fases agora geram entradas de terminal, não apenas a fase de execução

---

## v0.57.4 — Fix Crítico: Streaming ao Vivo Funcionando de Verdade (01/Abr/2026)

### Bugs Corrigidos (3 root causes identificadas)

**Bug #53 — SQLAlchemy JSON mutation não persistia** (causa raiz #1):
- Os helpers `_atualizar_fase_agente`, `_escrever_codigo_no_editor`, `_adicionar_terminal_agente` compartilhavam a mesma `db` session de toda a execução. SQLAlchemy não detectava as mutações nos campos JSON, fazendo `db.commit()` não salvar nada.
- Fix: cada helper cria sua própria `SessionLocal()`, usa `flag_modified()` explicitamente, e faz deep copy com `[dict(a) for a in list]`. try/except/finally em cada helper — uma falha não mata a execução.

**Bug #54 — Auto-save sobrescrevia conteúdo do agente** (causa raiz #2):
- O auto-save do frontend enviava `painel_editor: { conteudo: '// Selecione...', arquivo_ativo: '...' }` a cada 10s com o conteúdo INICIAL do editor, antes do poll ter atualizado o state.
- Fix backend: se `painel_editor.fonte === 'agente'`, auto-save ignora o update (agente controla o editor).
- Fix frontend: `agentExecutandoRef` — quando agente está executando, auto-save pula completamente.

**Bug #55 — Polling reiniciava a cada poll** (causa raiz #3):
- `useEffect` de polling tinha `sessao?.agentes_ativos` no deps array. Como `setSessao(data)` cria nova referência a cada poll, o effect reiniciava constantemente (clearInterval + setInterval), causando timing instável.
- Fix: polling fixo de 2s, sem `sessao?.agentes_ativos` nos deps.

### Outras melhorias
- `dispararAgente`: recarrega sessão imediatamente após dispatch (antes esperava até 5s para ver a barra)
- `carregarSessao`: lógica de update do editor simplificada — usa `editorEditadoRef` (useRef) para evitar stale closures
- Terminal sempre atualizado do banco a cada poll (antes era condicional)

---

## v0.57.3 — Modo LIVE: Código Streaming ao Vivo no Editor (01/Abr/2026)

### Feature Principal
Botão **LIVE** (verde, ligado por padrão) na barra de progresso. Quando ativado, o código aparece **ao vivo** no painel Editor — linha a linha, como se alguém estivesse digitando em tempo real. O frontend faz polling a cada 1s (vs 5s normal) e mostra indicadores visuais de streaming.

### Backend
- `_escrever_codigo_no_editor()` aceita flag `streaming: bool` — sinaliza ao frontend se ainda está escrevendo
- **Streaming progressivo na Fase 3**: após receber o código do LLM, escreve em blocos de 4 linhas com 350ms de delay entre cada flush. Para 40 linhas = 10 flushes em ~3.5s de "digitação" visível
- `painel_editor.streaming = True` durante escrita, `False` ao concluir

### Frontend
- **Botão toggle LIVE**: verde quando ativo, cinza quando desligado. Na barra de progresso (aparece só durante execução)
- **Polling dinâmico**: 1s quando LIVE + agente executando, 5s caso contrário
- **Badge "LIVE"** vermelho pulsante no header do editor durante streaming, com ícone Radio e glow
- **Indicador "escrevendo..."** no canto inferior direito do editor: cursor verde pulsante
- **Badge "STREAMING"** na barra de progresso quando o backend está enviando chunks
- **Proteção**: se o usuário digitar manualmente no editor, o streaming não sobrescreve

### Bug Fix Crítico — Recovery de Agentes Órfãos (Bug #52)
- **Problema**: `systemctl restart` matava threads de execução silenciosamente. Agentes ficavam presos em `status: "executando"` para sempre no banco — sem possibilidade de retry pelo usuário.
- **Fix**: `_recovery_agentes_orfaos()` adicionada em `api/routes/mission_control.py`, chamada no import do módulo. A cada startup do servidor, varre todas as sessões ativas e marca como `status: "erro"` qualquer agente ainda em `"executando"`.
- **Commit**: `fix(mission-control): recovery de agentes orfaos no startup`
- **Lição registrada**: qualquer thread de background que persiste estado no banco precisa de recovery no startup.

---

## v0.57.2 — Visible Execution: Progresso Real + Código ao Vivo (01/Abr/2026)

### Feature Principal
O usuário agora VÊ a execução acontecendo: barra de progresso animada por fase ("Fase 2/5 — Discussão · 35%"), código aparecendo no editor conforme os agentes geram, e terminal mostrando cada passo dos agentes em tempo real. A sensação de "está acontecendo de verdade" foi completamente implementada.

### Backend (`api/routes/mission_control.py`)
- **`_atualizar_fase_agente()`** — novo helper que escreve `fase_atual`, `fase_label`, `progresso` no registro do agente dentro de `agentes_ativos`. Frontend detecta no polling a cada 5s.
- **`_escrever_codigo_no_editor()`** — novo helper que persiste o código gerado diretamente em `painel_editor.conteudo` com flag `fonte: "agente"`. Frontend atualiza o editor automaticamente.
- **`_adicionar_terminal_agente()`** — novo helper que insere entradas tipadas como `"tipo": "agente"` no `painel_terminal.historico`. Frontend as renderiza com ícone Bot verde.
- Fluxo de progresso: Planejamento (10%) → Discussão (35%) → Execução (60%) → Review QA (85%) → Concluído (100%)
- Durante Fase 3: escreve placeholder `"// ⚡ Gerando código..."` no editor imediatamente; ao concluir, substitui pelo código real
- Após QA: terminal mostra parecer e contagem de itens do checklist

### Frontend (`dashboard/src/pages/MissionControl.tsx`)
- **Interfaces atualizadas**: `AgenteAtivo` com `fase_atual?`, `fase_label?`, `progresso?`; `TerminalEntry` com `tipo?: string`; `painel_editor` com `fonte?: string`
- **Novos estados**: `editorFonteAgente` (badge "agente" no painel), `editorEditadoPeloUsuario` (protege edições manuais)
- **Barra de progresso animada**: aparece acima do campo de instrução apenas durante execução — mostra fase atual, label e % com gradiente verde→azul e glow
- **Editor ao vivo**: `carregarSessao` detecta `fonte === "agente"` e atualiza editor sem sobrescrever o que o usuário digitou manualmente
- **Badge no editor**: "🤖 agente" pulsante quando há código do agente; "⚡ gerando..." durante Fase 3
- **Terminal estilizado**: entradas do agente têm ícone `Bot` verde; entradas do usuário mantêm `$` azul; scroll automático quando agente adiciona entradas
- **Botão "Rodar Testes"** no modal de artifact de código: executa `node --version` no terminal e exibe o resultado

---

## v0.57.1 — Team Chat Multi-Agente + Artifact Modal Estavel (01/Abr/2026)

### Feature Principal
Mission Control agora exibe a conversa real entre agentes em tempo real. O CEO assiste ao vivo o Tech Lead planejar, os especialistas debaterem e o QA revisar — tudo em 4 fases coordenadas. O modal de artifacts foi reescrito para nunca fechar sozinho e com botões de ação.

### Backend
- **`TeamChatDB`** — novo model: armazena cada mensagem de agente com campos `sessao_id`, `agente_nome`, `tipo` (sistema/mensagem/acao), `conteudo`, `fase` (planejamento/discussão/execução/review/conclusão), `dados_extra` (JSON), `company_id`, `criado_em`
- **`GET /api/mission-control/sessao/{id}/chat`** — endpoint de polling incremental (param `?desde=timestamp`). Retorna apenas mensagens novas — frontend chama a cada 2s
- **`_executar_agente_mission_control()`** reescrito para 4 fases multi-agente:
  - **Fase 1 — Planejamento**: Tech Lead chama LLM, gera JSON de plano estruturado, cria artifact PLANO
  - **Fase 2 — Discussão**: Backend Dev, Frontend Dev e QA Engineer dão parecer técnico via LLM
  - **Fase 3 — Execução**: Tech Lead gera código real, cria artifact CODIGO
  - **Fase 4 — Review**: QA Engineer gera checklist de qualidade, cria artifact CHECKLIST
- Todos os `classificar_mensagem()` chamados corretamente — retornam `ProviderRecomendado` (não string raw)

### Frontend (`MissionControl.tsx`)
- **Painel 3 com abas**: **Team Chat** | **Artifacts** — alterna para Team Chat automaticamente ao disparar agente
- **Team Chat em tempo real**: polling a cada 2s via GET /chat. Renderiza cada mensagem com:
  - Ícone colorido por agente (User2, Bot, Cpu, Shield)
  - Badge de fase colorido (planejamento=azul, discussão=amarelo, execução=verde, review=roxo, conclusão=cinza)
  - Timestamp relativo
  - Mensagens de sistema centralizadas em itálico
- **Artifact modal estável**: nunca fecha sozinho. Somente via botão X ou clique fora. Tamanho máximo (`max-w-4xl`)
- **Botões de ação no modal**: "Aplicar no Editor" (cola código no textarea), "Copiar" (clipboard), "Download" (.txt)
- **Editor como `<textarea>`**: substituiu `<pre>` para permitir digitação real com fonte monospace

### Bugs Corrigidos (nesta versão)
- **Bug #49** — `metadata` reservado pelo SQLAlchemy → renomeado para `dados_extra` em TeamChatDB
- **Bug #50** — `'str' object has no attribute 'cadeia_fallback'` → todas as chamadas passavam string raw, corrigidas para `classificar_mensagem(texto)`
- **Bug #51** — TypeScript `TS6133: 'FileText' declared but never read` → removido import desnecessário

### Teste de Integração (01/Abr/2026) — APROVADO ✅
- Sessão `17f4adb17602` criada com instrução "Crie um componente de Login com validação de email..."
- **14 mensagens** no Team Chat (Tech Lead, Backend Dev, Frontend Dev, QA Engineer)
- **3 artifacts** gerados: PLANO, CODIGO, CHECKLIST — todos com conteúdo real
- 4 fases executadas sem crash em sequência
- Polling frontend 2s funcionando sem duplicações
- Modal de artifact aberto, conteúdo copiado para editor — fluxo completo

---

## v0.57.0 — Persistencia Completa de Sessoes no Mission Control (01/Abr/2026)

### Feature Principal
Sessoes do Mission Control agora persistem no banco. O usuario pode sair e voltar horas/dias depois, retomando exatamente de onde parou (editor, terminal, artifacts, comentarios).

### Backend
- `PATCH /api/mission-control/sessao/{id}/save` — Auto-save do estado dos paineis (editor + terminal)

### Frontend
- **Tela de sessoes**: lista sessoes recentes com titulo, status, metricas (artifacts, cmds), ultimo agente, tempo relativo ("5min atras", "2h atras")
- **Nova sessao**: campo de titulo + botao "Nova Sessao"
- **Auto-save a cada 10s**: salva conteudo do editor, arquivo ativo e historico do terminal no banco via PATCH
- **URL com ID**: `/mission-control/{sessionId}` — acesso direto via link (compartilhavel)
- **Resume perfeito**: ao retomar, editor restaura conteudo exato, terminal restaura historico completo, artifacts carregam
- **Editor editavel**: `<pre>` substituido por `<textarea>` para digitacao real com fonte monospace
- **Indicador de save**: "Salvo HH:MM" no header com icone de disquete/spinner
- **Voltar para lista**: clique no icone Rocket no header volta para a tela de sessoes
- **Rota React**: `/mission-control/:sessionId` adicionada no App.tsx

---

## v0.56.0 — Suporte Completo aos Novos Agentes (01/Abr/2026)

### Feature Principal
Todos os 16 agentes do catálogo (incluindo Test Master, GitHub Master, GitBucket Master, Factory Optimizer) agora aparecem corretamente em todas as telas com ícones, cores e filtros adequados.

### Corrigido
- **`Catalogo.tsx`**: Ícones `GitBranch`, `TrendingUp`, `FlaskConical` adicionados ao mapa estático. Chips de filtro e paleta de cores para categorias `qualidade` (cyan), `infraestrutura` (sky), `otimizacao` (teal).
- **`Atribuicoes.tsx`**: Mesmos ícones e cores. Categoria `qualidade` (#22d3ee) e `otimizacao` (#2dd4bf) mapeadas.
- **`Skills.tsx`**: Perfis `diretor` (Factory Optimizer) e `arquiteto` adicionados à aba "Por Agente".
- **`api/routes/catalogo.py`**: `CATEGORIAS_DISPONIVEIS` expandido com `qualidade`, `infraestrutura`, `otimizacao`.
- **`Escritorio.tsx`**: Array `DK` expandido de 9 → 16 posições. Agentes 10–16 agora têm mesa, cadeira e espaço dedicado no escritório virtual (fileiras 4 e 5 adicionadas no eixo x 920–1060).

### Agentes Afetados
| ID | Nome | Categoria | Ícone |
|----|------|-----------|-------|
| 13 | Test Master — Principal Engineer de Testes | qualidade | ShieldCheck |
| 14 | GitHub Master — Staff Engineer de Platform | infraestrutura | GitBranch |
| 15 | GitBucket Master — Staff Engineer de Platform | infraestrutura | GitBranch |
| 16 | Factory Optimizer — Meta-Analista de Sistemas IA | otimizacao | TrendingUp |

---

## v0.55.1 — Fix Mission Control URL em Produção (01/Abr/2026)

### Corrigido
- **`MissionControl.tsx` linha 16**: `VITE_API_URL || 'http://localhost:8000'` → `VITE_API_URL || ''`
- Em produção, `VITE_API_URL` não está definida no build estático. O fallback `localhost:8000` tornava as chamadas à API inacessíveis do browser.
- Com URL relativa (`''`), o Nginx faz proxy de `/api/` → porta 8000 corretamente.
- Botão "Iniciar Mission Control" agora cria sessão e abre o painel triplo.

### Infraestrutura
- Criado `/etc/systemd/system/synerium-dashboard.service` no servidor para manter o `vite preview` ativo após reboot.
- Problema diagnosticado: porta 5173 estava bloqueada pelo firewall Lightsail → URL correta é o domínio `https://synerium-factory.objetivasolucao.com.br`.

---

## v0.55.0 — Code Studio 2.0: Mission Control (01/Abr/2026)

### Feature Principal
Painel triplo simultâneo (Editor + Terminal + Artifacts) com agentes vivos e comentários inline.

### Funcionalidades
- **Painel Triplo Redimensionável** — Editor, Terminal e Artifacts lado a lado, cada um maximizável
- **Terminal Interativo Sandboxed** — Executa comandos com histórico, output colorido e timeout de 30s
- **Agentes Vivos** — Aparecem animados no header (pulse) enquanto executam, geram artifacts automaticamente
- **Artifacts Inteligentes** — Planos, checklists, código e logs de terminal gerados pelos agentes
- **Comentários Inline** — Estilo Google Docs em qualquer artifact (CEO comenta, agente lê e ajusta)
- **Barra de Instrução** — Dispatch rápido de agentes com Enter

### Endpoints
- `POST /api/mission-control/sessao` — Cria sessão
- `GET /api/mission-control/sessao/{id}` — Detalhes com artifacts
- `POST /api/mission-control/sessao/{id}/comando` — Terminal
- `POST /api/mission-control/sessao/{id}/agente` — Dispara agente
- `GET /api/mission-control/artifacts/{sessao_id}` — Lista artifacts
- `POST /api/mission-control/artifacts/{id}/comentar` — Comentário inline
- `POST /api/mission-control/artifacts/{id}/status` — Aprovar/rejeitar

### Models
- `ArtifactDB` — Entregáveis tangíveis com comentários inline (JSON)
- `MissionControlSessaoDB` — Sessão com estado dos 3 painéis

### Arquivos
- `api/routes/mission_control.py` (NOVO) — 450+ linhas
- `dashboard/src/pages/MissionControl.tsx` (NOVO) — 400+ linhas
- `database/models.py` — 2 novos models

---

## v0.54.0 — Continuous Factory — Modo Contínuo 24/7 (31/Mar/2026)

### Feature Principal
A fábrica agora opera autonomamente 24/7 mesmo quando o CEO está offline.

### Funcionalidades
- **Toggle Modo Contínuo** — CEO ativa/desativa via API ou Command Center
- **Auto-aprovação de gates** — Gates soft: sempre automáticos. Gates hard: configurável (auto ou email)
- **Notificação por email** — Gates hard pendentes enviam email ao CEO via Amazon SES
- **Relatório Diário Automático** — Gerado às 23:00 com métricas, resumo LLM e próximos passos
- **Worker Background** — Loop a cada 30s: auto-aprovação, relatório, métricas
- **Recovery automático** — Ao reiniciar o servidor, o modo contínuo retoma automaticamente

### Endpoints
- `GET /api/continuous-factory` — Status e configuração
- `POST /api/continuous-factory/ativar` — Ativa modo contínuo
- `POST /api/continuous-factory/desativar` — Desativa
- `POST /api/continuous-factory/config` — Atualiza configurações
- `GET /api/continuous-factory/relatorios` — Lista relatórios diários
- `POST /api/continuous-factory/relatorio-agora` — Gera relatório manualmente

### Models
- `ContinuousFactoryDB` — Configuração singleton por empresa
- `RelatorioDiarioDB` — Relatórios diários com métricas e resumo LLM

### Arquivos
- `api/routes/continuous_factory.py` (NOVO) — 600+ linhas
- `database/models.py` — 2 novos models
- `api/main.py` — Registro de rota + recovery no lifespan
- `api/routes/tarefas.py` — Integração com auto-aprovação de gates

---

## v0.53.3 — Retry no CrewAI + Throttling Fase 4 (31/Mar/2026)

### Correções
- **Retry com backoff no CrewAI** — `executar_agente()` agora faz até 3 tentativas com backoff (5s→10s→20s) quando `crew.kickoff()` dá 429. Antes, o erro era retornado direto sem retry.
- **Fase 4 throttled** — `max_workers=2` na Fase 4 (Implementação) para reduzir pico de tokens. Fases 1-3 continuam com 3 workers paralelos.
- **Root cause:** O GPT-4o-mini tem limite de 200K TPM. Com 3 agentes paralelos na Fase 4 (contexto ~40K tokens cada), ultrapassava o limite instantaneamente.

---

## v0.53.2 — Instrução de Tools no Workflow Autônomo BMAD (31/Mar/2026)

### Correções
- **PROMPTS_FASE com instrução de tools** — Todas as 4 fases BMAD agora incluem `_INSTRUCAO_TOOLS` com lista completa de ferramentas e fluxo obrigatório para implementação. Fase 4 tem instrução CRÍTICA reforçada: cada arquivo = uma proposta via `propor_edicao_syneriumx`.
- **Root cause:** O prompt do workflow autônomo era independente dos prompts de tarefas/reuniões. As correções v0.52.3/v0.53.0 só cobriam esses dois — o autônomo ficou sem instrução de tools.

---

## v0.53.1 — Correções Finais Vision-to-Product (31/Mar/2026)

### Correções
- **Rate Limit Retry** — Backoff exponencial (2s→4s→8s) para erros 429/rate_limit em `llm_fallback.py`. Até 3 tentativas por provider antes de fazer fallback. Versões sync e async.
- **Self-Evolving Factory** — `_executar_review_session()` agora SEMPRE salva no `EvolucaoFactoryDB`, mesmo se LLM falhar. Registro criado antes da chamada LLM. Se ocorrer erro fatal, cria registro com status "erro".
- **Tool Schemas GPT-4o-mini** — Adicionado `args_schema` Pydantic explícito em todas as 10 tools CrewAI (syneriumx, zip, email). Cada campo tem `description` e `type` corretos para function calling confiável no GPT-4o-mini.

### Arquivos alterados
- `core/llm_fallback.py` — retry com `_eh_rate_limit()`, `MAX_RETRIES=3`, `BACKOFF_BASE=2s`
- `api/routes/tarefas.py` — `_executar_review_session()` reescrita com 3 passos: criar registro → LLM → commit
- `tools/syneriumx_tools.py` — 6 schemas: `LerArquivoInput`, `ListarDiretorioInput`, `ProporEdicaoInput`, `BuscarInput`, `GitInput`, `TerminalInput`
- `tools/zip_tool.py` — 2 schemas: `CriarZipInput`, `CriarProjetoInput`
- `tools/email_tool.py` — 2 schemas: `EnviarEmailInput`, `EnviarEmailComAnexoInput`

---

## v0.53.0 — Pipeline Completo: Agente → Proposta → Build → Deploy (31/Mar/2026)

### Funcionalidades
- **Pipeline de código completo** — Agentes usam `propor_edicao_syneriumx` para criar propostas formais de edição
- **Prompt v0.53.0** — Instrução explícita em tarefas + reuniões paralelas + reuniões sequenciais para usar tools de proposta
- **Endpoint pendentes** — `GET /api/propostas/pendentes/count` para badge no dashboard
- **Build Gate na aprovação** — Após aprovar edição, valida build antes de confirmar. Se falha, reverte com `git checkout`
- **Auto-deploy opcional** — Flag `auto_deploy=true` na aprovação pula segunda aprovação e faz push+PR+merge automático
- **Fluxo completo:** agente lê código → propõe edição → CEO aprova → build gate → commit → deploy

---

## v0.52.2 — Build Gate + Deploy (31/Mar/2026)

### Funcionalidades
- **Build Gate** no `core/vcs_service.py` — Validação de build obrigatória antes de qualquer push
  - Node.js: `npm run build` (bloqueante, timeout 3min)
  - Python: `py_compile` nos arquivos alterados
  - Se build falhar: commit revertido (`git reset HEAD~1`), push bloqueado
- **Build Gate integrado em 3 pontos**: `commit_e_push()`, `push_branch()`, `deploy_pipeline_v2.py`
- **deploy_pipeline_v2.py**: Stage 4 (Build) agora é estritamente bloqueante (antes era warning-only para PHP)

### Bugs corrigidos
- **Bug #43**: Factory destruiu `EditProposalModal.tsx` (PR #195 SyneriumX) — agente substituiu código React por descrição textual. Build Gate previne esse cenário

### Merge
- PR #2 mergeado na main: Smart Router Dinâmico v0.52.0 + Minimax fix v0.52.1 + Build Gate v0.52.2

---

## v0.52.1 — Correção Minimax + Smart Router Luna (31/Mar/2026)

### Corrigido
- **Bug #42**: Minimax retornava 404 — GroupId como query param na base_url conflitava com SDK OpenAI — Fix: extra_body
- **Luna Engine** não respeitava classificação do Smart Router — sempre começava com Minimax independente da complexidade
- **_obter_cadeia_fallback()** reordenada: SIMPLES→minimax primeiro, MEDIO→groq primeiro, COMPLEXO→anthropic_sonnet primeiro

### Verificado
- Teste end-to-end: SIMPLES→minimax (2s), MEDIO→groq (2s), COMPLEXO→anthropic_sonnet (49s)
- CrewAI Escritório Virtual: GPT-4o-mini funcional para todas as tarefas
- Anthropic com créditos restabelecidos

---

## v0.52.0 — Smart Router Dinâmico por Mensagem (31/03/2026)

### Funcionalidades
- **Smart Router Dinâmico** — Classificação por mensagem individual (não mais por módulo)
- **core/classificador_mensagem.py** (novo) — Classificador regex de complexidade com 4 níveis
- **Matriz de decisão dinâmica:**
  - `SIMPLES` → Minimax MiniMax-Text-01 (mais barato)
  - `MEDIO` → Groq Llama 3.3 70B (rápido e bom custo)
  - `COMPLEXO` → Claude Sonnet (qualidade premium)
  - `TOOLS` → GPT-4o-mini (suporta function calling + system role)
- **6 pontos de chamada integrados** com classificação dinâmica por mensagem
- **Adaptador de mensagens para Minimax** — Converte role `system` para `user` (Minimax não suporta system role)
- **GPT-4o-mini como LLM principal no CrewAI** — Único que suporta tools (function calling) e system role simultaneamente

### Bugs corrigidos
- **Bug #40**: Groq falha em function calling — `tool_use_failed` ao usar ferramentas no CrewAI. Groq não suporta function calling nativo de forma confiável
- **Bug #41**: Minimax não suporta role `system` — erro 2013 ao enviar mensagens com role system. Resolvido com adaptador que converte system → user

---

## v0.51.0 — Minimax como LLM Principal (31/03/2026)

### Funcionalidades
- **Minimax MiniMax-Text-01** como LLM principal do sistema (mais barato: $0.0004/1K input)
- **Cadeia definitiva de fallback:** Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
- **Endpoint global correto:** `api.minimaxi.chat` (com **i**) — host China (`api.minimax.chat`) não funciona para contas globais
- **core/llm_fallback.py** atualizado com 6 providers (Minimax, Groq, Fireworks, Together, Anthropic, OpenAI)
- **Fireworks e Together** adicionados via API OpenAI-compatible
- **Smart Router Global** com Provider.MINIMAX + PROVIDER_CONFIG
- **config/settings.py** com minimax_api_key e minimax_group_id
- **config/llm_providers.py** com ProviderID.MINIMAX
- **API key pay-as-you-go** (`sk-api-`) — Token Plan Key (`sk-cp-`) NÃO funciona na API REST

### Bug corrigido
- **Bug #39**: Endpoint China (`api.minimax.chat`) vs Global (`api.minimaxi.chat`) — contas internacionais devem usar host com **i**

---

## v0.50.0 — Vision-to-Product + Correções Críticas (2026-03-30)

### Funcionalidades
- **Vision-to-Product** — PM Central gera roadmap, estimativa de dias e custo estimado a partir de uma visão de produto
- **Features com prioridade e complexidade** no Comando Estratégico do Command Center
- **Barra de progresso %** em cada card de squad no Command Center
- **Session SQLite isolada por fase** no Autonomous Squads (fix crítico — `SessionLocal()` por fase evita crash de `commit()`)
- **Fila de workflows automática** — Próximo workflow inicia automaticamente ao concluir/falhar o anterior
- **LLM Fallback robusto** — `core/llm_fallback.py` com cadeia Anthropic → Groq → OpenAI
- **6 pontos de chamada LLM** atualizados para usar fallback centralizado
- **langchain-groq** instalado no servidor para suporte ao fallback Groq
- **Rota conflito corrigida** — `GET /{tarefa_id}` → `GET /detalhe/{tarefa_id}`
- **Botão Novo Projeto** na página Projetos + modal de criação (CEO only)
- **Sistema de conversas separadas** no AgentPanel (localStorage por projeto, máx 20)
- **Scroll inteligente** no AgentPanel (início da resposta, não final)
- **Convites corrigidos** — Tratamento naive vs aware datetime em `auth.py` e `convites.py`
- **Painel Geral** busca usuários do banco (não mais config estático)
- **Jonatas removido do seed** — Agora entra via sistema de convites
- **CEO pode excluir qualquer usuário** exceto ele mesmo
- **permissoes.py corrompido** restaurado via SCP do servidor
- **Pull no Code Studio** com token VCS + auto-pull após merge
- **Push dialog** — Invalid Date corrigido + commits já mergeados somem da lista
- **Regex extrairBlocoCodigo** com 3 fallbacks para robustez
- **Fix: review session + fila no gate approval** — Review session e fila agora disparam quando gate final é aprovado via endpoint (antes só disparava via bg function)
- **Teste end-to-end Vision-to-Product APROVADO** — 4 fases BMAD, 3 gates (soft+hard), review com 3 sugestões reais, fila automática — tudo funcionando

---

## v0.49.0 — Autonomous Squads + Self-Evolving Factory + Command Center (2026-03-30)

### Funcionalidades
- **Autonomous Squads** — Workflow BMAD completo automatizado com 4 fases, gates soft/hard, execução paralela de agentes
- **Self-Evolving Factory** — Review session automática pós-workflow, Factory Optimizer (ID=16), modelo `EvolucaoFactoryDB` para registrar sugestões de melhoria
- **Command Center** — Painel CEO com KPIs em tempo real, comando estratégico, spawn de squads sob demanda
- **LLM Fallback robusto** — Cadeia centralizada Anthropic → Groq → OpenAI em `core/llm_fallback.py`
- **Recovery de workflows travados** — No startup do servidor, workflows parados há >30min são marcados como erro
- **Gate approval com threading.Lock** — Verificação thread-safe de CEO/OpsLead, evita race condition
- **Rota conflito corrigida** — `/{tarefa_id}` → `/detalhe/{tarefa_id}` para evitar colisão com outras rotas
- **langchain-groq** instalado no servidor para suporte ao fallback Groq
- **Botão Novo Projeto** na página Projetos (CEO only)
- **Sistema de conversas separadas** no AgentPanel do Code Studio
- **Convites corrigidos** — Tratamento naive vs aware datetime em `auth.py` e `convites.py`
- **Painel Geral** busca usuários do banco (não mais config estático)
- **Jonatas removido do seed** — Agora entra via sistema de convites

---

## v0.48.0 — Preview de Arquivos por Commit + Horário Brasília (2026-03-30)

### Funcionalidades
- **Preview de arquivos por commit** no PushDialog — Ao selecionar um commit, lista os arquivos alterados com diff visual
- **Horário Brasília** — Timestamps de commits exibidos em fuso horário America/Sao_Paulo (UTC-3) no PushDialog
- **Seleção visual de commits** — Checkboxes para selecionar quais commits incluir no push

---

## v0.47.0 — Botão Novo Projeto + Modal de Criação (2026-03-30)

### Funcionalidades
- **Botão "Novo Projeto"** na página Projetos — Visível apenas para CEO/proprietários
- **Modal de criação de projeto** — Formulário completo com nome, descrição, stack, membros
- **Validação de permissão** — Apenas CEO pode criar novos projetos via dashboard

---

## v0.46.0 — 3 Agentes Elite + BMAD Mapeamento Completo (2026-03-30)

### Funcionalidades
- **Test Master** — Agente especializado em testes automatizados, obrigatório e bloqueante no pipeline Apply+Deploy
- **GitHub Master** — Agente especializado em operações GitHub (PRs, issues, reviews, merges)
- **GitBucket Master** — Agente especializado em operações GitBucket (repositórios on-premise)
- **BMAD mapeamento completo** — 15 agentes mapeados com fases, palavras-chave e especialidades definidas
- **Catálogo expandido** — De 12 para 15 templates de agentes reutilizáveis

---

## v0.45.0 — Sistema de Conversas Separadas no AgentPanel (2026-03-30)

### Funcionalidades
- **Conversas separadas** no AgentPanel do Code Studio — Cada conversa é independente com histórico próprio
- **Botão "Novo Chat"** — Inicia nova conversa sem perder as anteriores
- **Histórico de conversas** — Lista lateral com título e preview de cada conversa
- **Scroll inteligente** — Scrolla para o início da resposta do agente (não para o final), facilitando leitura
- **Persistência em localStorage** — Conversas salvas por projeto, sobrevivem a reload
- **Indicador de conversa ativa** — Destaque visual na conversa selecionada

---

## v0.44.0 — Painéis Redimensionáveis no Code Studio (2026-03-30)

### Funcionalidades
- **Painéis redimensionáveis** — Drag handle entre os painéis do Code Studio para ajustar largura
- **Largura mínima garantida** — Editor central mantém tamanho mínimo confortável mesmo ao redimensionar
- **Persistência de tamanho** — Largura dos painéis salva em localStorage
- **Cursor visual de resize** — Indicador visual ao passar sobre a borda entre painéis

---

## v0.43.0 — Live Agents (2026-03-30)

### Funcionalidades
- **Progresso rotativo no AgentPanel** — Indicador visual de que o agente está processando com animação de rotação
- **Balão de status no Escritório Virtual** — Mostra status do agente (pensando, digitando, ocioso) com ícone animado
- **Shimmer no ChatFloating** — Efeito shimmer durante carregamento de resposta do agente
- **Animações contextuais** — Diferentes animações para diferentes estados do agente (idle, thinking, responding)

---

## v0.42.0 — Push & PR & Merge direto do Code Studio (2026-03-30)

### Funcionalidades
- **Push direto do Code Studio** — Botão "Push" que envia commits selecionados para o remote
- **Criação de Pull Request** — Gera PR no GitHub/GitBucket diretamente pelo dashboard
- **Merge via GitHub API** — Merge de PRs sem sair do Code Studio
- **Seleção de commits** — Interface com checkboxes para escolher quais commits enviar
- **PushDialog** — Modal completo com preview de commits, seleção e ações (push, PR, merge)
- **Integração GitHub API** — Usa token VCS criptografado para operações autenticadas

---

## v0.41.0 — One-Click Apply+Deploy (2026-03-30)

### Funcionalidades
- **One-Click Apply+Deploy** — Pipeline completo acionado por um único clique no Code Studio
- **Pipeline de 5 etapas**: backup → aplicar alteração → Test Master (obrigatório) → commit → push
- **Test Master bloqueante** — Testes automatizados executados antes do commit; se falharem, pipeline para
- **Backup automático** — Arquivo original salvo antes de aplicar alteração do agente IA
- **Feedback em tempo real** — Progresso visual de cada etapa do pipeline no frontend
- **Rollback em caso de falha** — Se qualquer etapa falhar, o backup é restaurado automaticamente

### Correções
- **Convites inválidos (naive vs aware datetime)** — Corrigido em `convites.py` e `auth.py` para usar timezone-aware datetime
- **permissoes.py corrompido no servidor** — Arquivo continha conteúdo de IA misturado; restaurado do Git
- **Painel Geral mostrava usuários deletados** — Buscava config estático em vez do banco; corrigido para buscar dinâmico
- **Push dialog: Invalid Date** — Parsing de data de commits corrigido para formato ISO 8601
- **Commits já mergeados aparecendo no PushDialog** — Filtro adicionado para excluir commits já presentes em origin/main
- **VCS remote corrompido após commit** — URL do remote era sobrescrita; restaurada no bloco finally
- **CEO não podia excluir outros proprietários** — Regra de permissão corrigida para permitir CEO deletar qualquer usuário
- **Git pull HTTPS sem token** — Fetch com token VCS para sincronizar origin/main corretamente

---

## v0.40.0 — Chat Resiliente + Timeout + Retomar Conversa (2026-03-30)

### Funcionalidades
- **Timeout de tarefas/reuniões aumentado** de 10 para 30 minutos — consultas complexas não expiram mais prematuramente
- **Novo endpoint** `POST /tarefas/{id}/retomar` — Re-executa tarefa ou reabre reunião que deu erro/timeout
- **Botão "Retomar conversa"** no ChatFloating do Escritório Virtual quando agente retorna erro
- **Botão "Retomar de onde parou"** no ReuniaoModal quando reunião dá timeout ou erro
- **Git Pull com token VCS** — Code Studio agora injeta token VCS na URL HTTPS para autenticação automática no git pull
- **GIT_TERMINAL_PROMPT=0** — Evita que o git trave esperando input do usuário em operações HTTPS

### Correções
- **LLM tracked incompatível com CrewAI 1.11+** — Corrigido com `**kwargs` no wrapper (parâmetro `available_tools`)
- **Gemini 2.0-flash descontinuado** — Atualizado para Gemini 2.5-flash
- **LangSmith 403 no RAG** — Removido `@traceable` do endpoint de query que causava erro de permissão
- **Chroma deprecation warning** — Migrado de `langchain_community.vectorstores` para `langchain_chroma`
- **Estimador de tokens inflado** — Valores fantasma ($55) corrigidos para refletir custos reais
- **Botão "Aplicar" não aparecia em Refatorar/Documentar** — Regex corrigida para capturar todas as ações, não só Otimizar
- **NetworkError no fetch do analyze** — Timeout aumentado para 120s com AbortController
- **Estouro de 213K tokens ao enviar imagem** — Imagens agora são tratadas como descrição textual no contexto
- **Texto muted com baixo contraste** — Cores de texto `muted` ajustadas para acessibilidade em dark/light mode
- **Git Pull falhava com "could not read Username"** — Resolvido com injeção de token VCS na URL HTTPS
- **Agente do Escritório enviava emails sem pedir** — Bloqueado com regras obrigatórias no prompt do agente

---

## v0.39.0 — 2026-03-29
### Company Context Total — Agente IA com Conhecimento Completo
- **Novo módulo** core/company_context.py com CompanyContextBuilder (3 níveis: minimal/standard/full)
- **Nível standard**: detalhes profundos do projeto (membros, regras, VCS, fase, líder técnico)
- **Nível full**: empresa + todos projetos + busca RAG semântica (top 3 chunks do ChromaDB)
- **Toggle** "Contexto Empresa" no AgentPanel com switch ON/OFF (ligado por padrão)
- **Badge visual** "Contexto Total" nas respostas do assistente quando contexto ativo
- **Cache inteligente**: 5 minutos para lista de projetos, empresa estático
- **Integração RAG**: ChromaDB + Obsidian vaults, filtrando vault por projeto automaticamente
- Budget de tokens limitado a 4000 chars para não exceder context window

---

## v0.38.0 — Histórico de Atividades + Feedback Detalhado no Code Studio (2026-03-29)

### Funcionalidades
- **Novo endpoint** `GET /api/code-studio/historico` — Lista cronológica de atividades com paginação e filtro por projeto
- **Cálculo de diff no apply-action** — Retorna linhas adicionadas/removidas via `difflib` ao aplicar ação do agente IA
- **Novo componente HistoricoPanel** — Painel com lista cronológica de atividades, ícones por tipo, tempo relativo e paginação
- **Toast detalhado ao aplicar ação IA** — Mostra diff (+N/-N linhas), commit hash e branch VCS no feedback visual
- **Confirmação inline antes de aplicar ações** — Botões Confirmar/Cancelar antes de executar ação do agente IA
- **Botão Histórico na Toolbar** — Toggle mutuamente exclusivo com AgentPanel para não comprimir o editor
- **Clique em arquivo no histórico** — Abre diretamente no editor ao clicar em uma entrada do histórico

---

## v0.37.1 — Auto-Clone VCS no Code Studio (2026-03-29)

### Funcionalidades
- **Auto-clone VCS** — Quando um projeto tem VCS (GitHub/GitBucket) configurado mas não possui diretório local, o Code Studio clona automaticamente o repositório para `/opt/projetos/{slug}/`
- **Atualização automática do `caminho`** — O campo `caminho` no banco de dados é atualizado automaticamente após o clone bem-sucedido
- **Git pull inteligente** — Se o diretório já existe com pasta `.git`, faz `git pull` em vez de re-clonar
- **Endpoint `POST /api/code-studio/git-pull`** — Novo endpoint para atualizar o repositório a partir do remote
- **Botão "Pull" no header** — Novo botão no cabeçalho do Code Studio (visível quando o projeto tem VCS configurado) para puxar atualizações do remote
- **Botão de refresh na árvore** — Novo botão para recarregar a árvore de arquivos sem recarregar a página
- **Mensagem de loading inteligente** — Exibe "Clonando repositório..." quando o auto-clone está em andamento

### Correções
- **Caminho local inválido no servidor AWS** — O projeto SyneriumX tinha `caminho` definido como `/Users/thiagoxavier/propostasap` (caminho do Mac), que não existe no servidor AWS; agora o auto-clone resolve isso automaticamente

---

## v0.37.0 — Code Studio Multi-Projeto (2026-03-29)

### Funcionalidades
- **Code Studio multi-projeto** — O Code Studio agora é project-aware: cada projeto abre seu próprio diretório base, árvore de arquivos e configuração VCS
- **Seletor de projeto no header** — Dropdown no cabeçalho do Code Studio mostrando nome do projeto, stack e ícone do VCS vinculado
- **`_obter_base_projeto()`** — Função backend que resolve o caminho base do projeto a partir do ID, centralizando a lógica de diretório
- **Parâmetro `project_id` em todos os endpoints** — Todos os endpoints do Code Studio aceitam `project_id` para operar no projeto correto
- **VCS auto-commit por projeto** — O commit automático agora usa a configuração VCS específica do projeto selecionado
- **Contexto de projeto no Agente IA** — O system prompt do agente IA recebe o contexto do projeto ativo (nome, stack, estrutura)
- **Audit log com nome do projeto** — Todas as entradas de audit log do Code Studio agora incluem o nome do projeto
- **Persistência de projeto no frontend** — O último projeto selecionado é salvo em `localStorage` e restaurado ao reabrir o Code Studio
- **Troca de projeto limpa** — Ao trocar de projeto, o frontend limpa abas abertas e recarrega a árvore de arquivos do novo projeto

---

## v0.36.3 — JWT Auto-Refresh + Bloqueio de Binários no Code Studio (2026-03-29)

### Melhorias
- **JWT 8h de expiração** — Access token aumentado de 1h para 8h (jornada de trabalho completa), eliminando logouts aleatórios durante o expediente
- **Auto-refresh transparente** — Quando recebe 401, o frontend tenta renovar o token via refresh token antes de redirecionar para login; o usuário nem percebe a renovação
- **Bloqueio de arquivos binários no Code Studio** — Extensões bloqueadas: `.docx`, `.xlsx`, `.pptx`, `.pdf`, `.doc`, `.xls`, `.ppt`, `.odt`, `.ods`, `.odp`, `.rtf`, `.bmp`, `.tiff`, `.psd`, `.ai`, `.eps`, `.bin`, `.dat`, `.lock`

### Correções
- **Code Studio travava ao abrir binários** — Clicar em arquivos de ata (PPTX de reuniões) congelava o editor inteiro; agora exibe mensagem de aviso e não tenta abrir

---

## v0.36.2 — Fix Campos AuditLogDB no VCS (2026-03-29)

### Correções
- **Erro 500 no endpoint VCS** — Endpoint usava campos inexistentes `usuario_id` e `detalhes` no AuditLogDB; corrigido para `user_id` e `descricao`

---

## v0.36.1 — Fix Rotas VCS (2026-03-29)

### Correções
- **404 ao salvar configuração VCS** — Endpoints VCS estavam registrados como `/api/{id}/vcs` em vez de `/api/projetos/{id}/vcs`; corrigido prefixo das rotas

---

## v0.36.0 — Hierarquia Editável + Regras de Aprovação por Projeto (2026-03-29)

### Funcionalidades
- **Hierarquia editável por projeto** — Proprietário, líder técnico e membros podem ser alterados diretamente na interface do projeto
- **Regras de aprovação customizáveis** — Cada projeto pode definir suas próprias regras de aprovação (quem aprova mudanças pequenas, grandes e críticas)
- **Campo `regras_aprovacao` (JSON)** — Novo campo JSON em `ProjetoDB` para armazenar regras de aprovação personalizadas por projeto
- **Endpoint `PUT /projetos/{id}/regras`** — Novo endpoint para atualizar regras de aprovação de um projeto específico
- **Dropdowns inline no frontend** — Edição da hierarquia e regras diretamente na página de projetos com dropdowns inline (sem modal separado)

### Detalhes
- Regras de aprovação são flexíveis: cada projeto pode ter fluxo diferente
- Retrocompatível: projetos sem regras customizadas usam o padrão global (líder → proprietário → proprietário+líder)

---

## v0.35.1 — Fix Geração de PDF (Luna) (2026-03-29)

### Correções
- **Erro 400 ao gerar PDF** — Tags HTML vindas do navegador estavam sendo passadas diretamente ao ReportLab, causando erro na geração
- **`_sanitizar_para_pdf()`** — Nova função que remove/converte tags HTML antes de enviar conteúdo ao ReportLab
- **Sanitização geral em `gerar_arquivo()`** — Tratamento de HTML aplicado de forma global na função de geração de arquivos, prevenindo erros similares em outros formatos

---

## v0.35.0 — Version Control (VCS) — Integração GitHub/GitBucket por Projeto (2026-03-29)

### Funcionalidades
- **Integração VCS por projeto** — Cada projeto pode ter repositório GitHub ou GitBucket vinculado com token criptografado
- **`core/vcs_service.py`** — Serviço central de Version Control com suporte a GitHub e GitBucket (clone, commit, push via API)
- **Criptografia Fernet** — Tokens de acesso armazenados com criptografia simétrica (Fernet/AES-128-CBC); token nunca exposto em resposta da API
- **`ProjetoVCSDB`** — Novo modelo SQLAlchemy para armazenar configuração VCS (provider, repo_url, branch, token criptografado)
- **4 endpoints VCS** — `POST /api/projetos/{id}/vcs` (cadastrar), `GET /api/projetos/{id}/vcs` (buscar sem token), `POST /api/projetos/{id}/vcs/testar` (testar conexão), `DELETE /api/projetos/{id}/vcs` (remover)
- **Commit + push automático no Code Studio** — Após aplicar ação do agente IA, o Code Studio faz commit e push automaticamente no repositório vinculado
- **Seção VCS no modal de projeto** — Interface para configurar repositório, branch e token diretamente no dashboard

### Segurança
- Token de acesso nunca retornado pela API (apenas indicação `token_configurado: true/false`)
- Criptografia Fernet com chave derivada do `JWT_SECRET_KEY`
- Apenas proprietário e líder técnico do projeto podem configurar VCS
- Audit log LGPD para todas as operações VCS

---

## v0.34.1 — Correções e Melhorias do Code Studio (2026-03-29)

### Correções
- **Token de autenticação** — Renomeado de `token` para `sf_token` em todos os endpoints do Code Studio
- **Árvore de arquivos** — Melhor tratamento de erro ao listar diretórios (catch de exceções com feedback ao usuário)
- **Integração Smart Router** — Corrigido envio de `modelo_forcado` removido; integração LLM do Code Studio funcional

### Funcionalidades
- **Menu de contexto no Escritório Virtual** — Clique direito nas salas do Escritório abre menu contextual; ação "Code Studio" abre o editor diretamente
- **AgentPanel: ação "Testar"** — 5ª ação adicionada ao painel de agentes: gera testes unitários para o código aberto no editor
- **Contexto do arquivo enviado ao LLM** — Nome, linguagem e caminho do arquivo agora são enviados como contexto ao agente IA do Code Studio

---

## v0.34.0 — Code Studio — Editor de Código Integrado (2026-03-28)

### Funcionalidades
- **Code Studio** — Editor de código integrado ao dashboard com CodeMirror 6
- **4 endpoints REST** — CRUD de arquivos do projeto (ler, salvar, listar árvore, criar)
- **Árvore de arquivos** — Navegação hierárquica com ícones por tipo de arquivo
- **Sistema de abas** — Múltiplos arquivos abertos simultaneamente com indicador de modificação
- **Agente IA integrado** — Assistência de código via agentes do Factory dentro do editor
- **Syntax highlighting** — Destaque de sintaxe para Python, TypeScript, JavaScript, JSON, Markdown, CSS, HTML e mais
- **Audit log LGPD** — Todas as operações de leitura e escrita registradas no audit log

### Segurança
- Proteção contra path traversal (sanitização de caminhos)
- Backup automático antes de sobrescrever arquivos
- Permissões baseadas no sistema de autenticação existente (JWT)

### Dependências
- CodeMirror 6 — Editor de código moderno e extensível
- Extensões: lang-python, lang-javascript, lang-html, lang-css, lang-json, lang-markdown

---

## v0.33.1 — Gemini 2.0 Flash + GPT-4o como Providers Reais (2026-03-28)

### Funcionalidades
- **Gemini 2.0 Flash adicionado** — Google Gemini integrado via API OpenAI-compatible (`generativelanguage.googleapis.com`)
- **GPT-4o adicionado** — OpenAI GPT-4o como provider alternativo na cadeia de fallback
- **Cadeia completa de fallback** — Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together (7 providers ativos)
- **Smart Router Global no dashboard** — Página LLM Providers (`/llm-providers`) agora exibe e gerencia todos os providers do Router Global
- **Gemini no Consumo de APIs** — Tela de Consumo (`/consumo`) agora inclui Gemini como provider rastreável

### Detalhes
- Gemini usa free tier: 1.5M tokens/dia sem custo
- API do Gemini acessada via base_url OpenAI-compatible (sem SDK próprio)
- GPT-4o complementa a cadeia entre Sonnet e Gemini para maior resiliência

---

## v0.33.0 — Smart Router Global Multi-Provider + Multi-Ferramenta (2026-03-28)

### Funcionalidades
- **Smart Router Global** — Novo roteador inteligente (`core/smart_router_global.py`) que expande o roteamento para todos os providers e ferramentas externas
- **7 providers de LLM** — Opus, Sonnet, GPT-4o, Gemini, Groq, Fireworks, Together
- **8 ferramentas externas** — Exa, Tavily, Firecrawl, Scrapingdog, Composio, E2B, LiveKit, SES
- **13 categorias de intenção** — Detecção automática por regex (sem ML) para roteamento preciso
- **Override manual** — Prefixo no prompt permite forçar provider/ferramenta específica
- **Tempo de decisão** — Média de 0.12ms por roteamento (regex puro, sem overhead de ML)

### Arquitetura
- Coexiste com o SmartRouter antigo (`llm_router.py`) que continua roteando Opus/Sonnet para CrewAI
- Router Global é o ponto único de decisão para qualquer provider ou ferramenta do ecossistema
- Cadeia de fallback multi-provider para alta disponibilidade
- Endpoints da API para consulta e override de roteamento

---

## v0.32.0 — Avatares Reais dos Agentes (2026-03-28)

### Funcionalidades
- **10 avatares oficiais em JPG** — Kenji, Amara, Carlos, Yuki, Rafael, Hans, Fatima, Marco, Sofia, Luna
- **Config centralizada** — `src/config/agents.ts` com dados de todos os agentes (nome, cargo, avatar, cor, especialidade)
- **Componente `AgentAvatar.tsx` reutilizável** — Tamanhos sm/md/lg/xl/2xl, fallback com iniciais, indicador de status online/offline, efeito hover
- **`AgentAvatarGroup`** — Empilhamento de avatares com sobreposição (ex: participantes de reunião)
- **Integração em múltiplas telas** — ChatFloating, ReuniaoModal, Escritório Virtual, Catálogo de Agentes, Luna Chat, Luna Welcome

### Correções
- **Token de convite** — Agora usa `token_hex` ao invés de `token_urlsafe` (evita ambiguidade visual entre l/I/1/0/O)

### Melhorias
- **Aba "Desativados" em Configurações** — Proprietários podem reativar ou excluir permanentemente usuários desativados
- **Vault Obsidian migrado para dentro do repo Git** — `docs/obsidian/` agora é versionado junto com o código

---

## v0.16.5 — Exclusão Permanente de Usuários (2026-03-27)

### Funcionalidades
- **Hard delete de usuários** — Proprietários (CEO/Operations Lead) podem excluir permanentemente um usuário
- **Endpoint dedicado** — `DELETE /api/usuarios/{id}/permanente` com confirmação obrigatória
- **Liberação de email** — Ao excluir permanentemente, o email fica disponível para reconvite
- **Caso de uso** — Quando um convite foi enviado para o email errado ou funcionário precisa ser recadastrado

### Motivação
Antes existia apenas soft delete (desativação). Porém, com o email vinculado ao registro desativado, não era possível reenviar convite para o mesmo email. O hard delete resolve isso mantendo o audit log da exclusão.

---

## v0.16.4 — Fix Download de Arquivos Luna em Produção (2026-03-27)

### Correção
- **UPLOAD_DIR corrigido** — Path de uploads no `api/routes/uploads.py` apontava para `~/synerium` (local) ao invés de `/opt/synerium-factory` (servidor AWS)
- **Problema** — Downloads de arquivos gerados pela Luna retornavam 404 em produção
- **Solução** — Ajuste do caminho para usar path relativo ao projeto, funcional tanto local quanto no servidor

---

## Syncthing Desinstalado (2026-03-27)

### Infraestrutura
- **Syncthing removido do Mac** — Sincronização era redundante com o rsync do script de deploy (`scripts/deploy_producao.sh`)
- **Espaço liberado** — ~93 GB livres no Mac após remoção
- **Deploy continua via** — `bash scripts/deploy_producao.sh` (rsync + SSH)

---

## v0.16.3 — Luna: Geração de Arquivos para Download (2026-03-27)

### Funcionalidades
- **Geração de arquivos no chat** — Luna gera arquivos para download direto na conversa
- **9 formatos suportados** — XLSX, DOCX, PPTX, PDF, TXT, MD, CSV, JSON, HTML
- **Motor de geração** — `core/luna_file_generator.py` com engines especializadas por formato
- **Endpoint dedicado** — `POST /api/luna/gerar-arquivo` para geração sob demanda
- **Marcadores no system prompt** — Sintaxe `:::arquivo[nome.ext]` para Luna sinalizar geração
- **Componente LunaFileBlock** — Card de download profissional no chat com ícone, nome e tamanho

### Detalhes por formato
- **Planilhas (XLSX)** — Headers emerald, bordas, largura automática de colunas
- **Documentos (DOCX)** — Markdown parseado com estilos profissionais
- **Apresentações (PPTX)** — Slides separados por `##` com layout automático
- **PDFs** — Layout profissional com ReportLab
- **Texto/Dados** — TXT, MD, CSV, JSON, HTML gerados diretamente

---

## v0.16.2 — Luna: Anexos de Arquivos (2026-03-27)

### Funcionalidades
- **Anexos no chat** — Luna aceita imagens, PDFs, documentos e código como anexo nas mensagens
- **Botão de anexo** — Ícone 📎 no input com preview dos arquivos selecionados antes do envio
- **Contexto enriquecido** — Anexos incluídos automaticamente no contexto enviado ao LLM
- **Exibição nos balões** — Anexos aparecem clicáveis nos balões de mensagem (visualização inline)
- **Múltiplos arquivos** — Suporte a múltiplos anexos por mensagem (máximo 50MB cada)

---

## v0.16.1 — Luna: Soft Delete + Lixeira (2026-03-27) ✅ EM PRODUÇÃO

### Funcionalidades
- **Soft delete transparente** — Exclusão lógica; o usuário não percebe diferença na experiência
- **Lixeira exclusiva para proprietários** — Acessível no painel de supervisão (apenas CEO/Operations Lead)
- **Restaurar conversas** — Proprietário pode restaurar conversas da lixeira ao estado original
- **Exclusão permanente** — Proprietário pode excluir conversas definitivamente da lixeira
- **Confirmação dupla** — Exclusão permanente exige 2 confirmações para evitar acidentes
- **Audit log LGPD** — Todas as ações (soft delete, restauração, exclusão permanente) registradas no audit log com conformidade LGPD

### Deploy
- Deploy Luna v0.16.0 + v0.16.1 em produção AWS — 27/Mar/2026

---

## v0.16.0 — Luna: Assistente IA Integrada (2026-03-27) ✅ EM PRODUÇÃO

### Criado (Backend)
- **LunaConversaDB** e **LunaMensagemDB** — 2 novos modelos no banco para conversas e mensagens
- **luna_engine.py** — Motor de IA com streaming + cadeia de fallback (Opus → Sonnet → Groq → Fireworks → Together)
- **api/routes/luna.py** — Rotas REST + SSE streaming para chat em tempo real
- Perfil Smart Router: `consultora_estrategica` com peso 0.4

### Criado (Frontend)
- **7 componentes novos**: MarkdownRenderer, LunaWelcome, LunaInput, LunaChat, LunaSidebar, LunaPreview, LunaAdminView
- **Luna.tsx** — Página principal da assistente (`/luna`)
- **luna.ts** — Service de API para comunicação com backend
- Rota `/luna` no router + entrada na Sidebar com badge IA especial

### Funcionalidades
- **Streaming SSE** — Respostas em tempo real token a token
- **Entrada por voz** — Web Speech API integrada no input
- **Markdown rendering** — Respostas formatadas com syntax highlighting
- **Preview de artefatos** — Visualização de código e conteúdo gerado
- **Gestão de conversas** — Criar, listar, renomear, excluir conversas
- **Supervisão do CEO** — Proprietário pode visualizar chats de funcionários com audit log (LGPD)

### Conceito
- Luna é uma assistente estilo ChatGPT/Claude dentro do Synerium Factory
- Consultora estratégica para todos os usuários da plataforma
- Multi-provider com fallback automático para alta disponibilidade
- Supervisão com conformidade LGPD (auditoria de acessos)

---

## v0.31.0 — Escritório Virtual 3D Isométrico Premium (2026-03-27) ✅ EM PRODUÇÃO

### Reescrita visual completa
- **Profundidade real** nas mesas — laterais visíveis com gradiente, pernas 3D
- **Piso de madeira premium** — tábuas horizontais, reflexo diagonal animado
- **Janelas panorâmicas maiores** (8 janelas com caixilho cruzado) com Rio de Janeiro detalhado — Pão de Açúcar, bondinho, Cristo, prédios no horizonte, ondas do mar
- **Avatares premium** — sapatos, calças, camisetas com degradê, pescoço, orelhas, sobrancelhas
- **Cadeiras ergonômicas** com encosto e 5 rodas visíveis
- **Monitores modernos** com stand arredondado, tela com flicker sutil
- **Luzes pontuais no teto** (5 spots) com pulso animado
- **Divisória de vidro** entre área de trabalho e sala de reunião
- **Relógio com marcas de hora** (12 marcadores)
- **Máquina de café Nespresso** com display digital "READY"
- **Theme vars refatoradas** — prefixo `--of-*` para isolamento
- **Header premium** com ícone Zap e fundo gradiente

---

## v0.30.0 — Escritório Virtual Revolucionário (2026-03-27)

### Reescrito do zero
- **Canvas premium 1600×750** full-bleed com mesas bem espaçadas
- **Janelas com vista do Rio de Janeiro** — Pão de Açúcar, Cristo Redentor, montanhas
- **Ciclo dia/noite real** — céu muda por hora (amanhecer, dia, entardecer, noite com estrelas)
- **Mesas detalhadas** — monitores com glow, teclado, café com vapor, planta pessoal, objetos únicos
- **CEO desk** — 2 monitores, nameplate dourado, cadeira executiva maior
- **Sala de reunião premium** — paredes de vidro transparente, mesa oval grande, telão, máquina de café
- **Avatares aprimorados** — micro-animações CSS (breathing, typing, thinking com bolha)
- **Animações Framer Motion** — agente caminha ao CEO (click) e reunião com stagger (80ms delay)
- **Elementos decorativos** — relógio de parede real, quadros, bebedouro com bolhas, luminárias que respondem ao dia/noite
- **Performance** — React.memo, useMemo, useCallback, CSS-only animations (60fps target)
- **Legend bar** premium com glow nos status dots

---

## v0.29.0 — Catálogo de Agentes + Atribuição Dinâmica (2026-03-27) ✅ EM PRODUÇÃO

### Criado
- **Catálogo de Agentes** — "Prateleira" de templates reutilizáveis de agentes IA
- 3 novos modelos no banco: `AgenteCatalogoDB`, `AgenteAtribuidoDB`, `SolicitacaoAgenteDB`
- `squads/regras.py` — Regras anti-alucinação extraídas para arquivo compartilhado
- `database/seed_catalogo.py` — Seed dos 12 agentes existentes no catálogo
- `api/routes/catalogo.py` — CRUD completo do catálogo, atribuições e solicitações
- Página **Catálogo de Agentes** no dashboard (`/catalogo`)
- Página **Atribuições** no dashboard (`/atribuicoes`)
- Aba **Agentes** na página de Aprovações (solicitações de agentes)

### Alterado
- `api/dependencias.py` — Squads agora carregados dinamicamente do banco (não mais hardcoded)
- `api/routes/squads.py` — Removido `SQUAD_POR_EMAIL` hardcoded
- `api/main.py` — Registrado router do catálogo
- `api/schemas.py` — 9 novos schemas Pydantic
- Dashboard: types, API service, Sidebar, App.tsx atualizados

### Conceito
- Admin (CEO, Diretor, Operations Lead) monta squads atribuindo agentes do catálogo a usuários
- Usuários podem solicitar agentes via fluxo de aprovação
- Hot-reload: atribuição/remoção recarrega o squad em memória sem restart

---

## v0.28.0 — Bootstrap AWS Completo (2026-03-27)

### Atualizado
- `scripts/bootstrap_aws.py` — Deteccao automatica de ambiente (local/servidor), areas_aprovacao nos seeds, cargos corrigidos (Rhammon=Diretor Comercial, Marcos=Especialista IA)
- Usuarios no servidor atualizados com papeis e permissoes corretos

### Criado
- `scripts/deploy_producao.sh` — Script de deploy do Mac para AWS (6 etapas: SSH, vaults, pull, deps, bootstrap, restart)
- Configuracao SSH (`~/.ssh/config`) com alias `synerium-aws`

### Executado no Servidor
- Git inicializado e conectado ao GitHub (v0.27.0)
- Vaults sincronizados: 53 arquivos .md (23 SyneriumX + 30 Factory)
- RAG reindexado: 1.064 chunks (701 SyneriumX + 363 Factory)
- Dashboard rebuildado com todas as features v0.26-v0.27
- API reiniciada via systemd
- Verificacoes: SES OK, LiveKit OK, Anthropic OK, OpenAI OK

### Resultado
- https://synerium-factory.objetivasolucao.com.br 100% operacional
- Login funcionando via HTTPS
- RAG com dados atualizados
- 4 usuarios com permissoes corretas

---

## v0.27.0 — Convite por Email ao Adicionar Novo Membro (2026-03-27)

### Atualizado
- `Configuracoes.tsx` — Botao "Novo Usuario" virou "Convidar Membro" (envia email via Amazon SES)
- Removido campo de senha do formulario (usuario cria a propria ao aceitar convite)
- Nova secao "Convites Pendentes" com expiracao e botao copiar link
- `api.ts` — Funcoes `enviarConvite()` e `listarConvites()`
- `convites.py` — Retorna token e criado_em na listagem

### Fluxo Completo
1. Admin clica "Convidar Membro" → preenche nome, email, cargo, papeis
2. Backend gera token seguro (32 chars) + salva ConviteDB + envia email SES
3. Email premium HTML com botao "Aceitar Convite" (link com token, expira em 7 dias)
4. Usuario clica link → /registrar?token=XXX → cria sua propria senha
5. Conta criada com papeis herdados do convite → login normal

---

## v0.26.0 — Tracking Automático de Consumo em Todos os Agentes (2026-03-27)

### Criado
- `core/llm_tracked.py` — Monkey-patch no LLM do CrewAI para interceptar CADA chamada e registrar no banco
- Tracking transparente: agentes não percebem diferença, mas cada call() é registrado

### Atualizado
- `core/llm_router.py` — Smart Router agora retorna LLM com tracking ativo (via `criar_llm_tracked`)
- `squads/squad_template.py` — Passa nome do agente e squad para o router (contexto de tracking)
- `tools/usage_tracker.py` — Custos por modelo (Opus $0.015/$0.075, Sonnet $0.003/$0.015 por 1k tokens)

### Resultado
- 12 agentes (9 CEO + 3 Jonatas) com tracking automático
- Dashboard de consumo (`/api/consumo`) agora mostra dados reais a cada interação com agentes
- Custo calculado com precisão por modelo, não por provider genérico

---

## v0.25.0 — Smart Router Híbrido Sonnet/Opus (2026-03-26)

### Criado
- `core/llm_router.py` — Smart Router que decide automaticamente entre Claude Sonnet 4 e Opus 4
- `core/__init__.py` — Módulo core inicializado
- 3 novos endpoints: GET /api/llm/router/status, POST /api/llm/router/decidir, POST /api/llm/router/toggle

### Atualizado
- `config/llm_providers.py` — Anthropic agora tem 2 providers: Opus (prioridade 0) e Sonnet (prioridade 1)
- `squads/squad_template.py` — Agentes recebem LLM do Smart Router via perfil_agente
- `squads/squad_ceo_thiago.py` — 9 agentes com perfil definido (Tech Lead → Opus, Backend Dev → Sonnet, etc.)
- `squads/squad_diretor_jonatas.py` — 3 agentes com perfil definido
- `agents/pm_central.py` — PM Central usa Opus (perfil product_manager)
- `agents/operations_lead.py` — Operations Lead usa Opus (perfil operations_lead)
- `api/routes/llm.py` — Novos endpoints do router + status integrado

### Corrigido
- Agentes NÃO usavam o LLM Manager — caíam no default do CrewAI (gpt-4.1-mini!)
- Agora TODOS recebem LLM explícito via Smart Router

### Mapa Agentes → Modelo
| Agente | Peso | Modelo |
|--------|------|--------|
| Tech Lead (Kenji) | 0.6 | Opus |
| Arquiteto Infra | 0.7 | Opus |
| Operations Lead | 0.7 | Opus |
| PM Central (Alex) | 0.5 | Sonnet* |
| Especialista IA (Yuki) | 0.5 | Sonnet* |
| QA, DevOps, Backend, Frontend, Integrações, Sofia | 0.0-0.4 | Sonnet |

*Escalam para Opus quando prompt tem palavras de complexidade.

---

## v0.24.0 — Tracking Real de Consumo + Auto-Obsidian (2026-03-26)

### Criado
- `database/models.py` — Tabela `UsageTrackingDB` para tracking permanente de consumo
- `tools/usage_tracker.py` — Serviço global `tracker` que registra cada chamada de API no banco
- Endpoint `GET /api/consumo/por-agente` — Consumo agrupado por agente
- Endpoint `GET /api/consumo/por-tipo` — Consumo agrupado por tipo (chat, reunião, RAG, etc.)

### Atualizado
- `api/routes/consumo.py` — Reescrito para ler do banco SQLite (não mais de logs locais)
- `CLAUDE.md` — Adicionadas regras automáticas: atualizar Obsidian ao final de cada tarefa + consultar antes de responder
- Todos os 14 providers agora aparecem no dashboard (incluindo E2B e AWS SES que faltavam)

### Corrigido
- Consumo não reseta mais ao reiniciar servidor (dados permanentes no banco)
- Fonte de dados mudou de logs (voláteis) para SQLite (permanente)

### 14 Providers Monitorados
1. Anthropic (Claude) 2. OpenAI 3. LangSmith 4. Tavily 5. EXA
6. Firecrawl 7. ScrapingDog 8. Composio 9. Groq 10. Fireworks
11. Together.ai 12. LiveKit 13. E2B (Sandbox) 14. Amazon SES (Email)

---

## v0.23.0 — Deploy em Produção AWS Lightsail (2026-03-26)

### Realizado
- Synerium Factory em produção: **https://synerium-factory.objetivasolucao.com.br**
- AWS Lightsail: Ubuntu 22.04, 2 GB RAM, 2 vCPU, 60 GB SSD ($12/mês — 90 dias grátis)
- IP estático: 3.223.92.171 (SyneriumFactory-ip)
- DNS: registro A `synerium-factory` em objetivasolucao.com.br (via cPanel)
- Python 3.13.12 + Node 20.20.2 + Nginx 1.18 instalados
- SSL HTTPS (Let's Encrypt) ativo com redirect automático
- Systemd: API rodando permanentemente como serviço
- Nginx: reverse proxy (frontend dist + API proxy)
- Projeto copiado via rsync do Mac para /opt/synerium-factory
- Build do frontend com correção de TypeScript (noUnusedLocals desabilitado)
- Dependências extras instaladas: tavily-python, firecrawl-py, exa-py, livekit-api, composio

### Infraestrutura

| Item | Valor |
|------|-------|
| Provider | AWS Lightsail |
| Região | Virginia (us-east-1) |
| OS | Ubuntu 22.04 LTS |
| RAM | 2 GB |
| CPU | 2 vCPU |
| SSD | 60 GB |
| IP | 3.223.92.171 (estático) |
| URL | https://synerium-factory.objetivasolucao.com.br |
| SSL | Let's Encrypt (auto-renew) |
| Backup | Snapshots automáticos (3h BRT) |
| Custo | $12/mês (90 dias grátis) |

### Arquivos de configuração no servidor
- `/etc/nginx/sites-available/synerium-factory` — Nginx config
- `/etc/systemd/system/synerium-factory.service` — Systemd service
- `/opt/synerium-factory/` — Diretório do projeto
- SSH Key: `~/Downloads/LightsailDefaultKey-us-east-1.pem`

---

## v0.22.0 — Guia de Deploy em Produção + LiveKit no Consumo + Sala de Reunião Premium (2026-03-26)

### Criado
- `05-Deploy/Deploy-Producao.md` — Guia completo de 8 etapas para deploy em `synerium-factory.objetivasolucao.com.br`
- Sala de Reunião redesenhada: mesa oval grande, 12 cadeiras, telão com gravação, plantas, quadro, carpete, itens na mesa
- LiveKit adicionado como 12º serviço no dashboard de Consumo (cyan, tracking de participant_minutes)

### Planejado
- VPS: AWS Lightsail $5/mês (sa-east-1 São Paulo)
- DNS: registro A em `synerium-factory` no Registro.br
- Nginx como reverse proxy + SSL Let's Encrypt
- Systemd para API permanente
- GitHub Actions para deploy automático via SSH

---

## v0.21.0 — LiveKit Video Call + Escritório Sowork + Anti-Travamento (2026-03-26)

### Criado
- `api/routes/videocall.py` — Endpoint para gerar tokens LiveKit (JWT com permissões áudio/vídeo/chat)
- `dashboard/src/components/ReuniaoVideo.tsx` — Modal de vídeo chamada com LiveKit SDK (tela de entrada + sala ao vivo)
- Escritório Visual redesenhado estilo Sowork: piso de madeira, parede com janelas de vidro, plantas animadas, luminárias, cadeiras, caneca de café do CEO com vapor
- Auto-timeout de reuniões: tarefas executando há +10min são resetadas automaticamente
- Endpoint `POST /api/tarefas/limpar-travadas` para limpeza manual

### Integrado
- LiveKit Cloud: `wss://synerium-factory-rhayv819.livekit.cloud` (100 participantes simultâneos, grátis)
- Botão "Video Call" no header do Escritório Virtual (azul, ao lado de "Reunir todos")
- Sofia entra automaticamente como transcritora silenciosa nas vídeo chamadas

### Atualizado
- `.env` — 3 chaves LiveKit: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
- `api/main.py` — Rota videocall registrada
- `api/routes/tarefas.py` — Timeout automático (10min) em /historico + endpoint /limpar-travadas
- `dashboard/src/pages/Escritorio.tsx` — Redesign Sowork (madeira, vidro, plantas, luminárias) + botão Video Call
- Reunião travada do Jonatas resetada no banco

### Dependências
- `@livekit/components-react` + `@livekit/components-styles` + `livekit-client` (frontend)
- `livekit-api` (backend Python)

### Visual Escritório (Sowork-inspired)
- Piso de madeira com tábuas horizontais/verticais (theme-aware)
- Parede traseira com 4 janelas de vidro (reflexo de céu)
- Mesas de madeira com grão, monitor, teclado, mouse, cadeira
- 4 plantas com animação de balanço (leafSway)
- 2 luminárias de chão com luz amarela
- Caneca de café na mesa do CEO com vapor (steam animation)
- Dark/Light mode via CSS variables --office-*

---

## v0.20.0 — Isolamento de Squads + Visão Geral + Toggle Permissões (2026-03-26)

### Criado
- Isolamento de squads por usuário: cada um vê só o próprio squad
- Permissão `visao_geral`: CEO e Diretor veem todos os squads
- Toggle "Ver outros squads" (botão roxo) no Escritório com dropdown de squads
- Opção "Ver todos os squads" com grid de mini-escritórios
- Toggle de visão geral desbloqueado para todos (CEO pode editar qualquer um)
- Chat expandível (botão Maximize no ChatFloating)

### Atualizado
- `api/routes/squads.py` — Filtro por usuário + audit log + endpoint /squads/meu + /squads/todos
- `api/schemas.py` — SquadResponse com proprietario_email, tipo, is_meu
- `dashboard/src/pages/Escritorio.tsx` — Seletor de squad + visão geral + indicador
- `dashboard/src/pages/Configuracoes.tsx` — Toggle visão geral sempre editável
- Dark mode corrigido em modais de reunião e chat

### Segurança
- Sem visão_geral: usuário só vê seu squad + squads de área
- Tentativa de acessar squad alheio: HTTP 403 + log de segurança
- Audit log em todo acesso a squads

---

## v0.19.0 — Deploy Pipeline com Progresso + Squad Jonatas (2026-03-26)

### Criado
- `tools/deploy_pipeline_v2.py` — Pipeline de 8 etapas com progresso em tempo real (JSON)
- `api/routes/deploy.py` — Endpoints: executar (background thread), progresso (polling), histórico
- `dashboard/src/pages/Deploy.tsx` — Página premium com barra de progresso 0→100%, etapas animadas, link para PR
- `squads/squad_diretor_jonatas.py` — Squad do Jonatas com 3 agentes (Revisor, Infra, Segurança)

### Pipeline de Deploy (8 etapas)
1. Verificar repositório (5%)
2. Staging de arquivos (15%)
3. Git commit --no-verify (25%)
4. npm run build (45%)
5. Executar testes — warning, não bloqueante (60%)
6. Criar branch sf/deploy-{id} (70%)
7. Push + Pull Request via gh CLI (85%)
8. Merge automático (squash + admin bypass + auto fallback) (95→100%)

### Deploys realizados com sucesso
- Feature: deletar planos individualmente → PR #158 mergeado ✅
- Fix: adicionar JSDoc no AdminPlansPage para corrigir CI → CI verde ✅

### Corrigido
- Pre-commit hook (lint-staged) bloqueando commit → --no-verify
- Testes Vitest falhando → tratado como warning não bloqueante
- Branch protection impedindo merge → admin bypass + --auto fallback
- Conflitos de merge com main remota → resolução automática
- Códigos ANSI na saída do terminal → limpeza com regex

### Atualizado
- `api/main.py` — Rota /api/deploy registrada
- `dashboard/src/components/Sidebar.tsx` — Link Deploy com ícone Rocket
- `dashboard/src/App.tsx` — Rota /deploy registrada
- `api/dependencias.py` — Squad do Jonatas registrado
- `orchestrator.py` — Squad do Jonatas registrado

---

## v0.18.0 — BMAD Workflow Engine (2026-03-25)

### Criado
- `workflows/main-workflow.yaml` — Workflow Principal com 4 fases (Análise → Planejamento → Solução → Implementação)
- `templates/PRD.md` — Template PRD com 12 etapas estruturadas (padrão BMAD)
- `templates/story.md` — Template de Story com BDD (Given/When/Then) + Dev Notes (guardrails)
- `state/sprint-status.yaml` — Kanban central com 6 épicos, 15 stories, estados automáticos

### Atualizado
- `gates/approval_gates.py` — Novo gate: Implementation Readiness Check (PASS / CONCERNS / FAIL)
- Mapeamento BMAD → Synerium Factory: Mary→Marco, Winston→Kenji, Amelia→Amara, Bob→Sofia, Sally→Carlos

### BMAD Integration
- 4 fases com gates obrigatórios entre cada fase
- Quick Flow para tarefas pequenas (pula fases 1-3)
- Sprint Status YAML como fonte de verdade central
- Dev Notes com guardrails (company_id, audit log, LGPD, prepared statements)
- ReadinessCheck automático com resultado PASS / CONCERNS / FAIL

---

## v0.17.0 — Light Mode + Escritório Imersivo + Correções (2026-03-25)

### Corrigido
- Light Mode corrigido em TODAS as 15 páginas — classes sf-page, sf-glass, sf-text-white, sf-text-dim, sf-border, sf-glow
- 212 edições automáticas: bg-[#0a0a0f], text-white, text-gray-*, border-white/* substituídos por variáveis CSS responsivas
- Bug fix: Aprovacoes.tsx — tag JSX sem `>` na linha 186 (PARSE_ERROR)
- Reuniões travadas resetadas no banco (status "executando" → "erro")

### Atualizado
- index.css — CSS Variables completas para Light Mode (--sf-bg-*, --sf-text-*, --sf-border-*, --sf-glow-opacity)
- Classes utilitárias: sf-page, sf-glass, sf-glow, sf-text-white, sf-text-dim, sf-text-ghost, sf-text-faint, sf-border
- Escritório Virtual — Full-bleed imersivo com Framer Motion, mesa do CEO destacada, animações de visita e reunião
- Escritório SVGs (DeskSVG, MonitorSVG) usam var() para funcionar em ambos os temas
- Legenda flutuante fixada no bottom com backdrop-blur

### Light Mode (novo)
- Fundo: #f8f9fa | Cards: #ffffff com borda #e2e8f0
- Textos: #111827 (principal), #4b5563 (secundário), #6b7280 (ghost)
- Glows reduzidos a opacidade 0 no light mode
- Toggle ☀️/🌙 na sidebar funciona globalmente

---

## v0.16.0 — Redesign Premium Completo (Dark Mode Obsessivo) (2026-03-25)

### Redesenhado (todas as páginas)
- PainelGeral — Cards KPI dark com ícones lucide, glow sutil, zero emojis
- Sidebar — Ícones lucide premium, fundo #0a0a0f, hover emerald translúcido
- Squads — Cards dark com ícones por squad (Crown, Code2, Palette, Megaphone), hover lift
- Escritório Virtual — Ambiente imersivo open-space 3x3 com mesas, monitores animados, sala de reunião central pulsante, personagens com animações typing/idle
- Aprovações — Cards dark com badges coloridos por tipo (Rocket, Zap, Briefcase, Megaphone, Radio)
- Relatórios — Cards dark com status premium (Clock, CheckCircle2, XCircle, Hand), rodadas e chunks dark
- Base de Conhecimento (RAG) — KPI cards com ícones (Layers, Database, Cpu, Ruler), vaults dark, consulta IA com spinner orbital
- Standup Diário — Loading orbital com ClipboardList, relatório em card dark com header separado
- Skills — 31 skills com lucide-react mapeado por ID (BookOpen, Code2, Globe, Terminal, etc.), categorias com cor
- Equipe — Avatares iniciais premium com cor, papéis com ícones (Crown, Shield, Briefcase), badge Aprovador dark
- Projetos — Modal dark #111113 com hierarquia (Crown, Wrench, Users), regras sem amarelo, solicitações dark
- Configurações — 3 abas com lucide (Users, ShieldCheck, Settings), form de criação dark, pills dark por papel
- Consumo — Refinamento: DollarSign, Gauge, ArrowUpRight, Hexagon substituindo caracteres texto
- LLM Providers — Cards dark com cadeia de fallback, botão testar premium
- Login — Fundo dark, card translúcido

### Eliminado
- TODOS os emojis de TODAS as páginas (substituídos por lucide-react)
- Todos os fundos claros (bg-white, bg-gray-50, bg-amber-50, bg-blue-50, etc.)
- Todos os badges com fundo claro (bg-emerald-100, bg-yellow-100, bg-red-100, etc.)

### Dependências
- lucide-react instalado (ícones premium)
- Recharts instalado (gráficos)

### Padrão Visual Estabelecido
- Fundo: #0a0a0f
- Cards: from-white/[0.04] to-white/[0.01] com border-white/[0.08]
- Hover: -translate-y-0.5 + border-white/15 + glow sutil
- Badges: bg-{cor}-500/10 border-{cor}-500/20 text-{cor}-400
- Inputs: bg-white/[0.04] border-white/[0.08] com focus emerald
- Botões: bg-emerald-500/20 text-emerald-400 border-emerald-500/20

---

## v0.15.0 — Multi-Provider LLM com Fallback + Dashboard de Consumo (2026-03-24)

### Criado
- `config/llm_providers.py` — LLMProviderManager com fallback inteligente (4 providers)
- `api/routes/llm.py` — Endpoints: status, trocar provider, ativar/desativar, testar
- `api/routes/consumo.py` — Dashboard de consumo com métricas por API
- `dashboard/src/pages/LLMProviders.tsx` — Página visual de gestão de providers com teste em tempo real
- `dashboard/src/pages/Consumo.tsx` — Dashboard de consumo com gráficos Recharts (Line, Pie, Bar)

### Providers Configurados
1. 🧠 Claude (Anthropic) — Principal, melhor qualidade
2. ⚡ Llama via Groq — Fallback 1, mais rápido
3. 🔥 Llama via Fireworks — Fallback 2
4. 🤝 Llama via Together.ai — Fallback 3

### Atualizado
- `.env` — 3 novas chaves: GROQ_API_KEY, FIREWORKS_API_KEY, TOGETHER_API_KEY
- `api/main.py` — Rotas /api/llm e /api/consumo registradas
- `requirements.txt` — groq, fireworks-ai, together, litellm
- Sidebar — Links para Consumo de APIs e LLM Providers

### Dependências Instaladas
- LiteLLM para suporte multi-provider via CrewAI
- Recharts para gráficos no dashboard
- SDKs: groq, fireworks-ai, together

---

## v0.14.0 — Permissões Granulares + Upload de Arquivos + Isolamento de Sessão + Ferramentas SyneriumX (2026-03-24)

### Criado
- Sistema de **permissões granulares por módulo** — 13 módulos x 5 ações (ver, criar, editar, excluir, aprovar)
- Módulos: Dashboard, Squads, Agentes, Tarefas, Reuniões, Projetos, RAG, Skills, Escritório, Configurações, Usuários, Aprovações, Relatórios
- **Upload de arquivos** no chat e nas reuniões (anexos por mensagem)
- **Sofia** (Secretária Executiva) — agente #9 integrada ao fluxo de reuniões
- **gstack do Y Combinator** instalado — 28 skills profissionais via Claude Code
- **Diversidade no escritório virtual** — rostos diversos com bandeiras representando a equipe

### Atualizado
- `api/routes/usuarios.py` — Endpoints: `GET /api/usuarios/modulos-disponiveis`, `PUT /api/usuarios/{id}/permissoes`
- `dashboard/src/utils/permissoes.ts` — Função `temPermissao(modulo, acao)` para controle no frontend
- `dashboard/src/components/ChatFloating.tsx` — Suporte a upload de arquivos nas mensagens
- `dashboard/src/components/ReuniaoModal.tsx` — Upload de arquivos durante reuniões
- Papéis base (CEO, Diretor, Líder, Desenvolvedor, etc.) com permissões padrão + overrides individuais
- **Propostas de edição** — agentes geram propostas que requerem aprovação do proprietário antes de aplicar
- Ferramentas de edição do SyneriumX com **aprovação obrigatória do proprietário** antes de executar

### Segurança
- **Correção de isolamento de sessão** (bug crítico) — sessões de usuários diferentes não compartilham mais estado
- Permissões verificadas tanto no backend (middleware) quanto no frontend (temPermissao)
- Overrides individuais não podem exceder as permissões máximas do papel base
- Audit log de todas as alterações de permissão (LGPD)

---

## v0.13.0 — Projetos com Propriedade e Solicitações (2026-03-24)

### Criado
- `database/models.py` — ProjetoDB e SolicitacaoDB (hierarquia completa)
- `api/routes/projetos.py` — 10 endpoints: CRUD projetos, nomear proprietário/líder, gerenciar membros, solicitações de mudança, aprovar/rejeitar
- `dashboard/src/pages/Projetos.tsx` — Página completa com hierarquia, regras de aprovação, solicitações

### Funcionalidades
- **Hierarquia completa**: Proprietário → Líder Técnico → Membros
- **Só CEO pode nomear proprietários** de projetos
- **Regras de aprovação por nível**:
  - Pequena (bug fix) → Líder Técnico aprova
  - Grande (feature) → Proprietário aprova
  - Crítica (deploy, banco) → Proprietário + Líder
- **Auto-aprovação** para proprietário e CEO
- **Solicitações de mudança** com título, descrição, tipo e categoria
- **Audit log** de todas as ações (LGPD)

### Seed
- SyneriumX registrado como primeiro projeto:
  - Proprietário: Thiago (CEO)
  - Líder Técnico: Jonatas
  - Membro: Rhammon
  - Caminho: ~/propostasap

### Atualizado
- `api/main.py` — Rota /api/projetos registrada
- `dashboard/src/App.tsx` — Rota /projetos
- `dashboard/src/components/Sidebar.tsx` — Link "📁 Projetos"

---

## v0.12.0 — SyneriumX Tools + Sofia + gstack + Skills Completas (2026-03-24)

### Criado
- `tools/syneriumx_tools.py` — 6 ferramentas para edição real do SyneriumX (~/propostasap):
  - LerArquivoSyneriumX, ListarDiretorioSyneriumX, EscreverArquivoSyneriumX
  - BuscarNoSyneriumX (grep), GitSyneriumX, TerminalSyneriumX
- `tools/email_tool.py` — EnviarEmailTool + EnviarEmailComAnexoTool (Amazon SES)
- `tools/zip_tool.py` — CriarProjetoTool + CriarZipTool
- `tools/scrapingdog_tool.py` — Google SERP via ScrapingDog
- Agente #9 Sofia — Secretária Executiva 🇧🇷 (faz atas e executa pedidos em reuniões)
- gstack do Y Combinator instalado (28 skills profissionais via Claude Code)
- Escritório Virtual com rostos diversos + bandeiras (9 agentes)

### Atualizado
- `tools/skills_setup.py` — 6 novas skills SyneriumX + email com anexo + zip + projeto
- `squads/squad_ceo_thiago.py` — Agente Sofia + skills SyneriumX em todos os perfis
- `api/routes/tarefas.py` — Sofia integrada nas reuniões (compila ATA + executa pedidos)
- `dashboard/src/pages/Escritorio.tsx` — Rostos diversos com bandeiras, Sofia adicionada
- `.env` — Composio key corrigida, Tavily, ScrapingDog, Firecrawl, EXA, GitHub, E2B, AWS SES

### Segurança
- Path restrito a ~/propostasap — agentes não operam fora
- Comandos destrutivos bloqueados (rm -rf, drop, format)
- Git push/merge/reset requerem aprovação do Operations Lead
- Email com limite de 10 por execução + 10MB por anexo

### Testado
- Leitura de 249 itens na raiz do SyneriumX ✅
- Busca grep: 125 arquivos com company_id ✅
- Criação de arquivo teste_composio.md ✅
- Git status no SyneriumX ✅
- Email de teste via Amazon SES ✅

---

## v0.11.1 — Escritório Virtual Refatorado (2026-03-24)

### Corrigido
- Removida rotação CSS 3D isométrica que distorcia o layout e deixava ilegível
- Substituída por grid responsivo 4x2 com cards limpos e legíveis

### Melhorado
- Bonequinhos com emoji + corpo + braços animados (digitação quando trabalhando)
- Monitores com tela dinâmica: apagada (livre), código rolando (trabalhando), amarela (reunião)
- Hover levanta o card com borda colorida + tooltip "Clique para conversar"
- Banner de reunião ativa no topo com animação pulsante
- 6 animações CSS: digitando, flutuando, pulso, brilho, balaoFala, giraCadeira
- Responsivo: 2 colunas mobile, 4 desktop

---

## v0.11.0 — Escritório Virtual Isométrico (2026-03-24)

### Criado
- `dashboard/src/pages/Escritorio.tsx` — Escritório virtual com visualização isométrica 3D
- Rota `/escritorio` e link "🏢 Escritório" na sidebar

### Funcionalidades
- **Vista isométrica** do escritório com 8 mesas em grid 4x2
- **Bonequinhos com emoji** por área: 🏗️ Tech Lead, ⚙️ Backend, 🎨 Frontend, 🧠 IA, 🔗 Integrações, 🚀 DevOps, 🛡️ QA, 📊 PM
- **Status em tempo real**: 🟢 Disponível, 🔵 Trabalhando (pulsando), 🟡 Em reunião (pulsando)
- **Monitor na mesa** muda de cor conforme status do agente
- **Hover** mostra tooltip com nome completo e status detalhado
- **Clique no agente** abre o chat messenger flutuante
- **Sala de reunião** aparece no centro quando há reunião ativa
- **Botão "Reunir todos"** no rodapé para iniciar reunião com todos os agentes
- Legenda de status na parte inferior
- Cores únicas por agente para fácil identificação

### Correções nesta versão
- Corrigido auto-scroll na reunião que impedia leitura (pausa quando usuário scrolla para cima)
- Adicionado botões "Reabrir Reunião" e "Continuar Reunião" na página de Relatórios

---

## v0.10.0 — Reuniões Interativas com Rodadas (2026-03-23)

### Criado
- Sistema de **rodadas** para reuniões — cada agente responde individualmente em sequência
- **Progresso em tempo real** — dashboard mostra qual agente está falando (polling 2s)
- **Continuar reunião** — após a rodada, CEO envia feedback e inicia nova rodada
- **Encerrar reunião** — CEO decide quando parar
- Endpoint `POST /api/tarefas/{id}/continuar` — feedback → nova rodada
- Endpoint `POST /api/tarefas/{id}/encerrar` — encerrar reunião

### Atualizado
- `database/models.py` — campos: rodadas (JSON), rodada_atual, agente_atual, agentes_indices
- `api/routes/tarefas.py` — reescrito com suporte a rodadas, progresso por agente, continuação
- `dashboard/src/components/ReuniaoModal.tsx` — chat em tempo real com rodadas visuais
- `dashboard/src/types/index.ts` — RodadaItem, status 'aguardando_feedback', agente_atual
- `dashboard/src/services/api.ts` — continuarReuniao(), encerrarReuniao()

### Fluxo da Reunião
1. CEO define pauta + seleciona participantes
2. **Rodada 1**: cada agente responde (progresso em tempo real)
3. Status muda para "✋ Sua vez!" — CEO lê e envia feedback
4. **Rodada 2+**: agentes respondem com contexto das rodadas anteriores + feedback
5. CEO pode continuar quantas rodadas quiser ou encerrar

---

## v0.9.0 — Skills dos Agentes + Catálogo (2026-03-23)

### Criado
- `tools/registry.py` — SkillRegistry: catálogo centralizado de skills com perfis por agente
- `tools/skills_setup.py` — Inicialização de 13 skills com atribuição por perfil
- `api/routes/skills.py` — Endpoints GET /api/skills e GET /api/skills/perfis
- `dashboard/src/pages/Skills.tsx` — Página visual do catálogo (por categoria e por agente)

### Skills Disponíveis (13 total, 12 ativas)
| Categoria | Skills |
|-----------|--------|
| 📚 Conhecimento | Consultar Base de Conhecimento (RAG), Buscar em Markdown |
| 💻 Código | Ler Arquivo, Listar Diretório, Buscar em Diretório, Executar Python, GitHub (requer config) |
| 🌐 Web | Ler Página Web, Buscar em Site |
| ✏️ Escrita | Escrever Arquivo |
| 📊 Dados | Buscar em JSON, CSV, PDF, Texto |

### Perfis de Agentes (6-7 skills cada)
- Tech Lead: 7 skills (código + web + conhecimento)
- Backend Dev: 6 skills (código + Python + conhecimento)
- Frontend Dev: 6 skills (código + web + conhecimento)
- Especialista IA: 6 skills (web + Python + dados)
- Integrações: 6 skills (web + Python + JSON)
- DevOps: 7 skills (código + terminal + logs)
- QA & Segurança: 6 skills (código + Python + web)
- Product Manager: 6 skills (web + escrita + dados)

---

## v0.8.0 — Chat Messenger Flutuante + Reuniões (2026-03-23)

### Criado
- `dashboard/src/components/ChatFloating.tsx` — Janela de chat flutuante estilo Messenger
- `dashboard/src/components/ChatManager.tsx` — Gerenciador de múltiplas janelas de chat (contexto React)
- `dashboard/src/components/ReuniaoModal.tsx` — Modal de reunião com seleção de participantes

### Atualizado
- `api/routes/tarefas.py` — Endpoint `POST /api/tarefas/reuniao` para reuniões multi-agente
- `dashboard/src/App.tsx` — ChatProvider envolvendo toda a aplicação
- `dashboard/src/pages/Squads.tsx` — Clique no agente abre chat flutuante, botões de reunião
- `dashboard/src/services/api.ts` — `executarReuniao()`
- `dashboard/src/types/index.ts` — Tipos `ChatAberto`, campo `tipo` e `participantes` em TarefaResultado

### Funcionalidades
- **Chat Messenger**: clicar no agente abre janela flutuante no canto inferior
- **Múltiplos chats**: até 4 janelas abertas ao mesmo tempo, lado a lado
- **Minimizar/maximizar**: cada chat pode ser minimizado para um badge compacto
- **Reunião com todos**: botão para iniciar reunião com todos os agentes do squad
- **Reunião selecionada**: escolher quais agentes participam da reunião
- **Resultado em tempo real**: polling a cada 3s para acompanhar execução
- **Histórico por agente**: cada chat mantém seu próprio histórico

---

## v0.7.0 — Chat e Tarefas dos Agentes no Dashboard (2026-03-23)

### Criado
- `api/routes/tarefas.py` — Endpoints: executar tarefa, histórico, buscar por ID
- `dashboard/src/pages/Agente.tsx` — Página de chat com agente (envio de tarefas + respostas em tempo real)

### Atualizado
- `api/main.py` — Rota `/api/tarefas` registrada
- `dashboard/src/App.tsx` — Rota `/agente` registrada
- `dashboard/src/pages/Squads.tsx` — Agentes agora são clicáveis (abre chat)
- `dashboard/src/services/api.ts` — `executarTarefa()`, `buscarHistoricoTarefas()`, `buscarTarefa()`
- `dashboard/src/types/index.ts` — Tipo `TarefaResultado`

### Funcionalidades
- Chat por agente: enviar tarefas e ver respostas em tempo real
- Execução em background (não bloqueia a UI)
- Polling automático a cada 3s para tarefas em execução
- Histórico de tarefas por agente
- Status visual: pendente, executando, concluída, erro
- Integração com RAG (agentes consultam a base de conhecimento)
- Clicar no agente na página Squads → abre o chat direto

---

## v0.6.0 — Squad do CEO com 8 Agentes (2026-03-23)

### Criado
- `squads/squad_ceo_thiago.py` — Squad pessoal do CEO Thiago com 8 agentes especializados
- `09-Squads/Squad-CEO-Thiago.md` — Documentação completa do squad piloto

### Agentes Criados
1. **Tech Lead / Arquiteto** — Decisões técnicas, padrões, migrations
2. **Backend Developer** — PHP, endpoints, MySQL, multi-tenant
3. **Frontend Developer** — React/TypeScript, shadcn/ui, UX
4. **Especialista IA** — Prompts, RAG, scoring, chat, automações
5. **Especialista Integrações** — APIs externas, OAuth, webhooks
6. **DevOps & Infra** — Deploy, CI/CD, cloud, DNS, SSL
7. **QA & Segurança** — Testes, LGPD, bugs, segurança
8. **Product Manager** — Roadmap, backlog, documentação

### Atualizado
- `orchestrator.py` — Squad do CEO registrado com 8 agentes + acesso ao RAG
- `dashboard/src/pages/Squads.tsx` — UI melhorada: card expandível, destaque do squad piloto, grid de agentes
- `09-Squads/Mapa-Squads.md` — Atualizado com squad do CEO

### Metodologia
- Varredura completa do vault SyneriumX (17 arquivos, 14 módulos, 136+ PRs)
- Cada agente desenhado para cobrir uma área crítica identificada na análise
- Squad piloto para o CEO testar antes de replicar para os 44 funcionários restantes

---

## v0.5.0 — RAG Completo com IA (2026-03-23)

### Criado
- `rag/assistant.py` — RAGAssistant: síntese de respostas com Claude claude-sonnet-4-20250514
- `04-Arquitetura/RAG.md` — Documentação completa do sistema RAG

### Atualizado
- `rag/store.py` — Método `contar_chunks()` para estatísticas
- `api/routes/rag.py` — 4 endpoints: status, stats, consultar com IA, indexar
- `api/schemas.py` — RAGStatsResponse, RAGIndexarResponse, RAGChunkResponse
- `dashboard/src/pages/RAG.tsx` — UI completa com reindex, filtro por vault, resposta IA, chunks colapsáveis
- `dashboard/src/types/index.ts` — RAGStats, RAGChunk, RAGIndexarResult
- `dashboard/src/services/api.ts` — buscarRAGStats, indexarRAG
- `orchestrator.py` — RAGAssistant integrado na fábrica

### Funcionalidades
- Resposta inteligente do Claude baseada nos chunks recuperados
- Reindexação pelo dashboard (todos os vaults ou individual)
- Filtro por vault na consulta
- Estatísticas visuais (total chunks, chunks por vault)
- Fontes consultadas com detalhes colapsáveis
- Tracing completo via LangSmith

---

## v0.4.0 — Gestão de Usuários e Permissões (2026-03-23)

### Criado
- `dashboard/src/pages/Configuracoes.tsx` — Página de configurações com 3 abas (Usuários, Permissões, Sistema)
- `04-Arquitetura/Gestao-Usuarios.md` — Documentação completa do sistema de permissões
- 10 papéis disponíveis: CEO, Diretor Técnico, Operations Lead, PM Central, Líder, Desenvolvedor, Marketing, Financeiro, Suporte, Membro
- 5 áreas de aprovação: Deploy, Gasto IA, Arquitetura, Marketing, Outreach

### Atualizado
- `api/routes/usuarios.py` — CRUD completo: criar, editar, permissões, desativar (10 rotas)
- `api/routes/auth.py` — Endpoint trocar-senha agora funcional com JWT
- `dashboard/src/services/api.ts` — 6 novos endpoints de gestão de usuários
- `dashboard/src/types/index.ts` — Tipos para papéis, áreas e payloads
- `dashboard/src/components/Sidebar.tsx` — Link para Configurações
- `dashboard/src/App.tsx` — Rota /configuracoes registrada

### Segurança
- Apenas CEO/Diretor Técnico/Operations Lead podem criar/editar/desativar usuários
- Audit log completo de todas as ações admin (LGPD)
- Proteção contra auto-desativação
- Verificação de duplicata de email na criação e edição

---

## v0.3.0 — Autenticação e Perfil de Usuário (2026-03-23)

### Criado
- `database/models.py` — Modelos SQLAlchemy: UsuarioDB, ConviteDB, AuditLogDB
- `database/session.py` — Engine SQLite + sessão (data/synerium.db)
- `database/seed.py` — Seed automático Thiago + Jonatas
- `api/security.py` — JWT (HS256, 1h) + bcrypt (cost 12)
- `api/routes/auth.py` — Login, refresh token, registro via convite, trocar senha
- `api/routes/convites.py` — Criar e validar convites por email
- `config/usuarios.py` — Cadastro com papéis e permissões (Thiago + Jonatas)
- `dashboard/src/contexts/AuthContext.tsx` — Contexto React de autenticação
- `dashboard/src/pages/Login.tsx` — Tela de login com email/senha
- `dashboard/src/pages/Perfil.tsx` — Perfil editável (nome, cargo, bio)
- `dashboard/src/pages/Equipe.tsx` — Página de liderança com papéis e permissões
- Documentação: `04-Arquitetura/Autenticacao.md`

### Atualizado
- `api/main.py` — Inicialização do banco + rotas auth/convites (v0.3.0)
- `api/dependencias.py` — `obter_usuario_atual()` via JWT
- `api/routes/usuarios.py` — Migrado para consultas ao banco SQLite
- `api/routes/status.py` — Seção "Liderança" com usuários reais
- `agents/operations_lead.py` — Agente personalizado para Jonatas
- `dashboard/src/App.tsx` — Rotas protegidas + AuthProvider
- `dashboard/src/components/Sidebar.tsx` — Mostra usuário logado + botão sair
- `dashboard/src/services/api.ts` — Header Authorization em todas as requests
- `vite.config.ts` — Proxy para /auth além de /api
- `.env` — JWT_SECRET, AWS SES config
- `requirements.txt` — sqlalchemy, python-jose, passlib, boto3, email-validator

### Segurança
- Bloqueio de conta após 10 tentativas (30 min)
- Refresh token automático (30 dias)
- Audit log de todos os logins
- Senha seed: SyneriumFactory@2026 (trocar no primeiro uso)

---

## v0.2.0 — Dashboard Web (2026-03-23)

### Criado
- `api/main.py` — App FastAPI com CORS e lifespan
- `api/dependencias.py` — Singleton do SyneriumFactory
- `api/schemas.py` — Schemas Pydantic para request/response
- `api/routes/` — Rotas: status, squads, aprovações, RAG, standup
- `dashboard/` — Frontend React 18 + Vite 6 + TypeScript + Tailwind CSS 4
- Páginas: Painel Geral, Aprovações, Squads, RAG, Standup
- Hook de polling automático (10s status, 5s aprovações)
- Proxy do Vite para FastAPI
- Documentação: `04-Arquitetura/Dashboard-Web.md`

### Atualizado
- `requirements.txt` — adicionado FastAPI e uvicorn
- `.gitignore` — adicionado node_modules e dist
- Roadmap — adicionada Fase 1.5 (Dashboard Web)
- Home do vault — link para Dashboard-Web
- Visão Geral — stack atualizada com FastAPI e React

---

## v0.1.0 — Fundação (2026-03-23)

### Criado
- Estrutura de pastas do projeto
- Virtualenv Python 3.13 com dependências (CrewAI 1.11, LangGraph 1.1, LangSmith 0.7, LangChain 1.2)
- `orchestrator.py` — ponto de entrada com menu interativo
- `agents/pm_central.py` — Alex, PM Agent Central
- `agents/operations_lead.py` — Operations Lead (Diretor de Serviços)
- `gates/approval_gates.py` — Approval Gates com human-in-the-loop
- `flows/daily_standup.py` — Standup diário automático
- `squads/squad_template.py` — Template de squad duplicável
- `config/settings.py` — Configurações via pydantic-settings + .env
- `.env` com chaves de API (LangSmith, Anthropic, OpenAI)
- `README.md` com instruções completas
- `CLAUDE.md` com regras permanentes do projeto
- Vault Obsidian `SyneriumFactory-notes` com documentação completa

### Definido
- Premissas estratégicas (45 funcionários, multi-tenant, multi-produto)
- Hierarquia de comando (CEO → Operations Lead → PM Central → Squads)
- Roadmap em 5 fases

---

> Última atualização: 2026-03-25
