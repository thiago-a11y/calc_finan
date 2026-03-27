"""
Rota: Aprovações (Approval Gates)

GET  /api/aprovacoes          — Lista todas as aprovações (filtro opcional)
POST /api/aprovacoes           — Cria nova solicitação de aprovação
POST /api/aprovacoes/{id}/acao — Aprovar ou rejeitar uma solicitação
"""

from fastapi import APIRouter, Depends, HTTPException

from api.dependencias import obter_fabrica, obter_usuario_atual
from database.models import UsuarioDB
from api.schemas import (
    AprovacaoResponse,
    AprovacaoAcaoRequest,
    CriarAprovacaoRequest,
)
from gates.approval_gates import approval_gate

router = APIRouter(prefix="/api", tags=["Aprovações"])


@router.get("/aprovacoes", response_model=list[AprovacaoResponse])
def listar_aprovacoes(pendentes: bool = False, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """
    Lista aprovações. Use ?pendentes=true para filtrar apenas pendentes.
    """
    historico = approval_gate.historico

    if pendentes:
        historico = [s for s in historico if s.aprovado is None]

    return [
        AprovacaoResponse(
            indice=i,
            tipo=s.tipo.value,
            descricao=s.descricao,
            solicitante=s.solicitante,
            valor_estimado=s.valor_estimado,
            criado_em=s.criado_em,
            aprovado=s.aprovado,
            aprovado_por=s.aprovado_por,
        )
        for i, s in enumerate(historico)
    ]


@router.post("/aprovacoes", response_model=AprovacaoResponse)
def criar_aprovacao(req: CriarAprovacaoRequest, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Cria uma nova solicitação de aprovação."""
    solicitacao = approval_gate.requer_aprovacao(
        tipo=req.tipo,
        descricao=req.descricao,
        solicitante=req.solicitante,
        valor=req.valor_estimado,
    )

    indice = len(approval_gate.historico) - 1
    return AprovacaoResponse(
        indice=indice,
        tipo=solicitacao.tipo.value,
        descricao=solicitacao.descricao,
        solicitante=solicitacao.solicitante,
        valor_estimado=solicitacao.valor_estimado,
        criado_em=solicitacao.criado_em,
        aprovado=solicitacao.aprovado,
        aprovado_por=solicitacao.aprovado_por,
    )


@router.post("/aprovacoes/{indice}/acao", response_model=AprovacaoResponse)
def acao_aprovacao(indice: int, req: AprovacaoAcaoRequest, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """
    Aprovar ou rejeitar uma solicitação pelo índice.

    Body: { "aprovado": true } para aprovar, { "aprovado": false } para rejeitar.
    """
    if indice < 0 or indice >= len(approval_gate.historico):
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    solicitacao = approval_gate.historico[indice]

    if solicitacao.aprovado is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Solicitação já foi {'aprovada' if solicitacao.aprovado else 'rejeitada'}.",
        )

    if req.aprovado:
        approval_gate.aprovar(solicitacao)
    else:
        approval_gate.rejeitar(solicitacao)

    return AprovacaoResponse(
        indice=indice,
        tipo=solicitacao.tipo.value,
        descricao=solicitacao.descricao,
        solicitante=solicitacao.solicitante,
        valor_estimado=solicitacao.valor_estimado,
        criado_em=solicitacao.criado_em,
        aprovado=solicitacao.aprovado,
        aprovado_por=solicitacao.aprovado_por,
    )
