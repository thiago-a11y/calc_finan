"""
Exit Plan Mode — Ferramenta para desativar o Plan Mode.

Quando o CEO ou agente solicita "sair do modo plano",
esta ferramenta encerra a sessão e restaura o modo anterior.

Uso:
    from core.governance.plan_mode.exit_plan_mode import sair_plan_mode

    resultado = await sair_plan_mode(
        sessao=sessao_ativa,
        usuario_nome="Thiago",
    )
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.governance.plan_mode.types import PlanSession
from core.governance.plan_mode.permission_guard import permission_guard

logger = logging.getLogger("synerium.governance.exit")


async def sair_plan_mode(
    sessao: PlanSession,
    usuario_nome: str = "",
) -> dict:
    """
    Desativa o Plan Mode e encerra a sessão de planejamento.

    Args:
        sessao: sessão ativa para encerrar
        usuario_nome: quem está saindo

    Returns:
        Dict com resumo da sessão (duração, ações bloqueadas, plano gerado)
    """
    if not sessao.ativo:
        logger.warning(f"[PlanMode] Sessão {sessao.id} já estava encerrada")
        return {"sucesso": False, "erro": "Sessão já encerrada"}

    # Encerrar sessão
    sessao.ativo = False
    sessao.encerrado_em = datetime.now(timezone.utc)

    # Calcular duração
    duracao_seg = 0.0
    if sessao.criado_em and sessao.encerrado_em:
        duracao_seg = (sessao.encerrado_em - sessao.criado_em).total_seconds()

    # Coletar estatísticas do guard
    stats = permission_guard.estatisticas()

    # Restaurar modo anterior
    permission_guard.desativar_plan_mode()

    # Capturar snapshot no Kairos (non-blocking)
    try:
        from core.memory.kairos.service import kairos_service
        await kairos_service.criar_snapshot(
            agente_id=sessao.agente_id or "ceo",
            source="manual",
            conteudo=(
                f"Plan Mode desativado por {usuario_nome}. "
                f"Sessao: {sessao.id}. "
                f"Duracao: {duracao_seg:.0f}s. "
                f"Acoes bloqueadas: {stats['total_bloqueados']}. "
                f"Plano gerado: {'Sim' if sessao.plano else 'Nao'}"
            ),
            contexto={
                "tipo_acao": "sair_plan_mode",
                "sessao_id": sessao.id,
                "usuario_id": sessao.usuario_id,
                "duracao_seg": duracao_seg,
                "acoes_bloqueadas": stats["total_bloqueados"],
            },
            tenant_id=1,
            relevancia=0.5,
        )
    except Exception as e:
        logger.warning(f"[PlanMode] Kairos snapshot falhou: {e}")

    logger.info(
        f"[PlanMode] DESATIVADO por {usuario_nome} "
        f"(sessao={sessao.id}, duracao={duracao_seg:.0f}s, "
        f"bloqueados={stats['total_bloqueados']})"
    )

    return {
        "sucesso": True,
        "sessao_id": sessao.id,
        "duracao_segundos": duracao_seg,
        "acoes_bloqueadas": stats["total_bloqueados"],
        "plano_gerado": bool(sessao.plano),
    }
