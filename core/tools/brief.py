"""
BriefTool — Ferramenta para envio de mensagens ao usuário.

Implementa o sistema de messaging do TypeScript (brief_tool.ts):

Características principais:
- Canal primário de output visible para o usuário
- Suporte a markdown no message
- Attachments (files, images)
- Status: normal (resposta) ou proactive (não solicitado)

Integração com:
- ToolFactory: criação via factory pattern
- Feature gates: CLAURST_FEATURE_BRIEF para enable/disable
- ToolRegistry: registro automático

Usage:
    from core.tools.brief import BriefTool, is_brief_enabled, is_brief_entitled

    if is_brief_enabled():
        result = await BriefTool.call({"message": "Tarefa concluída!"})
"""

import logging
from datetime import datetime, timezone
from typing import Any

from core.tools.base import (
    ToolDefinition,
    ToolFactory,
    ToolResult,
    ValidationResult,
)

logger = logging.getLogger("synerium.tools.brief")

# Constants
BRIEF_TOOL_NAME = "Brief"
LEGACY_BRIEF_TOOL_NAME = "SendUserMessage"

DESCRIPTION = """Send a message to the user. This is your primary visible output channel.

Use this tool to:
- Report task completion
- Communicate status updates
- Ask questions when necessary
- Share results and findings

Supports markdown formatting. The user will see your message in the conversation."""


# =============================================================================
# Feature Gates
# =============================================================================


def _is_env_truthy(val: str | None) -> bool:
    """Retorna True se val é truthy (1, true, yes, on)."""
    if val is None:
        return False
    return val.lower() in ("1", "true", "yes", "on")


def _is_feature_enabled(gate_name: str) -> bool:
    """Verifica se feature gate está habilitado via env var."""
    normalized = gate_name.upper().replace("-", "_")
    key = f"CLAURST_FEATURE_{normalized}"
    return _is_env_truthy(_get_env(key))


def _get_env(key: str) -> str | None:
    """Wrapper para acesso a env vars (permite mock em testes)."""
    import os
    return os.environ.get(key)


def is_brief_entitled() -> bool:
    """
    Verifica se o usuário tem direito a usar Brief.

    Entitlements:
    - CLAURST_FEATURE_BRIEF definido E
    - CLAURST_BRIEF_DEV_MODE (dev override) OU
    - Feature gate ativo via CLAURST_FEATURE_TENGU_KAIROS_BRIEF

    Returns:
        True se entitled
    """
    # Dev override for testing
    if _is_feature_enabled("brief_dev_mode"):
        return True

    # Main feature gate
    if _is_feature_enabled("brief"):
        return True

    # Kairos brief integration
    if _is_feature_enabled("kairos_brief"):
        return True

    return False


def is_brief_enabled() -> bool:
    """
    Verifica se Brief está habilitado para esta sessão.

    Combina entitlement check com session opt-in.
    Por ora, opt-in é sempre True (simplificação do TypeScript).

    Returns:
        True se Brief pode ser usado
    """
    # Check feature gate
    if not is_brief_entitled():
        return False

    # Session opt-in (simplified: always True for now)
    # Full implementation would check getUserMsgOptIn()
    return True


# =============================================================================
# Input/Output Schemas
# =============================================================================


def _get_input_schema() -> dict[str, Any]:
    """Retorna schema de input para BriefTool."""
    return {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message for the user. Supports markdown formatting.",
            },
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional file paths (absolute or relative to cwd) to attach.",
            },
            "status": {
                "type": "string",
                "enum": ["normal", "proactive"],
                "description": "Use 'proactive' for unsolicited updates the user needs to see now.",
                "default": "normal",
            },
        },
        "required": ["message"],
    }


