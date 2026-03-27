"""
Rotas: Upload de Arquivos

POST /api/uploads          — Upload de um ou mais arquivos
GET  /uploads/chat/{nome}  — Servir arquivo estático
"""

import os
import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse

from api.dependencias import obter_usuario_atual
from database.models import UsuarioDB

logger = logging.getLogger("synerium.uploads")

router = APIRouter(tags=["Uploads"])

UPLOAD_DIR = os.path.expanduser("~/synerium-factory/data/uploads/chat")
# No servidor AWS o projeto fica em /opt/
if os.path.exists("/opt/synerium-factory"):
    UPLOAD_DIR = "/opt/synerium-factory/data/uploads/chat"

# Extensões permitidas
EXTENSOES_PERMITIDAS = {
    # Imagens
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp",
    # Documentos
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml",
    # Código
    ".php", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".sql", ".py",
    # Vídeo
    ".mp4", ".webm", ".mov", ".avi",
    # Áudio
    ".mp3", ".wav", ".ogg",
    # Compactados
    ".zip", ".rar", ".tar", ".gz",
}

# Tamanho máximo: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/api/uploads")
async def upload_arquivos(
    files: list[UploadFile] = File(...),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Upload de um ou mais arquivos.
    Retorna lista de URLs e metadados de cada arquivo.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    resultados = []

    for file in files:
        # Validar extensão
        ext = Path(file.filename or "").suffix.lower()
        if ext not in EXTENSOES_PERMITIDAS:
            resultados.append({
                "nome_original": file.filename,
                "erro": f"Extensão '{ext}' não permitida.",
            })
            continue

        # Ler conteúdo
        conteudo = await file.read()

        # Validar tamanho
        if len(conteudo) > MAX_FILE_SIZE:
            resultados.append({
                "nome_original": file.filename,
                "erro": f"Arquivo excede o limite de 50MB ({len(conteudo) / 1024 / 1024:.1f}MB).",
            })
            continue

        # Gerar nome único
        file_uuid = uuid.uuid4().hex[:12]
        nome_seguro = f"{file_uuid}{ext}"
        caminho = os.path.join(UPLOAD_DIR, nome_seguro)

        # Salvar
        with open(caminho, "wb") as f:
            f.write(conteudo)

        # Determinar tipo
        tipo = "imagem" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"} else \
               "video" if ext in {".mp4", ".webm", ".mov", ".avi"} else \
               "audio" if ext in {".mp3", ".wav", ".ogg"} else \
               "pdf" if ext == ".pdf" else \
               "documento"

        resultado = {
            "nome_original": file.filename,
            "nome_salvo": nome_seguro,
            "url": f"/uploads/chat/{nome_seguro}",
            "tipo": tipo,
            "tamanho": len(conteudo),
            "extensao": ext,
            "enviado_por": usuario.nome,
            "enviado_em": datetime.now().isoformat(),
        }

        resultados.append(resultado)
        logger.info(f"[UPLOAD] {file.filename} → {nome_seguro} ({len(conteudo)} bytes) por {usuario.nome}")

    return {"arquivos": resultados}


@router.get("/uploads/chat/{nome_arquivo}")
async def servir_arquivo(nome_arquivo: str):
    """Serve um arquivo estático do diretório de uploads."""
    caminho = os.path.join(UPLOAD_DIR, nome_arquivo)

    if not os.path.isfile(caminho):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Verificar que o caminho é seguro (não permite path traversal)
    caminho_real = os.path.realpath(caminho)
    if not caminho_real.startswith(os.path.realpath(UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return FileResponse(caminho)
