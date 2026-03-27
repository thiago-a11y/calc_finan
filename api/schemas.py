"""
Schemas Pydantic para a API REST do Synerium Factory.

Define os modelos de request/response para cada endpoint.
Todos os schemas seguem o padrão Pydantic v2.
"""

from datetime import datetime
from pydantic import BaseModel

from gates.approval_gates import TipoAprovacao


# --- Status Geral ---

class SquadResumo(BaseModel):
    """Resumo de um squad para o painel geral."""
    nome: str
    especialidade: str
    contexto: str
    num_agentes: int
    num_tarefas: int


class VaultResumo(BaseModel):
    """Resumo de um vault RAG."""
    nome: str
    caminho: str


class UsuarioResumo(BaseModel):
    """Resumo de um usuário para o painel."""
    id: str
    nome: str
    cargo: str
    pode_aprovar: bool


class StatusGeralResponse(BaseModel):
    """Resposta do endpoint GET /api/status."""
    ambiente: str
    data_hora: str
    pm_central: str = "Alex (ativo)"
    operations_lead: str = "Jonatas — Diretor Técnico"
    lideranca: list[UsuarioResumo]
    squads: list[SquadResumo]
    total_squads: int
    aprovacoes_pendentes: int
    rag_vaults: list[VaultResumo]
    total_vaults: int


# --- Squads ---

class SquadResponse(BaseModel):
    """Resposta detalhada de um squad."""
    nome: str
    especialidade: str
    contexto: str
    num_agentes: int
    num_tarefas: int
    nomes_agentes: list[str]
    proprietario_email: str = ""
    tipo: str = "area"  # "pessoal" ou "area"
    is_meu: bool = False  # True se pertence ao usuário logado


# --- Aprovações ---

class AprovacaoResponse(BaseModel):
    """Resposta de uma solicitação de aprovação."""
    indice: int
    tipo: str
    descricao: str
    solicitante: str
    valor_estimado: float | None = None
    criado_em: datetime
    aprovado: bool | None = None
    aprovado_por: str | None = None


class AprovacaoAcaoRequest(BaseModel):
    """Request para aprovar ou rejeitar uma solicitação."""
    aprovado: bool


class CriarAprovacaoRequest(BaseModel):
    """Request para criar uma nova solicitação de aprovação."""
    tipo: TipoAprovacao
    descricao: str
    solicitante: str
    valor_estimado: float | None = None


# --- RAG ---

class RAGStatusResponse(BaseModel):
    """Status do sistema RAG."""
    vaults_configurados: list[VaultResumo]
    total_vaults: int
    persist_directory: str
    company_id: str
    chunk_size: int
    chunk_overlap: int
    embedding_model: str


class RAGConsultaRequest(BaseModel):
    """Request para consultar a base de conhecimento."""
    pergunta: str
    vault: str | None = None


class RAGChunkResponse(BaseModel):
    """Um chunk recuperado da busca semântica."""
    vault: str
    arquivo: str
    secao: str
    conteudo: str


class RAGConsultaResponse(BaseModel):
    """Resposta de uma consulta RAG com IA."""
    pergunta: str
    resposta_ia: str
    chunks: list[RAGChunkResponse]
    total_chunks: int


class RAGIndexarRequest(BaseModel):
    """Request para reindexar vaults."""
    vault: str | None = None  # None = todos


class RAGIndexarResponse(BaseModel):
    """Resposta da reindexação."""
    mensagem: str
    vaults_indexados: list[str]
    total_chunks: int


class RAGStatsResponse(BaseModel):
    """Estatísticas do RAG."""
    total_chunks: int
    por_vault: dict[str, int]
    vaults_indexados: list[str]
    persist_directory: str
    company_id: str
    chunk_size: int
    chunk_overlap: int
    embedding_model: str


# --- Standup ---

class StandupResponse(BaseModel):
    """Resposta do standup diário."""
    relatorio: str
    data_execucao: str
    squads_reportados: int
