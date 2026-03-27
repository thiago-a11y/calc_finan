"""
Módulo RAG (Retrieval-Augmented Generation) do Synerium Factory.

Fornece a base de conhecimento para os agentes consultarem
os vaults Obsidian do SyneriumX e do Synerium Factory.

Componentes principais:
    - RAGConfig: Configurações (vaults, chunk sizes, modelo de embedding)
    - RAGIndexer: Pipeline de indexação (load → split → embed → store)
    - RAGQuery: Interface de consulta formatada para LLM
    - RAGStore: Gerenciador do ChromaDB com suporte multi-tenant
"""

from rag.config import RAGConfig
from rag.indexer import RAGIndexer
from rag.query import RAGQuery
from rag.store import RAGStore
from rag.assistant import RAGAssistant

__all__ = ["RAGConfig", "RAGIndexer", "RAGQuery", "RAGStore", "RAGAssistant"]
