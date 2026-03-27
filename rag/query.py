"""
Interface de consulta do RAG.

Fornece uma API simples para consultar a base de conhecimento
e retornar contexto formatado para os agentes LLM consumirem.

Integra com LangSmith para tracing de cada consulta.
"""

import logging

from langchain_core.documents import Document
from langsmith import traceable

from rag.store import RAGStore

logger = logging.getLogger("synerium.rag.query")


class RAGQuery:
    """
    Interface de consulta para a base de conhecimento.

    Consulta o ChromaDB e formata os resultados em texto
    estruturado que os agentes conseguem interpretar facilmente.
    """

    def __init__(self, store: RAGStore, company_id: str):
        """
        Inicializa a interface de consulta.

        Args:
            store: Instância do RAGStore (ChromaDB).
            company_id: Identificador do tenant para filtrar resultados.
        """
        self.store = store
        self.company_id = company_id

    @traceable(name="rag_consultar")
    def consultar(
        self,
        pergunta: str,
        vaults: list[str] | None = None,
        k: int = 5,
    ) -> str:
        """
        Consulta a base de conhecimento e retorna contexto formatado.

        Args:
            pergunta: Texto da pergunta para busca semântica.
            vaults: Lista de vaults para consultar. None = todos.
            k: Quantidade máxima de resultados.

        Returns:
            Texto formatado com os trechos mais relevantes encontrados.
            Retorna mensagem informativa se nenhum resultado for encontrado.
        """
        logger.info(f"[QUERY] Consultando: '{pergunta[:80]}...'")

        documentos = self.store.consultar(
            company_id=self.company_id,
            pergunta=pergunta,
            vaults=vaults,
            k=k,
        )

        if not documentos:
            logger.info("[QUERY] Nenhum resultado encontrado.")
            return (
                "Nenhum resultado encontrado na base de conhecimento. "
                "Verifique se os vaults foram indexados com 'python orchestrator.py --indexar'."
            )

        contexto = self._formatar_contexto(documentos)
        logger.info(f"[QUERY] {len(documentos)} resultado(s) retornado(s).")
        return contexto

    def _formatar_contexto(self, documentos: list[Document]) -> str:
        """
        Formata documentos em texto estruturado para o LLM.

        Cada resultado inclui metadados de origem (vault, arquivo, seção)
        seguido do conteúdo, separados por linhas divisórias.

        Args:
            documentos: Lista de Documents retornados pela busca.

        Returns:
            Texto formatado com todos os trechos relevantes.
        """
        partes: list[str] = []
        partes.append(f"📚 Base de Conhecimento — {len(documentos)} resultado(s):\n")

        for i, doc in enumerate(documentos, 1):
            meta = doc.metadata
            vault = meta.get("vault", "desconhecido")
            arquivo = meta.get("source_path", meta.get("file_name", "?"))
            header_1 = meta.get("header_1", "")
            header_2 = meta.get("header_2", "")
            header_3 = meta.get("header_3", "")

            # Montar caminho de seção: Header1 > Header2 > Header3
            secoes = [s for s in [header_1, header_2, header_3] if s]
            secao_str = " > ".join(secoes) if secoes else "Documento completo"

            partes.append(
                f"--- Resultado {i} ---\n"
                f"[Vault: {vault} | Arquivo: {arquivo} | Seção: {secao_str}]\n"
                f"{doc.page_content}\n"
            )

        return "\n".join(partes)
