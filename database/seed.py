"""
Seed do banco de dados — cria os usuários iniciais.

Executado na primeira inicialização do sistema.
Cria Thiago (CEO) e Jonatas (Diretor Técnico e Operations Lead).
Senha inicial: SyneriumFactory@2026 (devem trocar no primeiro login).
"""

import logging

from sqlalchemy.orm import Session

from database.models import UsuarioDB

logger = logging.getLogger("synerium.database.seed")

SENHA_INICIAL = "SyneriumFactory@2026"

USUARIOS_SEED = [
    {
        "email": "thiago@objetivasolucao.com.br",
        "nome": "Thiago",
        "cargo": "CEO",
        "papeis": ["ceo"],
        "areas_aprovacao": [
            "deploy_producao", "gasto_ia", "mudanca_arquitetura",
            "campanha_marketing", "outreach_massa",
        ],
        "pode_aprovar": True,
    },
    {
        "email": "jonatas@objetivasolucao.com.br",
        "nome": "Jonatas",
        "cargo": "Diretor Técnico e Operations Lead",
        "papeis": ["diretor_tecnico", "operations_lead"],
        "areas_aprovacao": [
            "deploy_producao", "gasto_ia", "mudanca_arquitetura",
            "campanha_marketing", "outreach_massa",
        ],
        "pode_aprovar": True,
    },
]


def executar_seed(db: Session):
    """
    Cria os usuários iniciais se não existirem.

    Verifica por email para evitar duplicatas.
    """
    from api.security import hash_senha

    criados = 0
    for dados in USUARIOS_SEED:
        existente = db.query(UsuarioDB).filter_by(email=dados["email"]).first()
        if existente:
            logger.info(f"[SEED] Usuário já existe: {dados['email']}")
            continue

        usuario = UsuarioDB(
            email=dados["email"],
            password_hash=hash_senha(SENHA_INICIAL),
            nome=dados["nome"],
            cargo=dados["cargo"],
            papeis=dados["papeis"],
            areas_aprovacao=dados["areas_aprovacao"],
            pode_aprovar=dados["pode_aprovar"],
            company_id=1,
        )
        db.add(usuario)
        criados += 1
        logger.info(f"[SEED] Usuário criado: {dados['nome']} ({dados['email']})")

    if criados > 0:
        db.commit()
        logger.info(
            f"[SEED] {criados} usuário(s) criado(s). "
            f"Senha inicial: {SENHA_INICIAL} (trocar no primeiro login!)"
        )
    else:
        logger.info("[SEED] Nenhum usuário novo criado (todos já existem).")
