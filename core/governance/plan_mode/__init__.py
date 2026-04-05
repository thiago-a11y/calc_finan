"""
Plan Mode — Sistema de planejamento com permissões granulares.

Permite que agentes e CEO entrem em modo somente-leitura para
planejar sem executar ações perigosas. Ferramentas são classificadas
por categoria de risco e bloqueadas conforme o modo ativo.

Componentes:
- PlanModeService: singleton orquestrador (ponto de entrada único)
- PermissionGuard: verifica permissões antes de executar ferramentas
- PlanAgent: gera planos estruturados via LLM
- Enter/Exit: transições de modo seguras com snapshots Kairos

Uso:
    from core.governance.plan_mode import plan_mode_service

    # Entrar em Plan Mode
    sessao = await plan_mode_service.entrar(usuario_id=1, motivo="Planejar Fase 4")

    # Verificar permissão
    resultado = plan_mode_service.verificar_permissao("Bash")
    # resultado.permitido = False (bloqueado em Plan Mode)

    # Gerar plano
    plano = await plan_mode_service.gerar_plano("Migrar para PostgreSQL")

    # Sair
    resumo = await plan_mode_service.sair(usuario_nome="Thiago")
"""

from core.governance.plan_mode.service import plan_mode_service, PlanModeService
from core.governance.plan_mode.permission_guard import permission_guard, PermissionGuard
from core.governance.plan_mode.types import (
    AgentMode,
    ToolCategory,
    PlanModeConfig,
    PlanSession,
    PermissionRequest,
    PermissionStatus,
)

__all__ = [
    "plan_mode_service",
    "PlanModeService",
    "permission_guard",
    "PermissionGuard",
    "AgentMode",
    "ToolCategory",
    "PlanModeConfig",
    "PlanSession",
    "PermissionRequest",
    "PermissionStatus",
]
