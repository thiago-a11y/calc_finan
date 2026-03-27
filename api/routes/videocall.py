"""
Rotas: Video Call — LiveKit (salas de áudio/vídeo em tempo real)

POST /api/videocall/token    — Gera token para entrar numa sala
GET  /api/videocall/salas     — Lista salas ativas
POST /api/videocall/encerrar  — Encerra uma sala
"""

import os
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants

from api.dependencias import obter_usuario_atual
from database.models import UsuarioDB

logger = logging.getLogger("synerium.videocall")

router = APIRouter(prefix="/api/videocall", tags=["Video Call"])

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")


class TokenRequest(BaseModel):
    sala: str  # Nome da sala (ex: "reuniao-thiago-jonatas")
    participante: str | None = None  # Nome do participante (default: nome do usuário)


class EncerrarRequest(BaseModel):
    sala: str


@router.post("/token")
def gerar_token(
    req: TokenRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Gera um token JWT do LiveKit para o usuário entrar numa sala.
    O token inclui permissões de áudio, vídeo e chat.
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit não configurado. Adicione LIVEKIT_API_KEY e LIVEKIT_API_SECRET no .env"
        )

    nome_participante = req.participante or usuario.nome

    # Criar token com permissões
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.identity = f"user-{usuario.id}"
    token.name = nome_participante

    # Permissões: pode publicar áudio/vídeo, assinar áudio/vídeo de outros
    grant = VideoGrants(
        room_join=True,
        room=req.sala,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,  # Chat de texto na sala
    )
    token.video_grants = grant

    # Gerar JWT
    jwt_token = token.to_jwt()

    logger.info(
        f"[VIDEOCALL] Token gerado: sala={req.sala}, participante={nome_participante} ({usuario.email})"
    )

    return {
        "token": jwt_token,
        "url": LIVEKIT_URL,
        "sala": req.sala,
        "participante": nome_participante,
    }


@router.get("/config")
def obter_config(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna configuração do LiveKit (URL pública)."""
    return {
        "url": LIVEKIT_URL,
        "configurado": bool(LIVEKIT_API_KEY and LIVEKIT_API_SECRET and LIVEKIT_URL),
    }
