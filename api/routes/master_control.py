"""
Rotas: Master Control — Feature Flags GUI (CEO Only)

GET  /api/master-control/flags           — Lista todas as flags com status
POST /api/master-control/flags/{nome}/toggle — Toggle uma flag
GET  /api/master-control/flags/history    — Histórico de alterações
POST /api/master-control/flags/{nome}/restart — Trigger restart do serviço
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual, get_db
from database.models import UsuarioDB, FeatureFlagDB, FeatureFlagHistoryDB

logger = logging.getLogger("synerium.master_control")

router = APIRouter(prefix="/api/master-control/flags", tags=["Master Control"])


# =====================================================================
# Schemas Pydantic
# =====================================================================

class FeatureFlagSchema(BaseModel):
    id: int
    nome: str
    habilitado: bool
    descricao: str
    requer_restart: bool
    atualizado_por: str
    atualizado_em: str | None

    class Config:
        from_attributes = True


class ToggleResponse(BaseModel):
    nome: str
    habilitado: bool
    requer_restart: bool
    mensagem: str


class HistoryEntrySchema(BaseModel):
    id: int
    flag_nome: str
    usuario_email: str
    valor_anterior: bool
    valor_novo: bool
    criado_em: str

    class Config:
        from_attributes = True


# =====================================================================
# Endpoints
# =====================================================================

@router.get("", response_model=list[FeatureFlagSchema])
def listar_flags(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Lista todas as feature flags com status atual.
    Acessível por qualquer usuário autenticado (para visualização).
    """
    flags = db.query(FeatureFlagDB).order_by(FeatureFlagDB.id).all()

    return [
        FeatureFlagSchema(
            id=f.id,
            nome=f.nome,
            habilitado=f.habilitado,
            descricao=f.descricao,
            requer_restart=f.requer_restart,
            atualizado_por=f.atualizado_por or "",
            atualizado_em=f.atualizado_em.isoformat() if f.atualizado_em else None,
        )
        for f in flags
    ]


@router.post("/{nome}/toggle", response_model=ToggleResponse)
def toggle_flag(
    nome: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Toggle uma feature flag. Apenas CEO pode executar.
    Registra a alteração no histórico.
    """
    # Verificar se é CEO
    if not any(p == "ceo" for p in (usuario.papeis or [])):
        raise HTTPException(
            status_code=403,
            detail="Apenas o CEO pode alterar feature flags.",
        )

    # Buscar a flag
    flag = db.query(FeatureFlagDB).filter(FeatureFlagDB.nome == nome).first()
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{nome}' não encontrada.")

    # Toggle
    valor_anterior = flag.habilitado
    flag.habilitado = not flag.habilitado
    flag.atualizado_por = usuario.email
    flag.atualizado_em = datetime.utcnow()

    # Registrar no histórico
    historico = FeatureFlagHistoryDB(
        flag_nome=nome,
        usuario_id=usuario.id,
        usuario_email=usuario.email,
        valor_anterior=valor_anterior,
        valor_novo=flag.habilitado,
    )
    db.add(historico)
    db.commit()

    logger.info(
        f"[MasterControl] Flag '{nome}' alterada de {valor_anterior} para "
        f"{flag.habilitado} por {usuario.email}"
    )

    status_texto = "ON" if flag.habilitado else "OFF"
    return ToggleResponse(
        nome=nome,
        habilitado=flag.habilitado,
        requer_restart=flag.requer_restart,
        mensagem=f"Flag '{nome}' alterada para {status_texto}.",
    )


@router.get("/history", response_model=list[HistoryEntrySchema])
def listar_historico(
    limit: int = 50,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Lista o histórico de alterações de flags (mais recente primeiro).
    Acessível por qualquer usuário autenticado.
    """
    entradas = (
        db.query(FeatureFlagHistoryDB)
        .order_by(FeatureFlagHistoryDB.criado_em.desc())
        .limit(limit)
        .all()
    )

    return [
        HistoryEntrySchema(
            id=e.id,
            flag_nome=e.flag_nome,
            usuario_email=e.usuario_email,
            valor_anterior=e.valor_anterior,
            valor_novo=e.valor_novo,
            criado_em=e.criado_em.isoformat() if e.criado_em else "",
        )
        for e in entradas
    ]


@router.post("/{nome}/restart")
def restart_servico(
    nome: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Marca que um restart foi solicitado para uma flag que requer restart.
    O restart em si é executado manualmente via SSH/systemd.
    """
    if not any(p == "ceo" for p in (usuario.papeis or [])):
        raise HTTPException(
            status_code=403,
            detail="Apenas o CEO pode solicitar restart.",
        )

    flag = db.query(FeatureFlagDB).filter(FeatureFlagDB.nome == nome).first()
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{nome}' não encontrada.")

    if not flag.requer_restart:
        raise HTTPException(
            status_code=400,
            detail=f"Flag '{nome}' não requer restart.",
        )

    logger.warning(
        f"[MasterControl] Restart solicitado para '{nome}' por {usuario.email}"
    )

    # Limpar requer_restart de TODAS as flags que têm essa flag como true
    # (após restart, nenhuma flag precisa de restart — o serviço já reiniciou)
    flags_para_limpar = db.query(FeatureFlagDB).filter(
        FeatureFlagDB.requer_restart == True
    ).all()
    for f in flags_para_limpar:
        f.requer_restart = False
    if flags_para_limpar:
        logger.info(f"[MasterControl] Flags com requer_restart limpos: {[f.nome for f in flags_para_limpar]}")

    # Executar o restart — mata o processo atual (SIGTERM).
    # systemd vai automaticamente reiniciar após RestartSec=5.
    # O response é enviado ANTES do kill para garantir que o usuário receba a confirmação.
    import os, signal, sys

    logger.info(f"[MasterControl] Solicitando restart do serviço por {usuario.email}")

    # Registrar no histórico ANTES de matar o processo
    historico = FeatureFlagHistoryDB(
        flag_nome=nome,
        usuario_id=usuario.id,
        usuario_email=usuario.email,
        valor_anterior=flag.habilitado,
        valor_novo=flag.habilitado,
    )
    db.add(historico)
    db.commit()

    # Enviar response ANTES de matar — senão o HTTP connection morre sem resposta
    # Usamos threads para não bloquear o response
    def restart_after_response():
        import time
        time.sleep(2)  # dá tempo do response chegar ao cliente
        os.kill(os.getpid(), signal.SIGTERM)

    import threading
    threading.Thread(target=restart_after_response, daemon=True).start()

    return {
        "mensagem": f"Restart solicitado para '{nome}'. "
        "O serviço será reiniciado em instantes.",
        "flag": nome,
        "solicitado_por": usuario.email,
    }

    return {
        "mensagem": f"Restart solicitado para '{nome}'. "
        "O serviço será reiniciado automaticamente em instantes.",
        "flag": nome,
        "solicitado_por": usuario.email,
    }
