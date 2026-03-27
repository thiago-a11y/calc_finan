"""
Ferramenta CrewAI para consultar a base de conhecimento (RAG).

Os agentes (PM Central, squads) usam esta ferramenta para buscar
informações nos vaults Obsidian indexados no ChromaDB.

Exemplo de uso pelo agente:
    "Qual a arquitetura do SyneriumX?"
    "Quais são os módulos em produção do CRM?"
    "Quais decisões técnicas foram tomadas sobre o banco de dados?"
"""

from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from rag.query import RAGQuery


class ConsultarBaseConhecimentoInput(BaseModel):
    """Esquema de entrada para consulta na base de conhecimento."""

    pergunta: str = Field(
        description=(
            "Pergunta para buscar na base de conhecimento. "
            "Pode ser sobre arquitetura, decisões técnicas, roadmap, "
            "backlog, bugs, deploys ou qualquer documentação do projeto."
        )
    )
    vault: str | None = Field(
        default=None,
        description=(
            "Vault específico para consultar. Opções: 'syneriumx' (CRM) "
            "ou 'factory' (Synerium Factory). Se não informado, busca em todos."
        ),
    )


class ConsultarBaseConhecimento(BaseTool):
    """
    Ferramenta para agentes consultarem a base de conhecimento.

    Busca nos vaults Obsidian indexados no ChromaDB usando
    busca semântica por similaridade vetorial.

    O agente pode especificar um vault específico ou buscar em todos.
    Resultados incluem metadados de origem (vault, arquivo, seção).
    """

    name: str = "consultar_base_conhecimento"
    description: str = (
        "Consulta a base de conhecimento do Synerium Factory e do SyneriumX. "
        "Use para buscar informações sobre arquitetura, decisões técnicas, "
        "roadmap, backlog, bugs conhecidos, guia de deploy e toda a "
        "documentação dos projetos. Retorna os trechos mais relevantes "
        "encontrados nos vaults Obsidian."
    )
    args_schema: type = ConsultarBaseConhecimentoInput

    # Estado interno — injetado na construção
    _rag_query: RAGQuery | None = None

    def __init__(self, rag_query: RAGQuery, **kwargs: Any):
        """
        Inicializa a ferramenta com a instância de RAGQuery.

        Args:
            rag_query: Interface de consulta RAG já configurada.
        """
        super().__init__(**kwargs)
        self._rag_query = rag_query

    def _run(self, pergunta: str, vault: str | None = None) -> str:
        """
        Executa a consulta na base de conhecimento.

        Args:
            pergunta: Texto da pergunta.
            vault: Vault específico ou None para todos.

        Returns:
            Texto formatado com os resultados encontrados.
        """
        if self._rag_query is None:
            return (
                "Erro: Base de conhecimento não inicializada. "
                "Execute 'python orchestrator.py --indexar' primeiro."
            )

        vaults = [vault] if vault else None
        return self._rag_query.consultar(pergunta, vaults=vaults)
