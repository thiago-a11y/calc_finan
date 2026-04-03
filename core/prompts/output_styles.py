"""
Gerenciador de estilos de output — controla formatacao de respostas.

Inspirado no OutputStyleManager da arquitetura de referencia.
Cada estilo adiciona instrucoes de formatacao ao prompt.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from core.prompts.registry import PromptSection, SectionPriority


class OutputStyle(Enum):
    """Estilos de output disponiveis."""
    DEFAULT = "default"
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    EXPLANATORY = "explanatory"


_STYLE_INSTRUCTIONS: dict[OutputStyle, str] = {
    OutputStyle.DEFAULT: "",

    OutputStyle.CONCISE: (
        "ESTILO: CONCISO\n"
        "- Seja extremamente breve e direto\n"
        "- Maximo 3 paragrafos por resposta\n"
        "- Sem explicacoes desnecessarias — va direto ao ponto\n"
        "- Use bullet points em vez de paragrafos longos\n"
        "- Omita contexto obvio"
    ),

    OutputStyle.DETAILED: (
        "ESTILO: DETALHADO\n"
        "- Explique cada passo com clareza\n"
        "- Inclua contexto, justificativa e alternativas consideradas\n"
        "- Use exemplos praticos para ilustrar pontos importantes\n"
        "- Estruture a resposta com headers e subsecoes\n"
        "- Inclua referencias a documentacao quando relevante"
    ),

    OutputStyle.TECHNICAL: (
        "ESTILO: TECNICO\n"
        "- Foco em precisao tecnica e implementacao\n"
        "- Inclua trechos de codigo quando relevante\n"
        "- Referencie patterns, libs e APIs especificas\n"
        "- Use terminologia tecnica sem simplificacao excessiva\n"
        "- Inclua consideracoes de performance, seguranca e escalabilidade"
    ),

    OutputStyle.EXPLANATORY: (
        "ESTILO: EXPLICATIVO\n"
        "- Explique o 'porque' alem do 'como'\n"
        "- Use analogias e exemplos do mundo real\n"
        "- Antecipe duvidas e responda proativamente\n"
        "- Conecte conceitos novos com conhecimento existente\n"
        "- Ideal para decisoes de arquitetura e trade-offs"
    ),
}


def get_style_section(style: OutputStyle) -> Optional[PromptSection]:
    """Retorna a secao de estilo. None para DEFAULT."""
    instructions = _STYLE_INSTRUCTIONS.get(style, "")
    if not instructions:
        return None

    return PromptSection(
        name=f"output.style.{style.value}",
        content=instructions,
        is_static=True,
        priority=SectionPriority.OUTPUT,
        tags=("output", "style", style.value),
    )


def registrar(registry) -> None:
    """Registra secoes de estilo no registry."""
    for style in OutputStyle:
        section = get_style_section(style)
        if section:
            registry.register(section)

    registry.register_factory(
        "output.style",
        lambda style=OutputStyle.DEFAULT: get_style_section(style),
    )
