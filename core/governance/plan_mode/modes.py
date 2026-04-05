"""
Modes — Definição e gestão dos modos de operação do agente.

Cada modo define quais categorias de ferramentas são permitidas.
O PlanMode é o modo principal deste módulo: somente-leitura,
análise e planejamento sem execução de ações perigosas.

Uso:
    from core.governance.plan_mode.modes import MODOS, obter_modo

    modo = obter_modo(AgentMode.PLAN)
    if modo.permite_categoria(ToolCategory.EXECUTE):
        executar()
    else:
        bloquear()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.governance.plan_mode.types import AgentMode, ToolCategory

logger = logging.getLogger("synerium.governance.modes")


@dataclass
class ModeDefinition:
    """
    Definição de um modo de operação.

    Atributos:
        modo: enum do modo
        nome: nome de exibição
        descricao: descrição do modo
        categorias_permitidas: categorias de ferramentas permitidas
        mensagem_bloqueio: mensagem exibida quando uma ação é bloqueada
    """
    modo: AgentMode
    nome: str
    descricao: str
    categorias_permitidas: set[ToolCategory] = field(default_factory=set)
    mensagem_bloqueio: str = ""

    def permite_categoria(self, categoria: ToolCategory) -> bool:
        """Verifica se uma categoria de ferramenta é permitida neste modo."""
        return categoria in self.categorias_permitidas

    def permite_ferramenta(self, ferramenta: str, classificacao: dict[str, ToolCategory]) -> bool:
        """Verifica se uma ferramenta específica é permitida."""
        categoria = classificacao.get(ferramenta, ToolCategory.SAFE)
        return self.permite_categoria(categoria)


# =============================================================================
# Modos pré-definidos
# =============================================================================

MODO_NORMAL = ModeDefinition(
    modo=AgentMode.NORMAL,
    nome="Modo Normal",
    descricao="Todas as ferramentas habilitadas. Modo padrão de operação.",
    categorias_permitidas={
        ToolCategory.SAFE,
        ToolCategory.WRITE,
        ToolCategory.EXECUTE,
        ToolCategory.DESTRUCTIVE,
        ToolCategory.EXTERNAL,
    },
    mensagem_bloqueio="",  # Nunca bloqueia
)

MODO_PLAN = ModeDefinition(
    modo=AgentMode.PLAN,
    nome="Modo Plano",
    descricao=(
        "Somente-leitura. Permite análise, consulta e geração de planos. "
        "Bloqueia escrita, execução, ações destrutivas e chamadas externas."
    ),
    categorias_permitidas={
        ToolCategory.SAFE,
    },
    mensagem_bloqueio=(
        "Acao bloqueada: voce esta em Plan Mode (somente-leitura). "
        "Saia do Plan Mode para executar esta acao, ou solicite permissao ao CEO."
    ),
)

MODO_RESTRICTED = ModeDefinition(
    modo=AgentMode.RESTRICTED,
    nome="Modo Restrito",
    descricao=(
        "Apenas ferramentas explicitamente permitidas. "
        "Usado para agentes com escopo limitado."
    ),
    categorias_permitidas={
        ToolCategory.SAFE,
    },
    mensagem_bloqueio=(
        "Acao bloqueada: voce esta em Modo Restrito. "
        "Apenas ferramentas de leitura e consulta estao disponiveis."
    ),
)

# Mapa de modos para lookup rápido
MODOS: dict[AgentMode, ModeDefinition] = {
    AgentMode.NORMAL: MODO_NORMAL,
    AgentMode.PLAN: MODO_PLAN,
    AgentMode.RESTRICTED: MODO_RESTRICTED,
}


def obter_modo(modo: AgentMode) -> ModeDefinition:
    """Retorna a definição de um modo pelo enum."""
    return MODOS.get(modo, MODO_NORMAL)
