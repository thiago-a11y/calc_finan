"""
Carregador de documentos Markdown dos vaults Obsidian.

Lê todos os arquivos .md de um vault e enriquece
cada documento com metadados (vault, caminho, nome do arquivo, data).
"""

import logging
from datetime import datetime
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger("synerium.rag.loader")


def carregar_vault(caminho: str, nome_vault: str) -> list[Document]:
    """
    Carrega todos os arquivos .md de um vault Obsidian.

    Percorre recursivamente o diretório do vault, lê cada arquivo
    Markdown e cria um Document do LangChain com metadados enriquecidos.

    Args:
        caminho: Caminho absoluto do diretório do vault.
        nome_vault: Nome identificador do vault (ex: "syneriumx", "factory").

    Returns:
        Lista de Documents com conteúdo e metadados.

    Metadados adicionados a cada documento:
        - vault: Nome do vault de origem.
        - source_path: Caminho relativo do arquivo dentro do vault.
        - file_name: Nome do arquivo sem o caminho.
        - indexed_at: Data/hora da indexação em formato ISO.
    """
    caminho_vault = Path(caminho)

    if not caminho_vault.exists():
        logger.error(f"[LOADER] Vault não encontrado: {caminho}")
        return []

    documentos: list[Document] = []
    arquivos_md = sorted(caminho_vault.rglob("*.md"))

    # Ignorar arquivos dentro de .obsidian e Templates
    arquivos_filtrados = [
        arq for arq in arquivos_md
        if ".obsidian" not in str(arq)
    ]

    logger.info(
        f"[LOADER] Vault '{nome_vault}': encontrados {len(arquivos_filtrados)} "
        f"arquivos .md em {caminho}"
    )

    for arquivo in arquivos_filtrados:
        try:
            conteudo = arquivo.read_text(encoding="utf-8")

            # Ignorar arquivos vazios
            if not conteudo.strip():
                logger.warning(f"[LOADER] Arquivo vazio ignorado: {arquivo.name}")
                continue

            # Caminho relativo dentro do vault
            caminho_relativo = str(arquivo.relative_to(caminho_vault))

            documento = Document(
                page_content=conteudo,
                metadata={
                    "vault": nome_vault,
                    "source_path": caminho_relativo,
                    "file_name": arquivo.name,
                    "indexed_at": datetime.now().isoformat(),
                },
            )
            documentos.append(documento)

            logger.debug(f"[LOADER] Carregado: {caminho_relativo}")

        except Exception as e:
            logger.error(f"[LOADER] Erro ao ler {arquivo}: {e}")

    logger.info(
        f"[LOADER] Vault '{nome_vault}': {len(documentos)} documentos carregados."
    )
    return documentos
