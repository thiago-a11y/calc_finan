"""
Composers — funcoes de alto nivel para compor prompts completos.

Cada composer resolve secoes do registry, aplica cache quando possivel
e retorna o prompt final como string ou dict.

Uso:
    from core.prompts import compose_luna_prompt, compose_agent_prompt, compose_bmad_prompt

    # Luna
    prompt = compose_luna_prompt()
    prompt_conciso = compose_luna_prompt(OutputStyle.CONCISE)

    # Agente CrewAI
    agent_config = compose_agent_prompt(
        name="Kenji", role="Tech Lead", goal="Analisar arquitetura",
        backstory="Voce e Kenji...", perfil="tech_lead", squad_name="CEO",
    )

    # BMAD
    prompt_fase = compose_bmad_prompt(fase=1, titulo="Nova feature", descricao="...")
"""

import logging

from core.prompts.cache import prompt_cache
from core.prompts.output_styles import OutputStyle, get_style_section
from core.prompts.utils import limpar_prompt, truncar

logger = logging.getLogger("synerium.prompts.composers")


def compose_luna_prompt(style: OutputStyle = OutputStyle.DEFAULT) -> str:
    """
    Compoe o system prompt completo da Luna.

    Resultado e cacheado por 1 hora (por estilo).
    Drop-in replacement para SYSTEM_PROMPT em luna_engine.py.
    """
    cache_key = f"luna:{style.value}"
    cached = prompt_cache.get(cache_key)
    if cached is not None:
        return cached

    # Import local para evitar circular na inicializacao
    from core.prompts import registry

    sections = ["luna.identity", "luna.rules", "luna.file_generation", "luna.context"]
    prompt = registry.compose(sections)

    # Adicionar estilo se nao for default
    style_section = get_style_section(style)
    if style_section:
        prompt = prompt + "\n\n" + style_section.content

    prompt = limpar_prompt(prompt)
    prompt_cache.set(cache_key, prompt)

    logger.debug(f"[COMPOSER] Luna prompt composto ({style.value}): {len(prompt)} chars")
    return prompt


def compose_agent_prompt(
    name: str,
    role: str,
    goal: str,
    backstory: str,
    perfil: str = "",
    squad_name: str = "",
    include_rules: bool = True,
    include_tools: bool = True,
) -> dict[str, str]:
    """
    Compoe role/goal/backstory para um agente CrewAI.

    Injeta automaticamente regras anti-alucinacao e instrucoes de ferramentas.
    Retorna dict compativel com CrewAI Agent kwargs.

    Substitui o padrao antigo:
        historia=backstory + REGRAS_ANTI_ALUCINACAO
    """
    from core.prompts import registry

    composed_backstory = backstory

    # Injetar regras anti-alucinacao
    if include_rules:
        rules_section = registry.get("rules.anti_hallucination")
        if rules_section:
            composed_backstory = composed_backstory + "\n\n" + rules_section.content

    # Injetar instrucoes de ferramentas por perfil
    if include_tools and perfil:
        tools_section = registry.get("tools.for_profile", perfil=perfil)
        if tools_section:
            composed_backstory = composed_backstory + "\n\n" + tools_section.content

    composed_backstory = limpar_prompt(composed_backstory)

    logger.debug(
        f"[COMPOSER] Agente '{name}' composto: "
        f"rules={'sim' if include_rules else 'nao'}, "
        f"tools={'sim' if include_tools else 'nao'}, "
        f"{len(composed_backstory)} chars"
    )

    return {
        "role": role,
        "goal": goal,
        "backstory": composed_backstory,
    }


def compose_bmad_prompt(
    fase: int,
    titulo: str,
    descricao: str,
    output_anterior: str = "",
) -> str:
    """
    Compoe prompt para uma fase BMAD.

    Resolve o template da fase e aplica variaveis.
    Substitui PROMPTS_FASE.get(fase, "").format(...) em tarefas.py.
    """
    from core.prompts.bmad import PROMPTS_FASE

    template = PROMPTS_FASE.get(fase, "")
    if not template:
        logger.warning(f"[COMPOSER] Fase BMAD {fase} nao encontrada")
        return ""

    # Truncar output anterior para evitar prompts gigantes
    output_truncado = truncar(output_anterior, max_chars=3000)

    prompt = template.format(
        titulo=titulo,
        descricao=descricao,
        output_anterior=output_truncado,
    )

    return limpar_prompt(prompt)
