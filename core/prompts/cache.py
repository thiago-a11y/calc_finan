"""
Cache de Prompts — thread-safe com TTL.

Segue o padrao existente de core/company_context.py:28-36.
Usa cachetools.TTLCache com threading.Lock para seguranca em FastAPI.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger("synerium.prompts.cache")

try:
    from cachetools import TTLCache
except ImportError:
    TTLCache = None  # type: ignore


class PromptCache:
    """Cache thread-safe para prompts compostos. TTL padrao: 3600s (1h)."""

    def __init__(self, maxsize: int = 64, ttl: int = 3600):
        self._default_ttl = ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        if TTLCache is not None:
            self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        else:
            logger.warning("[CACHE] cachetools nao disponivel — usando dict simples")
            self._cache: dict = {}

    def get(self, key: str) -> Optional[str]:
        """Recupera valor do cache. None se nao encontrado ou expirado."""
        with self._lock:
            value = self._cache.get(key)
            if value is not None:
                self._hits += 1
            else:
                self._misses += 1
            return value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Armazena valor no cache."""
        with self._lock:
            self._cache[key] = value

    def invalidate(self, key: str) -> None:
        """Remove uma entrada especifica do cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove todas as entradas do cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("[CACHE] Cache de prompts limpo")

    def stats(self) -> dict:
        """Retorna estatisticas do cache para observabilidade."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "0%",
                "size": len(self._cache),
            }


# Instancia global
prompt_cache = PromptCache()
