"""
PlanModeService — Singleton orquestrador do Plan Mode.

Ponto de entrada único para todas as operações de Plan Mode:
- Entrar/sair do Plan Mode
- Verificar permissões
- Gerar planos
- Status e histórico

Uso:
    from core.governance.plan_mode import plan_mode_service

    # Entrar em Plan Mode
    sessao = await plan_mode_service.entrar(
        usuario_id=1, usuario_nome="Thiago", motivo="Planejar Fase 4"
    )

    # Verificar permissão
    resultado = plan_mode_service.verificar_permissao("Bash", "npm run build")

    # Gerar plano
    plano = await plan_mode_service.gerar_plano("Migrar banco para PostgreSQL")

    # Sair do Plan Mode
    resumo = await plan_mode_service.sair(usuario_nome="Thiago")
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from core.governance.plan_mode.types import (
    AgentMode,
    PlanModeConfig,
    PlanSession,
    PermissionRequest,
)
from core.governance.plan_mode.permission_guard import (
    permission_guard,
    VerificationResult,
)
from core.governance.plan_mode.enter_plan_mode import entrar_plan_mode
from core.governance.plan_mode.exit_plan_mode import sair_plan_mode
from core.governance.plan_mode.plan_agent import plan_agent
from core.governance.plan_mode.modes import obter_modo

logger = logging.getLogger("synerium.governance")


class PlanModeService:
    """
    Serviço singleton de Plan Mode.

    Orquestra todos os componentes:
    - PermissionGuard: verifica permissões em tempo real
    - PlanAgent: gera planos estruturados via LLM
    - Enter/Exit: transições de modo seguras
    - Sessões: tracking de sessões de planejamento

    Thread-safe: usa lock para operações críticas.
    """

    _instance: PlanModeService | None = None
    _lock = threading.Lock()

    def __new__(cls) -> PlanModeService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = PlanModeConfig()
        self._sessao_ativa: PlanSession | None = None
        self._historico_sessoes: list[PlanSession] = []
        self._initialized = True
        logger.info("[PlanMode] Serviço inicializado")

    # =========================================================================
    # Entrar / Sair
    # =========================================================================

    async def entrar(
        self,
        usuario_id: int,
        usuario_nome: str = "",
        agente_id: str | None = None,
        motivo: str = "",
    ) -> PlanSession:
        """
        Ativa o Plan Mode.

        Returns:
            PlanSession criada
        Raises:
            RuntimeError: se já está em Plan Mode
        """
        if self._sessao_ativa and self._sessao_ativa.ativo:
            raise RuntimeError(
                f"Plan Mode já ativo (sessao={self._sessao_ativa.id}). "
                "Saia primeiro com plan_mode_service.sair()."
            )

        sessao = await entrar_plan_mode(
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            agente_id=agente_id,
            motivo=motivo,
        )
        self._sessao_ativa = sessao
        return sessao

    async def sair(self, usuario_nome: str = "") -> dict:
        """
        Desativa o Plan Mode e retorna resumo.

        Returns:
            Dict com resumo (duração, bloqueios, plano gerado)
        """
        if not self._sessao_ativa or not self._sessao_ativa.ativo:
            return {"sucesso": False, "erro": "Plan Mode não está ativo"}

        resultado = await sair_plan_mode(
            sessao=self._sessao_ativa,
            usuario_nome=usuario_nome,
        )

        # Mover para histórico
        self._historico_sessoes.append(self._sessao_ativa)
        self._sessao_ativa = None

        return resultado

    # =========================================================================
    # Verificação de permissões
    # =========================================================================

    def verificar_permissao(
        self,
        ferramenta: str,
        descricao: str = "",
        parametros: dict | None = None,
    ) -> VerificationResult:
        """Verifica se uma ferramenta pode ser executada no modo atual."""
        return permission_guard.verificar(ferramenta, descricao, parametros)

    def aprovar_permissao(self, request_id: str, aprovado_por: str) -> bool:
        """Aprova um pedido de permissão pendente."""
        return permission_guard.aprovar_request(request_id, aprovado_por)

    def rejeitar_permissao(self, request_id: str, rejeitado_por: str) -> bool:
        """Rejeita um pedido de permissão pendente."""
        return permission_guard.rejeitar_request(request_id, rejeitado_por)

    def listar_permissoes_pendentes(self) -> list[PermissionRequest]:
        """Lista pedidos de permissão pendentes."""
        return permission_guard.listar_pendentes()

    # =========================================================================
    # Planejamento
    # =========================================================================

    async def gerar_plano(
        self,
        diretiva: str,
        contexto: dict | None = None,
        modelo: str = "sonnet",
    ) -> dict:
        """
        Gera um plano estruturado via PlanAgent.

        O plano é automaticamente salvo na sessão ativa (se houver).
        """
        resultado = await plan_agent.gerar_plano(diretiva, contexto, modelo)

        # Salvar na sessão ativa
        if resultado.get("sucesso") and self._sessao_ativa:
            self._sessao_ativa.plano = resultado["plano"]

        return resultado

    # =========================================================================
    # Status
    # =========================================================================

    @property
    def em_plan_mode(self) -> bool:
        """Retorna True se Plan Mode está ativo."""
        return permission_guard.em_plan_mode

    @property
    def sessao_ativa(self) -> PlanSession | None:
        """Retorna a sessão ativa (None se não está em Plan Mode)."""
        return self._sessao_ativa

    def status(self) -> dict[str, Any]:
        """Retorna status completo do Plan Mode."""
        guard_stats = permission_guard.estatisticas()
        return {
            "em_plan_mode": self.em_plan_mode,
            "modo_atual": guard_stats["modo_atual"],
            "sessao_ativa": {
                "id": self._sessao_ativa.id,
                "usuario_nome": self._sessao_ativa.usuario_nome,
                "motivo": self._sessao_ativa.motivo,
                "criado_em": self._sessao_ativa.criado_em.isoformat(),
                "tem_plano": bool(self._sessao_ativa.plano),
            } if self._sessao_ativa else None,
            "total_sessoes": len(self._historico_sessoes),
            "guard": guard_stats,
        }


# Instância singleton global
plan_mode_service = PlanModeService()
