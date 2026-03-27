"""
Configurações do módulo RAG (Retrieval-Augmented Generation).

Define parâmetros para indexação, embedding e consulta
da base de conhecimento do Synerium Factory.
"""

from pydantic import BaseModel


class RAGConfig(BaseModel):
    """
    Configurações do RAG.

    Atributos:
        vaults: Dicionário com nome e caminho de cada vault Obsidian.
        persist_directory: Diretório onde o ChromaDB persiste os dados.
        chunk_size: Tamanho máximo de cada chunk em caracteres.
        chunk_overlap: Sobreposição entre chunks para manter contexto.
        embedding_model: Modelo de embedding OpenAI a ser usado.
        company_id: Identificador do tenant (multi-tenant).
        k_results: Quantidade de resultados por consulta.
    """

    # Caminhos dos vaults Obsidian
    # Exemplo: {"syneriumx": "/caminho/para/SyneriumX-notes", "factory": "/caminho/para/Factory-notes"}
    vaults: dict[str, str] = {}

    # ChromaDB — diretório de persistência
    persist_directory: str = "data/chromadb"

    # Splitting — tamanho e sobreposição dos chunks
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Embedding — modelo OpenAI
    embedding_model: str = "text-embedding-3-small"

    # Multi-tenant — identificador do tenant atual
    company_id: str = "synerium"

    # Consulta — quantidade de resultados retornados
    k_results: int = 5
