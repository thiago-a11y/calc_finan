"""
core.prompts — Sistema Unificado de Prompts Modulares do Synerium Factory (v0.59.0)

Camada centralizada de engenharia de prompts com:
- Secoes modulares e versionaveis (PromptSection)
- Registry central com composicao ordenada por prioridade
- Cache thread-safe com TTL (padrao company_context.py)
- Separacao estatico/dinamico
- Output styles configuraveis
- Backward compatibility total

Uso rapido:
    from core.prompts import compose_luna_prompt, compose_agent_prompt, compose_bmad_prompt
    from core.prompts import registry, OutputStyle

    # Luna
    prompt = compose_luna_prompt()

    # Agente CrewAI
    config = compose_agent_prompt("Kenji", "Tech Lead", "Analisar", "Voce e Kenji...", "tech_lead", "CEO")

    # BMAD
    prompt_fase = compose_bmad_prompt(fase=1, titulo="Feature X", descricao="...")

    # Registry direto
    section = registry.get("luna.identity")
    all_luna = registry.list_by_tag("luna")
"""

from core.prompts.registry import PromptSection, SectionPriority, SectionRegistry
from core.prompts.cache import PromptCache, prompt_cache
from core.prompts.output_styles import OutputStyle
from core.prompts.composers import (
    compose_luna_prompt,
    compose_agent_prompt,
    compose_bmad_prompt,
)

# Registry global — inicializado com todas as secoes
registry = SectionRegistry()


def _inicializar_registry() -> None:
    """Registra todas as secoes de todos os modulos no registry global."""
    from core.prompts import base, luna, rules, tools, bmad, agents, output_styles

    base.registrar(registry)
    luna.registrar(registry)
    rules.registrar(registry)
    tools.registrar(registry)
    bmad.registrar(registry)
    agents.registrar(registry)
    output_styles.registrar(registry)


# Auto-inicializar ao importar
_inicializar_registry()


__all__ = [
    # Classes
    "PromptSection",
    "SectionPriority",
    "SectionRegistry",
    "PromptCache",
    "OutputStyle",
    # Registry global
    "registry",
    "prompt_cache",
    # Composers
    "compose_luna_prompt",
    "compose_agent_prompt",
    "compose_bmad_prompt",
]
