"""
Enter Plan Mode — Ferramenta para ativar o Plan Mode.

Quando o CEO, agente ou Luna solicita "entrar em modo plano",
esta ferramenta cria uma sessão de planejamento e ativa o guard.

Uso:
    from core.governance.plan_mode.enter_plan_mode import entrar_plan_mode

    sessao = await entrar_plan_mode(
        usuario_id=1,
        usuario_nome="Thiago",
        motivo="Planejar a Fase 4 sem executar nada",
    )
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone

from core.governance.plan_mode.types import AgentMode, PlanSession
from core.governance.plan_mode.permission_guard import permission_guard

logger = logging.getLogger("synerium.governance.enter")


def _gerar_id(tamanho: int = 10) -> str:
    alfabeto = string.ascii_lowercase + string.digits
    return f"plan_{''.join(secrets.choice(alfabeto) for _ in range(tamanho))}"


async def entrar_plan_mode(
    usuario_id: int,
    usuario_nome: str = "",
    agente_id: str | None = None,
    motivo: str = "",
) -> PlanSession:
    """
    Ativa o Plan Mode e cria uma sessão de planejamento.

    Args:
        usuario_id: quem está ativando
        usuario_nome: nome de quem está ativando
        agente_id: agente operando em Plan Mode (None = direto)
        motivo: razão para entrar em Plan Mode

    Returns:
        PlanSession criada e ativa
    """
    sessao = PlanSession(
        id=_gerar_id(),
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        agente_id=agente_id,
        motivo=motivo,
        modo_anterior=permission_guard.modo_atual,
        ativo=True,
        criado_em=datetime.now(timezone.utc),
    )

    # Ativar no guard
    permission_guard.ativar_plan_mode(sessao.id)

    # Capturar snapshot no Kairos (non-blocking)
    try:
        from core.memory.kairos.service import kairos_service
        await kairos_service.criar_snapshot(
            agente_id=agente_id or "ceo",
            source="manual",
            conteudo=(
                f"Plan Mode ativado por {usuario_nome}. "
                f"Motivo: {motivo or 'Nao informado'}. "
                f"Sessao: {sessao.id}"
            ),
            contexto={
                "tipo_acao": "entrar_plan_mode",
                "sessao_id": sessao.id,
                "usuario_id": usuario_id,
            },
            tenant_id=1,
            relevancia=0.6,
        )
    except Exception as e:
        logger.warning(f"[PlanMode] Kairos snapshot falhou: {e}")

    logger.info(
        f"[PlanMode] ATIVADO por {usuario_nome} "
        f"(sessao={sessao.id}, motivo='{motivo[:80]}')"
    )

    return sessao
