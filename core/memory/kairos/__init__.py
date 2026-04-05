"""
Kairos — Sistema de memória auto-evolutiva (Self-Evolving Memory).

Inspirado no padrão AutoDream: consolidação periódica de snapshots
de memória por agente/produto/tenant em background.

Componentes:
- KairosService: singleton principal, orquestra todo o sistema
- AutoDream: processo de consolidação automática em background
- MemorySnapshot: captura de estado de memória por contexto
- ConsolidationLock: lock distribuído para evitar concorrência
- MemoryRegistry: catálogo de memórias ativas por agente/tenant

Uso:
    from core.memory.kairos import kairos_service

    # Criar snapshot
    snapshot = kairos_service.criar_snapshot(agente_id="tech_lead", contexto={...})

    # Disparar consolidação (dream)
    await kairos_service.dream()

    # Consultar memória consolidada
    memoria = kairos_service.consultar(agente_id="tech_lead", query="prioridades")
"""

from core.memory.kairos.service import kairos_service, KairosService
from core.memory.kairos.types import (
    MemorySnapshotData,
    ConsolidationResult,
    MemoryQuery,
    MemoryEntry,
    KairosConfig,
)

__all__ = [
    "kairos_service",
    "KairosService",
    "MemorySnapshotData",
    "ConsolidationResult",
    "MemoryQuery",
    "MemoryEntry",
    "KairosConfig",
]
