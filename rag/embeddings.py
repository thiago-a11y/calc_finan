"""
Factory de embeddings para o módulo RAG.

Usa OpenAI text-embedding-3-small por padrão.
Anthropic não oferece API de embeddings, então usamos OpenAI
que já está configurado no .env (OPENAI_API_KEY).

Custo estimado: ~$0.002 para indexar os ~30 arquivos Markdown dos vaults.
"""

import logging

from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger("synerium.rag.embeddings")


def criar_embeddings(modelo: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """
    Cria uma instância de embeddings OpenAI.

    Args:
        modelo: Nome do modelo de embedding. Padrão: text-embedding-3-small.

    Returns:
        Instância de OpenAIEmbeddings pronta para uso.

    Nota:
        A chave OPENAI_API_KEY deve estar configurada no .env.
        O modelo text-embedding-3-small é o mais barato e eficiente
        para nosso volume de documentos (~30 arquivos Markdown).
    """
    logger.info(f"[EMBEDDINGS] Criando embeddings com modelo: {modelo}")
    return OpenAIEmbeddings(model=modelo)
