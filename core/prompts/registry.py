"""
Registry Central de Prompt Sections — Synerium Factory v0.59.0

Modelo de dados e registro central para secoes de system prompt.
Cada secao e uma unidade independente, versionavel e cacheavel.

Uso:
    from core.prompts.registry import PromptSection, SectionRegistry, SectionPriority

    section = PromptSection(
        name="luna.identity",
        content="Voce e Luna...",
        priority=SectionPriority.IDENTITY,
        tags=("luna",),
    )
    registry = SectionRegistry()
    registry.register(section)
    prompt = registry.compose(["luna.identity", "luna.rules"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional

logger = logging.getLogger("synerium.prompts.registry")


class SectionPriority(IntEnum):
    """Prioridade de ordenacao na composicao do prompt."""
    IDENTITY = 10
    RULES = 20
    CONTEXT = 30
    TOOLS = 40
    OUTPUT = 50
    CUSTOM = 60


@dataclass(frozen=True)
class PromptSection:
    """Unidade atomica de um system prompt."""
    name: str
    content: str
    is_static: bool = True
    priority: int = SectionPriority.CUSTOM
    version: str = "1.0"
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.name:
            raise ValueError("PromptSection.name nao pode ser vazio")
        if not self.content:
            raise ValueError(f"PromptSection '{self.name}' nao pode ter content vazio")


class SectionRegistry:
    """
    Registro central de secoes de prompt.

    Armazena secoes estaticas (pre-computadas) e factories dinamicas
    (computadas sob demanda com kwargs).
    """

    def __init__(self):
        self._sections: dict[str, PromptSection] = {}
        self._factories: dict[str, Callable[..., PromptSection]] = {}

    def register(self, section: PromptSection) -> None:
        """Registra uma secao estatica."""
        if section.name in self._sections:
            logger.debug(f"[REGISTRY] Sobrescrevendo secao: {section.name}")
        self._sections[section.name] = section

    def register_factory(self, name: str, factory: Callable[..., PromptSection]) -> None:
        """Registra uma factory de secao dinamica."""
        self._factories[name] = factory

    def get(self, name: str, **kwargs) -> Optional[PromptSection]:
        """Recupera uma secao por nome (estatica ou factory)."""
        if name in self._sections:
            return self._sections[name]
        if name in self._factories:
            return self._factories[name](**kwargs)
        return None

    def compose(self, names: list[str], separator: str = "\n\n", **kwargs) -> str:
        """Compoe multiplas secoes em um unico prompt, ordenado por prioridade."""
        sections: list[PromptSection] = []
        for name in names:
            section = self.get(name, **kwargs)
            if section is None:
                logger.warning(f"[REGISTRY] Secao nao encontrada: {name}")
                continue
            sections.append(section)

        sections.sort(key=lambda s: s.priority)
        composed = separator.join(s.content for s in sections)

        if sections:
            versions = ", ".join(f"{s.name}@{s.version}" for s in sections)
            logger.debug(f"[REGISTRY] Prompt composto: {versions}")

        return composed

    def list_by_tag(self, tag: str) -> list[PromptSection]:
        """Retorna todas as secoes que contem a tag."""
        return [s for s in self._sections.values() if tag in s.tags]

    def all_sections(self) -> list[PromptSection]:
        """Retorna todas as secoes estaticas registradas."""
        return list(self._sections.values())

    def has(self, name: str) -> bool:
        """Verifica se uma secao ou factory existe."""
        return name in self._sections or name in self._factories

    def clear(self) -> None:
        """Remove todas as secoes e factories."""
        self._sections.clear()
        self._factories.clear()
