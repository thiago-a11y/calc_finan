"""
Agente base — definições, parâmetros e resultados.

Contém:
- Enums: AgentPermissionMode, IsolationMode
- Dataclasses: AgentDefinition, AgentSpawnParams, AgentResult

Inspirado em advanced_agent_architecture (TypeScript):
- Fork subagent com herança de contexto
- Worktree isolation para execução paralela
- Permission modes: default, bubble, acceptEdits, plan

Uso:
    from core.agents.base import AgentDefinition, AgentSpawnParams, AgentPermissionMode

    agent = AgentDefinition(
        agent_type="tech_lead",
        name="Tech Lead",
        description="Arquiteto de software e líder técnico",
        tools=["Bash", "Read", "Write"],
        max_turns=50,
        model="sonnet",
        permission_mode=AgentPermissionMode.ACCEPT_EDITS,
    )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# =============================================================================
# Enums
# =============================================================================


class AgentPermissionMode(str, Enum):
    """
    Modo de permissão do agente.

    Define como o agente lida com operações que requerem confirmação:
    - DEFAULT: herda configuração do agente parent
    - BUBBLE: prompts de permissão sobem para o parent decidir
    - ACCEPT_EDITS: pode editar arquivos sem pedir confirmação
    - PLAN: requer aprovação de plano antes de executar ações
    """

    DEFAULT = "default"
    BUBBLE = "bubble"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"


class IsolationMode(str, Enum):
    """
    Modo de isolamento do agente.

    Define como o agente é isolado ao executar:
    - NONE: executa no contexto normal (mesmo processo/working directory)
    - WORKTREE: cria git worktree isolado para modificar código sem conflito
    - REMOTE: executa em ambiente remoto (CCR)
    """

    NONE = "none"
    WORKTREE = "worktree"
    REMOTE = "remote"


# =============================================================================
# Agent Definition
# =============================================================================


@dataclass
class AgentDefinition:
    """
    Definição completa de um tipo de agente.

    Representa um "template" de agente que pode ser instanciado
    via AgentRegistry. Contém metadados, configuração de execução
    e factory para o sistema prompt.

    Equivalente a BuiltInAgentDefinition em loadAgentsDir.ts.

    Args:
        agent_type: Identificador único (ex: "tech_lead", "backend_dev")
        name: Nome de exibição (ex: "Tech Lead / Arquiteto de Software")
        description: Descrição curta da especialidade do agente
        tools: Lista de nomes de ferramentas disponíveis (None = todas)
        max_turns: Máximo de turnos de conversação (default: 50)
        model: Modelo LLM preferido (None = herda do parent/spawner)
        permission_mode: Modo de permissão (default: ACCEPT_EDITS)
        isolation: Modo de isolamento (default: NONE)
        background: Se True, spawns são sempre em background
        source: Origem do registro (ex: "built-in", "catalog", "custom")
        base_dir: Diretório base para resolução de paths
        color: Cor hex para UI (ex: "#8b5cf6")
        required_mcp_servers: Lista de servers MCP requeridos
        memory: Se True, agente mantém memória de conversas
        get_system_prompt: Factory que retorna system prompt (subclasses sobrescrevem)

    Example:
        >>> agent = AgentDefinition(
        ...     agent_type="tech_lead",
        ...     name="Tech Lead",
        ...     description="Arquiteto de software e líder técnico",
        ...     tools=["Bash", "Read", "Write", "Edit"],
        ...     max_turns=50,
        ...     model="sonnet",
        ...     permission_mode=AgentPermissionMode.ACCEPT_EDITS,
        ... )
    """

    agent_type: str
    name: str
    description: str
    tools: list[str] | None = None  # None = todas as tools disponíveis
    max_turns: int = 50
    model: str | None = None  # None = herdar do parent ou Smart Router
    permission_mode: AgentPermissionMode = AgentPermissionMode.ACCEPT_EDITS
    isolation: IsolationMode = IsolationMode.NONE
    background: bool = False  # Foreground por padrão
    source: str = "built-in"
    base_dir: str = "built-in"
    color: str | None = None  # Cor para UI (ex: "#8b5cf6")
    required_mcp_servers: list[str] = field(default_factory=list)
    memory: bool = False

    # Factory para system prompt — subclasses sobrescrevem
    # Recebe contexto de execução e retorna string com system prompt
    get_system_prompt: Callable[..., str] | None = None

    def __post_init__(self):
        """Validações pós-criação."""
        if not self.agent_type:
            raise ValueError("agent_type é obrigatório")
        if not self.name:
            raise ValueError("name é obrigatório")
        if self.max_turns < 1:
            raise ValueError("max_turns deve ser >= 1")

    def inherits_tools(self) -> bool:
        """Retorna True se este agente herda todas as tools do parent."""
        return self.tools is None

    def inherits_model(self) -> bool:
        """Retorna True se este agente herda o modelo do parent."""
        return self.model is None

    def inherits_permission_mode(self) -> bool:
        """Retorna True se este agente herda o permission mode do parent."""
        return self.permission_mode == AgentPermissionMode.DEFAULT


# =============================================================================
# Agent Spawn Params
# =============================================================================


@dataclass
class AgentSpawnParams:
    """
    Parâmetros para spawn de um agente.

    Usado por AgentSpawner e ForkManager para criar instâncias
    de agentes com configuração específica.

    Equivalente a AgentToolInput em agent_core.tsx.

    Args:
        prompt: Instrução/diretiva para o agente
        description: Descrição curta da tarefa (3-5 palavras)
        agent_type: Tipo do agente (None = fork implícito)
        model: Override de modelo LLM (None = usa default do AgentDefinition)
        name: Nome para agente nomeado (None = agente anônimo)
        team_name: Nome da equipe (None = usa contexto atual)
        run_in_background: Se True, executa em background
        isolation: Modo de isolamento override
        cwd: Working directory override (mutuamente exclusivo com isolation=worktree)

    Example:
        >>> params = AgentSpawnParams(
        ...     prompt="Revise o código em src/api.py",
        ...     description="Revisar código API",
        ...     agent_type="qa_engineer",
        ...     run_in_background=True,
        ... )
    """

    prompt: str
    description: str = ""
    agent_type: str | None = None  # None = fork implícito
    model: str | None = None
    name: str | None = None  # Nome para endereçamento
    team_name: str | None = None
    run_in_background: bool = False
    isolation: IsolationMode = IsolationMode.NONE
    cwd: str | None = None

    def is_fork_path(self) -> bool:
        """Retorna True se este spawn deve usar o path de fork implícito."""
        return self.agent_type is None

    def is_team_spawn(self) -> bool:
        """Retorna True se este é um spawn de teammate (nomeado)."""
        return self.name is not None and self.team_name is not None


# =============================================================================
# Agent Result
# =============================================================================


@dataclass
class AgentResult:
    """
    Resultado da execução de um agente.

    Retornado por AgentSpawner após spawn/execução de um agente.
    Pode representar execução síncrona, assíncrona (background),
    ou fork.

    Equivalente a AgentToolOutput em agent_core.tsx.

    Args:
        status: Estado final ("completed", "async_launched", "fork", "error")
        prompt: Prompt original enviado ao agente
        agent_id: ID do agente criado (None se error)
        output_file: Path para arquivo de output (None se síncrono)
        can_read_output: Se True, agente pode ler o output file
        error: Mensagem de erro (None se status != "error")
        fork_parent_messages: Mensagens herdadas do parent (fork path)
        worktree_path: Path do worktree isolado (isolation=worktree)

    Example:
        >>> result = AgentResult(
        ...     status="async_launched",
        ...     prompt="Gerar testes para api.py",
        ...     agent_id="agent-abc123",
        ...     output_file="/tmp/agent-output.json",
        ...     can_read_output=True,
        ... )
    """

    status: str  # "completed" | "async_launched" | "fork" | "error"
    prompt: str
    agent_id: str | None = None
    output_file: str | None = None
    can_read_output: bool = False
    error: str | None = None
    fork_parent_messages: list[dict] | None = None
    worktree_path: str | None = None

    def is_async(self) -> bool:
        """Retorna True se o agente está executando em background."""
        return self.status == "async_launched"

    def is_completed(self) -> bool:
        """Retorna True se a execução foi concluída."""
        return self.status == "completed"

    def is_error(self) -> bool:
        """Retorna True se houve erro."""
        return self.status == "error"

    def is_fork(self) -> bool:
        """Retorna True se é um fork subagent."""
        return self.status == "fork"


# =============================================================================
# Fork Context
# =============================================================================


@dataclass
class ForkContext:
    """
    Contexto de um fork subagent em execução.

    Mantém referência ao parent e todas as informações necessárias
    para o child executar em isolation (worktree) e depois
    reportar results.

    Equivalente a forkSubagent.ts ForkContext.
    """

    fork_id: str
    parent_agent_id: str
    directive: str
    worktree_path: str | None = None
    created_at: str | None = None  # ISO timestamp

    def __post_init__(self):
        from datetime import datetime, timezone

        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


# =============================================================================
# Constants
# =============================================================================


# Tag injetada no conteúdo de fork workers para prevenir fork recursivo
FORK_BOILERPLATE_TAG = "fork_worker"

# Prefixo que indica uma diretiva de fork na mensagem
FORK_DIRECTIVE_PREFIX = "[FORK DIRECTIVE]"

# Placeholder de tool result usado em todos os fork children
# para maximizar prompt cache hits (API prefixes byte-identical)
FORK_PLACEHOLDER_RESULT = "Fork started — processing in background"

# Agente built-in padrão para fork path
GENERAL_PURPOSE_AGENT_TYPE = "general_purpose"
