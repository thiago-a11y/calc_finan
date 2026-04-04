"""
Ferramentas (Tools) — Interface base e Factory para ferramentas de agente.

Implementa o padrão buildTool() inspirado em tool_registry.ts (TypeScript):

Características principais:
- ToolFactory: factory pattern para criar ferramentas com defaults fail-closed
- ToolDefinition: definição de ferramenta com schema de input/output
- Validação de input com ValidationResult
- Permission handling integrado

Defaults (fail-closed onde importa):
- is_enabled() → True
- is_concurrency_safe() → False
- is_read_only() → False
- is_destructive() → False
- check_permissions() → allow
- to_auto_classifier_input() → ''
- user_facing_name() → name

Usage:
    from core.tools.base import ToolFactory, ToolDefinition, ValidationResult

    tool = ToolFactory.build({
        'name': 'Bash',
        'description': lambda: 'Execute shell commands',
        'input_schema': {...},
        'call': my_call_func,
    })
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")

logger = logging.getLogger("synerium.tools")


# =============================================================================
# Validation Result
# =============================================================================


@dataclass
class ValidationResult:
    """
    Resultado de validação de input de ferramenta.

    Equivalente a ValidationResult em tool_registry.ts.
    """

    result: bool
    message: str | None = None
    error_code: int | None = None

    @classmethod
    def ok(cls) -> ValidationResult:
        """Validação passou."""
        return cls(result=True)

    @classmethod
    def error(cls, message: str, error_code: int = -1) -> ValidationResult:
        """Validação falhou."""
        return cls(result=False, message=message, error_code=error_code)


# =============================================================================
# Tool Permission
# =============================================================================


@dataclass
class ToolPermissionContext:
    """
    Contexto de permissão para execução de ferramenta.

    Equivalente a ToolPermissionContext em tool_registry.ts.
    """

    mode: str = "default"  # PermissionMode
    additional_working_directories: dict[str, str] = field(default_factory=dict)
    always_allow_rules: dict[str, list[str]] = field(default_factory=dict)
    always_deny_rules: dict[str, list[str]] = field(default_factory=dict)
    always_ask_rules: dict[str, list[str]] = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    is_auto_mode_available: bool = False
    stripped_dangerous_rules: dict[str, list[str]] | None = None
    should_avoid_permission_prompts: bool = False
    await_automated_checks_before_dialog: bool = False
    pre_plan_mode: str | None = None


@dataclass
class PermissionResult:
    """
    Resultado de verificação de permissão.

    Equivalente a PermissionResult em tool_registry.ts.
    """

    behavior: str  # "allow" | "deny" | "ask"
    updated_input: dict[str, Any] | None = None
    message: str | None = None


# =============================================================================
# Tool Progress
# =============================================================================


@dataclass
class ToolProgressData:
    """
    Dados base para progresso de ferramenta.

    Equivalente a ToolProgressData em tool_registry.ts.
    """
    pass


# =============================================================================
# Tool Definition Interface
# =============================================================================


@dataclass
class ToolDefinition:
    """
    Definição de uma ferramenta (Tool).

    Equivalente a ToolDef em tool_registry.ts.

    Attributes:
        name: Nome único da ferramenta
        description: Descrição ou callable que retorna descrição
        input_schema: Schema de input (dict ou callable)
        output_schema: Schema de output (opcional)
        max_result_size_chars: Tamanho máximo antes de persistir em disco
        aliases: Nomes alternativos para lookup
        search_hint: Frase deCapability para busca por keywords

    Example:
        >>> tool = ToolDefinition(
        ...     name="Bash",
        ...     description="Execute shell commands",
        ...     input_schema={"type": "object", "properties": {...}},
        ...     call=lambda args, ctx: {...},
        ... )
    """

    name: str
    description: str | Callable[[], str]
    input_schema: dict[str, Any] | Callable[[], dict[str, Any]]
    call: Callable[..., Any]
    output_schema: dict[str, Any] | None = None
    max_result_size_chars: int = 10000
    aliases: list[str] = field(default_factory=list)
    search_hint: str | None = None
    is_enabled: Callable[[], bool] = field(default_factory=lambda: True)
    is_concurrency_safe: Callable[[], bool] = field(default_factory=lambda: False)
    is_read_only: Callable[[], bool] = field(default_factory=lambda: False)
    is_destructive: Callable[[], bool] = field(default_factory=lambda: False)
    check_permissions: Callable[..., PermissionResult] | None = None
    to_auto_classifier_input: Callable[[str], str] = field(default_factory=lambda _: "")
    user_facing_name: Callable[[str], str] = field(default_factory=lambda name: name)

    def get_description(self) -> str:
        """Retorna descrição (suporta callable)."""
        if callable(self.description):
            return self.description()
        return self.description

    def get_input_schema(self) -> dict[str, Any]:
        """Retorna input schema (suporta callable)."""
        if callable(self.input_schema):
            return self.input_schema()
        return self.input_schema

    def matches_name(self, name: str) -> bool:
        """Verifica se a ferramenta corresponde ao nome (primary ou alias)."""
        return self.name == name or name in self.aliases


@dataclass
class ToolResult(Generic[T]):
    """
    Resultado de execução de uma ferramenta.

    Equivalente a ToolResult em tool_registry.ts.

    Type parameters:
        T: Tipo do dado de output
    """

    data: T
    new_messages: list[dict] | None = None
    context_modifier: Callable[[ToolPermissionContext], ToolPermissionContext] | None = None
    mcp_meta: dict[str, Any] | None = None


# =============================================================================
# Tool Factory
# =============================================================================


class ToolFactory:
    """
    Factory para criar ferramentas com defaults fail-closed.

    Equivalente a buildTool() em tool_registry.ts.

    Defaults:
    - is_enabled() → True
    - is_concurrency_safe() → False
    - is_read_only() → False
    - is_destructive() → False
    - check_permissions() → allow
    - to_auto_classifier_input() → ''
    - user_facing_name() → name

    Usage:
        >>> tool = ToolFactory.build({
        ...     'name': 'Read',
        ...     'description': 'Read file contents',
        ...     'input_schema': {...},
        ...     'call': read_func,
        ... })
    """

    @staticmethod
    def build(definition: dict[str, Any]) -> ToolDefinition:
        """
        Constrói uma ToolDefinition completa com defaults fail-closed.

        Args:
            definition: Dict com campos da ferramenta

        Returns:
            ToolDefinition com todos os defaults aplicados
        """
        name = definition.get("name")
        if not name:
            raise ValueError("Tool definition must have 'name'")

        # Aplicar defaults
        return ToolDefinition(
            name=name,
            description=definition.get("description", ""),
            input_schema=definition.get("input_schema", {"type": "object"}),
            output_schema=definition.get("output_schema"),
            max_result_size_chars=definition.get("max_result_size_chars", 10000),
            aliases=definition.get("aliases", []),
            search_hint=definition.get("search_hint"),
            is_enabled=definition.get("is_enabled", lambda: True),
            is_concurrency_safe=definition.get("is_concurrency_safe", lambda: False),
            is_read_only=definition.get("is_read_only", lambda: False),
            is_destructive=definition.get("is_destructive", lambda: False),
            check_permissions=definition.get("check_permissions"),
            to_auto_classifier_input=definition.get(
                "to_auto_classifier_input", lambda _: ""
            ),
            user_facing_name=definition.get(
                "user_facing_name", lambda n: n
            ),
            call=definition.get("call"),
        )


# =============================================================================
# Tool Registry
# =============================================================================


class ToolRegistry:
    """
    Registro centralizado de ferramentas disponíveis.

    Equivalente a ferramenta que mantém.tools = [...] em tool_registry.ts.

    SINGLETON — acesso via ToolRegistry.get_instance()

    Usage:
        >>> registry = ToolRegistry.get_instance()
        >>> registry.register(my_tool)
        >>> tool = registry.get("Bash")
        >>> all_tools = registry.list_all()
    """

    _instance: "ToolRegistry | None" = None

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._lock = False  # Placeholder para threading

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Retorna instância singleton do registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: ToolDefinition) -> None:
        """Registra uma ferramenta."""
        self._tools[tool.name] = tool
        # Também registrar aliases
        for alias in tool.aliases:
            self._tools[alias] = tool
        logger.debug(f"[TOOLS] Registrada: {tool.name}")

    def get(self, name: str) -> ToolDefinition | None:
        """Retorna ferramenta por nome ou alias."""
        return self._tools.get(name)

    def list_all(self) -> list[ToolDefinition]:
        """Lista todas as ferramentas registradas."""
        # Retornar apenas ferramentas únicas (não aliases)
        seen = set()
        unique = []
        for tool in self._tools.values():
            if tool.name not in seen:
                seen.add(tool.name)
                unique.append(tool)
        return unique

    def list_enabled(self) -> list[ToolDefinition]:
        """Lista apenas ferramentas habilitadas."""
        return [t for t in self.list_all() if t.is_enabled()]

    def find_by_name(self, name: str) -> ToolDefinition | None:
        """Encontra ferramenta por nome (alias ou primary)."""
        return self._tools.get(name)

    def clear(self) -> None:
        """Limpa todos os registros (útil para testes)."""
        self._tools.clear()