def _get_output_schema() -> dict[str, Any]:
    """Retorna schema de output para BriefTool."""
    return {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The message sent."},
            "attachments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "size": {"type": "number"},
                        "is_image": {"type": "boolean"},
                        "file_uuid": {"type": "string"},
                    },
                },
                "description": "Resolved attachment metadata.",
            },
            "sent_at": {
                "type": "string",
                "description": "ISO timestamp captured at tool execution.",
            },
        },
    }


# =============================================================================
# Attachment Resolution (Stub)
# =============================================================================


async def _resolve_attachments(
    paths: list[str],
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Resolve attachments para metadata.

    Por ora, implementação stub que retorna apenas o path.
    Full implementation: verificar arquivo existe, identificar imagens, etc.

    Args:
        paths: Lista de paths de arquivo
        context: Contexto de execução

    Returns:
        Lista de metadata dos attachments
    """
    import os

    resolved = []
    for path in paths:
        try:
            stat = os.stat(path)
            resolved.append({
                "path": path,
                "size": stat.st_size,
                "is_image": path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")),
                "file_uuid": None,  # Placeholder
            })
        except OSError:
            # File doesn't exist or can't be accessed
            resolved.append({
                "path": path,
                "size": 0,
                "is_image": False,
                "file_uuid": None,
            })
    return resolved


# =============================================================================
# BriefTool Implementation
# =============================================================================


async def _brief_call(
    args: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> ToolResult[dict[str, Any]]:
    """
    Executa o Brief tool.

    Args:
        args: Input com message, attachments, status
        context: Contexto de execução

    Returns:
        ToolResult com message e metadata de attachments
    """
    message = args.get("message", "")
    attachments = args.get("attachments")
    status = args.get("status", "normal")

    sent_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"BriefTool: status={status}, "
        f"message_len={len(message)}, "
        f"attachments={len(attachments) if attachments else 0}"
    )

    # Resolve attachments if provided
    resolved_attachments = None
    if attachments and len(attachments) > 0:
        resolved_attachments = await _resolve_attachments(attachments, context)

    result_data = {
        "message": message,
        "sent_at": sent_at,
    }
    if resolved_attachments:
        result_data["attachments"] = resolved_attachments

    return ToolResult(data=result_data)


def _brief_description() -> str:
    """Retorna description do BriefTool."""
    return DESCRIPTION


def _brief_to_auto_classifier_input(args: dict[str, Any]) -> str:
    """Retorna input para auto-classifier (vazio = skip)."""
    return args.get("message", "")


async def _brief_validate_input(
    args: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> ValidationResult:
    """Valida input do BriefTool."""
    if "message" not in args:
        return ValidationResult.error("message é obrigatório", 400)

    message = args.get("message", "")
    if not isinstance(message, str):
        return ValidationResult.error("message deve ser string", 400)

    # Validate attachments if present
    attachments = args.get("attachments")
    if attachments is not None:
        if not isinstance(attachments, list):
            return ValidationResult.error("attachments deve ser array", 400)
        for path in attachments:
            if not isinstance(path, str):
                return ValidationResult.error("cada attachment deve ser string", 400)

    return ValidationResult.ok()


# =============================================================================
# BriefTool Factory
# =============================================================================


def create_brief_tool() -> ToolDefinition:
    """
    Cria uma instância do BriefTool.

    Returns:
        ToolDefinition pronta para registro
    """
    return ToolFactory.build({
        "name": BRIEF_TOOL_NAME,
        "aliases": [LEGACY_BRIEF_TOOL_NAME],
        "search_hint": "send a message to the user",
        "max_result_size_chars": 100_000,
        "description": _brief_description,
        "input_schema": _get_input_schema,
        "output_schema": _get_output_schema,
        "is_enabled": is_brief_enabled,
        "is_concurrency_safe": lambda: True,
        "is_read_only": lambda: True,
        "to_auto_classifier_input": _brief_to_auto_classifier_input,
        "validate_input": _brief_validate_input,
        "call": _brief_call,
    })


# Instância singleton do BriefTool
BriefTool = create_brief_tool()