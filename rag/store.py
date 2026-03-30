"""
ChromaDB Store com suporte multi-tenant.

Cada tenant (empresa) tem coleções separadas no ChromaDB,
garantindo isolamento total de dados. O padrão de nomeação
das coleções é: tenant_{company_id}_{vault}.

Exemplo:
    - tenant_synerium_syneriumx → docs do SyneriumX da Objetiva
    - tenant_synerium_factory → docs do Factory da Objetiva
    - tenant_acme_factory → docs do Factory da empresa Acme (futuro)
"""

import logging
from pathlib import Path

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger("synerium.rag.store")


class RAGStore:
    """
    Gerenciador do ChromaDB com isolamento por tenant.

    Cada combinação de tenant + vault gera uma coleção separada,
    garantindo que dados de diferentes empresas nunca se misturam.
    """

    def __init__(self, persist_directory: str, embedding_function: Embeddings):
        """
        Inicializa o store.

        Args:
            persist_directory: Caminho onde o ChromaDB persiste dados em disco.
            embedding_function: Função de embedding (OpenAI) para vetorizar textos.
        """
        self._persist_dir = persist_directory
        self._embeddings = embedding_function

        # Criar diretório se não existir
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(f"[STORE] ChromaDB inicializado em: {persist_directory}")

    def nome_colecao(self, company_id: str, vault: str) -> str:
        """
        Gera o nome da coleção no ChromaDB.

        Padrão: tenant_{company_id}_{vault}
        Exemplo: tenant_synerium_syneriumx

        Args:
            company_id: Identificador do tenant.
            vault: Nome do vault (ex: "syneriumx", "factory").

        Returns:
            Nome da coleção formatado.
        """
        # ChromaDB exige nomes com 3-63 caracteres, sem caracteres especiais
        nome = f"tenant_{company_id}_{vault}"
        # Sanitizar: apenas letras, números e underscores
        nome = "".join(c if c.isalnum() or c == "_" else "_" for c in nome)
        return nome[:63]  # Limite do ChromaDB

    def indexar(self, company_id: str, vault: str, documentos: list[Document]):
        """
        Indexa documentos em uma coleção específica do ChromaDB.

        Cria a coleção se não existir. Se já existir, adiciona
        os documentos à coleção existente.

        Args:
            company_id: Identificador do tenant.
            vault: Nome do vault de origem.
            documentos: Lista de Documents (já divididos em chunks).
        """
        nome = self.nome_colecao(company_id, vault)

        logger.info(
            f"[STORE] Indexando {len(documentos)} chunks na coleção '{nome}'..."
        )

        Chroma.from_documents(
            documents=documentos,
            embedding=self._embeddings,
            collection_name=nome,
            persist_directory=self._persist_dir,
        )

        logger.info(f"[STORE] Coleção '{nome}' indexada com sucesso.")

    def consultar(
        self,
        company_id: str,
        pergunta: str,
        vaults: list[str] | None = None,
        k: int = 5,
    ) -> list[Document]:
        """
        Consulta uma ou mais coleções e retorna os documentos mais relevantes.

        Se nenhum vault for especificado, consulta TODAS as coleções
        do tenant e combina os resultados.

        Args:
            company_id: Identificador do tenant.
            pergunta: Texto da pergunta para busca semântica.
            vaults: Lista de vaults para consultar. None = todos.
            k: Quantidade de resultados por coleção.

        Returns:
            Lista de Documents mais relevantes, ordenados por similaridade.
        """
        # Se não especificou vaults, descobrir quais existem para este tenant
        if vaults is None:
            vaults = self._listar_vaults_tenant(company_id)

        todos_resultados: list[Document] = []

        for vault in vaults:
            nome = self.nome_colecao(company_id, vault)
            try:
                store = Chroma(
                    collection_name=nome,
                    embedding_function=self._embeddings,
                    persist_directory=self._persist_dir,
                )
                resultados = store.similarity_search(pergunta, k=k)
                todos_resultados.extend(resultados)

                logger.debug(
                    f"[STORE] Coleção '{nome}': {len(resultados)} resultados."
                )
            except Exception as e:
                logger.warning(
                    f"[STORE] Erro ao consultar coleção '{nome}': {e}"
                )

        logger.info(
            f"[STORE] Consulta '{pergunta[:50]}...': "
            f"{len(todos_resultados)} resultados de {len(vaults)} coleção(ões)."
        )
        return todos_resultados[:k]  # Limitar ao total de k resultados

    def reindexar(self, company_id: str, vault: str, documentos: list[Document]):
        """
        Reindexa uma coleção do zero (deleta e recria).

        Útil quando arquivos do vault foram atualizados.
        Como o volume é pequeno (~200-400 chunks), a reindexação
        é rápida e simples.

        Args:
            company_id: Identificador do tenant.
            vault: Nome do vault a reindexar.
            documentos: Novos documentos para indexar.
        """
        nome = self.nome_colecao(company_id, vault)

        logger.info(f"[STORE] Reindexando coleção '{nome}'...")

        # Deletar coleção existente
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self._persist_dir)
            client.delete_collection(nome)
            logger.info(f"[STORE] Coleção '{nome}' deletada para reindexação.")
        except Exception:
            logger.debug(f"[STORE] Coleção '{nome}' não existia (primeira indexação).")

        # Recriar com novos documentos
        self.indexar(company_id, vault, documentos)

    def contar_chunks(self, company_id: str) -> dict:
        """
        Conta o total de chunks indexados por vault para um tenant.

        Returns:
            Dict com: total, por_vault (dict vault→count), vaults_indexados (list)
        """
        vaults = self._listar_vaults_tenant(company_id)
        por_vault: dict[str, int] = {}
        total = 0

        try:
            import chromadb
            client = chromadb.PersistentClient(path=self._persist_dir)

            for vault in vaults:
                nome = self.nome_colecao(company_id, vault)
                try:
                    colecao = client.get_collection(nome)
                    count = colecao.count()
                    por_vault[vault] = count
                    total += count
                except Exception:
                    por_vault[vault] = 0
        except Exception as e:
            logger.warning(f"[STORE] Erro ao contar chunks: {e}")

        return {
            "total": total,
            "por_vault": por_vault,
            "vaults_indexados": vaults,
        }

    def _listar_vaults_tenant(self, company_id: str) -> list[str]:
        """
        Lista os vaults disponíveis para um tenant.

        Verifica quais coleções existem no ChromaDB que começam
        com o prefixo do tenant.

        Args:
            company_id: Identificador do tenant.

        Returns:
            Lista de nomes de vaults encontrados.
        """
        prefixo = f"tenant_{company_id}_"
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self._persist_dir)
            colecoes = client.list_collections()
            vaults = []
            for col in colecoes:
                nome = col.name if hasattr(col, "name") else str(col)
                if nome.startswith(prefixo):
                    vault_nome = nome[len(prefixo):]
                    vaults.append(vault_nome)
            return vaults
        except Exception as e:
            logger.warning(f"[STORE] Erro ao listar coleções: {e}")
            return []
