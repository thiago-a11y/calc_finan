"""
Rota: RAG (Base de Conhecimento)

GET  /api/rag/status    — Status dos vaults e configuração do RAG
GET  /api/rag/stats     — Estatísticas de indexação (total chunks, por vault)
POST /api/rag/consultar — Consulta semântica com resposta da IA
POST /api/rag/indexar   — Reindexar vaults (todos ou específico)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.dependencias import obter_fabrica
from api.schemas import (
    RAGStatusResponse,
    RAGConsultaRequest,
    RAGConsultaResponse,
    RAGChunkResponse,
    RAGIndexarRequest,
    RAGIndexarResponse,
    RAGStatsResponse,
    VaultResumo,
)

logger = logging.getLogger("synerium.api.rag")

router = APIRouter(prefix="/api/rag", tags=["RAG"])


@router.get("/status", response_model=RAGStatusResponse)
def status_rag(fabrica=Depends(obter_fabrica)):
    """Retorna status e configuração do sistema RAG."""
    config = fabrica.rag_config
    vaults = [
        VaultResumo(nome=nome, caminho=caminho)
        for nome, caminho in config.vaults.items()
    ]

    return RAGStatusResponse(
        vaults_configurados=vaults,
        total_vaults=len(vaults),
        persist_directory=config.persist_directory,
        company_id=config.company_id,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        embedding_model=config.embedding_model,
    )


@router.get("/stats", response_model=RAGStatsResponse)
def stats_rag(fabrica=Depends(obter_fabrica)):
    """Retorna estatísticas de indexação do RAG."""
    config = fabrica.rag_config
    stats = fabrica.rag_indexer.store.contar_chunks(config.company_id)

    return RAGStatsResponse(
        total_chunks=stats["total"],
        por_vault=stats["por_vault"],
        vaults_indexados=stats["vaults_indexados"],
        persist_directory=config.persist_directory,
        company_id=config.company_id,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        embedding_model=config.embedding_model,
    )


@router.post("/consultar", response_model=RAGConsultaResponse)
def consultar_rag(req: RAGConsultaRequest, fabrica=Depends(obter_fabrica)):
    """Consulta a base de conhecimento com resposta inteligente da IA."""
    vaults = [req.vault] if req.vault else None

    resultado = fabrica.rag_assistant.consultar(
        pergunta=req.pergunta,
        vaults=vaults,
    )

    chunks = [
        RAGChunkResponse(**chunk)
        for chunk in resultado["chunks"]
    ]

    return RAGConsultaResponse(
        pergunta=req.pergunta,
        resposta_ia=resultado["resposta_ia"],
        chunks=chunks,
        total_chunks=resultado["total_chunks"],
    )


@router.post("/indexar", response_model=RAGIndexarResponse)
def indexar_rag(req: RAGIndexarRequest, fabrica=Depends(obter_fabrica)):
    """
    Reindexa os vaults Obsidian no ChromaDB.

    Se vault for especificado, reindexa apenas aquele vault.
    Se for None, reindexa todos os vaults configurados.
    """
    config = fabrica.rag_config

    if req.vault:
        # Indexar vault específico
        if req.vault not in config.vaults:
            raise HTTPException(
                status_code=404,
                detail=f"Vault '{req.vault}' não encontrado. Disponíveis: {list(config.vaults.keys())}"
            )
        logger.info(f"[RAG] Reindexando vault: {req.vault}")
        fabrica.rag_indexer.reindexar_vault(
            nome_vault=req.vault,
            caminho=config.vaults[req.vault],
            company_id=config.company_id,
        )
        vaults_indexados = [req.vault]
    else:
        # Indexar todos
        logger.info("[RAG] Reindexando todos os vaults...")
        for nome, caminho in config.vaults.items():
            fabrica.rag_indexer.reindexar_vault(
                nome_vault=nome,
                caminho=caminho,
                company_id=config.company_id,
            )
        vaults_indexados = list(config.vaults.keys())

    # Contar chunks após indexação
    stats = fabrica.rag_indexer.store.contar_chunks(config.company_id)

    logger.info(f"[RAG] Indexação concluída: {stats['total']} chunks em {len(vaults_indexados)} vault(s)")

    return RAGIndexarResponse(
        mensagem=f"Indexação concluída com sucesso!",
        vaults_indexados=vaults_indexados,
        total_chunks=stats["total"],
    )
