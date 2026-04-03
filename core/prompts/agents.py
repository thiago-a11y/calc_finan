"""
Composicao de identidade de agentes CrewAI.

Factory para gerar PromptSections de identidade de agentes
com injecao automatica de regras e instrucoes de ferramentas.
"""

import logging

from core.prompts.registry import PromptSection, SectionPriority

logger = logging.getLogger("synerium.prompts.agents")


def agent_identity(
    name: str,
    role: str,
    specialty: str,
    squad_name: str,
) -> PromptSection:
    """
    Factory: gera secao de identidade para um agente CrewAI generico.

    Usado pelo squad_template.py para agentes criados dinamicamente.
    """
    content = (
        f"Voce e {name}, {role} do squad '{squad_name}' no Synerium Factory.\n"
        f"Sua especialidade e {specialty}.\n"
        "Voce faz parte de uma equipe de agentes IA que trabalha para a Objetiva Solucao."
    )

    return PromptSection(
        name=f"agent.identity.{name.lower().replace(' ', '_')}",
        content=content,
        is_static=False,
        priority=SectionPriority.IDENTITY,
        tags=("agent", "identity", squad_name.lower().replace(" ", "_")),
    )


def registrar(registry) -> None:
    """Registra factories de agentes no registry."""
    registry.register_factory("agent.identity", agent_identity)
