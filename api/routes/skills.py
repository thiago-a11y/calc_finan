"""
Rota: Skills dos Agentes

GET /api/skills             — Lista todas as skills disponíveis
GET /api/skills/perfis      — Lista perfis de agentes e suas skills
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencias import obter_usuario_atual
from tools.registry import skill_registry

logger = logging.getLogger("synerium.skills")

router = APIRouter(prefix="/api/skills", tags=["Skills"])


class SkillResponse(BaseModel):
    """Resposta de uma skill."""
    id: str
    nome: str
    descricao: str
    categoria: str
    ativa: bool
    icone: str
    requer_config: bool


class PerfilSkillsResponse(BaseModel):
    """Resposta de um perfil com suas skills."""
    perfil: str
    skills: list[str]


@router.get("", response_model=list[SkillResponse])
def listar_skills(usuario=Depends(obter_usuario_atual)):
    """Lista todas as skills disponíveis no catálogo."""
    return [
        SkillResponse(
            id=s.id,
            nome=s.nome,
            descricao=s.descricao,
            categoria=s.categoria,
            ativa=s.ativa,
            icone=s.icone,
            requer_config=s.requer_config,
        )
        for s in skill_registry.listar()
    ]


@router.get("/perfis", response_model=list[PerfilSkillsResponse])
def listar_perfis(usuario=Depends(obter_usuario_atual)):
    """Lista os perfis de agentes e quais skills cada um usa."""
    return [
        PerfilSkillsResponse(perfil=perfil, skills=skill_ids)
        for perfil, skill_ids in skill_registry._perfis.items()
    ]
