"""
KairosService — Singleton principal do sistema de memória auto-evolutiva.

Ponto de entrada único para todas as operações de memória:
- Captura de snapshots
- Consulta de memórias consolidadas
- Disparo manual de dream
- Gerenciamento do loop automático
- Métricas e status

Uso:
    from core.memory.kairos import kairos_service

    # Capturar snapshot
    await kairos_service.criar_snapshot(
        agente_id="tech_lead",
        source="luna",
        conteudo="Decidimos usar PostgreSQL",
    )

    # Consultar memória
    resultados = kairos_service.consultar(
        agente_id="tech_lead",
        query="banco de dados",
    )

    # Disparar dream manualmente
    resultado = await kairos_service.dream()
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from core.memory.kairos.auto_dream import auto_dream, AutoDream
from core.memory.kairos.consolidation_lock import consolidation_lock
from core.memory.kairos.memory_snapshot import snapshot_manager
from core.memory.kairos.registry import memory_registry
from core.memory.kairos.types import (
    ConsolidationResult,
    KairosConfig,
    MemoryEntry,
    MemoryQuery,
    MemorySnapshotData,
    MemoryType,
    SnapshotSource,
)

logger = logging.getLogger("synerium.kairos")


class KairosService:
    """
    Serviço singleton de memória auto-evolutiva.

    Orquestra todos os componentes do sistema Kairos:
    - SnapshotManager: captura de fragmentos brutos
    - MemoryRegistry: armazenamento de memórias consolidadas
    - AutoDream: consolidação automática em background
    - ConsolidationLock: proteção contra concorrência

    Thread-safe: usa lock para operações críticas.
    """

    _instance: KairosService | None = None
    _lock = threading.Lock()

    def __new__(cls) -> KairosService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = KairosConfig()
        self._initialized = True
        logger.info("[Kairos] Serviço inicializado")

    # =========================================================================
    # Snapshots — Captura de fragmentos brutos
    # =========================================================================

    async def criar_snapshot(
        self,
        agente_id: str,
        source: str | SnapshotSource,
        conteudo: str,
        contexto: dict[str, Any] | None = None,
        tenant_id: int = 1,
        relevancia: float = 0.5,
    ) -> MemorySnapshotData:
        """
        Captura um snapshot de memória a partir de uma interação.

        Args:
            agente_id: agente que gerou ou a quem pertence
            source: origem ("luna", "mission_control", "reuniao", etc.)
            conteudo: texto bruto capturado
            contexto: metadados (conversa_id, tarefa_id, etc.)
            tenant_id: company_id multi-tenant
            relevancia: score de relevância (0.0 a 1.0)

        Returns:
            MemorySnapshotData criado
        """
        # Converter string para enum
        if isinstance(source, str):
            try:
                source = SnapshotSource(source)
            except ValueError:
                source = SnapshotSource.MANUAL

        return await snapshot_manager.capturar(
            agente_id=agente_id,
            source=source,
            conteudo=conteudo,
            contexto=contexto,
            tenant_id=tenant_id,
            relevancia=relevancia,
        )

    # =========================================================================
    # Consulta — Busca em memórias consolidadas
    # =========================================================================

    def consultar(
        self,
        agente_id: str | None = None,
        query: str = "",
        tipo: str | MemoryType | None = None,
        tenant_id: int = 1,
        limite: int = 10,
        min_relevancia: float = 0.0,
    ) -> list[MemoryEntry]:
        """
        Consulta memórias consolidadas.

        Args:
            agente_id: filtrar por agente (None = todos)
            query: texto de busca
            tipo: tipo de memória ("episodica", "semantica", etc.)
            tenant_id: filtrar por tenant
            limite: máximo de resultados
            min_relevancia: relevância mínima

        Returns:
            Lista de MemoryEntry ordenada por relevância
        """
        # Converter string para enum
        tipo_enum = None
        if tipo:
            if isinstance(tipo, str):
                try:
                    tipo_enum = MemoryType(tipo)
                except ValueError:
                    pass
            else:
                tipo_enum = tipo

        return memory_registry.consultar(MemoryQuery(
            agente_id=agente_id,
            tenant_id=tenant_id,
            query=query,
            tipo=tipo_enum,
            limite=limite,
            min_relevancia=min_relevancia,
        ))

    def listar_memorias(
        self,
        agente_id: str | None = None,
        tenant_id: int = 1,
        limite: int = 20,
    ) -> list[MemoryEntry]:
        """Lista todas as memórias ativas de um agente."""
        return memory_registry.listar(
            agente_id=agente_id,
            tenant_id=tenant_id,
            limite=limite,
        )

    # =========================================================================
    # Dream — Consolidação
    # =========================================================================

    async def dream(self) -> ConsolidationResult:
        """
        Dispara um ciclo de dream (consolidação) manualmente.

        Returns:
            ConsolidationResult com métricas
        """
        return await auto_dream.dream()

    def iniciar_auto_dream(self) -> None:
        """Inicia o loop de dream automático em background."""
        auto_dream.iniciar_loop()

    def parar_auto_dream(self) -> None:
        """Para o loop de dream automático."""
        auto_dream.parar_loop()

    # =========================================================================
    # Status e Métricas
    # =========================================================================

    def status(self, tenant_id: int = 1) -> dict[str, Any]:
        """
        Retorna status completo do sistema Kairos.

        Returns:
            Dict com métricas e estado atual
        """
        return {
            "ativo": True,
            "auto_dream_rodando": auto_dream.esta_rodando,
            "lock_ativo": consolidation_lock.is_locked(),
            "snapshots_pendentes": snapshot_manager.contar_pendentes(tenant_id),
            "memorias_ativas": memory_registry.contar(tenant_id=tenant_id),
            "config": {
                "dream_interval_min": self._config.dream_interval_min,
                "max_snapshots_por_dream": self._config.max_snapshots_por_dream,
                "modelo_consolidacao": self._config.modelo_consolidacao,
                "habilitar_auto_dream": self._config.habilitar_auto_dream,
            },
        }

    @property
    def config(self) -> KairosConfig:
        """Retorna configuração atual."""
        return self._config

    def atualizar_config(self, **kwargs) -> None:
        """Atualiza configuração do Kairos."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"[Kairos] Config atualizada: {key}={value}")


# Instância singleton global
kairos_service = KairosService()
