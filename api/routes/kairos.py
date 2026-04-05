"""
Kairos — API REST do sistema de memória auto-evolutiva.

Endpoints:
- GET  /api/kairos/status          — Status geral do sistema
- GET  /api/kairos/snapshots       — Lista snapshots (paginação + filtros)
- GET  /api/kairos/memories        — Lista memórias consolidadas (busca + filtros)
- POST /api/kairos/dream/manual    — Dispara ciclo de dream manualmente

Todos os endpoints requerem autenticação JWT.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import UsuarioDB, MemorySnapshotDB, MemoryEntryDB
from core.memory.kairos.service import kairos_service
from core.memory.kairos.types import SnapshotSource, MemoryType

logger = logging.getLogger("synerium.kairos.api")

router = APIRouter(prefix="/api/kairos", tags=["Kairos"])


# =====================================================================
# GET /status — Status geral do sistema Kairos
# =====================================================================

@router.get("/status")
def kairos_status(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Retorna status geral do sistema de memória Kairos."""
    tenant_id = usuario.company_id or 1
    status = kairos_service.status(tenant_id=tenant_id)

    # Contar por source
    db_local = None
    por_source = {}
    por_agente = {}
    try:
        from database.session import SessionLocal
        db_local = SessionLocal()

        # Snapshots por source
        from sqlalchemy import func
        rows = (
            db_local.query(MemorySnapshotDB.source, func.count())
            .filter(MemorySnapshotDB.tenant_id == tenant_id)
            .group_by(MemorySnapshotDB.source)
            .all()
        )
        por_source = {r[0]: r[1] for r in rows}

        # Memórias por agente
        rows = (
            db_local.query(MemoryEntryDB.agente_id, func.count())
            .filter(MemoryEntryDB.tenant_id == tenant_id, MemoryEntryDB.ativo == True)  # noqa
            .group_by(MemoryEntryDB.agente_id)
            .all()
        )
        por_agente = {r[0]: r[1] for r in rows}
    except Exception:
        pass
    finally:
        if db_local:
            db_local.close()

    return {
        **status,
        "snapshots_por_source": por_source,
        "memorias_por_agente": por_agente,
    }


# =====================================================================
# GET /snapshots — Lista snapshots com paginação e filtros
# =====================================================================

@router.get("/snapshots")
def listar_snapshots(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
    agente_id: str | None = Query(None, description="Filtrar por agente"),
    source: str | None = Query(None, description="Filtrar por source (luna, mission_control, etc.)"),
    consolidado: bool | None = Query(None, description="Filtrar por status de consolidação"),
    limite: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """Lista snapshots de memória com filtros opcionais."""
    tenant_id = usuario.company_id or 1

    query = db.query(MemorySnapshotDB).filter(
        MemorySnapshotDB.tenant_id == tenant_id,
    )

    if agente_id:
        query = query.filter(MemorySnapshotDB.agente_id == agente_id)
    if source:
        query = query.filter(MemorySnapshotDB.source == source)
    if consolidado is not None:
        query = query.filter(MemorySnapshotDB.consolidado == consolidado)

    total = query.count()

    registros = (
        query
        .order_by(MemorySnapshotDB.criado_em.desc())
        .offset(offset)
        .limit(limite)
        .all()
    )

    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "snapshots": [
            {
                "id": r.id,
                "agente_id": r.agente_id,
                "source": r.source,
                "conteudo": r.conteudo[:500],
                "contexto": r.contexto,
                "relevancia": r.relevancia,
                "consolidado": r.consolidado,
                "consolidado_em": r.consolidado_em.isoformat() if r.consolidado_em else None,
                "criado_em": r.criado_em.isoformat() if r.criado_em else None,
            }
            for r in registros
        ],
    }


# =====================================================================
# GET /memories — Lista memórias consolidadas com busca e filtros
# =====================================================================

