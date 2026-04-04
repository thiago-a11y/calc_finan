"""
Core Tools — Ferramentas de agente.

Módulos:
- base: ToolFactory, ToolDefinition, ToolRegistry, ValidationResult
- brief: BriefTool para envio de mensagens ao usuário

Usage:
    from core.tools.base import ToolFactory, ToolDefinition
    from core.tools.brief import BriefTool
"""

from core.tools.base import (
    PermissionResult,
    ToolDefinition,
    ToolFactory,
    ToolPermissionContext,
    ToolProgressData,
    ToolRegistry,
    ToolResult,
    ValidationResult,
)

__all__ = [
    "PermissionResult",
    "ToolDefinition",
    "ToolFactory",
    "ToolProgressData",
    "ToolRegistry",
    "ToolResult",
    "ToolPermissionContext",
    "ValidationResult",
]