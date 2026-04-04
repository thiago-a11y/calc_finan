"""
Core Agents — Orquestração avançada de agentes autônomos.

Módulos:
- base: AgentDefinition, AgentSpawnParams, AgentResult, enums de modo
- registry: AgentRegistry (singleton) — registro centralizado de tipos de agentes
- fork: ForkManager — fork implícito com herança de contexto
- spawn: AgentSpawner — spawning de agentes
- lifecycle: Async lifecycle e progress tracking

Uso:
    from core.agents import AgentRegistry, AgentDefinition, AgentSpawnParams

    registry = AgentRegistry.get_instance()
    agents = registry.list_active()
"""

from core.agents.base import (
    AgentPermissionMode,
    IsolationMode,
    AgentDefinition,
    AgentSpawnParams,
    AgentResult,
    ForkContext,
    FORK_BOILERPLATE_TAG,
    FORK_DIRECTIVE_PREFIX,
    FORK_PLACEHOLDER_RESULT,
    GENERAL_PURPOSE_AGENT_TYPE,
)
from core.agents.registry import AgentRegistry
from core.agents.fork import fork_manager, AutoApproveMode, AutoModeState
from core.agents.spawn import AgentSpawner, agent_spawner, SpawnProgress
from core.agents.lifecycle import (
    AgentLifecycle,
    LifecycleState,
    LifecycleEvent,
    LifecycleManager,
    lifecycle_manager,
)

__all__ = [
    # base
    "AgentPermissionMode",
    "IsolationMode",
    "AgentDefinition",
    "AgentSpawnParams",
    "AgentResult",
    "ForkContext",
    "FORK_BOILERPLATE_TAG",
    "FORK_DIRECTIVE_PREFIX",
    "FORK_PLACEHOLDER_RESULT",
    "GENERAL_PURPOSE_AGENT_TYPE",
    # registry
    "AgentRegistry",
    # fork
    "fork_manager",
    "AutoApproveMode",
    "AutoModeState",
    # spawn
    "AgentSpawner",
    "agent_spawner",
    "SpawnProgress",
    # lifecycle
    "AgentLifecycle",
    "LifecycleState",
    "LifecycleEvent",
    "LifecycleManager",
    "lifecycle_manager",
]
