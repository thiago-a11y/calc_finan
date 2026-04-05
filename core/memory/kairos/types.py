"""
Tipos e dataclasses do sistema Kairos.

Define as estruturas de dados centrais:
- MemorySnapshotData: snapshot de memória capturado
- MemoryEntry: entrada consolidada de memória
- ConsolidationResult: resultado de um ciclo de dream
- MemoryQuery: consulta à memória
- KairosConfig: configuração do sistema
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# Enums
# =============================================================================


class MemoryType(str, Enum):
    """Tipo de memória armazenada."""
    EPISODICA = "episodica"        # Evento específico (reunião, decisão, bug)
    SEMANTICA = "semantica"        # Conhecimento geral (padrão, regra, conceito)
    PROCEDURAL = "procedural"      # Como fazer algo (workflow, processo)
    ESTRATEGICA = "estrategica"    # Decisão de alto nível (roadmap, prioridade)


class ConsolidationStatus(str, Enum):
    """Status de um ciclo de consolidação (dream)."""
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"
    CANCELADO = "cancelado"


class SnapshotSource(str, Enum):
    """Origem do snapshot de memória."""
    LUNA = "luna"                  # Conversa na Luna
    MISSION_CONTROL = "mission_control"  # Sessão Mission Control
    REUNIAO = "reuniao"            # Reunião no Escritório Virtual
    WORKFLOW = "workflow"          # Workflow BMAD autônomo
    MANUAL = "manual"             # Registrado manualmente
    AGENTE = "agente"             # Gerado por agente durante tarefa


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class KairosConfig:
    """
    Configuração do sistema Kairos.

    Atributos:
        dream_interval_min: intervalo entre ciclos de dream (minutos)
        max_snapshots_por_dream: máximo de snapshots processados por ciclo
        max_memoria_por_agente: máximo de memórias consolidadas por agente
        ttl_snapshot_horas: tempo de vida de um snapshot não consolidado
        modelo_consolidacao: modelo LLM para consolidação
        habilitar_auto_dream: se True, dream roda automaticamente
    """
    dream_interval_min: int = 60
    max_snapshots_por_dream: int = 50
    max_memoria_por_agente: int = 200
    ttl_snapshot_horas: int = 72
    modelo_consolidacao: str = "sonnet"
    habilitar_auto_dream: bool = True


@dataclass
class MemorySnapshotData:
    """
    Snapshot de memória capturado de uma interação.

    Representa um fragmento bruto de informação antes da consolidação.
    O AutoDream processa snapshots e gera MemoryEntry consolidadas.

    Atributos:
        id: identificador único
        agente_id: agente que gerou ou a quem pertence
        tenant_id: company_id para isolamento multi-tenant
        source: origem do snapshot (luna, mission_control, etc.)
        conteudo: texto bruto capturado
        contexto: metadados adicionais (conversa_id, tarefa_id, etc.)
        relevancia: score de relevância estimado (0.0 a 1.0)
        criado_em: timestamp de criação
        consolidado: se já foi processado pelo dream
        consolidado_em: timestamp de consolidação
    """
    id: str = ""
    agente_id: str = ""
    tenant_id: int = 1
    source: SnapshotSource = SnapshotSource.MANUAL
    conteudo: str = ""
    contexto: dict[str, Any] = field(default_factory=dict)
    relevancia: float = 0.5
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consolidado: bool = False
    consolidado_em: datetime | None = None


@dataclass
class MemoryEntry:
    """
    Entrada consolidada de memória.

    Resultado do processo de dream: informação destilada,
    categorizada e pronta para consulta.

    Atributos:
        id: identificador único
        agente_id: agente dono desta memória
        tenant_id: company_id multi-tenant
        tipo: tipo de memória (episódica, semântica, etc.)
        titulo: título curto da memória
        conteudo: conteúdo consolidado
        tags: tags para busca e categorização
        relevancia: score de relevância (0.0 a 1.0)
        acessos: número de vezes que foi consultada
        ultimo_acesso: timestamp do último acesso
        fonte_snapshots: IDs dos snapshots que originaram esta memória
        criado_em: timestamp de criação
        atualizado_em: timestamp da última atualização
        ativo: se está ativa (soft delete)
    """
    id: str = ""
    agente_id: str = ""
    tenant_id: int = 1
    tipo: MemoryType = MemoryType.SEMANTICA
    titulo: str = ""
    conteudo: str = ""
    tags: list[str] = field(default_factory=list)
    relevancia: float = 0.5
    acessos: int = 0
    ultimo_acesso: datetime | None = None
    fonte_snapshots: list[str] = field(default_factory=list)
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    atualizado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ativo: bool = True


@dataclass
class MemoryQuery:
    """
    Consulta à memória consolidada.

    Atributos:
        agente_id: filtrar por agente (None = todos)
        tenant_id: filtrar por tenant
        query: texto de busca
        tipo: filtrar por tipo de memória
        tags: filtrar por tags
        limite: máximo de resultados
        min_relevancia: relevância mínima
    """
    agente_id: str | None = None
    tenant_id: int = 1
    query: str = ""
    tipo: MemoryType | None = None
    tags: list[str] = field(default_factory=list)
    limite: int = 10
    min_relevancia: float = 0.0


@dataclass
class ConsolidationResult:
    """
    Resultado de um ciclo de consolidação (dream).

    Atributos:
        dream_id: identificador do ciclo
        status: status final
        snapshots_processados: quantidade de snapshots processados
        memorias_criadas: quantidade de novas memórias
        memorias_atualizadas: quantidade de memórias atualizadas
        memorias_removidas: quantidade de memórias expiradas/removidas
        duracao_ms: duração do ciclo em milissegundos
        erro: mensagem de erro (se falhou)
        iniciado_em: timestamp de início
        concluido_em: timestamp de conclusão
    """
    dream_id: str = ""
    status: ConsolidationStatus = ConsolidationStatus.PENDENTE
    snapshots_processados: int = 0
    memorias_criadas: int = 0
    memorias_atualizadas: int = 0
    memorias_removidas: int = 0
    duracao_ms: float = 0.0
    erro: str | None = None
    iniciado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    concluido_em: datetime | None = None
