"""
Rotas: Propostas de Edição do SyneriumX

GET  /api/propostas              — Lista todas as propostas
GET  /api/propostas/:id          — Detalhe de uma proposta
POST /api/propostas/:id/aprovar  — Aprova e aplica a edição
POST /api/propostas/:id/rejeitar — Rejeita a proposta
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencias import obter_usuario_atual
from database.models import UsuarioDB

logger = logging.getLogger("synerium.propostas")

router = APIRouter(prefix="/api", tags=["Propostas de Edição"])

PROPOSTAS_DIR = os.path.expanduser("~/synerium-factory/data/propostas_edicao")


def _carregar_propostas() -> list[dict]:
    """Carrega todas as propostas do diretório."""
    if not os.path.isdir(PROPOSTAS_DIR):
        return []

    propostas = []
    for arquivo in sorted(Path(PROPOSTAS_DIR).glob("*.json"), reverse=True):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                proposta = json.load(f)
                propostas.append(proposta)
        except Exception:
            continue
    return propostas


def _salvar_proposta(proposta: dict):
    """Salva uma proposta de volta no disco."""
    proposta_path = os.path.join(PROPOSTAS_DIR, f"{proposta['id']}.json")
    with open(proposta_path, "w", encoding="utf-8") as f:
        json.dump(proposta, f, ensure_ascii=False, indent=2)


@router.get("/propostas")
def listar_propostas(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Lista todas as propostas de edição."""
    return _carregar_propostas()


