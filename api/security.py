"""
Módulo de Segurança — JWT + bcrypt

Implementa autenticação JWT (HS256) e hashing de senhas
seguindo o padrão do SyneriumX adaptado para Python/FastAPI.
"""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from config.settings import settings

logger = logging.getLogger("synerium.security")

# --- Configuração ---

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
TOKEN_EXPIRATION_MINUTES = settings.jwt_expiration_minutes
REFRESH_TOKEN_EXPIRATION_DAYS = settings.jwt_refresh_expiration_days


# --- Senhas (bcrypt direto, sem passlib) ---

def hash_senha(senha: str) -> str:
    """Gera hash bcrypt de uma senha."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_senha(senha: str, hash_str: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(senha.encode("utf-8"), hash_str.encode("utf-8"))


# --- JWT ---

def criar_token_jwt(dados: dict, expira_em: timedelta | None = None) -> str:
    """
    Cria um token JWT assinado.

    Args:
        dados: Payload do token (user_id, email, etc.)
        expira_em: Duração do token. Padrão: 1 hora.

    Returns:
        Token JWT assinado como string.
    """
    payload = dados.copy()
    if expira_em is None:
        expira_em = timedelta(minutes=TOKEN_EXPIRATION_MINUTES)

    payload["exp"] = datetime.now(timezone.utc) + expira_em
    payload["iat"] = datetime.now(timezone.utc)

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def criar_refresh_token(user_id: int, email: str) -> str:
    """Cria um refresh token (30 dias)."""
    return criar_token_jwt(
        dados={"sub": str(user_id), "email": email, "type": "refresh"},
        expira_em=timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS),
    )


def criar_access_token(user_id: int, email: str, nome: str,
                        papeis: list[str], company_id: int) -> str:
    """Cria um access token (1 hora) com dados do usuário."""
    return criar_token_jwt(
        dados={
            "sub": str(user_id),
            "email": email,
            "nome": nome,
            "papeis": papeis,
            "company_id": company_id,
            "type": "access",
        },
    )


def decodificar_token(token: str) -> dict | None:
    """
    Decodifica e valida um token JWT.

    Returns:
        Payload do token se válido, None se inválido/expirado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"[SECURITY] Token inválido: {e}")
        return None
