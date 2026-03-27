"""
Luna — Rotas da assistente inteligente.

Endpoints:
- CRUD de conversas
- Envio de mensagens com streaming SSE
- Regeneração de resposta
- Supervisão (proprietários: CEO/Operations Lead)

Todos os endpoints requerem autenticação JWT.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import (
    UsuarioDB, LunaConversaDB, LunaMensagemDB
)
from core.luna_engine import luna_engine

logger = logging.getLogger("synerium.api.luna")

router = APIRouter(prefix="/api/luna", tags=["Luna"])

# =====================================================================
# Schemas Pydantic
# =====================================================================


class CriarConversaRequest(BaseModel):
    modelo_preferido: str = "auto"  # auto, sonnet, opus


class RenomearConversaRequest(BaseModel):
    titulo: str


class EnviarMensagemRequest(BaseModel):
    conteudo: str


# =====================================================================
# Helpers
# =====================================================================


def _verificar_proprietario(usuario: UsuarioDB):
    """Verifica se o usuário tem papel de proprietário."""
    papeis = usuario.papeis or []
    papeis_permitidos = {"ceo", "operations_lead", "proprietario", "diretor_tecnico"}
    if not any(p in papeis_permitidos for p in papeis):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Apenas proprietários podem acessar esta funcionalidade."
        )


def _serializar_conversa(c: LunaConversaDB, ultima_msg: str = "") -> dict:
    """Serializa uma conversa para JSON."""
    return {
        "id": c.id,
        "usuario_id": c.usuario_id,
        "usuario_nome": c.usuario_nome,
        "titulo": c.titulo,
        "modelo_preferido": c.modelo_preferido,
        "criado_em": c.criado_em.isoformat() if c.criado_em else None,
        "atualizado_em": c.atualizado_em.isoformat() if c.atualizado_em else None,
        "ultima_mensagem": ultima_msg,
    }


def _serializar_mensagem(m: LunaMensagemDB) -> dict:
    """Serializa uma mensagem para JSON."""
    return {
        "id": m.id,
        "conversa_id": m.conversa_id,
        "papel": m.papel,
        "conteudo": m.conteudo,
        "modelo_usado": m.modelo_usado or "",
        "provider_usado": m.provider_usado or "",
        "tokens_input": m.tokens_input or 0,
        "tokens_output": m.tokens_output or 0,
        "custo_usd": m.custo_usd or 0.0,
        "criado_em": m.criado_em.isoformat() if m.criado_em else None,
    }


# =====================================================================
# Endpoints — Conversas do Usuário
# =====================================================================


@router.get("/conversas")
def listar_conversas(
    limite: int = 50,
    offset: int = 0,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista as conversas do usuário autenticado, ordenadas por última atualização."""
    conversas = (
        db.query(LunaConversaDB)
        .filter(LunaConversaDB.usuario_id == usuario.id)
        .order_by(desc(LunaConversaDB.atualizado_em))
        .offset(offset)
        .limit(limite)
        .all()
    )

    resultado = []
    for c in conversas:
        # Buscar última mensagem para preview
        ultima = (
            db.query(LunaMensagemDB)
            .filter(LunaMensagemDB.conversa_id == c.id)
            .order_by(desc(LunaMensagemDB.id))
            .first()
        )
        preview = ""
        if ultima:
            preview = ultima.conteudo[:100] + ("..." if len(ultima.conteudo) > 100 else "")
        resultado.append(_serializar_conversa(c, preview))

    return resultado


