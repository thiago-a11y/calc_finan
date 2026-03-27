"""
Skill Registry — Catálogo centralizado de todas as skills disponíveis.

Cada skill tem:
- id: identificador único
- nome: nome legível
- descricao: o que faz
- categoria: agrupamento (codigo, web, dados, comunicacao, etc.)
- ferramenta: instância da ferramenta CrewAI
- requer_config: se precisa de API key extra

O registry permite:
- Listar todas as skills disponíveis
- Montar o kit de skills por perfil de agente
- Futuro: marketplace para baixar novas skills
"""

import logging
from dataclasses import dataclass, field
from crewai.tools import BaseTool

logger = logging.getLogger("synerium.skills")


@dataclass
class SkillDefinition:
    """Definição de uma skill no catálogo."""
    id: str
    nome: str
    descricao: str
    categoria: str
    ferramenta: BaseTool | None = None
    requer_config: bool = False
    ativa: bool = True
    icone: str = "🔧"


class SkillRegistry:
    """
    Catálogo centralizado de skills para os agentes.

    Uso:
        registry = SkillRegistry()
        registry.registrar(skill)
        tools = registry.montar_kit("tech_lead")
    """

    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}
        self._perfis: dict[str, list[str]] = {}

    def registrar(self, skill: SkillDefinition):
        """Registra uma skill no catálogo."""
        self._skills[skill.id] = skill
        logger.info(f"[SKILL] Registrada: {skill.id} — {skill.nome}")

    def registrar_perfil(self, perfil: str, skill_ids: list[str]):
        """Define um perfil de agente com as skills que ele usa."""
        self._perfis[perfil] = skill_ids

    def montar_kit(self, perfil: str) -> list[BaseTool]:
        """Retorna a lista de ferramentas para um perfil de agente."""
        skill_ids = self._perfis.get(perfil, [])
        tools = []
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if skill and skill.ferramenta and skill.ativa:
                tools.append(skill.ferramenta)
        return tools

    def listar(self) -> list[SkillDefinition]:
        """Lista todas as skills registradas."""
        return list(self._skills.values())

    def listar_por_categoria(self) -> dict[str, list[SkillDefinition]]:
        """Lista skills agrupadas por categoria."""
        categorias: dict[str, list[SkillDefinition]] = {}
        for skill in self._skills.values():
            if skill.categoria not in categorias:
                categorias[skill.categoria] = []
            categorias[skill.categoria].append(skill)
        return categorias

    def obter(self, skill_id: str) -> SkillDefinition | None:
        """Obtém uma skill por ID."""
        return self._skills.get(skill_id)

    @property
    def total(self) -> int:
        return len(self._skills)


# Instância global
skill_registry = SkillRegistry()
