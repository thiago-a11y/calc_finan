"""
Permission Guard — Verifica permissões antes de executar ferramentas.

O guard é o porteiro do sistema: classifica cada ferramenta por risco
e consulta o modo atual para decidir se a ação é permitida.

Integra-se com Luna e Mission Control para interceptar chamadas
de ferramentas e bloquear as que não são permitidas no modo atual.

Uso:
    from core.governance.plan_mode.permission_guard import permission_guard

    resultado = permission_guard.verificar("Bash", "rm -rf /tmp/teste")
    if resultado.permitido:
        executar()
    else:
        mostrar(resultado.mensagem)
"""

from __future__ import annotations

import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone

from core.governance.plan_mode.types import (
    AgentMode,
    PermissionRequest,
    PermissionStatus,
    ToolCategory,
)
from core.governance.plan_mode.modes import obter_modo

logger = logging.getLogger("synerium.governance.guard")


# =============================================================================
# Classificação de ferramentas por categoria de risco
# =============================================================================

TOOL_CLASSIFICATION: dict[str, ToolCategory] = {
    # SAFE — leitura, análise, consulta
    "Read": ToolCategory.SAFE,
    "Grep": ToolCategory.SAFE,
    "Glob": ToolCategory.SAFE,
    "Search": ToolCategory.SAFE,
    "WebSearch": ToolCategory.SAFE,
    "WebFetch": ToolCategory.SAFE,
    "status": ToolCategory.SAFE,
    "info": ToolCategory.SAFE,
    "listar": ToolCategory.SAFE,
    "consultar": ToolCategory.SAFE,
    "help": ToolCategory.SAFE,
    "dream": ToolCategory.SAFE,          # Dream do Kairos (leitura consolidada)

    # WRITE — escrita em arquivo ou banco
    "Write": ToolCategory.WRITE,
    "Edit": ToolCategory.WRITE,
    "NotebookEdit": ToolCategory.WRITE,
    "criar_arquivo": ToolCategory.WRITE,
    "salvar": ToolCategory.WRITE,
    "atualizar": ToolCategory.WRITE,
    "toggle": ToolCategory.WRITE,        # Toggle de feature flags

    # EXECUTE — execução de comandos
    "Bash": ToolCategory.EXECUTE,
    "executar_comando": ToolCategory.EXECUTE,
    "run": ToolCategory.EXECUTE,
    "spawn": ToolCategory.EXECUTE,       # Spawn de agentes
    "fork": ToolCategory.EXECUTE,        # Fork de sub-agentes

    # DESTRUCTIVE — ações irreversíveis
    "Delete": ToolCategory.DESTRUCTIVE,
    "drop": ToolCategory.DESTRUCTIVE,
    "remover": ToolCategory.DESTRUCTIVE,
    "push_force": ToolCategory.DESTRUCTIVE,
    "reset_hard": ToolCategory.DESTRUCTIVE,
    "restart": ToolCategory.DESTRUCTIVE,  # Restart do serviço

    # EXTERNAL — chamadas externas
    "Deploy": ToolCategory.EXTERNAL,
    "Email": ToolCategory.EXTERNAL,
    "enviar_email": ToolCategory.EXTERNAL,
    "push": ToolCategory.EXTERNAL,        # Git push
    "merge": ToolCategory.EXTERNAL,       # Git merge
    "criar_pr": ToolCategory.EXTERNAL,    # Criar Pull Request
}


@dataclass
class VerificationResult:
    """Resultado de uma verificação de permissão."""
    permitido: bool
    ferramenta: str
    categoria: ToolCategory
    modo_atual: AgentMode
    mensagem: str = ""
    request_id: str | None = None  # ID do PermissionRequest (se criado)


def _gerar_id(prefixo: str = "perm", tamanho: int = 8) -> str:
    alfabeto = string.ascii_lowercase + string.digits
    return f"{prefixo}_{''.join(secrets.choice(alfabeto) for _ in range(tamanho))}"


