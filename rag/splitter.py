"""
Divisão inteligente de documentos Markdown em chunks.

Estratégia em 2 estágios:
1. MarkdownHeaderTextSplitter — divide por headers (#, ##, ###),
   preservando o contexto hierárquico de cada seção.
2. RecursiveCharacterTextSplitter — subdivide chunks que ainda
   são grandes demais (ex: arquivo de 15K tokens do SyneriumX).

Cada chunk resultante mantém todos os metadados originais
do documento mais os headers da seção onde ele se encontra.
"""

import logging

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

logger = logging.getLogger("synerium.rag.splitter")

# Headers que o splitter vai usar para dividir os documentos
HEADERS_PARA_DIVIDIR = [
    ("#", "header_1"),
    ("##", "header_2"),
    ("###", "header_3"),
]


def dividir_documentos(
    documentos: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """
    Divide documentos Markdown em chunks inteligentes.

    Args:
        documentos: Lista de Documents carregados do vault.
        chunk_size: Tamanho máximo de cada chunk em caracteres.
        chunk_overlap: Sobreposição entre chunks para manter contexto.

    Returns:
        Lista de Documents divididos, com metadados preservados.

    Processo:
        1. Cada documento é dividido por headers Markdown (H1, H2, H3).
        2. Chunks resultantes que excedem chunk_size são subdivididos
           pelo RecursiveCharacterTextSplitter.
        3. Metadados originais (vault, source_path, etc.) são preservados
           e enriquecidos com informação dos headers.
    """
    # Splitters
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_PARA_DIVIDIR,
        strip_headers=False,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    todos_chunks: list[Document] = []

    for doc in documentos:
        # Estágio 1: Dividir por headers Markdown
        try:
            chunks_md = md_splitter.split_text(doc.page_content)
        except Exception as e:
            logger.warning(
                f"[SPLITTER] Erro no split por headers de {doc.metadata.get('file_name', '?')}: {e}. "
                f"Usando documento inteiro."
            )
            chunks_md = [doc]

        for chunk in chunks_md:
            # Mesclar metadados: originais do documento + headers do chunk
            metadados_mesclados = {**doc.metadata}

            # Se o chunk veio do MarkdownHeaderTextSplitter, ele tem metadata com headers
            if hasattr(chunk, "metadata") and chunk.metadata:
                metadados_mesclados.update(chunk.metadata)

            # Pegar o conteúdo do chunk
            conteudo = chunk.page_content if hasattr(chunk, "page_content") else str(chunk)

            # Estágio 2: Se o chunk ainda é grande demais, subdividir
            if len(conteudo) > chunk_size:
                sub_chunks = text_splitter.split_text(conteudo)
                for i, sub in enumerate(sub_chunks):
                    todos_chunks.append(Document(
                        page_content=sub,
                        metadata={
                            **metadados_mesclados,
                            "chunk_index": i,
                        },
                    ))
            else:
                todos_chunks.append(Document(
                    page_content=conteudo,
                    metadata=metadados_mesclados,
                ))

    logger.info(
        f"[SPLITTER] {len(documentos)} documentos → {len(todos_chunks)} chunks "
        f"(chunk_size={chunk_size}, overlap={chunk_overlap})"
    )
    return todos_chunks
