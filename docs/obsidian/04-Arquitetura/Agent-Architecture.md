# Agent Architecture — Synerium Factory

> Arquitetura de agentes avançados: fork subagent, tool registry, worktree isolation, e modo brief.

**Fase:** 2.2 | **Versão:** v0.59.2 | **Última atualização:** 03/Abr/2026

---

## Visão Geral

A arquitetura de agentes do Synerium Factory é inspirada em sistemas de orquestração avançada de IA, com foco em:

1. **Fork Subagent** — spawning implícito com herança de contexto
2. **Tool Registry** — registro centralizado de ferramentas com ciclo de vida completo
3. **Worktree Isolation** — isolamento via git worktree para agentes forked
4. **Brief Mode** — modo onde toda output deve passar por uma ferramenta de apresentação
5. **Multi-Agent Coordination** — spawning de agentes nomeados em equipes

---

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT ORCHESTRATION LAYER                         │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │  AgentRegistry  │    │   ForkManager    │    │   ToolRegistry      │   │
│  │  (singleton)    │    │                  │    │   (singleton)       │   │
│  │                 │    │ • isForkEnabled  │    │                     │   │
│  │  • register()   │    │ • buildForked()  │    │  • register_tool()  │   │
│  │  • get()        │    │ • worktree_     │    │  • get_tool()      │   │
│  │  • list_active()│    │   notice()      │    │  • list_tools()    │   │
│  └────────┬────────┘    └────────┬─────────┘    └──────────┬──────────┘   │
│           │                    │                         │               │
│           ▼                    ▼                         ▼               │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     AgentSpawner                                  │     │
│  │  • spawn(params) → AgentResult                                   │     │
│  │  • spawn_fork(params, parent_ctx) → AgentResult                 │     │
│  │  • spawn_team(params, team_name) → list[AgentResult]            │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT EXECUTION LAYER                              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │ General Purpose │    │   Tech Lead     │    │   Backend Dev       │   │
│  │   (Fork Child) │    │   (built-in)    │    │   (built-in)        │   │
│  │                 │    │                 │    │                     │   │
│  │ • Inherits ctx  │    │ • Planning      │    │ • PHP/Python code   │   │
│  │ • Directive-   │    │ • Architecture  │    │ • APIs REST         │   │
│  │   based        │    │ • Code review   │    │ • Migrations       │   │
│  └─────────────────┘    └──────────────────┘    └─────────────────────┘   │
│                                                                             │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │ Frontend Dev   │    │   QA Engineer   │    │   (extensible)       │   │
│  │   (built-in)   │    │   (built-in)    │    │                     │   │
│  │                 │    │                 │    │  Add new agents     │   │
│  │ • React/TS     │    │ • Test design   │    │  via AgentRegistry  │   │
│  │ • Components   │    │ • Test impl     │    │  .register()        │   │
│  │ • Performance  │    │ • QA gates     │    │                     │   │
│  └─────────────────┘    └──────────────────┘    └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKTREE ISOLATION LAYER                            │
│                                                                             │
│    Parent Agent (main)          Fork Child (worktree)                       │
│    ───────────────────          ────────────────────                         │
│    /opt/synerium-factory       /opt/synerium-factory/.worktrees/agent-abc │
│                                                                             │
│    • Has tools: Bash, Read,   • Same repo, isolated copy                  │
│      Write, Edit, etc.        • Can modify without affecting parent         │
│    • Commit changes            • Must commit before reporting                │
│    • System prompt inherited    • Directive: execute directly, no spawn        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Fork Subagent

### Conceito

Fork subagent é um mecanismo onde, quando `agent_type` é omitido no spawn, o sistema cria automaticamente um "child" que herda:

1. **Contexto completo da conversa** — todas as mensagens do parent
2. **System prompt do parent** — para prompt cache byte-exact
3. **Pool de ferramentas** — mesmas tools do parent

### Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Prompt Cache** | Fork children usam placeholder idêntico nos `tool_result` para API request prefixes byte-identical → cache hits maximized |
| **Contexto Completo** | Child tem acesso a todo o histórico da conversa sem precisar re-enviar |
| **Isolamento** | Pode rodar em worktree isolado, modificando arquivos sem afetar o parent |
| **Performance** | Não precisa recarregar contexto a cada spawn |

### Fluxo de Fork

```
1. Parent Agent decide "preciso fazer algo em paralelo"
2. Chama Agent(tool) SEM agent_type
3. ForkManager detecta fork path:
   a. Verifica recursive guard (FORK_BOILERPLATE_TAG)
   b. Constrói mensagens forkadas (placeholder results)
   c. Se isolation=worktree: cria git worktree
   d. Adiciona worktree notice se aplicável
4. Spawn em background
5. Parent recebe AgentResult com agent_id
6. Quando child completa: notificação via <task-notification>
```

