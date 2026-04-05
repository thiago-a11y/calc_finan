"""
Tipos e dataclasses do sistema Plan Mode.

Define as estruturas centrais:
- AgentMode: enum dos modos disponíveis (plan, normal, restricted)
- PlanModeConfig: configuração do Plan Mode
- PlanSession: sessão de planejamento ativa
- PermissionRequest: pedido de permissão para executar ação bloqueada
- ToolCategory: categorização de ferramentas por nível de risco
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# Enums
# =============================================================================


class AgentMode(str, Enum):
    """Modo de operação do agente."""
    NORMAL = "normal"          # Modo padrão — todas as ferramentas habilitadas
    PLAN = "plan"              # Modo plano — somente-leitura, sem ações destrutivas
    RESTRICTED = "restricted"  # Modo restrito — apenas ferramentas explicitamente permitidas


class ToolCategory(str, Enum):
    """Categoria de risco de uma ferramenta."""
    SAFE = "safe"              # Leitura, análise, consulta — sempre permitido
    WRITE = "write"            # Escrita em arquivo, banco — bloqueado em Plan Mode
    EXECUTE = "execute"        # Execução de comandos — bloqueado em Plan Mode
    DESTRUCTIVE = "destructive"  # Ações irreversíveis (delete, push --force) — requer aprovação explícita
    EXTERNAL = "external"      # Chamadas externas (API, email, deploy) — bloqueado em Plan Mode


class PermissionStatus(str, Enum):
    """Status de um pedido de permissão."""
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"
    EXPIRADO = "expirado"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class PlanModeConfig:
    """
    Configuração do Plan Mode.

    Atributos:
        ferramentas_permitidas: lista de ferramentas permitidas no Plan Mode
        ferramentas_bloqueadas: lista de ferramentas bloqueadas no Plan Mode
        timeout_sessao_min: timeout de uma sessão de planejamento em minutos
        permitir_escrita_plano: se True, permite salvar o plano em arquivo
        requer_aprovacao_saida: se True, exige aprovação do CEO para sair do Plan Mode
    """
    ferramentas_permitidas: list[str] = field(default_factory=lambda: [
        "Read", "Grep", "Glob", "Search", "Consultar",
        "listar", "status", "info", "help",
    ])
    ferramentas_bloqueadas: list[str] = field(default_factory=lambda: [
        "Bash", "Write", "Edit", "Delete", "Push",
        "Deploy", "Email", "Restart", "Drop",
    ])
    timeout_sessao_min: int = 120
    permitir_escrita_plano: bool = True
    requer_aprovacao_saida: bool = False


@dataclass
class PlanSession:
    """
    Sessão de planejamento ativa.

    Registra quando e por quem o Plan Mode foi ativado,
    e o plano gerado durante a sessão.

    Atributos:
        id: identificador único da sessão
        usuario_id: quem ativou o Plan Mode
        usuario_nome: nome de quem ativou
        agente_id: agente operando em Plan Mode (None = Luna/CEO direto)
        motivo: razão para entrar em Plan Mode
        plano: texto do plano gerado durante a sessão
        modo_anterior: modo antes de entrar em Plan Mode
        ativo: se a sessão está ativa
        acoes_bloqueadas: contagem de ações que foram bloqueadas
        criado_em: timestamp de criação
        encerrado_em: timestamp de encerramento
    """
    id: str = ""
    usuario_id: int = 0
    usuario_nome: str = ""
    agente_id: str | None = None
    motivo: str = ""
    plano: str = ""
    modo_anterior: AgentMode = AgentMode.NORMAL
    ativo: bool = True
    acoes_bloqueadas: int = 0
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    encerrado_em: datetime | None = None


@dataclass
class PermissionRequest:
    """
    Pedido de permissão para executar ação bloqueada.

    Quando uma ferramenta bloqueada é invocada em Plan Mode,
    um PermissionRequest é criado para o CEO/OpsLead aprovar.

    Atributos:
        id: identificador único
        sessao_id: sessão de planejamento associada
        ferramenta: nome da ferramenta bloqueada
        categoria: categoria de risco da ferramenta
        descricao: descrição da ação que seria executada
        parametros: parâmetros da chamada (sanitizados)
        status: status do pedido
        aprovado_por: quem aprovou (se aprovado)
        criado_em: timestamp
        resolvido_em: timestamp de resolução
    """
    id: str = ""
    sessao_id: str = ""
    ferramenta: str = ""
    categoria: ToolCategory = ToolCategory.WRITE
    descricao: str = ""
    parametros: dict[str, Any] = field(default_factory=dict)
    status: PermissionStatus = PermissionStatus.PENDENTE
    aprovado_por: str | None = None
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolvido_em: datetime | None = None
