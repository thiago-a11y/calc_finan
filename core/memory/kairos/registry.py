"""
Memory Registry — Catálogo de memórias consolidadas por agente/tenant.

Responsável por:
- Salvar e consultar memórias consolidadas (MemoryEntry)
- Busca por agente, tipo, tags e relevância
- Tracking de acessos (recency + frequency)
- Soft delete e manutenção

Uso:
    from core.memory.kairos.registry import memory_registry

    # Salvar memória
    memory_registry.salvar(entry)

    # Consultar
    resultados = memory_registry.consultar(MemoryQuery(
        agente_id="tech_lead",
        query="prioridades fase 3",
        limite=5,
    ))
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.memory.kairos.types import (
    MemoryEntry,
    MemoryQuery,
    MemoryType,
)
from database.session import SessionLocal

logger = logging.getLogger("synerium.kairos.registry")


def _gerar_id(prefixo: str = "mem", tamanho: int = 10) -> str:
    """Gera ID único para memória."""
    alfabeto = string.ascii_lowercase + string.digits
    sufixo = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
    return f"{prefixo}_{sufixo}"


class MemoryRegistry:
    """
    Catálogo de memórias consolidadas.

    Armazena e consulta MemoryEntry no banco de dados.
    Suporta busca por texto, tags, tipo e relevância.
    Rastreia acessos para priorização por recência/frequência.
    """

    def __init__(self):
        logger.debug("MemoryRegistry inicializado")

    def salvar(self, entry: MemoryEntry) -> MemoryEntry:
        """
        Salva uma nova memória no registro.

        Args:
            entry: MemoryEntry para salvar (id pode estar vazio)

        Returns:
            MemoryEntry com id preenchido
        """
        if not entry.id:
            entry.id = _gerar_id()

        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            registro = MemoryEntryDB(
                id=entry.id,
                agente_id=entry.agente_id,
                tenant_id=entry.tenant_id,
                tipo=entry.tipo.value,
                titulo=entry.titulo,
                conteudo=entry.conteudo,
                tags=entry.tags,
                relevancia=entry.relevancia,
                acessos=0,
                fonte_snapshots=entry.fonte_snapshots,
                ativo=True,
            )
            db.add(registro)
            db.commit()
            db.refresh(registro)

            logger.info(
                f"Memória salva: {entry.id} "
                f"(agente={entry.agente_id}, tipo={entry.tipo.value}, "
                f"título='{entry.titulo[:50]}')"
            )
            return entry

        except Exception as e:
            logger.error(f"Erro ao salvar memória: {e}")
            db.rollback()
            return entry
        finally:
            db.close()

    def consultar(self, query: MemoryQuery) -> list[MemoryEntry]:
        """
        Consulta memórias consolidadas com filtros.

        Args:
            query: parâmetros de consulta

        Returns:
            Lista de MemoryEntry ordenada por relevância
        """
        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            q = db.query(MemoryEntryDB).filter(
                MemoryEntryDB.ativo == True,  # noqa: E712
                MemoryEntryDB.tenant_id == query.tenant_id,
            )

            if query.agente_id:
                q = q.filter(MemoryEntryDB.agente_id == query.agente_id)

            if query.tipo:
                q = q.filter(MemoryEntryDB.tipo == query.tipo.value)

            if query.min_relevancia > 0:
                q = q.filter(MemoryEntryDB.relevancia >= query.min_relevancia)

            # Busca textual simples (LIKE no título e conteúdo)
            if query.query:
                termo = f"%{query.query}%"
                q = q.filter(
                    (MemoryEntryDB.titulo.ilike(termo))
                    | (MemoryEntryDB.conteudo.ilike(termo))
                )

            registros = (
                q.order_by(MemoryEntryDB.relevancia.desc())
                .limit(query.limite)
                .all()
            )

            # Atualizar contadores de acesso
            for reg in registros:
                reg.acessos = (reg.acessos or 0) + 1
                reg.ultimo_acesso = datetime.now(timezone.utc)
            db.commit()

            return [self._db_para_entry(r) for r in registros]

        except Exception as e:
            logger.warning(f"Erro ao consultar memórias: {e}")
            return []
        finally:
            db.close()

    def listar(
        self,
        agente_id: str | None = None,
        tenant_id: int = 1,
        limite: int = 20,
    ) -> list[MemoryEntry]:
        """
        Lista memórias ativas, ordenadas por relevância.

        Args:
            agente_id: filtrar por agente (None = todos)
            tenant_id: filtrar por tenant
            limite: máximo de resultados

        Returns:
            Lista de MemoryEntry
        """
        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            q = db.query(MemoryEntryDB).filter(
                MemoryEntryDB.ativo == True,  # noqa: E712
                MemoryEntryDB.tenant_id == tenant_id,
            )

            if agente_id:
                q = q.filter(MemoryEntryDB.agente_id == agente_id)

            registros = (
                q.order_by(MemoryEntryDB.relevancia.desc())
                .limit(limite)
                .all()
            )

            return [self._db_para_entry(r) for r in registros]

        except Exception as e:
            logger.warning(f"Erro ao listar memórias: {e}")
            return []
        finally:
            db.close()

    def atualizar(
        self,
        memory_id: str,
        conteudo: str | None = None,
        tags: list[str] | None = None,
        relevancia: float | None = None,
    ) -> bool:
        """
        Atualiza uma memória existente.

        Args:
            memory_id: ID da memória
            conteudo: novo conteúdo (None = não alterar)
            tags: novas tags (None = não alterar)
            relevancia: nova relevância (None = não alterar)

        Returns:
            True se atualizado com sucesso
        """
        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            registro = db.query(MemoryEntryDB).filter(
                MemoryEntryDB.id == memory_id
            ).first()

            if not registro:
                logger.warning(f"Memória não encontrada: {memory_id}")
                return False

            if conteudo is not None:
                registro.conteudo = conteudo
            if tags is not None:
                registro.tags = tags
            if relevancia is not None:
                registro.relevancia = relevancia

            registro.atualizado_em = datetime.now(timezone.utc)
            db.commit()

            logger.debug(f"Memória atualizada: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar memória: {e}")
            return False
        finally:
            db.close()

    def remover(self, memory_id: str) -> bool:
        """
        Soft delete de uma memória.

        Args:
            memory_id: ID da memória

        Returns:
            True se desativado com sucesso
        """
        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            registro = db.query(MemoryEntryDB).filter(
                MemoryEntryDB.id == memory_id
            ).first()

            if not registro:
                return False

            registro.ativo = False
            registro.atualizado_em = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Memória desativada: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao remover memória: {e}")
            return False
        finally:
            db.close()

    def contar(
        self,
        agente_id: str | None = None,
        tenant_id: int = 1,
    ) -> int:
        """Conta memórias ativas."""
        db = SessionLocal()
        try:
            from database.models import MemoryEntryDB

            q = db.query(MemoryEntryDB).filter(
                MemoryEntryDB.ativo == True,  # noqa: E712
                MemoryEntryDB.tenant_id == tenant_id,
            )
            if agente_id:
                q = q.filter(MemoryEntryDB.agente_id == agente_id)
            return q.count()
        except Exception:
            return 0
        finally:
            db.close()

    def _db_para_entry(self, registro) -> MemoryEntry:
        """Converte registro do banco para dataclass."""
        return MemoryEntry(
            id=registro.id,
            agente_id=registro.agente_id,
            tenant_id=registro.tenant_id,
            tipo=MemoryType(registro.tipo),
            titulo=registro.titulo,
            conteudo=registro.conteudo,
            tags=registro.tags or [],
            relevancia=registro.relevancia,
            acessos=registro.acessos or 0,
            ultimo_acesso=registro.ultimo_acesso,
            fonte_snapshots=registro.fonte_snapshots or [],
            criado_em=registro.criado_em,
            atualizado_em=registro.atualizado_em,
            ativo=registro.ativo,
        )


# Instância singleton
memory_registry = MemoryRegistry()