### Worktree Isolation

Cada fork child pode rodar em um git worktree isolado:

```python
# Criar worktree para isolamento
slug = f"agent-{agent_id[:8]}"
worktree_path = await create_agent_worktree(slug)

# Child recebe notice para traduzir paths
notice = buildWorktreeNotice(
    parent_cwd="/opt/synerium-factory",
    worktree_cwd="/opt/synerium-factory/.worktrees/agent-abc"
)
```

---

## 2. Tool Registry

### Interface Tool

```python
class Tool(Generic[InputT, OutputT]):
    """Interface completa de ferramenta."""
    
    # Identificação
    name: str
    aliases: list[str]  # Nomes alternativos para compatibilidade
    description: str
    
    # Schema
    input_schema: type[InputT]
    max_result_size_chars: int
    
    # Estado
    def is_enabled() -> bool: ...
    def is_concurrency_safe(input: InputT) -> bool: ...
    def is_read_only(input: InputT) -> bool: ...
    def is_destructive(input: InputT) -> bool: ...
    
    # Permissões
    async def check_permissions(
        input: InputT, 
        context: ToolUseContext
    ) -> ToolPermissionResult: ...
    
    # Execução
    async def call(
        input: InputT,
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Message,
        on_progress: Callable | None = None
    ) -> ToolResult[OutputT]: ...
    
    # UI/Hints
    def get_activity_description(input: InputT) -> str | None: ...
    def get_tool_use_summary(input: InputT) -> str | None: ...
```

### buildTool Factory

```python
def build_tool(def: ToolDefinition) -> Tool:
    """
    Factory que constrói Tool completa com defaults.
    
    Defaults (fail-closed onde importa):
    - isEnabled → True
    - isConcurrencySafe → False
    - isReadOnly → False  
    - isDestructive → False
    - checkPermissions → allow
    """
    return ToolDefinition(
        is_enabled=lambda: True,
        is_concurrency_safe=lambda _: False,
        is_read_only=lambda _: False,
        is_destructive=lambda _: False,
        check_permissions=lambda _, __: ToolPermissionResult(behavior=PermissionBehavior.ALLOW),
        **vars(def)
    )
```

### Permission Modes

| Mode | Comportamento |
|------|---------------|
| `default` | Herda do parent |
| `bubble` | Prompts de permissão sobem para o parent |
| `acceptEdits` | Pode editar arquivos sem pedir confirmação |
| `plan` | Requer aprovação de plano antes de executar |

---

## 3. Agent Definitions

### AgentDefinition Dataclass

```python
@dataclass
class AgentDefinition:
    agent_type: str           # Identificador único (ex: "tech_lead")
    name: str                 # Nome de exibição (ex: "Tech Lead / Arquiteto")
    description: str         # Descrição curta
    tools: list[str] | None   # None = todas as tools
    max_turns: int = 50
    model: str | None = None  # None = herdar
    permission_mode: AgentPermissionMode = DEFAULT
    isolation: IsolationMode = NONE
    background: bool = False
    color: str | None = None  # Cor para UI
    required_mcp_servers: list[str] = []
```

### Built-in Agents (12 agentes)

| Agent | Especialidade | Isolation |
|-------|---------------|-----------|
| `general_purpose` | Fork worker — propósito geral | none |
| `tech_lead` | Planejamento, arquitetura, code review | none |
| `backend_dev` | PHP/Python, APIs REST, migrations | worktree |
| `frontend_dev` | React/TypeScript, componentes | worktree |
| `qa_engineer` | Testes, QA gates, validação | none |
| `pm_agent` | Gestão de produto, roadmap | none |
| `devops` | CI/CD, Docker, AWS | worktree |
| `security` | Vulnerabilidades, compliance LGPD | none |
| `integration` | APIs externas, webhooks | none |
| `test_master` | Gestão de testes automatizados | none |
| `github_master` | Repositórios, branches, PRs | none |
| `gitbucket_master` | GitBucket on-premise | none |

---

## 4. Brief Mode

### Conceito

Modo onde toda output visível ao usuário deve passar pela ferramenta `Brief`. Usado para:

- **Kairos Mode**: Output controlada via Brief tool
- **Agent Swarms**: Comunicação entre agentes via Brief
- **Structured Output**: Garantir formatação consistente

### Fluxo

```
1. User ativa brief mode (/brief ou --brief)
2. Sistema injeta system-reminder no próximo turno:
   "Brief mode is now enabled. Use the Brief tool for all 
    user-facing output — plain text outside it is hidden."
3. Agent DEVE usar Brief tool para output visível
4. User desativa com /brief novamente
```

---

## 5. AgentSpawner

### Conceito

`AgentSpawner` é o orchestrator central de spawning de agentes. Direciona cada spawn para o path correto (fork ou named) e gerencia o lifecycle completo.

