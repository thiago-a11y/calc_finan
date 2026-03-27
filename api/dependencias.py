"""
Dependências compartilhadas da API.

Inclui:
- Singleton do SyneriumFactory
- Dependência de autenticação JWT (obter_usuario_atual)
- Inicialização do banco de dados
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.security import decodificar_token
from database.session import get_db
from database.models import UsuarioDB

logger = logging.getLogger("synerium.api")

# Esquema de autenticação Bearer
bearer_scheme = HTTPBearer(auto_error=False)

# Instância singleton da fábrica — inicializada no lifespan do FastAPI
_fabrica = None


def inicializar_fabrica():
    """
    Inicializa a instância singleton do SyneriumFactory.

    Chamado uma única vez no startup do FastAPI (via lifespan).
    Registra os squads padrão automaticamente.
    """
    global _fabrica

    from orchestrator import SyneriumFactory
    from squads.squad_ceo_thiago import criar_squad_ceo
    from squads.squad_diretor_jonatas import criar_squad_jonatas
    from tools.skills_setup import inicializar_skills

    logger.info("[API] Inicializando SyneriumFactory...")
    _fabrica = SyneriumFactory()

    # ==========================================
    # Inicializar Skills (ferramentas dos agentes)
    # ==========================================
    inicializar_skills(
        rag_query=_fabrica.rag_query,
        vault_factory_path=_fabrica.rag_config.vaults.get("factory", ""),
    )

    # ==========================================
    # Squad do CEO — Thiago (8 agentes turbinados)
    # ==========================================
    squad_ceo = criar_squad_ceo(tools=[_fabrica.ferramenta_rag])
    _fabrica.squads["CEO — Thiago"] = squad_ceo
    logger.info(
        f"[SQUAD] Registrado: CEO — Thiago "
        f"({len(squad_ceo.agentes)} agentes especializados)"
    )

    # ==========================================
    # Squad do Jonatas — Diretor Técnico (3 agentes)
    # ==========================================
    squad_jonatas = criar_squad_jonatas(tools=[_fabrica.ferramenta_rag])
    _fabrica.squads["Diretor Técnico — Jonatas"] = squad_jonatas
    logger.info(
        f"[SQUAD] Registrado: Diretor Técnico — Jonatas "
        f"({len(squad_jonatas.agentes)} agentes)"
    )

    # ==========================================
    # Squads de Área
    # ==========================================
    _fabrica.registrar_squad(
        nome="Dev Backend",
        especialidade="Desenvolvimento Backend PHP/Python",
        contexto="Foco em APIs REST, migrations, auditLog, company_id, LGPD.",
    )
    _fabrica.registrar_squad(
        nome="Dev Frontend",
        especialidade="Desenvolvimento Frontend React",
        contexto="Foco em UI/UX, componentes reutilizáveis e performance.",
    )
    _fabrica.registrar_squad(
        nome="Marketing",
        especialidade="Marketing Digital e Growth",
        contexto="Foco em campanhas, outreach e métricas de crescimento.",
    )

    logger.info("[API] SyneriumFactory inicializado com sucesso.")
    return _fabrica


def inicializar_banco():
    """
    Cria as tabelas do banco e executa o seed inicial.

    Chamado uma única vez no startup do FastAPI.
    """
    from database.models import Base
    from database.session import engine, SessionLocal
    from database.seed import executar_seed

    logger.info("[DB] Criando tabelas do banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] Tabelas criadas com sucesso.")

    # Seed — criar usuários iniciais
    db = SessionLocal()
    try:
        executar_seed(db)
    finally:
        db.close()

    logger.info("[DB] Banco de dados inicializado.")


def obter_fabrica():
    """Retorna a instância singleton do SyneriumFactory."""
    if _fabrica is None:
        raise RuntimeError(
            "SyneriumFactory não foi inicializado. "
            "Verifique se o lifespan do FastAPI está configurado."
        )
    return _fabrica


def obter_usuario_atual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UsuarioDB:
    """
    Dependência de autenticação — extrai o usuário do token JWT.

    Uso nas rotas protegidas:
        @router.get("/api/dados")
        def dados(usuario = Depends(obter_usuario_atual)):
            print(usuario.nome)  # Usuário autenticado
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido. Use um access token.",
        )

    user_id = int(payload.get("sub", 0))
    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()

    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou desativado.",
        )

    return usuario


def obter_usuario_opcional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UsuarioDB | None:
    """
    Dependência opcional — retorna o usuário se autenticado, None se não.

    Útil para rotas que funcionam com ou sem auth.
    """
    if credentials is None:
        return None

    payload = decodificar_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = int(payload.get("sub", 0))
    return db.query(UsuarioDB).filter_by(id=user_id, ativo=True).first()