@router.get("/memories")
def listar_memorias(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
    agente_id: str | None = Query(None, description="Filtrar por agente"),
    tipo: str | None = Query(None, description="Filtrar por tipo (episodica, semantica, procedural, estrategica)"),
    query: str | None = Query(None, alias="q", description="Busca textual no título e conteúdo"),
    min_relevancia: float = Query(0.0, ge=0.0, le=1.0, description="Relevância mínima"),
    limite: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """Lista memórias consolidadas com busca textual e filtros."""
    tenant_id = usuario.company_id or 1

    q = db.query(MemoryEntryDB).filter(
        MemoryEntryDB.tenant_id == tenant_id,
        MemoryEntryDB.ativo == True,  # noqa
    )

    if agente_id:
        q = q.filter(MemoryEntryDB.agente_id == agente_id)
    if tipo:
        q = q.filter(MemoryEntryDB.tipo == tipo)
    if min_relevancia > 0:
        q = q.filter(MemoryEntryDB.relevancia >= min_relevancia)
    if query:
        termo = f"%{query}%"
        q = q.filter(
            (MemoryEntryDB.titulo.ilike(termo))
            | (MemoryEntryDB.conteudo.ilike(termo))
        )

    total = q.count()

    registros = (
        q
        .order_by(MemoryEntryDB.relevancia.desc())
        .offset(offset)
        .limit(limite)
        .all()
    )

    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "memories": [
            {
                "id": r.id,
                "agente_id": r.agente_id,
                "tipo": r.tipo,
                "titulo": r.titulo,
                "conteudo": r.conteudo,
                "tags": r.tags or [],
                "relevancia": r.relevancia,
                "acessos": r.acessos or 0,
                "ultimo_acesso": r.ultimo_acesso.isoformat() if r.ultimo_acesso else None,
                "fonte_snapshots": r.fonte_snapshots or [],
                "criado_em": r.criado_em.isoformat() if r.criado_em else None,
                "atualizado_em": r.atualizado_em.isoformat() if r.atualizado_em else None,
            }
            for r in registros
        ],
    }


# =====================================================================
# POST /snapshot/teste — Cria snapshot de teste para validar o dream
# =====================================================================

@router.post("/snapshot/teste")
async def criar_snapshot_teste(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Cria um snapshot de teste para validar o fluxo do AutoDream."""
    from datetime import datetime

    logger.info(f"[Kairos/API] Snapshot de teste criado por {usuario.nome}")

    snapshot = await kairos_service.criar_snapshot(
        agente_id="teste",
        source="manual",
        conteudo=(
            f"Snapshot de teste criado manualmente por {usuario.nome} "
            f"em {datetime.now().strftime('%d/%m/%Y %H:%M')}. "
            f"Usado para validar o fluxo de consolidacao do AutoDream."
        ),
        contexto={
            "tipo_acao": "teste_manual",
            "usuario_id": usuario.id,
            "usuario_nome": usuario.nome,
        },
        tenant_id=usuario.company_id or 1,
        relevancia=0.3,
    )

    return {
        "sucesso": True,
        "snapshot_id": snapshot.id,
        "mensagem": f"Snapshot de teste criado: {snapshot.id}",
    }


# =====================================================================
# POST /dream/manual — Dispara ciclo de dream manualmente
# =====================================================================

@router.post("/dream/manual")
async def dream_manual(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Dispara um ciclo de dream (consolidação) manualmente.

    Útil para testes e para forçar consolidação imediata.
    Requer autenticação (qualquer usuário autenticado).
    """
    logger.info(f"[Kairos/API] Dream manual disparado por {usuario.nome}")

    resultado = await kairos_service.dream()

    return {
        "dream_id": resultado.dream_id,
        "status": resultado.status.value,
        "snapshots_processados": resultado.snapshots_processados,
        "memorias_criadas": resultado.memorias_criadas,
        "memorias_atualizadas": resultado.memorias_atualizadas,
        "memorias_removidas": resultado.memorias_removidas,
        "duracao_ms": round(resultado.duracao_ms, 1),
        "erro": resultado.erro,
    }
