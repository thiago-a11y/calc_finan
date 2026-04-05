"""
Memory Snapshot — Captura e persistência de snapshots de memória.

Responsável por:
- Criar snapshots a partir de interações (Luna, Mission Control, reuniões)
- Persistir snapshots no banco (MemorySnapshotDB)
- Listar snapshots pendentes de consolidação
- Marcar snapshots como consolidados após o dream

Uso:
    from core.memory.kairos.memory_snapshot import snapshot_manager

    # Capturar snapshot de uma conversa Luna
    snap = await snapshot_manager.capturar(
        agente_id="tech_lead",
        source=SnapshotSource.LUNA,
        conteudo="Decisão: usar PostgreSQL para produção",
        contexto={"conversa_id": "abc123"},
    )

    # Listar pendentes
    pendentes = snapshot_manager.listar_pendentes(limite=50)
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from core.memory.kairos.types import (
    MemorySnapshotData,
    SnapshotSource,
)
from database.session import SessionLocal

logger = logging.getLogger("synerium.kairos.snapshot")


def _gerar_id(prefixo: str = "snap", tamanho: int = 10) -> str:
    """Gera ID único para snapshot."""
    alfabeto = string.ascii_lowercase + string.digits
    sufixo = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
    return f"{prefixo}_{sufixo}"


class SnapshotManager:
    """
    Gerenciador de snapshots de memória.

    Captura fragmentos brutos de informação de diversas fontes
    (Luna, Mission Control, reuniões, workflows) e persiste
    para processamento posterior pelo AutoDream.
    """

    def __init__(self):
        logger.debug("SnapshotManager inicializado")

    async def capturar(
        self,
        agente_id: str,
        source: SnapshotSource,
        conteudo: str,
        contexto: dict | None = None,
        tenant_id: int = 1,
        relevancia: float = 0.5,
    ) -> MemorySnapshotData:
        """
        Captura um novo snapshot de memória.

        Args:
            agente_id: agente que gerou ou a quem pertence
            source: origem (luna, mission_control, reuniao, etc.)
            conteudo: texto bruto capturado
            contexto: metadados (conversa_id, tarefa_id, etc.)
            tenant_id: company_id para multi-tenant
            relevancia: score de relevância estimado (0.0 a 1.0)

        Returns:
            MemorySnapshotData criado e persistido
        """
        snapshot = MemorySnapshotData(
            id=_gerar_id(),
            agente_id=agente_id,
            tenant_id=tenant_id,
            source=source,
            conteudo=conteudo,
            contexto=contexto or {},
            relevancia=max(0.0, min(1.0, relevancia)),
            criado_em=datetime.now(timezone.utc),
            consolidado=False,
        )

        # Persistir no banco
        self._salvar(snapshot)

        logger.info(
            f"Snapshot capturado: {snapshot.id} "
            f"(agente={agente_id}, source={source.value}, "
            f"tamanho={len(conteudo)} chars)"
        )
        return snapshot

    def listar_pendentes(
        self,
        limite: int = 50,
        tenant_id: int | None = None,
    ) -> list[MemorySnapshotData]:
        """
        Lista snapshots pendentes de consolidação.

        Args:
            limite: máximo de snapshots a retornar
            tenant_id: filtrar por tenant (None = todos)

        Returns:
            Lista de snapshots não consolidados, ordenados por criação
        """
        db = SessionLocal()
        try:
            from database.models import MemorySnapshotDB

            query = db.query(MemorySnapshotDB).filter(
                MemorySnapshotDB.consolidado == False  # noqa: E712
            )

            if tenant_id is not None:
                query = query.filter(MemorySnapshotDB.tenant_id == tenant_id)

            registros = (
                query
                .order_by(MemorySnapshotDB.criado_em.asc())
                .limit(limite)
                .all()
            )

            return [self._db_para_data(r) for r in registros]

        except Exception as e:
            # Tabela pode não existir ainda — retornar lista vazia
            logger.warning(f"Erro ao listar snapshots pendentes: {e}")
            return []
        finally:
            db.close()

    def marcar_consolidado(self, snapshot_id: str) -> bool:
        """
        Marca um snapshot como consolidado após o dream.

        Args:
            snapshot_id: ID do snapshot

        Returns:
            True se atualizado com sucesso
        """
        db = SessionLocal()
        try:
            from database.models import MemorySnapshotDB

            registro = db.query(MemorySnapshotDB).filter(
                MemorySnapshotDB.id == snapshot_id
            ).first()

            if not registro:
                logger.warning(f"Snapshot não encontrado para consolidar: {snapshot_id}")
                return False

            registro.consolidado = True
            registro.consolidado_em = datetime.now(timezone.utc)
            db.commit()

            logger.debug(f"Snapshot consolidado: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao marcar snapshot como consolidado: {e}")
            return False
        finally:
            db.close()

    def limpar_expirados(self, ttl_horas: int = 72) -> int:
        """
        Remove snapshots consolidados mais antigos que o TTL.

        Args:
            ttl_horas: tempo de vida em horas

        Returns:
            Quantidade de snapshots removidos
        """
        db = SessionLocal()
        try:
            from database.models import MemorySnapshotDB

            limite = datetime.now(timezone.utc) - timedelta(hours=ttl_horas)
            removidos = db.query(MemorySnapshotDB).filter(
                MemorySnapshotDB.consolidado == True,  # noqa: E712
                MemorySnapshotDB.consolidado_em < limite,
            ).delete()

            db.commit()
            if removidos:
                logger.info(f"Snapshots expirados removidos: {removidos}")
            return removidos

        except Exception as e:
            logger.warning(f"Erro ao limpar snapshots expirados: {e}")
            return 0
        finally:
            db.close()

    def contar_pendentes(self, tenant_id: int | None = None) -> int:
        """Conta snapshots pendentes de consolidação."""
        db = SessionLocal()
        try:
            from database.models import MemorySnapshotDB

            query = db.query(MemorySnapshotDB).filter(
                MemorySnapshotDB.consolidado == False  # noqa: E712
            )
            if tenant_id is not None:
                query = query.filter(MemorySnapshotDB.tenant_id == tenant_id)
            return query.count()
        except Exception:
            return 0
        finally:
            db.close()

    # =========================================================================
    # Persistência
    # =========================================================================

    def _salvar(self, snapshot: MemorySnapshotData) -> None:
        """Persiste snapshot no banco."""
        db = SessionLocal()
        try:
            from database.models import MemorySnapshotDB

            registro = MemorySnapshotDB(
                id=snapshot.id,
                agente_id=snapshot.agente_id,
                tenant_id=snapshot.tenant_id,
                source=snapshot.source.value,
                conteudo=snapshot.conteudo,
                contexto=snapshot.contexto,
                relevancia=snapshot.relevancia,
                consolidado=False,
            )
            db.add(registro)
            db.commit()

        except Exception as e:
            logger.error(f"Erro ao salvar snapshot: {e}")
            db.rollback()
        finally:
            db.close()

    def _db_para_data(self, registro) -> MemorySnapshotData:
        """Converte registro do banco para dataclass."""
        return MemorySnapshotData(
            id=registro.id,
            agente_id=registro.agente_id,
            tenant_id=registro.tenant_id,
            source=SnapshotSource(registro.source),
            conteudo=registro.conteudo,
            contexto=registro.contexto or {},
            relevancia=registro.relevancia,
            criado_em=registro.criado_em,
            consolidado=registro.consolidado,
            consolidado_em=registro.consolidado_em,
        )


# Instância singleton
snapshot_manager = SnapshotManager()
