"""
Rota: Standup Diário

POST /api/standup — Gera o relatório de standup diário.

Nota: Este endpoint dispara uma chamada LLM (CrewAI crew.kickoff)
e pode levar 10-30 segundos para responder.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from api.dependencias import obter_fabrica
from api.schemas import StandupResponse

router = APIRouter(prefix="/api", tags=["Standup"])


@router.post("/standup", response_model=StandupResponse)
def gerar_standup(fabrica=Depends(obter_fabrica)):
    """
    Gera o relatório de standup diário.

    Coleta status de todos os squads e usa o agente relator
    para compilar um relatório em português.

    Atenção: pode levar 10-30s (chamada LLM).
    """
    relatorio = fabrica.executar_standup()

    return StandupResponse(
        relatorio=str(relatorio),
        data_execucao=datetime.now().strftime("%d/%m/%Y %H:%M"),
        squads_reportados=len(fabrica.squads),
    )
