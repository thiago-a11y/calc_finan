"""
Rota: Status Geral da Fábrica

GET /api/status — Visão geral completa do Synerium Factory.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from api.dependencias import obter_fabrica, obter_usuario_atual
from api.schemas import StatusGeralResponse, SquadResumo, VaultResumo, UsuarioResumo
from database.models import UsuarioDB
from database.session import get_db
from sqlalchemy.orm import Session
from gates.approval_gates import approval_gate

router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/status", response_model=StatusGeralResponse)
def obter_status(fabrica=Depends(obter_fabrica), usuario: UsuarioDB = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """Retorna o status geral da fábrica — squads, aprovações, RAG."""

    squads = [
        SquadResumo(
            nome=nome,
            especialidade=squad.especialidade,
            contexto=squad.contexto,
            num_agentes=len(squad.agentes),
            num_tarefas=len(squad.tarefas),
        )
        for nome, squad in fabrica.squads.items()
    ]

    vaults = [
        VaultResumo(nome=nome, caminho=caminho)
        for nome, caminho in fabrica.rag_config.vaults.items()
    ]

    pendentes = len(approval_gate.listar_pendentes())

    # Buscar usuarios ATIVOS do banco (nao do config estatico)
    usuarios_db = db.query(UsuarioDB).filter_by(ativo=True).all()
    lideranca = [
        UsuarioResumo(
            id=str(u.id),
            nome=u.nome or "",
            cargo=u.cargo or "",
            pode_aprovar=u.pode_aprovar or False,
        )
        for u in usuarios_db
    ]

    return StatusGeralResponse(
        ambiente=fabrica.rag_config.company_id,
        data_hora=datetime.now().strftime("%d/%m/%Y %H:%M"),
        lideranca=lideranca,
        squads=squads,
        total_squads=len(squads),
        aprovacoes_pendentes=pendentes,
        rag_vaults=vaults,
        total_vaults=len(vaults),
    )
