"""
Agent Lifecycle — Async lifecycle management e progress tracking.

Implementa o ciclo de vida de agentes com suporte a:
- Background task tracking
- Progress callbacks
- Cancellation support
- Teardown/cleanup

Equivalente a runAgent.ts + LocalAgentTask.ts (TypeScript).

Usage:
    from core.agents.lifecycle import AgentLifecycle, lifecycle_manager

    lifecycle = AgentLifecycle(agent_id)
    lifecycle.on_progress(lambda p: print(f'Progress: {p.percent}%'))
    await lifecycle.run()
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("synerium.agents.lifecycle")


# =============================================================================
# Lifecycle State
# =============================================================================


@dataclass
class LifecycleState:
    """Estado do lifecycle de um agente."""

    agent_id: str
    status: str = "idle"  # idle, running, paused, completed, failed, cancelled
    progress: float = 0.0
    message: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Lifecycle Events
# =============================================================================


@dataclass
class LifecycleEvent:
    """Evento de lifecycle."""

    type: str  # start, progress, complete, fail, cancel, timeout
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] | None = None


# =============================================================================
# AgentLifecycle
# =============================================================================


class AgentLifecycle:
    """
    Gerenciador de lifecycle para agente em execução.

    Responsável por:
    - Tracking de estado e progresso
    - Callbacks de progress
    - Cancellation support
    - Timeout handling
    - Cleanup ao completar

    Usage:
        >>> lifecycle = AgentLifecycle("agent-123")
        >>> lifecycle.on_progress(lambda s: print(f"Progress: {s.progress}%"))
        >>> await lifecycle.run()
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._state = LifecycleState(agent_id=agent_id)
        self._progress_callbacks: list[Callable[[LifecycleState], None]] = []
        self._event_callbacks: list[Callable[[LifecycleEvent], None]] = []
        self._lock = asyncio.Lock()
        self._cancelled = False
        self._completed = False

    # =========================================================================
    # State Management
    # =========================================================================

    @property
    def state(self) -> LifecycleState:
        """Retorna estado atual do lifecycle."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Retorna True se lifecycle está em execução."""
        return self._state.status == "running"

    @property
    def is_completed(self) -> bool:
        """Retorna True se lifecycle foi completado."""
        return self._completed

    @property
    def was_cancelled(self) -> bool:
        """Retorna True se lifecycle foi cancelado."""
        return self._cancelled

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_progress(self, callback: Callable[[LifecycleState], None]) -> None:
        """Registra callback para updates de progresso."""
        self._progress_callbacks.append(callback)

    def on_event(self, callback: Callable[[LifecycleEvent], None]) -> None:
        """Registra callback para eventos."""
        self._event_callbacks.append(callback)

    def _emit_progress(self) -> None:
        """Emite progresso para todos os callbacks."""
        for cb in self._progress_callbacks:
            try:
                cb(self._state)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def _emit_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emite evento para todos os callbacks."""
        event = LifecycleEvent(
            type=event_type,
            agent_id=self.agent_id,
            data=data,
        )
        for cb in self._event_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    # =========================================================================
    # Control Methods
    # =========================================================================

    async def start(self, message: str | None = None) -> None:
        """Inicia o lifecycle."""
        async with self._lock:
            self._state.status = "running"
            self._state.started_at = datetime.now(timezone.utc)
            if message:
                self._state.message = message
            self._emit_event("start", {"message": message})
            self._emit_progress()
        logger.info(f"Lifecycle {self.agent_id}: started")

    async def update_progress(
        self,
        progress: float,
        message: str | None = None,
    ) -> None:
        """
        Atualiza progresso do lifecycle.

        Args:
            progress: Valor entre 0.0 e 1.0 (ou -1 para indeterminate)
            message: Mensagem opcional de status
        """
        async with self._lock:
            self._state.progress = max(0.0, min(1.0, progress))
            if message:
                self._state.message = message
            self._emit_progress()
        logger.debug(f"Lifecycle {self.agent_id}: progress={progress:.1%}")

    async def complete(self, message: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        """
        Marca lifecycle como completado.

        Args:
            message: Mensagem final
            metadata: Metadata adicional
        """
        async with self._lock:
            self._state.status = "completed"
            self._state.progress = 1.0
            self._state.ended_at = datetime.now(timezone.utc)
            self._state.message = message
            if metadata:
                self._state.metadata.update(metadata)
            self._completed = True
            self._emit_event("complete", {"message": message, "metadata": metadata})
            self._emit_progress()
        logger.info(f"Lifecycle {self.agent_id}: completed")

    async def fail(self, error: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Marca lifecycle como falhou.

        Args:
            error: Mensagem de erro
            metadata: Metadata adicional
        """
        async with self._lock:
            self._state.status = "failed"
            self._state.ended_at = datetime.now(timezone.utc)
            self._state.error = error
            self._state.progress = 1.0
            if metadata:
                self._state.metadata.update(metadata)
            self._emit_event("fail", {"error": error})
            self._emit_progress()
        logger.error(f"Lifecycle {self.agent_id}: failed - {error}")

    async def cancel(self, message: str | None = None) -> None:
        """
        Cancela o lifecycle.

        Args:
            message: Mensagem de cancelamento
        """
        async with self._lock:
            if self._completed:
                return  # Already completed, can't cancel
            self._state.status = "cancelled"
            self._state.ended_at = datetime.now(timezone.utc)
            self._state.message = message or "Cancelled by user"
            self._cancelled = True
            self._emit_event("cancel", {"message": message})
            self._emit_progress()
        logger.info(f"Lifecycle {self.agent_id}: cancelled")

    async def pause(self, message: str | None = None) -> None:
        """Pausa o lifecycle (se suportado)."""
        async with self._lock:
            if self._state.status == "running":
                self._state.status = "paused"
                self._state.message = message or "Paused"
                self._emit_event("pause", {"message": message})
                self._emit_progress()

    async def resume(self, message: str | None = None) -> None:
        """Retoma o lifecycle (se estava pausado)."""
        async with self._lock:
            if self._state.status == "paused":
                self._state.status = "running"
                if message:
                    self._state.message = message
                self._emit_event("resume", {"message": message})
                self._emit_progress()

    # =========================================================================
    # Timeout Support
    # =========================================================================

    async def run_with_timeout(
        self,
        coro,
        timeout_seconds: float,
    ) -> Any:
        """
        Executa coroutine com timeout.

        Args:
            coro: Coroutine para executar
            timeout_seconds: Timeout em segundos

        Returns:
            Resultado da coroutine ou None se timeout

        Raises:
            asyncio.TimeoutError: Se timeout excedido
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            await self.fail(f"Timeout after {timeout_seconds}s")
            raise

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    async def __aenter__(self) -> "AgentLifecycle":
        """Entry do context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit do context manager."""
        if exc_type is not None:
            await self.fail(str(exc_val))
        elif self._cancelled:
            pass  # Already set by cancel()
        elif not self._completed:
            await self.complete()


# =============================================================================
# Lifecycle Manager
# =============================================================================


class LifecycleManager:
    """
    Gerenciador global de lifecycles.

    SINGLETON — gerencia todos os lifecycles ativos.

    Usage:
        >>> manager = LifecycleManager.get_instance()
        >>> manager.register(lifecycle)
        >>> manager.get("agent-123")
    """

    _instance: "LifecycleManager | None" = None

    def __init__(self):
        self._lifecycles: dict[str, AgentLifecycle] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "LifecycleManager":
        """Retorna instância singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, lifecycle: AgentLifecycle) -> None:
        """Registra um lifecycle."""
        self._lifecycles[lifecycle.agent_id] = lifecycle

    def unregister(self, agent_id: str) -> None:
        """Remove um lifecycle."""
        if agent_id in self._lifecycles:
            del self._lifecycles[agent_id]

    def get(self, agent_id: str) -> AgentLifecycle | None:
        """Retorna lifecycle por ID."""
        return self._lifecycles.get(agent_id)

    def list_active(self) -> list[AgentLifecycle]:
        """Lista todos os lifecycles ativos."""
        return [
            lc for lc in self._lifecycles.values()
            if lc.is_running and not lc.was_cancelled
        ]

    async def cancel_all(self) -> None:
        """Cancela todos os lifecycles ativos."""
        for lifecycle in self.list_active():
            await lifecycle.cancel()


# =============================================================================
# Singleton Instance
# =============================================================================

lifecycle_manager = LifecycleManager()