@router.post("/conversas")
def criar_conversa(
    dados: CriarConversaRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria uma nova conversa."""
    conversa = luna_engine.criar_conversa(
        db=db,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        company_id=usuario.company_id,
        modelo_preferido=dados.modelo_preferido,
    )
    return _serializar_conversa(conversa)


@router.get("/conversas/{conversa_id}")
def buscar_conversa(
    conversa_id: str,
    limite_msgs: int = 50,
    offset_msgs: int = 0,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Busca uma conversa com suas mensagens (paginadas)."""
    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == usuario.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Buscar mensagens (mais antigas primeiro)
    mensagens = (
        db.query(LunaMensagemDB)
        .filter(LunaMensagemDB.conversa_id == conversa_id)
        .order_by(LunaMensagemDB.id.asc())
        .offset(offset_msgs)
        .limit(limite_msgs)
        .all()
    )

    total_mensagens = db.query(func.count(LunaMensagemDB.id)).filter(
        LunaMensagemDB.conversa_id == conversa_id
    ).scalar()

    return {
        "conversa": _serializar_conversa(conversa),
        "mensagens": [_serializar_mensagem(m) for m in mensagens],
        "total_mensagens": total_mensagens,
        "tem_mais": (offset_msgs + limite_msgs) < total_mensagens,
    }


@router.put("/conversas/{conversa_id}")
def renomear_conversa(
    conversa_id: str,
    dados: RenomearConversaRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Renomeia uma conversa."""
    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == usuario.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa.titulo = dados.titulo[:500]
    conversa.atualizado_em = datetime.utcnow()
    db.commit()

    return _serializar_conversa(conversa)


@router.delete("/conversas/{conversa_id}")
def excluir_conversa(
    conversa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Exclui uma conversa e todas as suas mensagens."""
    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == usuario.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Excluir mensagens
    db.query(LunaMensagemDB).filter(
        LunaMensagemDB.conversa_id == conversa_id
    ).delete()

    # Excluir conversa
    db.delete(conversa)
    db.commit()

    return {"mensagem": "Conversa excluída com sucesso"}


# =====================================================================
# Endpoints — Mensagens (Streaming SSE)
# =====================================================================


@router.post("/conversas/{conversa_id}/mensagens")
async def enviar_mensagem(
    conversa_id: str,
    dados: EnviarMensagemRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Envia uma mensagem e retorna a resposta da Luna via streaming SSE.

    Formato dos eventos SSE:
    - data: {"tipo": "chunk", "conteudo": "texto parcial"}
    - data: {"tipo": "titulo", "titulo": "Título gerado"}
    - data: {"tipo": "fim", "mensagem_id": 123, "modelo": "...", "provider": "..."}
    - data: {"tipo": "erro", "mensagem": "..."}
    """
    # Verificar que a conversa pertence ao usuário
    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == usuario.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    if not dados.conteudo.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")

    async def gerar_stream():
        async for evento in luna_engine.stream_resposta(
            db=db,
            conversa_id=conversa_id,
            conteudo=dados.conteudo.strip(),
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
        ):
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gerar_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desabilitar buffering do nginx
        },
    )


@router.post("/conversas/{conversa_id}/regenerar")
async def regenerar_resposta(
    conversa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Regenera a última resposta da Luna via streaming SSE."""
    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == usuario.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    async def gerar_stream():
        async for evento in luna_engine.regenerar_resposta(
            db=db,
            conversa_id=conversa_id,
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
        ):
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gerar_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =====================================================================
# Endpoints — Supervisão (Proprietários)
# =====================================================================


@router.get("/admin/usuarios")
def listar_usuarios_luna(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Lista usuários que usam Luna com estatísticas.
    Somente proprietários (CEO/Operations Lead).
    """
    _verificar_proprietario(usuario)

    # Subquery: contagem de conversas por usuário
    from sqlalchemy import distinct

    # Buscar todos os usuários que têm pelo menos 1 conversa
    resultados = (
        db.query(
            LunaConversaDB.usuario_id,
            LunaConversaDB.usuario_nome,
            func.count(distinct(LunaConversaDB.id)).label("total_conversas"),
            func.max(LunaConversaDB.atualizado_em).label("ultimo_uso"),
        )
        .group_by(LunaConversaDB.usuario_id, LunaConversaDB.usuario_nome)
        .order_by(desc("ultimo_uso"))
        .all()
    )

    usuarios = []
    for r in resultados:
        # Contar mensagens do usuário
        total_msgs = db.query(func.count(LunaMensagemDB.id)).join(
            LunaConversaDB,
            LunaMensagemDB.conversa_id == LunaConversaDB.id,
        ).filter(
            LunaConversaDB.usuario_id == r.usuario_id
        ).scalar()

        # Buscar info do usuário
        user_db = db.query(UsuarioDB).filter(UsuarioDB.id == r.usuario_id).first()

        usuarios.append({
            "usuario_id": r.usuario_id,
            "nome": r.usuario_nome or (user_db.nome if user_db else ""),
            "email": user_db.email if user_db else "",
            "cargo": user_db.cargo if user_db else "",
            "total_conversas": r.total_conversas,
            "total_mensagens": total_msgs or 0,
            "ultimo_uso": r.ultimo_uso.isoformat() if r.ultimo_uso else None,
        })

    return usuarios


@router.get("/admin/conversas/{funcionario_id}")
def listar_conversas_funcionario(
    funcionario_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Lista conversas de um funcionário específico.
    Somente proprietários (CEO/Operations Lead).
    """
    _verificar_proprietario(usuario)

    conversas = (
        db.query(LunaConversaDB)
        .filter(LunaConversaDB.usuario_id == funcionario_id)
        .order_by(desc(LunaConversaDB.atualizado_em))
        .all()
    )

    resultado = []
    for c in conversas:
        ultima = (
            db.query(LunaMensagemDB)
            .filter(LunaMensagemDB.conversa_id == c.id)
            .order_by(desc(LunaMensagemDB.id))
            .first()
        )
        preview = ""
        if ultima:
            preview = ultima.conteudo[:100] + ("..." if len(ultima.conteudo) > 100 else "")
        resultado.append(_serializar_conversa(c, preview))

    return resultado


@router.get("/admin/conversas/{funcionario_id}/{conversa_id}")
def ver_conversa_funcionario(
    funcionario_id: int,
    conversa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Visualiza uma conversa de funcionário (somente leitura).
    Somente proprietários (CEO/Operations Lead).
    Registra auditoria LGPD.
    """
    _verificar_proprietario(usuario)

    conversa = db.query(LunaConversaDB).filter(
        LunaConversaDB.id == conversa_id,
        LunaConversaDB.usuario_id == funcionario_id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    mensagens = (
        db.query(LunaMensagemDB)
        .filter(LunaMensagemDB.conversa_id == conversa_id)
        .order_by(LunaMensagemDB.id.asc())
        .all()
    )

    # Registrar auditoria LGPD
    ip = request.client.host if request and request.client else ""
    luna_engine.registrar_auditoria_supervisao(
        db=db,
        proprietario_id=usuario.id,
        proprietario_email=usuario.email,
        funcionario_id=funcionario_id,
        conversa_id=conversa_id,
        ip=ip,
    )

    # Buscar info do funcionário
    funcionario = db.query(UsuarioDB).filter(UsuarioDB.id == funcionario_id).first()

    return {
        "conversa": _serializar_conversa(conversa),
        "mensagens": [_serializar_mensagem(m) for m in mensagens],
        "funcionario": {
            "id": funcionario.id if funcionario else funcionario_id,
            "nome": funcionario.nome if funcionario else "",
            "email": funcionario.email if funcionario else "",
            "cargo": funcionario.cargo if funcionario else "",
        },
        "modo_supervisao": True,
    }
