"""
Approval Gates — Portões de Aprovação com Human-in-the-Loop

Implementa o sistema de aprovação obrigatória para ações críticas.
Integra com LangSmith para tracing e observabilidade.
"""

import logging
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from config.settings import settings

logger = logging.getLogger("synerium.gates")


class TipoAprovacao(str, Enum):
    """Tipos de ação que requerem aprovação."""
    DEPLOY_PRODUCAO = "deploy_producao"
    GASTO_IA = "gasto_ia"
    MUDANCA_ARQUITETURA = "mudanca_arquitetura"
    CAMPANHA_MARKETING = "campanha_marketing"
    OUTREACH_MASSA = "outreach_massa"
    IMPLEMENTATION_READINESS = "implementation_readiness"


class ReadinessResult(str, Enum):
    """Resultado do Implementation Readiness Check."""
    PASS = "pass"
    CONCERNS = "concerns"
    FAIL = "fail"


class ReadinessCheck(BaseModel):
    """
    Implementation Readiness Check — Gate BMAD Fase 3.

    Verifica se tudo está pronto antes de escrever código.
    Resultado: PASS (implementar), CONCERNS (implementar com ressalvas), FAIL (voltar).
    """
    projeto: str
    prd_completo: bool = False
    prd_validado: bool = False
    arquitetura_documentada: bool = False
    epicos_criados: bool = False
    stories_com_bdd: bool = False
    stories_com_dev_notes: bool = False
    ux_alinhado: bool | None = None  # None = não aplicável
    riscos_mitigados: bool = False
    aprovado_por: str | None = None
    resultado: ReadinessResult | None = None
    observacoes: str = ""
    criado_em: datetime = datetime.now()

    def verificar(self) -> ReadinessResult:
        """
        Executa a verificação automática.
        Retorna PASS, CONCERNS ou FAIL.
        """
        checks = [
            self.prd_completo,
            self.prd_validado,
            self.arquitetura_documentada,
            self.epicos_criados,
            self.stories_com_bdd,
            self.stories_com_dev_notes,
            self.riscos_mitigados,
        ]

        # UX é opcional
        if self.ux_alinhado is not None:
            checks.append(self.ux_alinhado)

        total = len(checks)
        aprovados = sum(1 for c in checks if c)

        if aprovados == total:
            self.resultado = ReadinessResult.PASS
        elif aprovados >= total * 0.7:
            self.resultado = ReadinessResult.CONCERNS
        else:
            self.resultado = ReadinessResult.FAIL

        logger.info(
            f"[READINESS] {self.projeto}: {self.resultado.value} "
            f"({aprovados}/{total} critérios aprovados)"
        )
        return self.resultado


class SolicitacaoAprovacao(BaseModel):
    """Modelo de uma solicitação de aprovação."""
    tipo: TipoAprovacao
    descricao: str
    solicitante: str
    valor_estimado: float | None = None
    criado_em: datetime = datetime.now()
    aprovado: bool | None = None
    aprovado_por: str | None = None


class ApprovalGate:
    """
    Portão de aprovação com human-in-the-loop.

    Qualquer ação crítica passa por aqui antes de ser executada.
    O agente PARA automaticamente e aguarda resposta do Operations Lead.
    """

    def __init__(self):
        self.historico: list[SolicitacaoAprovacao] = []
        self.limite_gasto = settings.limite_gasto_ia

    def requer_aprovacao(self, tipo: TipoAprovacao, descricao: str,
                         solicitante: str, valor: float | None = None) -> SolicitacaoAprovacao:
        """
        Cria uma solicitação de aprovação e PARA a execução.
        Retorna a solicitação pendente para o Operations Lead decidir.
        """
        solicitacao = SolicitacaoAprovacao(
            tipo=tipo,
            descricao=descricao,
            solicitante=solicitante,
            valor_estimado=valor,
        )

        logger.info(
            f"[APPROVAL GATE] Solicitação criada: {tipo.value} | "
            f"Solicitante: {solicitante} | Descrição: {descricao}"
        )

        # Verificação automática de limite de gasto
        if tipo == TipoAprovacao.GASTO_IA and valor and valor <= self.limite_gasto:
            solicitacao.aprovado = True
            solicitacao.aprovado_por = "auto_aprovado_limite"
            logger.info(
                f"[APPROVAL GATE] Auto-aprovado: gasto de R${valor:.2f} "
                f"dentro do limite de R${self.limite_gasto:.2f}"
            )
        else:
            logger.warning(
                f"[APPROVAL GATE] AGUARDANDO APROVAÇÃO DO OPERATIONS LEAD: "
                f"{tipo.value} — {descricao}"
            )

        self.historico.append(solicitacao)
        return solicitacao

    def aprovar(self, solicitacao: SolicitacaoAprovacao, aprovador: str = "Operations Lead") -> SolicitacaoAprovacao:
        """Operations Lead aprova a solicitação."""
        solicitacao.aprovado = True
        solicitacao.aprovado_por = aprovador
        logger.info(f"[APPROVAL GATE] APROVADO por {aprovador}: {solicitacao.descricao}")
        return solicitacao

    def rejeitar(self, solicitacao: SolicitacaoAprovacao, aprovador: str = "Operations Lead") -> SolicitacaoAprovacao:
        """Operations Lead rejeita a solicitação."""
        solicitacao.aprovado = False
        solicitacao.aprovado_por = aprovador
        logger.warning(f"[APPROVAL GATE] REJEITADO por {aprovador}: {solicitacao.descricao}")
        return solicitacao

    def listar_pendentes(self) -> list[SolicitacaoAprovacao]:
        """Lista todas as solicitações pendentes de aprovação."""
        return [s for s in self.historico if s.aprovado is None]


# Instância global
approval_gate = ApprovalGate()
