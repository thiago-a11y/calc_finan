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
    Carrega squads dinamicamente do banco de dados (catálogo de agentes).
    """
    global _fabrica

    from orchestrator import SyneriumFactory
    from tools.skills_setup import inicializar_skills
    from database.session import SessionLocal

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
    # Carregar squads dinamicamente do banco
    # ==========================================
    db = SessionLocal()
    try:
        _carregar_squads_do_banco(_fabrica, db)
    finally:
        db.close()

    # ==========================================
    # Squads de Área (compartilhados, sem agentes do catálogo)
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


def _carregar_squads_do_banco(fabrica, db):
    """Carrega squads de TODOS os usuários que têm agentes atribuídos."""
    from database.models import UsuarioDB, AgenteAtribuidoDB

    # Encontrar todos os usuários com atribuições ativas
    usuarios_com_agentes = (
        db.query(UsuarioDB)
        .join(AgenteAtribuidoDB, AgenteAtribuidoDB.usuario_id == UsuarioDB.id)
        .filter(AgenteAtribuidoDB.ativo == True, UsuarioDB.ativo == True)
        .distinct()
        .all()
    )

    for usuario in usuarios_com_agentes:
        carregar_squad_usuario(fabrica, usuario.id, db)

    logger.info(f"[SQUADS] {len(usuarios_com_agentes)} squads carregados do banco.")


def carregar_squad_usuario(fabrica, usuario_id: int, db):
    """
    Carrega/recarrega o squad de um usuário a partir das atribuições no banco.

    Usado na inicialização e no hot-reload ao atribuir/remover agentes.
    """
    from database.models import UsuarioDB, AgenteAtribuidoDB, AgenteCatalogoDB
    from squads.squad_template import SquadPessoal
    from tools.registry import skill_registry

    usuario = db.query(UsuarioDB).filter_by(id=usuario_id, ativo=True).first()
    if not usuario:
        return

    atribuicoes = (
        db.query(AgenteAtribuidoDB)
        .filter_by(usuario_id=usuario.id, ativo=True)
        .order_by(AgenteAtribuidoDB.ordem)
        .all()
    )

    if not atribuicoes:
        # Remover squad existente se não tem mais agentes
        nome_squad = _nome_squad_usuario(usuario)
        fabrica.squads.pop(nome_squad, None)
        return

    # Determinar especialidade com base no cargo
    especialidade = f"Squad Pessoal — {usuario.cargo or 'Geral'}"
    nome_squad = _nome_squad_usuario(usuario)

    squad = SquadPessoal(
        nome_membro=f"{usuario.nome} ({usuario.cargo})",
        especialidade=especialidade,
        contexto=(
            f"Squad pessoal de {usuario.nome}. "
            f"Email: {usuario.email}. "
            "Domínio: @objetivasolucao.com.br."
        ),
        tools=[fabrica.ferramenta_rag] if hasattr(fabrica, 'ferramenta_rag') else [],
    )

    for atrib in atribuicoes:
        catalogo = db.query(AgenteCatalogoDB).filter_by(id=atrib.agente_catalogo_id).first()
        if not catalogo or not catalogo.ativo:
            continue

        objetivo = atrib.objetivo_custom or catalogo.objetivo
        historia = (atrib.historia_custom or catalogo.historia) + (catalogo.regras_extras or "")

        squad.criar_agente_auxiliar(
            papel=catalogo.papel,
            objetivo=objetivo,
            historia=historia,
            perfil_agente=catalogo.perfil_agente,
        )

        # Atribuir tools do perfil
        kit = skill_registry.montar_kit(catalogo.perfil_agente)
        if kit:
            squad.agentes[-1].tools = kit

    fabrica.squads[nome_squad] = squad
    logger.info(
        f"[SQUAD] {'Recarregado' if nome_squad in fabrica.squads else 'Registrado'}: "
        f"{nome_squad} ({len(squad.agentes)} agentes)"
    )


def _nome_squad_usuario(usuario) -> str:
    """Gera o nome do squad a partir do usuário."""
    cargo_curto = usuario.cargo.split(" e ")[0] if usuario.cargo else "Membro"
    return f"{cargo_curto} — {usuario.nome}"


def inicializar_banco():
    """
    Cria as tabelas do banco e executa o seed inicial.

    Chamado uma única vez no startup do FastAPI.
    """
    from database.models import Base
    from database.session import engine, SessionLocal
    from database.seed import executar_seed
    from database.seed_catalogo import executar_seed_catalogo

    logger.info("[DB] Criando tabelas do banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] Tabelas criadas com sucesso.")

    # Seed — criar usuários iniciais + catálogo de agentes
    db = SessionLocal()
    try:
        executar_seed(db)
        executar_seed_catalogo(db)
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
