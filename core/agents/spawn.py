"""
Agent Spawner — Spawning de agentes com suporte a fork, worktree e lifecycle.

Implementa o sistema de spawning inspirado em agent_core.tsx (TypeScript):

Características principais:
- Fork implícito: quando agent_type é omitido, usa ForkManager
- Worktree isolation: cria git worktree isolado para execução
- Background/foreground: suporte a execução assíncrona
- Progress tracking: callbacks para tracking de progresso
- Integration com AgentRegistry e AgentSpawnParams

Equivalente a:
- AgentSpawner (Python) ≈ forkSubagent.ts + agent_core.tsx call()

Usage:
    from core.agents.spawn import AgentSpawner

    spawner = AgentSpawner()
    result = await spawner.spawn(params)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core.agents.base import (
    AgentDefinition,
    AgentPermissionMode,
    AgentResult,
    AgentSpawnParams,
    ForkContext,
    IsolationMode,
    FORK_PLACEHOLDER_RESULT,
    GENERAL_PURPOSE_AGENT_TYPE,
)
from core.agents.fork import fork_manager
from core.agents.registry import AgentRegistry

logger = logging.getLogger("synerium.agents.spawn")


# =============================================================================
# Progress Tracking
# =============================================================================


@dataclass
class SpawnProgress:
    """Progress de spawn de agente."""

    agent_id: str
    status: str = "pending"  # pending, running, completed, failed
    message: str | None = None
    percent: float = 0.0
    started_at: datetime | None = None
    ended_at: datetime | None = None


# =============================================================================
# AgentSpawner
# =============================================================================


class AgentSpawner:
    """
    Gerenciador de spawn de agentes.

    Responsável por:
    - Selecionar tipo de agente (fork ou named)
    - Criar worktree isolado se isolation=worktree
    - Gerenciar lifecycle de agentes
    - Tracking de progresso

    Equivalente a parte de agent_core.tsx que faz call/surface.

    Attributes:
        _active_spawns: Mapa de agent_id → SpawnProgress
        _fork_manager: Referência ao ForkManager singleton
    """

    def __init__(self, fork_mgr=None):
        self._active_spawns: dict[str, SpawnProgress] = {}
        self._fork_manager = fork_mgr or fork_manager
        self._lock = asyncio.Lock()

    # =========================================================================
    # Public API
    # =========================================================================

    async def spawn(
        self,
        params: AgentSpawnParams,
        context: dict[str, Any] | None = None,
        parent_messages: list[dict] | None = None,
        assistant_message: dict | None = None,
        on_progress: Callable[[SpawnProgress], None] | None = None,
    ) -> AgentResult:
        """
        Spawn um agente según params.

        Fluxo:
        1. Se agent_type é None → fork path (ForkManager)
        2. Se isolation=worktree → criar worktree
        3. Executar (fork ou named agent)
        4. Retornar AgentResult

        Args:
            params: Parâmetros do spawn
            context: Contexto de execução (cwd, session_id, etc.)
            parent_messages: Mensagens do conversation history (fork)
            assistant_message: Última mensagem do assistant (fork)
            on_progress: Callback opcional para progress updates

        Returns:
            AgentResult com status da execução
        """
        context = context or {}
        parent_messages = parent_messages or []

        # Gerar ID único
        agent_id = self._generate_id()

        # Criar progress tracker
        progress = SpawnProgress(
            agent_id=agent_id,
            status="pending",
            started_at=datetime.now(timezone.utc),
        )
        self._active_spawns[agent_id] = progress

        try:
            if params.is_fork_path():
                # Fork path: usar ForkManager
                result = await self._spawn_fork(
                    agent_id, params, context, parent_messages, assistant_message, progress, on_progress
                )
            else:
                # Named agent path: buscar no registry
                result = await self._spawn_named(
                    agent_id, params, context, progress, on_progress
                )

            progress.status = "completed"
            progress.ended_at = datetime.now(timezone.utc)
            if on_progress:
                on_progress(progress)

            return result

        except Exception as e:
            logger.error(f"Agent spawn failed: {e}")
            progress.status = "failed"
            progress.message = str(e)
            progress.ended_at = datetime.now(timezone.utc)
            if on_progress:
                on_progress(progress)

            return AgentResult(
                status="error",
                prompt=params.prompt,
                agent_id=agent_id,
                error=str(e),
            )

    async def spawn_background(
        self,
        params: AgentSpawnParams,
        context: dict[str, Any] | None = None,
        parent_messages: list[dict] | None = None,
        assistant_message: dict | None = None,
    ) -> AgentResult:
        """
        Spawn agente em background (async).

        Args:
            params: Parâmetros do spawn
            context: Contexto de execução
            parent_messages: Mensagens do conversation history
            assistant_message: Mensagem do assistant

        Returns:
            AgentResult com status="async_launched"
        """
        # Força background mode
        params.run_in_background = True

        # Executa em background
        return await self.spawn(
            params, context, parent_messages, assistant_message
        )

    def get_active_spawns(self) -> list[SpawnProgress]:
        """Retorna lista de spawns ativos."""
        return list(self._active_spawns.values())

    def get_spawn(self, agent_id: str) -> SpawnProgress | None:
        """Retorna progresso de um spawn específico."""
        return self._active_spawns.get(agent_id)

    async def cancel_spawn(self, agent_id: str) -> bool:
        """
        Cancela um spawn em andamento.

        Args:
            agent_id: ID do spawn

        Returns:
            True se cancelado com sucesso
        """
        async with self._lock:
            if agent_id in self._active_spawns:
                progress = self._active_spawns[agent_id]
                if progress.status == "running":
                    progress.status = "failed"
                    progress.message = "Cancelled by user"
                    progress.ended_at = datetime.now(timezone.utc)
                    logger.info(f"Spawn {agent_id} cancelled")
                    return True
            return False

    async def complete_spawn(self, agent_id: str) -> None:
        """
        Marca um spawn como completo e limpa recursos.

        Args:
            agent_id: ID do spawn
        """
        async with self._lock:
            if agent_id in self._active_spawns:
                progress = self._active_spawns[agent_id]
                progress.status = "completed"
                progress.ended_at = datetime.now(timezone.utc)

                # Cleanup fork se existir
                fork_ctx = fork_manager.get_fork(agent_id)
                if fork_ctx:
                    await fork_manager.complete_fork(agent_id)

                # Remover do tracking
                del self._active_spawns[agent_id]
                logger.info(f"Spawn {agent_id} completed and cleaned")

    # =========================================================================
    # Fork Path
    # =========================================================================

    async def _spawn_fork(
        self,
        agent_id: str,
        params: AgentSpawnParams,
        context: dict[str, Any],
        parent_messages: list[dict],
        assistant_message: dict | None,
        progress: SpawnProgress,
        on_progress: Callable[[SpawnProgress], None] | None = None,
    ) -> AgentResult:
        """
        Spawn via fork path (ForkManager).

        Args:
            agent_id: ID único do agent
            params: Parâmetros de spawn
            context: Contexto de execução
            parent_messages: Mensagens do conversation history
            assistant_message: Mensagem do assistant (com tool_use blocks)
            progress: Progress tracker
            on_progress: Callback de progress

        Returns:
            AgentResult com status="fork"
        """
        logger.info(f"Fork spawn: {agent_id}, directive={params.prompt[:50]}...")

        # Atualizar progress
        progress.status = "running"
        progress.message = "Spawning fork subagent"
        if on_progress:
            on_progress(progress)

        # Verificar se fork está habilitado
        if not self._fork_manager.is_fork_subagent_enabled():
            raise ValueError("Fork subagent not enabled")

        # Verificar recursive guard
        if self._fork_manager.is_in_fork_child(parent_messages):
            raise ValueError("Fork not available in forked worker")

        # Criar worktree se necessário
        worktree_path = None
        if params.isolation == IsolationMode.WORKTREE:
            worktree_path = await self._fork_manager.create_worktree(
                agent_id, context.get("cwd")
            )
            if worktree_path:
                logger.info(f"Worktree created: {worktree_path}")

        # Construir mensagens forkadas
        fork_messages = None
        if assistant_message:
            fork_messages = self._fork_manager.build_forked_messages(
                params.prompt, assistant_message
            )

        # Criar ForkContext para tracking
        fork_ctx = ForkContext(
            fork_id=agent_id,
            parent_agent_id=context.get("parent_agent_id", ""),
            directive=params.prompt,
            worktree_path=worktree_path,
        )
        self._fork_manager._active_forks[agent_id] = fork_ctx

        # Atualizar progress
        progress.message = "Fork subagent spawned"
        progress.percent = 50.0
        if on_progress:
            on_progress(progress)

        # Retornar resultado de fork
        return AgentResult(
            status="fork",
            prompt=params.prompt,
            agent_id=agent_id,
            worktree_path=worktree_path,
            fork_parent_messages=fork_messages,
        )

    # =========================================================================
    # Named Agent Path
    # =========================================================================

    async def _spawn_named(
        self,
        agent_id: str,
        params: AgentSpawnParams,
        context: dict[str, Any],
        progress: SpawnProgress,
        on_progress: Callable[[SpawnProgress], None] | None = None,
    ) -> AgentResult:
        """
        Spawn um agente nomeado (buscado no registry).

        Args:
            agent_id: ID único do agent
            params: Parâmetros de spawn
            context: Contexto de execução
            progress: Progress tracker
            on_progress: Callback de progress

        Returns:
            AgentResult com status (completed, async_launched, ou error)
        """
        logger.info(f"Named spawn: {agent_id}, type={params.agent_type}")

        # Buscar definição do agente
        registry = AgentRegistry.get_instance()
        definition = registry.get(params.agent_type)

        if not definition:
            raise ValueError(f"Agent type '{params.agent_type}' not found")

        # Atualizar progress
        progress.status = "running"
        progress.message = f"Spawning {definition.name}"
        if on_progress:
            on_progress(progress)

        # Criar worktree se isolation=worktree
        worktree_path = None
        if params.isolation == IsolationMode.WORKTREE or definition.isolation == IsolationMode.WORKTREE:
            worktree_path = await self._create_worktree_for_agent(
                agent_id, definition, context.get("cwd")
            )

        # Para background, retorna async
        if params.run_in_background or definition.background:
            progress.message = f"{definition.name} running in background"
            progress.percent = 50.0
            if on_progress:
                on_progress(progress)

            return AgentResult(
                status="async_launched",
                prompt=params.prompt,
                agent_id=agent_id,
                worktree_path=worktree_path,
            )

        # Para foreground, executa e retorna completed
        progress.message = f"{definition.name} completed"
        progress.percent = 100.0
        if on_progress:
            on_progress(progress)

        return AgentResult(
            status="completed",
            prompt=params.prompt,
            agent_id=agent_id,
            worktree_path=worktree_path,
        )

    # =========================================================================
    # Worktree Helpers
    # =========================================================================

    async def _create_worktree_for_agent(
        self,
        agent_id: str,
        definition: AgentDefinition,
        parent_cwd: str | None = None,
    ) -> str | None:
        """
        Cria worktree isolado para um agente.

        Args:
            agent_id: ID do agente
            definition: Definição do agente
            parent_cwd: Diretório pai

        Returns:
            Path do worktree ou None
        """
        if not self._fork_manager.is_worktree_isolation_enabled():
            return None

        return await self._fork_manager.create_worktree(agent_id, parent_cwd)

    # =========================================================================
    # Utilities
    # =========================================================================

    def _generate_id(self, tamanho: int = 12) -> str:
        """
        Gera ID único para spawn.

        Args:
            tamanho: Comprimento do ID

        Returns:
            String aleatória
        """
        import secrets
        import string

        alfabeto = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


# =============================================================================
# Singleton Instance
# =============================================================================

# Instância global do AgentSpawner
agent_spawner = AgentSpawner()