class PermissionGuard:
    """
    Porteiro de permissões do sistema.

    Classifica ferramentas por risco e consulta o modo atual
    para decidir se a ação é permitida ou bloqueada.

    Mantém histórico de ações bloqueadas e pedidos de permissão.

    Atributos:
        _modo_atual: modo de operação do agente
        _sessao_id: ID da sessão de Plan Mode ativa (None se Normal)
        _requests: pedidos de permissão pendentes
        _historico: histórico de verificações
    """

    def __init__(self):
        self._modo_atual: AgentMode = AgentMode.NORMAL
        self._sessao_id: str | None = None
        self._requests: dict[str, PermissionRequest] = {}
        self._historico: list[VerificationResult] = []

    @property
    def modo_atual(self) -> AgentMode:
        return self._modo_atual

    @property
    def em_plan_mode(self) -> bool:
        return self._modo_atual == AgentMode.PLAN

    def ativar_plan_mode(self, sessao_id: str) -> None:
        """Ativa Plan Mode com sessão associada."""
        self._modo_atual = AgentMode.PLAN
        self._sessao_id = sessao_id
        logger.info(f"[Guard] Plan Mode ativado (sessao={sessao_id})")

    def desativar_plan_mode(self) -> None:
        """Volta para modo normal."""
        sessao_anterior = self._sessao_id
        self._modo_atual = AgentMode.NORMAL
        self._sessao_id = None
        logger.info(f"[Guard] Plan Mode desativado (sessao anterior={sessao_anterior})")

    def definir_modo(self, modo: AgentMode, sessao_id: str | None = None) -> None:
        """Define o modo de operação explicitamente."""
        self._modo_atual = modo
        self._sessao_id = sessao_id
        logger.info(f"[Guard] Modo definido: {modo.value}")

    def classificar(self, ferramenta: str) -> ToolCategory:
        """Classifica uma ferramenta por categoria de risco."""
        # Busca exata primeiro
        if ferramenta in TOOL_CLASSIFICATION:
            return TOOL_CLASSIFICATION[ferramenta]

        # Busca case-insensitive
        for key, cat in TOOL_CLASSIFICATION.items():
            if key.lower() == ferramenta.lower():
                return cat

        # Default: SAFE (fail-open para ferramentas desconhecidas em leitura)
        logger.debug(f"[Guard] Ferramenta '{ferramenta}' não classificada — default SAFE")
        return ToolCategory.SAFE

    def verificar(
        self,
        ferramenta: str,
        descricao: str = "",
        parametros: dict | None = None,
    ) -> VerificationResult:
        """
        Verifica se uma ferramenta pode ser executada no modo atual.

        Args:
            ferramenta: nome da ferramenta
            descricao: descrição da ação (para logs e permissão)
            parametros: parâmetros da chamada (sanitizados)

        Returns:
            VerificationResult com permitido=True/False e mensagem
        """
        categoria = self.classificar(ferramenta)
        modo_def = obter_modo(self._modo_atual)
        permitido = modo_def.permite_categoria(categoria)

        resultado = VerificationResult(
            permitido=permitido,
            ferramenta=ferramenta,
            categoria=categoria,
            modo_atual=self._modo_atual,
        )

        if not permitido:
            resultado.mensagem = modo_def.mensagem_bloqueio

            # Criar PermissionRequest se estiver em Plan Mode
            if self._modo_atual == AgentMode.PLAN and self._sessao_id:
                req = PermissionRequest(
                    id=_gerar_id(),
                    sessao_id=self._sessao_id,
                    ferramenta=ferramenta,
                    categoria=categoria,
                    descricao=descricao or f"Uso de {ferramenta}",
                    parametros=parametros or {},
                )
                self._requests[req.id] = req
                resultado.request_id = req.id

            logger.warning(
                f"[Guard] BLOQUEADO: {ferramenta} ({categoria.value}) "
                f"em {self._modo_atual.value} mode"
            )
        else:
            logger.debug(
                f"[Guard] PERMITIDO: {ferramenta} ({categoria.value}) "
                f"em {self._modo_atual.value} mode"
            )

        # Registrar no histórico
        self._historico.append(resultado)
        return resultado

    def aprovar_request(self, request_id: str, aprovado_por: str) -> bool:
        """Aprova um pedido de permissão pendente."""
        req = self._requests.get(request_id)
        if not req or req.status != PermissionStatus.PENDENTE:
            return False

        req.status = PermissionStatus.APROVADO
        req.aprovado_por = aprovado_por
        req.resolvido_em = datetime.now(timezone.utc)
        logger.info(f"[Guard] Permissão {request_id} aprovada por {aprovado_por}")
        return True

    def rejeitar_request(self, request_id: str, rejeitado_por: str) -> bool:
        """Rejeita um pedido de permissão pendente."""
        req = self._requests.get(request_id)
        if not req or req.status != PermissionStatus.PENDENTE:
            return False

        req.status = PermissionStatus.REJEITADO
        req.aprovado_por = rejeitado_por
        req.resolvido_em = datetime.now(timezone.utc)
        logger.info(f"[Guard] Permissão {request_id} rejeitada por {rejeitado_por}")
        return True

    def listar_pendentes(self) -> list[PermissionRequest]:
        """Lista pedidos de permissão pendentes."""
        return [
            r for r in self._requests.values()
            if r.status == PermissionStatus.PENDENTE
        ]

    def estatisticas(self) -> dict:
        """Retorna estatísticas do guard."""
        bloqueados = sum(1 for r in self._historico if not r.permitido)
        return {
            "modo_atual": self._modo_atual.value,
            "em_plan_mode": self.em_plan_mode,
            "sessao_id": self._sessao_id,
            "total_verificacoes": len(self._historico),
            "total_bloqueados": bloqueados,
            "requests_pendentes": len(self.listar_pendentes()),
        }


# Instância singleton
permission_guard = PermissionGuard()
