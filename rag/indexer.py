"""
Orquestrador de indexação do RAG.

Pipeline completo: carregar vault → dividir em chunks → gerar embeddings → armazenar no ChromaDB.

Suporta indexação de múltiplos vaults Obsidian com isolamento por tenant.
Usa LangSmith tracing para observabilidade de todo o processo.
"""

import logging
from datetime import datetime

from langsmith import traceable

from rag.config import RAGConfig
from rag.embeddings import criar_embeddings
from rag.loader import carregar_vault
from rag.splitter import dividir_documentos
from rag.store import RAGStore

logger = logging.getLogger("synerium.rag.indexer")


class RAGIndexer:
    """
    Orquestrador de indexação: load → split → embed → store.

    Gerencia o pipeline completo de indexação dos vaults Obsidian
    no ChromaDB, com suporte a multi-tenant e reindexação.
    """

    def __init__(self, config: RAGConfig):
        """
        Inicializa o indexador.

        Args:
            config: Configurações do RAG (vaults, chunk sizes, modelo, etc.)
        """
        self.config = config
        self.embeddings = criar_embeddings(config.embedding_model)
        self.store = RAGStore(config.persist_directory, self.embeddings)

        logger.info(
            f"[INDEXER] Inicializado com {len(config.vaults)} vault(s) configurado(s)."
        )

    @traceable(name="rag_indexar_vault")
    def indexar_vault(self, nome_vault: str, caminho: str, company_id: str):
        """
        Pipeline completo de indexação de um vault Obsidian.

        Etapas:
            1. Carregar todos os .md do vault
            2. Dividir em chunks inteligentes (por headers + recursive)
            3. Injetar company_id nos metadados
            4. Armazenar no ChromaDB com embeddings

        Args:
            nome_vault: Nome identificador do vault (ex: "syneriumx").
            caminho: Caminho absoluto do diretório do vault.
            company_id: Identificador do tenant.
        """
        inicio = datetime.now()
        logger.info(f"[INDEXER] Iniciando indexação do vault '{nome_vault}'...")

        # Etapa 1: Carregar documentos do vault
        documentos = carregar_vault(caminho, nome_vault)
        if not documentos:
            logger.warning(f"[INDEXER] Nenhum documento encontrado no vault '{nome_vault}'.")
            return

        # Etapa 2: Dividir em chunks
        chunks = dividir_documentos(
            documentos,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

        # Etapa 3: Injetar company_id nos metadados de cada chunk
        for chunk in chunks:
            chunk.metadata["company_id"] = company_id

        # Etapa 4: Armazenar no ChromaDB (com reindexação para evitar duplicatas)
        self.store.reindexar(company_id, nome_vault, chunks)

        duracao = (datetime.now() - inicio).total_seconds()
        logger.info(
            f"[INDEXER] Vault '{nome_vault}' indexado com sucesso! "
            f"{len(documentos)} docs → {len(chunks)} chunks em {duracao:.1f}s"
        )

    def indexar_todos(self, company_id: str | None = None):
        """
        Indexa todos os vaults configurados.

        Args:
            company_id: Identificador do tenant. Se None, usa o padrão da config.
        """
        company = company_id or self.config.company_id
        logger.info(
            f"[INDEXER] Indexando todos os vaults para tenant '{company}'..."
        )

        for nome, caminho in self.config.vaults.items():
            self.indexar_vault(nome, caminho, company)

        logger.info(f"[INDEXER] Todos os vaults indexados para tenant '{company}'.")

    def reindexar_vault(self, nome_vault: str, caminho: str, company_id: str | None = None):
        """
        Reindexa um vault específico (útil quando arquivos mudam).

        É o mesmo que indexar_vault, pois sempre faz reindexação completa.

        Args:
            nome_vault: Nome do vault a reindexar.
            caminho: Caminho absoluto do vault.
            company_id: Identificador do tenant. Se None, usa o padrão.
        """
        company = company_id or self.config.company_id
        self.indexar_vault(nome_vault, caminho, company)