@router.get("/propostas/{proposta_id}")
def detalhe_proposta(proposta_id: str, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna detalhes de uma proposta específica."""
    propostas = _carregar_propostas()
    proposta = next((p for p in propostas if p["id"] == proposta_id), None)
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")
    return proposta


class RejeicaoRequest(BaseModel):
    motivo: str = ""


@router.post("/propostas/{proposta_id}/aprovar")
def aprovar_proposta(proposta_id: str, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """
    Aprova a proposta e aplica a edição no arquivo real.
    Apenas proprietários do projeto (CEO/Diretor Técnico) podem aprovar.
    """
    # Verificar permissão
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(
            status_code=403,
            detail="Apenas o proprietário/líder técnico pode aprovar edições."
        )

    propostas = _carregar_propostas()
    proposta = next((p for p in propostas if p["id"] == proposta_id), None)
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")

    if proposta["status"] != "pendente":
        raise HTTPException(status_code=400, detail=f"Proposta já está '{proposta['status']}'.")

    # Aplicar a edição no arquivo real
    try:
        caminho_abs = proposta["caminho_absoluto"]

        # Criar diretórios intermediários se necessário
        os.makedirs(os.path.dirname(caminho_abs), exist_ok=True)

        # Escrever o conteúdo novo
        with open(caminho_abs, "w", encoding="utf-8") as f:
            f.write(proposta["conteudo_novo"])

        # Atualizar status da proposta
        proposta["status"] = "aprovada"
        proposta["aprovado_por"] = usuario.nome
        proposta["aprovado_em"] = datetime.now().isoformat()
        _salvar_proposta(proposta)

        logger.info(
            f"[PROPOSTA] Aprovada e aplicada: {proposta_id} — "
            f"{proposta['caminho']} por {usuario.nome}"
        )

        # ========================================
        # PIPELINE: Build + Commit + Deploy request
        # ========================================
        pipeline_resultado = None
        try:
            from tools.deploy_pipeline import pipeline_pos_aprovacao
            pipeline_resultado = pipeline_pos_aprovacao(proposta)
            logger.info(f"[PIPELINE] Executado para proposta {proposta_id}")
        except Exception as pe:
            logger.error(f"[PIPELINE] Erro: {pe}")
            pipeline_resultado = {"erro": str(pe)}

        return {
            "mensagem": f"Proposta aprovada e aplicada com sucesso!",
            "arquivo": proposta["caminho"],
            "aprovado_por": usuario.nome,
            "pipeline": pipeline_resultado,
        }

    except Exception as e:
        proposta["status"] = "erro"
        proposta["erro"] = str(e)
        _salvar_proposta(proposta)
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar edição: {e}")


@router.post("/propostas/{proposta_id}/rejeitar")
def rejeitar_proposta(
    proposta_id: str,
    req: RejeicaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Rejeita a proposta de edição."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(
            status_code=403,
            detail="Apenas o proprietário/líder técnico pode rejeitar edições."
        )

    propostas = _carregar_propostas()
    proposta = next((p for p in propostas if p["id"] == proposta_id), None)
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")

    proposta["status"] = "rejeitada"
    proposta["rejeitado_por"] = usuario.nome
    proposta["rejeitado_em"] = datetime.now().isoformat()
    proposta["motivo_rejeicao"] = req.motivo
    _salvar_proposta(proposta)

    logger.info(
        f"[PROPOSTA] Rejeitada: {proposta_id} — {proposta['caminho']} por {usuario.nome}"
    )

    return {
        "mensagem": "Proposta rejeitada.",
        "arquivo": proposta["caminho"],
        "rejeitado_por": usuario.nome,
    }


# =====================================================================
# DEPLOYS — 2ª aprovação (git push)
# =====================================================================

DEPLOYS_DIR = os.path.expanduser("~/synerium-factory/data/deploys")


def _carregar_deploys() -> list[dict]:
    """Carrega todas as solicitações de deploy."""
    if not os.path.isdir(DEPLOYS_DIR):
        return []
    deploys = []
    for arquivo in sorted(Path(DEPLOYS_DIR).glob("*.json"), reverse=True):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                deploys.append(json.load(f))
        except Exception:
            continue
    return deploys


def _salvar_deploy(deploy: dict):
    """Salva deploy de volta no disco."""
    deploy_path = os.path.join(DEPLOYS_DIR, f"{deploy['id']}.json")
    with open(deploy_path, "w", encoding="utf-8") as f:
        json.dump(deploy, f, ensure_ascii=False, indent=2)


@router.get("/deploys")
def listar_deploys(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Lista todas as solicitações de deploy."""
    return _carregar_deploys()


@router.post("/deploys/{deploy_id}/aprovar")
def aprovar_deploy(deploy_id: str, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """
    Aprova o deploy e executa git push.
    2ª aprovação — CEO/Diretor aprova o push para produção.
    """
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode aprovar deploys.")

    deploys = _carregar_deploys()
    deploy = next((d for d in deploys if d["id"] == deploy_id), None)
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy não encontrado.")

    if deploy["status"] != "pendente":
        raise HTTPException(status_code=400, detail=f"Deploy já está '{deploy['status']}'.")

    # Executar git push
    try:
        from tools.deploy_pipeline import executar_git_push
        push_resultado = executar_git_push()

        deploy["status"] = "deployado" if push_resultado["sucesso"] else "erro_push"
        deploy["aprovado_por"] = usuario.nome
        deploy["aprovado_em"] = datetime.now().isoformat()
        deploy["push_resultado"] = push_resultado
        _salvar_deploy(deploy)

        if push_resultado["sucesso"]:
            logger.info(f"[DEPLOY] Push executado com sucesso: {deploy_id} por {usuario.nome}")
            return {
                "mensagem": "Deploy aprovado e push executado! GitHub Actions vai completar o deploy.",
                "deploy_id": deploy_id,
                "push": push_resultado,
            }
        else:
            logger.error(f"[DEPLOY] Push falhou: {deploy_id} — {push_resultado['saida']}")
            return {
                "mensagem": "Deploy aprovado mas push falhou. Verifique os logs.",
                "deploy_id": deploy_id,
                "push": push_resultado,
            }
    except Exception as e:
        deploy["status"] = "erro"
        deploy["erro"] = str(e)
        _salvar_deploy(deploy)
        raise HTTPException(status_code=500, detail=f"Erro no deploy: {e}")


@router.post("/deploys/{deploy_id}/rejeitar")
def rejeitar_deploy(deploy_id: str, usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Rejeita o deploy (não faz push)."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode rejeitar deploys.")

    deploys = _carregar_deploys()
    deploy = next((d for d in deploys if d["id"] == deploy_id), None)
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy não encontrado.")

    deploy["status"] = "rejeitado"
    deploy["rejeitado_por"] = usuario.nome
    deploy["rejeitado_em"] = datetime.now().isoformat()
    _salvar_deploy(deploy)

    logger.info(f"[DEPLOY] Rejeitado: {deploy_id} por {usuario.nome}")
    return {"mensagem": "Deploy rejeitado. Nenhum push foi feito."}
