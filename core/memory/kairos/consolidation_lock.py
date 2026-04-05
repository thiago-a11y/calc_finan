"""
Consolidation Lock — Lock distribuído para evitar concorrência no dream.

Garante que apenas um processo de consolidação rode por vez,
mesmo com múltiplos workers ou restarts.

Estratégia:
- Lock baseado em arquivo + timestamp (compatível com SQLite e single-server)
- TTL de 10 minutos: se o lock expirar, outro processo pode assumir
- Suporte futuro a lock via banco (PostgreSQL advisory locks)

Uso:
    from core.memory.kairos.consolidation_lock import consolidation_lock

    async with consolidation_lock.acquire("dream_ciclo_123"):
        # Apenas um processo executa aqui
        await processar_snapshots()
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger("synerium.kairos.lock")

# TTL padrão do lock: 10 minutos
_LOCK_TTL_SECONDS = 600

# Diretório base para locks (relativo ao projeto)
_LOCK_DIR = Path(__file__).parent.parent.parent.parent / "data" / "kairos" / "locks"


class ConsolidationLock:
    """
    Lock de consolidação baseado em arquivo com TTL.

    Previne que dois processos de dream rodem simultaneamente.
    Usa arquivo de lock com PID e timestamp para detecção de
    locks órfãos (processo morreu sem liberar).

    Atributos:
        _lock_dir: diretório onde os arquivos de lock são criados
        _ttl: tempo de vida do lock em segundos
        _async_lock: lock asyncio para proteção intra-processo
    """

    def __init__(self, lock_dir: Path | None = None, ttl: int = _LOCK_TTL_SECONDS):
        self._lock_dir = lock_dir or _LOCK_DIR
        self._ttl = ttl
        self._async_lock = asyncio.Lock()

    def _lock_path(self, lock_id: str) -> Path:
        """Retorna o path do arquivo de lock."""
        # Sanitizar lock_id para nome de arquivo seguro
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in lock_id)
        return self._lock_dir / f"{safe_id}.lock"

    def _is_lock_stale(self, lock_path: Path) -> bool:
        """
        Verifica se um lock existente está expirado (órfão).

        Um lock é considerado stale se:
        - O arquivo tem mais de TTL segundos
        - O PID registrado não existe mais
        """
        if not lock_path.exists():
            return True

        try:
            conteudo = lock_path.read_text().strip()
            parts = conteudo.split("|")
            if len(parts) < 2:
                return True

            pid = int(parts[0])
            timestamp = float(parts[1])

            # Verificar TTL
            if time.time() - timestamp > self._ttl:
                logger.warning(
                    f"Lock stale por TTL: {lock_path.name} "
                    f"(idade: {time.time() - timestamp:.0f}s > {self._ttl}s)"
                )
                return True

            # Verificar se o processo ainda existe
            try:
                os.kill(pid, 0)  # Signal 0 = verificar existência
            except OSError:
                logger.warning(
                    f"Lock stale por PID morto: {lock_path.name} (PID {pid})"
                )
                return True

            return False

        except (ValueError, IOError) as e:
            logger.warning(f"Lock corrompido: {lock_path.name} ({e})")
            return True

    def _write_lock(self, lock_path: Path, lock_id: str) -> bool:
        """
        Escreve o arquivo de lock.

        Retorna True se conseguiu adquirir.
        """
        try:
            self._lock_dir.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(f"{os.getpid()}|{time.time()}|{lock_id}")
            logger.debug(f"Lock adquirido: {lock_path.name} (PID={os.getpid()})")
            return True
        except IOError as e:
            logger.error(f"Erro ao escrever lock: {e}")
            return False

    def _release_lock(self, lock_path: Path) -> None:
        """Remove o arquivo de lock."""
        try:
            if lock_path.exists():
                lock_path.unlink()
                logger.debug(f"Lock liberado: {lock_path.name}")
        except IOError as e:
            logger.warning(f"Erro ao liberar lock: {e}")

    async def try_acquire(self, lock_id: str) -> bool:
        """
        Tenta adquirir o lock sem bloquear.

        Retorna True se adquiriu, False se já está em uso.
        """
        async with self._async_lock:
            lock_path = self._lock_path(lock_id)

            if lock_path.exists() and not self._is_lock_stale(lock_path):
                logger.debug(f"Lock já em uso: {lock_id}")
                return False

            # Lock stale ou inexistente — adquirir
            if lock_path.exists():
                self._release_lock(lock_path)

            return self._write_lock(lock_path, lock_id)

    async def release(self, lock_id: str) -> None:
        """Libera o lock."""
        async with self._async_lock:
            lock_path = self._lock_path(lock_id)
            self._release_lock(lock_path)

    @asynccontextmanager
    async def acquire(self, lock_id: str = "dream"):
        """
        Context manager para adquirir e liberar o lock automaticamente.

        Raises:
            RuntimeError: se o lock não pôde ser adquirido
        """
        if not await self.try_acquire(lock_id):
            raise RuntimeError(
                f"Consolidation lock '{lock_id}' já em uso por outro processo"
            )
        try:
            yield lock_id
        finally:
            await self.release(lock_id)

    def is_locked(self, lock_id: str = "dream") -> bool:
        """Verifica se um lock está ativo (sem tentar adquirir)."""
        lock_path = self._lock_path(lock_id)
        return lock_path.exists() and not self._is_lock_stale(lock_path)

    def cleanup_stale(self) -> int:
        """
        Remove todos os locks stale do diretório.

        Retorna a quantidade de locks removidos.
        """
        if not self._lock_dir.exists():
            return 0

        removidos = 0
        for lock_file in self._lock_dir.glob("*.lock"):
            if self._is_lock_stale(lock_file):
                self._release_lock(lock_file)
                removidos += 1

        if removidos:
            logger.info(f"Cleanup: {removidos} lock(s) stale removidos")
        return removidos


# Instância singleton
consolidation_lock = ConsolidationLock()
