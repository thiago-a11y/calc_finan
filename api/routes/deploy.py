"""
Rotas: Deploy Pipeline V2

POST /api/deploy/executar    — Inicia deploy com progresso
GET  /api/deploy/progresso/:id — Consulta progresso em tempo real
GET  /api/deploy/historico   — Lista todos os deploys
"""

import logging
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencias import obter_usuario_atual
from database.models import UsuarioDB

logger = logging.getLogger("synerium.deploy.api")

router = APIRouter(prefix="/api/deploy", tags=["Deploy"])


class DeployRequest(BaseModel):
    descricao: str
    arquivos: list[str] | None = None


@router.post("/executar")
def iniciar_deploy(req: DeployRequest, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """
    Inicia o pipeline de deploy em background.
    Retorna o deploy_id para acompanhar o progresso.
    """
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode iniciar deploys.")

    from tools.deploy_pipeline_v2 import executar_deploy_completo

    deploy_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Executar em background thread
    def _run_deploy():
        try:
            executar_deploy_completo(
                deploy_id=deploy_id,
                descricao=req.descricao,
                arquivos=req.arquivos,
                usuario=usuario.nome,
            )
        except Exception as e:
            logger.error(f"[DEPLOY] Erro fatal: {e}")

    thread = threading.Thread(target=_run_deploy, daemon=True)
    thread.start()

    logger.info(f"[DEPLOY] Iniciado: {deploy_id} por {usuario.nome} — {req.descricao}")

    return {
        "deploy_id": deploy_id,
        "mensagem": "Deploy iniciado! Acompanhe o progresso em tempo real.",
        "status": "executando",
    }


@router.get("/progresso/{deploy_id}")
def obter_progresso_deploy(deploy_id: str, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna o progresso atual de um deploy."""
    from tools.deploy_pipeline_v2 import obter_progresso

    progresso = obter_progresso(deploy_id)
    if not progresso:
        raise HTTPException(status_code=404, detail="Deploy não encontrado.")
    return progresso


@router.get("/historico")
def listar_historico(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Lista todos os deploys realizados."""
    from tools.deploy_pipeline_v2 import listar_deploys_v2
    return listar_deploys_v2()
