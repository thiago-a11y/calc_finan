"""
Cadastro de Usuários do Synerium Factory.

Define os perfis dos usuários do sistema com seus papéis,
permissões e áreas de aprovação.
"""

from enum import Enum
from pydantic import BaseModel


class Papel(str, Enum):
    """Papéis disponíveis no sistema."""
    CEO = "ceo"
    DIRETOR_TECNICO = "diretor_tecnico"
    OPERATIONS_LEAD = "operations_lead"
    PM_CENTRAL = "pm_central"
    LIDER = "lider"
    MEMBRO = "membro"


class Usuario(BaseModel):
    """Perfil de um usuário do Synerium Factory."""
    id: str
    nome: str
    cargo: str
    papeis: list[Papel]
    email: str = ""
    pode_aprovar: bool = False
    areas_aprovacao: list[str] = []
    ativo: bool = True


# =====================================================
# Cadastro de Usuários
# =====================================================

USUARIOS: dict[str, Usuario] = {
    "thiago": Usuario(
        id="thiago",
        nome="Thiago",
        cargo="CEO",
        papeis=[Papel.CEO],
        email="thiago@objetivasolucao.com.br",
        pode_aprovar=True,
        areas_aprovacao=[
            "deploy_producao",
            "gasto_ia",
            "mudanca_arquitetura",
            "campanha_marketing",
            "outreach_massa",
        ],
    ),
    "jonatas": Usuario(
        id="jonatas",
        nome="Jonatas",
        cargo="Diretor Técnico e Operations Lead",
        papeis=[Papel.DIRETOR_TECNICO, Papel.OPERATIONS_LEAD],
        email="jonatas@objetivasolucao.com.br",
        pode_aprovar=True,
        areas_aprovacao=[
            "deploy_producao",
            "gasto_ia",
            "mudanca_arquitetura",
            "campanha_marketing",
            "outreach_massa",
        ],
    ),
}


def obter_usuario(user_id: str) -> Usuario | None:
    """Busca um usuário pelo ID."""
    return USUARIOS.get(user_id)


def listar_aprovadores() -> list[Usuario]:
    """Lista todos os usuários com poder de aprovação."""
    return [u for u in USUARIOS.values() if u.pode_aprovar]


def listar_usuarios() -> list[Usuario]:
    """Lista todos os usuários ativos."""
    return [u for u in USUARIOS.values() if u.ativo]
