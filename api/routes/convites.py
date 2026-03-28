"""
Rotas de Convites — Criar, enviar e validar convites por email

POST /api/convites          — Criar e enviar convite (CEO/admin only)
GET  /api/convites/{token}  — Validar token de convite
GET  /api/convites          — Listar convites pendentes
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import ConviteDB, UsuarioDB, AuditLogDB

logger = logging.getLogger("synerium.convites")

router = APIRouter(prefix="/api/convites", tags=["Convites"])


class CriarConviteRequest(BaseModel):
    email: EmailStr
    nome: str = ""
    cargo: str = ""
    papeis: list[str] = []
    enviar_email: bool = True  # Toggle para enviar ou não


class ConviteResponse(BaseModel):
    id: int
    email: str
    nome: str
    token: str
    link_registro: str
    expira_em: str
    usado: bool
    email_enviado: bool = False


@router.post("", response_model=ConviteResponse)
def criar_convite(
    req: CriarConviteRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Cria convite e envia email via Amazon SES.
    Apenas CEO/Diretor/Operations Lead podem convidar.
    """
    # Verificar permissão
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode enviar convites.")

    # Verificar se email já está cadastrado
    existente = db.query(UsuarioDB).filter_by(email=req.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado no sistema.")

    # Verificar convite pendente
    pendente = db.query(ConviteDB).filter_by(email=req.email, usado=False).first()
    if pendente:
        raise HTTPException(status_code=409, detail="Já existe um convite pendente para este email.")

    # Gerar token seguro (hex para evitar ambiguidade visual l/I/1/O/0)
    token = secrets.token_hex(32)

    convite = ConviteDB(
        email=req.email,
        nome=req.nome,
        cargo=req.cargo,
        papeis=req.papeis,
        token=token,
        convidado_por_id=usuario.id,
        company_id=usuario.company_id or 1,
        expira_em=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(convite)
    db.commit()
    db.refresh(convite)

    # Link de registro
    import os
    base_url = os.getenv("SYNERIUM_BASE_URL", "https://synerium-factory.objetivasolucao.com.br")
    link = f"{base_url}/registrar?token={token}"

    # Enviar email via SES
    email_enviado = False
    if req.enviar_email:
        try:
            from services.email_service import enviar_convite
            resultado = enviar_convite(
                nome=req.nome or req.email.split("@")[0],
                email=req.email,
                token=token,
                cargo=req.cargo,
                convidado_por=usuario.nome,
            )
            email_enviado = resultado.get("sucesso", False)
        except Exception as e:
            logger.error(f"[CONVITE] Erro ao enviar email: {e}")
            # Não bloqueia a criação — apenas loga

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="CRIAR_CONVITE",
        descricao=f"Convite enviado para {req.nome} ({req.email}) — email={'enviado' if email_enviado else 'falhou'}",
        ip="api",
        company_id=usuario.company_id or 1,
    ))
    db.commit()

    logger.info(f"[CONVITE] Criado por {usuario.nome} para {req.email} — email={'OK' if email_enviado else 'FALHOU'}")

    return ConviteResponse(
        id=convite.id,
        email=convite.email,
        nome=convite.nome,
        token=convite.token,
        link_registro=link,
        expira_em=convite.expira_em.isoformat(),
        usado=convite.usado,
        email_enviado=email_enviado,
    )


@router.get("")
def listar_convites(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista convites pendentes (apenas admin)."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Sem permissão.")

    convites = db.query(ConviteDB).order_by(ConviteDB.id.desc()).limit(50).all()
    return [
        {
            "id": c.id,
            "email": c.email,
            "nome": c.nome,
            "cargo": c.cargo,
            "usado": c.usado,
            "token": c.token,
            "expira_em": c.expira_em.isoformat() if c.expira_em else "",
            "criado_em": c.criado_em.isoformat() if c.criado_em else "",
        }
        for c in convites
    ]


@router.get("/{token}")
def validar_convite(token: str, db: Session = Depends(get_db)):
    """Valida se um token de convite é válido e não expirou."""
    convite = db.query(ConviteDB).filter_by(token=token, usado=False).first()

    if not convite:
        raise HTTPException(status_code=404, detail="Convite não encontrado ou já utilizado.")

    if convite.expira_em < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Convite expirado.")

    return {
        "valido": True,
        "email": convite.email,
        "nome": convite.nome,
        "cargo": convite.cargo,
    }
