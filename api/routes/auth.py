"""
Rotas de Autenticação — Login, Refresh, Registro, Trocar Senha

POST /auth/login          — Login com email/senha → JWT
POST /auth/refresh        — Refresh token → novo access token
POST /auth/registrar      — Completar registro via convite
POST /auth/trocar-senha   — Alterar senha (autenticado)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.security import (
    hash_senha, verificar_senha,
    criar_access_token, criar_refresh_token, decodificar_token,
)
from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import UsuarioDB, ConviteDB, AuditLogDB

logger = logging.getLogger("synerium.auth")

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# --- Schemas inline (simples, não precisa separar) ---

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistroRequest(BaseModel):
    token: str
    senha: str
    nome: str | None = None


class TrocarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


# --- Endpoints ---

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Login com email e senha.

    Retorna access_token (1h) + refresh_token (30d) + dados do usuário.
    """
    usuario = db.query(UsuarioDB).filter_by(email=req.email).first()

    if not usuario:
        logger.warning(f"[AUTH] Login falhou: email não encontrado ({req.email})")
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    # Verificar bloqueio
    if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423,
            detail="Conta bloqueada temporariamente. Tente novamente em 30 minutos.",
        )

    # Verificar senha
    if not verificar_senha(req.senha, usuario.password_hash):
        usuario.tentativas_login = (usuario.tentativas_login or 0) + 1
        if usuario.tentativas_login >= 10:
            from datetime import timedelta
            usuario.bloqueado_ate = datetime.now(timezone.utc) + timedelta(minutes=30)
            logger.warning(f"[AUTH] Conta bloqueada: {req.email} (10 tentativas)")
        db.commit()
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta desativada.")

    # Resetar tentativas e gerar tokens
    usuario.tentativas_login = 0
    usuario.bloqueado_ate = None
    db.commit()

    access_token = criar_access_token(
        user_id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        papeis=usuario.papeis or [],
        company_id=usuario.company_id,
    )
    refresh_token = criar_refresh_token(user_id=usuario.id, email=usuario.email)

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="LOGIN",
        descricao=f"Login bem-sucedido de {usuario.nome}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))
    db.commit()

    logger.info(f"[AUTH] Login: {usuario.nome} ({usuario.email})")

    from config.permissoes import calcular_permissoes_efetivas
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        usuario={
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "cargo": usuario.cargo,
            "papeis": usuario.papeis or [],
            "pode_aprovar": usuario.pode_aprovar,
            "avatar_url": usuario.avatar_url or "",
            "company_id": usuario.company_id,
            "permissoes_efetivas": calcular_permissoes_efetivas(
                papeis=usuario.papeis or [],
                overrides=usuario.permissoes_granulares,
            ),
        },
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """Renova o access token usando o refresh token."""
    payload = decodificar_token(req.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    user_id = int(payload["sub"])
    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()

    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")

    access_token = criar_access_token(
        user_id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        papeis=usuario.papeis or [],
        company_id=usuario.company_id,
    )

    return RefreshResponse(access_token=access_token)


@router.post("/registrar")
def registrar(req: RegistroRequest, db: Session = Depends(get_db)):
    """
    Completa o registro via convite.

    O usuário recebe um link com token, preenche a senha e a conta é criada.
    """
    convite = db.query(ConviteDB).filter_by(token=req.token, usado=False).first()

    if not convite:
        raise HTTPException(status_code=404, detail="Convite não encontrado ou já utilizado.")

    if convite.expira_em < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Convite expirado.")

    # Verificar se email já existe
    existente = db.query(UsuarioDB).filter_by(email=convite.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Email já registrado.")

    # Criar usuário
    usuario = UsuarioDB(
        email=convite.email,
        password_hash=hash_senha(req.senha),
        nome=req.nome or convite.nome,
        cargo=convite.cargo,
        papeis=convite.papeis or [],
        company_id=convite.company_id,
    )
    db.add(usuario)

    # Marcar convite como usado
    convite.usado = True
    db.commit()
    db.refresh(usuario)

    logger.info(f"[AUTH] Registro: {usuario.nome} ({usuario.email}) via convite")

    return {
        "mensagem": "Conta criada com sucesso!",
        "usuario": {"id": usuario.id, "nome": usuario.nome, "email": usuario.email},
    }


@router.post("/trocar-senha")
def trocar_senha(
    req: TrocarSenhaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Troca a senha do usuário autenticado."""
    # Verificar senha atual
    if not verificar_senha(req.senha_atual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    # Validar nova senha
    if len(req.nova_senha) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 8 caracteres.")

    # Atualizar senha
    usuario.password_hash = hash_senha(req.nova_senha)
    db.commit()

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="TROCAR_SENHA",
        descricao=f"Senha alterada por {usuario.nome}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))
    db.commit()

    logger.info(f"[AUTH] Senha alterada: {usuario.nome} ({usuario.email})")

    return {"mensagem": "Senha alterada com sucesso!"}
