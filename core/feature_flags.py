"""
Feature Flag Service — Leitura centralizada de feature flags do banco de dados.

Fornece:
- Leitura de flags direto do banco (FeatureFlagDB)
- Cache TTL de 30 segundos (evita consultas excessivas ao DB)
- Fallback seguro: se a flag não existe, retorna False

Uso:
    from core.feature_flags import FeatureFlagService

    service = FeatureFlagService()
    if service.is_enabled("fork_subagent"):
        ...
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from cachetools import TTLCache

from database.session import SessionLocal
from database.models import FeatureFlagDB

logger = logging.getLogger("synerium.feature_flags")

# Cache TTL: 30 segundos
_CACHE_TTL_SECONDS = 30
# Tamanho máximo do cache (número de flags em cache)
_CACHE_MAX_SIZE = 100


class FeatureFlagService:
    """
    Serviço singleton de feature flags com cache TTL.

    Lê valores do banco (FeatureFlagDB) e mantém em memória
    por 30 segundos para evitar hits excessivos no SQLite.

    Thread-safe: usa lock para operações de cache.
    """

    _instance: Optional["FeatureFlagService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "FeatureFlagService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._cache: TTLCache[str, bool] = TTLCache(
            maxsize=_CACHE_MAX_SIZE,
            ttl=_CACHE_TTL_SECONDS,
        )
        self._initialized = True
        logger.debug("FeatureFlagService inicializado (cache TTL=30s)")

    def is_enabled(self, flag_name: str) -> bool:
        """
        Verifica se uma feature flag está habilitada.

        Utiliza cache TTL: consulta o banco apenas se a entrada
        expirou ou não existe.

        Fallback seguro: se a flag não existe no banco, retorna False.

        Args:
            flag_name: Nome técnico da flag (ex: "fork_subagent",
                       "worktree_isolation", "autonomous_mode")

        Returns:
            True se a flag está habilitada, False caso contrário
            (incluindo flag inexistente).
        """
        # Consulta cache primeiro
        with self._lock:
            if flag_name in self._cache:
                logger.debug(f"Flag '{flag_name}' lida do cache: {self._cache[flag_name]}")
                return self._cache[flag_name]

        # Cache miss: consultar banco
        db = SessionLocal()
        try:
            flag = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.nome == flag_name
            ).first()

            if flag is None:
                logger.warning(
                    f"Flag '{flag_name}' não encontrada no banco — "
                    "fallback OFF (fail-closed)"
                )
                enabled = False
            else:
                enabled = bool(flag.habilitado)
                logger.debug(
                    f"Flag '{flag_name}' lida do banco: {enabled}"
                    f" (atualizado em {flag.atualizado_em})"
                )

            # Atualizar cache
            with self._lock:
                self._cache[flag_name] = enabled

            return enabled

        finally:
            db.close()

    def invalidate(self, flag_name: str) -> None:
        """
        Invalida cache de uma flag específica (força releitura do banco).

        Útil após um toggle para garantir que o próximo is_enabled()
        leia o valor real.

        Args:
            flag_name: Nome da flag a invalidar
        """
        with self._lock:
            if flag_name in self._cache:
                del self._cache[flag_name]
                logger.debug(f"Cache invalidado para flag '{flag_name}'")

    def invalidate_all(self) -> None:
        """Invalida todo o cache de flags."""
        with self._lock:
            self._cache.clear()
            logger.debug("Cache de flags totalmente limpo")

    def get_flag_info(self, flag_name: str) -> Optional[dict]:
        """
        Retorna info completa de uma flag (nome, status, descrição).

        Args:
            flag_name: Nome da flag

        Returns:
            Dicionário com info da flag ou None se não existir
        """
        db = SessionLocal()
        try:
            flag = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.nome == flag_name
            ).first()
            if flag is None:
                return None
            return {
                "nome": flag.nome,
                "habilitado": flag.habilitado,
                "descricao": flag.descricao,
                "requer_restart": flag.requer_restart,
                "atualizado_por": flag.atualizado_por,
                "atualizado_em": flag.atualizado_em.isoformat() if flag.atualizado_em else None,
            }
        finally:
            db.close()


# Instância singleton global
feature_flag_service = FeatureFlagService()