### Fluxo de Spawn

```
1. spawn(params, context, messages, assistant_msg)
   │
   ├── agent_type == None?  ──→ Fork Path (ForkManager)
   │   ├── is_fork_subagent_enabled() → check feature gate
   │   ├── is_in_fork_child() → recursive guard
   │   ├── build_forked_messages() → placeholder cache
   │   ├── isolation=worktree? → create_worktree()
   │   └── return AgentResult(status="fork", fork_messages=...)
   │
   └── agent_type != None? ──→ Named Agent Path (AgentRegistry)
       ├── registry.get(agent_type) → AgentDefinition
       ├── isolation=worktree? → create_worktree()
       ├── background? → return AgentResult(status="async_launched")
       └── foreground → return AgentResult(status="completed")
```

### Interface

```python
class AgentSpawner:
    """Singleton de spawn de agentes."""

    # Spawn principal — determina fork vs named
    async def spawn(
        params: AgentSpawnParams,
        context: dict | None = None,
        parent_messages: list[dict] | None = None,
        assistant_message: dict | None = None,
        on_progress: Callable[[SpawnProgress], None] | None = None,
    ) -> AgentResult: ...

    # Spawn em background (async_launched)
    async def spawn_background(
        params: AgentSpawnParams,
        context: dict | None = None,
        parent_messages: list[dict] | None = None,
        assistant_message: dict | None = None,
    ) -> AgentResult: ...

    # Lifecycle
    async def complete_spawn(agent_id: str) -> None: ...
    async def cancel_spawn(agent_id: str) -> bool: ...

    # Tracking
    def get_active_spawns() -> list[SpawnProgress]: ...
    def get_spawn(agent_id: str) -> SpawnProgress | None: ...
```

### SpawnProgress

```python
@dataclass
class SpawnProgress:
    agent_id: str
    status: str = "pending"  # pending, running, completed, failed
    message: str | None = None
    percent: float = 0.0
    started_at: datetime | None = None
    ended_at: datetime | None = None
```

---

## 6. Multi-Agent Coordination

### Spawn com Equipe

```python
@dataclass
class AgentSpawnParams:
    prompt: str
    description: str = ""
    agent_type: str | None = None
    name: str | None = None          # Nome para endereçamento
    team_name: str | None = None    # Nome da equipe
    run_in_background: bool = False
    isolation: IsolationMode = NONE
    cwd: str | None = None
```

### Comunicação Entre Agentes

- Agentes nomeados são endereçáveis via `SendMessage({to: name})`
- Equipes têm roster flat (não hierárquico)
- Agentes em worktree isolado podem modificar arquivos sem conflito

---

## Estrutura de Pastas

```
core/agents/
├── __init__.py          # Exports centralizados
├── base.py              # AgentDefinition, AgentSpawnParams, AgentResult, enums
├── registry.py          # AgentRegistry singleton + 12 agentes built-in
├── fork.py              # ForkManager, AutoApproveMode, AutoModeState
├── spawn.py             # AgentSpawner, SpawnProgress
└── lifecycle.py         # AgentLifecycle, LifecycleManager, callbacks

core/tools/
├── __init__.py          # Exports centralizados
├── base.py              # ToolFactory, ToolDefinition, ToolRegistry, ValidationResult
└── brief.py             # BriefTool (SendUserMessage)
```

---

## Benefícios da Arquitetura

| Categoria | Benefício |
|-----------|-----------|
| **Performance** | Prompt cache optimization com byte-identical fork prefixes |
| **Isolamento** | Git worktree para modificar código sem conflito |
| **Flexibilidade** | Registry permite adicionar agentes sem alterar core |
| **Segurança** | Permission modes e recursive fork guard |
| **Observabilidade** | Progress tracking e notificação de completion |
| **Retrocompatibilidade** | Aliases em tools e agentes para migração suave |

---

## Integração com Stack Existente

| Componente | Integração |
|-----------|-----------|
| **FastAPI** | Endpoints em `api/routes/` usam AgentSpawner |
| **Mission Control** | Fork agents para execução paralela de fases |
| **Luna Engine** | Agent spawning via tool call |
| **BMAD** | Agentes como crewAI agents com fork capability |
| **Code Studio** | Tools de edição integradas ao ToolRegistry |

---

## Métricas de Sucesso

- [ ] Fork subagent reduz latência de spawn em >50% (cache hit)
- [ ] Worktree isolation permite execução paralela sem conflitos
- [ ] ToolRegistry suporta 20+ ferramentas sem degradação
- [ ] Brief mode funcional para Kairos-style output

---

## Referências

- [BMAD Workflow](BMAD-Workflow.md)
- [Autonomous Squads](Autonomous-Squads.md)
- [Luna Engine](Luna.md)
- [Code Studio](Code-Studio-Mission-Control.md)
