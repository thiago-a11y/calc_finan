"""
Rotas do Catálogo de Agentes — Prateleira + Atribuições + Solicitações

Catálogo (CRUD admin):
  GET    /api/catalogo          — Listar agentes do catálogo
  GET    /api/catalogo/perfis   — Listar perfis disponíveis
  GET    /api/catalogo/{id}     — Detalhe de um agente
  POST   /api/catalogo          — Criar novo agente (admin)
  PUT    /api/catalogo/{id}     — Atualizar agente (admin)
  DELETE /api/catalogo/{id}     — Desativar agente (admin)

Atribuições:
  GET    /api/atribuicoes/meus            — Meus agentes
  GET    /api/atribuicoes/usuario/{id}    — Agentes de um usuário
  POST   /api/atribuicoes                 — Atribuir agente a usuário (admin)
  DELETE /api/atribuicoes/{id}            — Remover atribuição (admin)

Solicitações:
  GET    /api/solicitacoes-agente         — Listar solicitações
  POST   /api/solicitacoes-agente         — Criar solicitação
  POST   /api/solicitacoes-agente/{id}/acao — Aprovar/rejeitar (admin)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import (
    UsuarioDB, AgenteCatalogoDB, AgenteAtribuidoDB,
    SolicitacaoAgenteDB, AuditLogDB,
)
from api.schemas import (
    AgenteCatalogoResponse, AgenteCatalogoCreateRequest, AgenteCatalogoUpdateRequest,
    AgenteAtribuidoResponse, AtribuirAgenteRequest,
    SolicitacaoAgenteResponse, SolicitacaoAgenteCreateRequest, SolicitacaoAgenteAcaoRequest,
)
from squads.regras import REGRAS_ANTI_ALUCINACAO

logger = logging.getLogger("synerium.catalogo")

PAPEIS_ADMIN = {"ceo", "diretor_tecnico", "operations_lead"}

PERFIS_DISPONIVEIS = [
    {"id": "tech_lead", "nome": "Tech Lead", "tier": "opus"},
    {"id": "backend_dev", "nome": "Desenvolvedor Backend", "tier": "sonnet"},
    {"id": "frontend_dev", "nome": "Desenvolvedor Frontend", "tier": "sonnet"},
    {"id": "especialista_ia", "nome": "Especialista IA", "tier": "opus"},
    {"id": "integracao", "nome": "Integrações e APIs", "tier": "sonnet"},
    {"id": "devops", "nome": "DevOps e Infraestrutura", "tier": "sonnet"},
    {"id": "qa_seguranca", "nome": "QA e Segurança", "tier": "sonnet"},
    {"id": "product_manager", "nome": "Product Manager", "tier": "opus"},
    {"id": "secretaria_executiva", "nome": "Secretária Executiva", "tier": "sonnet"},
    {"id": "diretor", "nome": "Diretor / Revisor", "tier": "opus"},
    {"id": "arquiteto", "nome": "Arquiteto", "tier": "opus"},
]

CATEGORIAS_DISPONIVEIS = [
    "desenvolvimento", "gestao", "seguranca", "ia", "operacional", "geral",
]


def _verificar_admin(usuario: UsuarioDB):
    """Verifica se o usuário tem papel admin."""
    papeis = set(usuario.papeis or [])
    if not papeis & PAPEIS_ADMIN:
        raise HTTPException(status_code=403, detail="Apenas admin pode executar esta ação.")


# ============================================================
# CATÁLOGO — CRUD
# ============================================================

router = APIRouter(prefix="/api", tags=["Catálogo de Agentes"])


@router.get("/catalogo", response_model=list[AgenteCatalogoResponse])
def listar_catalogo(
    categoria: str | None = Query(None),
    perfil: str | None = Query(None),
    ativo: bool = Query(True),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista todos os agentes do catálogo com contagem de usuários."""
    query = db.query(AgenteCatalogoDB).filter_by(company_id=usuario.company_id or 1)

    if ativo is not None:
        query = query.filter_by(ativo=ativo)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if perfil:
        query = query.filter_by(perfil_agente=perfil)

    agentes = query.order_by(AgenteCatalogoDB.categoria, AgenteCatalogoDB.nome_exibicao).all()

    resultado = []
    for a in agentes:
        total = db.query(func.count(AgenteAtribuidoDB.id)).filter_by(
            agente_catalogo_id=a.id, ativo=True
        ).scalar()

        resultado.append(AgenteCatalogoResponse(
            id=a.id,
            nome_exibicao=a.nome_exibicao,
            papel=a.papel,
            objetivo=a.objetivo,
            historia=a.historia,
            perfil_agente=a.perfil_agente,
            categoria=a.categoria,
            icone=a.icone,
            allow_delegation=a.allow_delegation,
            ativo=a.ativo,
            criado_em=a.criado_em,
            total_usuarios=total,
        ))

    return resultado


@router.get("/catalogo/perfis")
def listar_perfis(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Lista perfis de agente disponíveis com tier do LLM."""
    return {"perfis": PERFIS_DISPONIVEIS, "categorias": CATEGORIAS_DISPONIVEIS}


@router.get("/catalogo/{agente_id}", response_model=AgenteCatalogoResponse)
def detalhe_catalogo(
    agente_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Detalhe de um agente do catálogo."""
    agente = db.query(AgenteCatalogoDB).filter_by(id=agente_id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente não encontrado no catálogo.")

    total = db.query(func.count(AgenteAtribuidoDB.id)).filter_by(
        agente_catalogo_id=agente.id, ativo=True
    ).scalar()

    return AgenteCatalogoResponse(
        id=agente.id,
        nome_exibicao=agente.nome_exibicao,
        papel=agente.papel,
        objetivo=agente.objetivo,
        historia=agente.historia,
        perfil_agente=agente.perfil_agente,
        categoria=agente.categoria,
        icone=agente.icone,
        allow_delegation=agente.allow_delegation,
        ativo=agente.ativo,
        criado_em=agente.criado_em,
        total_usuarios=total,
    )


@router.post("/catalogo", response_model=AgenteCatalogoResponse)
def criar_agente_catalogo(
    req: AgenteCatalogoCreateRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria um novo agente no catálogo (admin only)."""
    _verificar_admin(usuario)

    agente = AgenteCatalogoDB(
        nome_exibicao=req.nome_exibicao,
        papel=req.papel,
        objetivo=req.objetivo,
        historia=req.historia,
        perfil_agente=req.perfil_agente,
        categoria=req.categoria,
        icone=req.icone,
        regras_extras=req.regras_extras or REGRAS_ANTI_ALUCINACAO,
        allow_delegation=req.allow_delegation,
        company_id=usuario.company_id or 1,
        criado_por_id=usuario.id,
    )
    db.add(agente)
    db.commit()
    db.refresh(agente)

    db.add(AuditLogDB(
        user_id=usuario.id, email=usuario.email,
        acao="CRIAR_AGENTE_CATALOGO",
        descricao=f"Agente '{req.nome_exibicao}' criado no catálogo",
        ip="api", company_id=usuario.company_id or 1,
    ))
    db.commit()

    logger.info(f"[CATALOGO] {usuario.nome} criou agente: {req.nome_exibicao}")

    return AgenteCatalogoResponse(
        id=agente.id, nome_exibicao=agente.nome_exibicao,
        papel=agente.papel, objetivo=agente.objetivo, historia=agente.historia,
        perfil_agente=agente.perfil_agente, categoria=agente.categoria,
        icone=agente.icone, allow_delegation=agente.allow_delegation,
        ativo=agente.ativo, criado_em=agente.criado_em, total_usuarios=0,
    )


@router.put("/catalogo/{agente_id}", response_model=AgenteCatalogoResponse)
def atualizar_agente_catalogo(
    agente_id: int,
    req: AgenteCatalogoUpdateRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atualiza um agente do catálogo (admin only)."""
    _verificar_admin(usuario)

    agente = db.query(AgenteCatalogoDB).filter_by(id=agente_id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente não encontrado.")

    campos_atualizados = req.model_dump(exclude_unset=True)
    for campo, valor in campos_atualizados.items():
        setattr(agente, campo, valor)

    db.commit()
    db.refresh(agente)

    logger.info(f"[CATALOGO] {usuario.nome} atualizou agente #{agente_id}")

    total = db.query(func.count(AgenteAtribuidoDB.id)).filter_by(
        agente_catalogo_id=agente.id, ativo=True
    ).scalar()

    return AgenteCatalogoResponse(
        id=agente.id, nome_exibicao=agente.nome_exibicao,
        papel=agente.papel, objetivo=agente.objetivo, historia=agente.historia,
        perfil_agente=agente.perfil_agente, categoria=agente.categoria,
        icone=agente.icone, allow_delegation=agente.allow_delegation,
        ativo=agente.ativo, criado_em=agente.criado_em, total_usuarios=total,
    )


@router.delete("/catalogo/{agente_id}")
def desativar_agente_catalogo(
    agente_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Desativa um agente do catálogo (soft delete, admin only)."""
    _verificar_admin(usuario)

    agente = db.query(AgenteCatalogoDB).filter_by(id=agente_id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente não encontrado.")

    agente.ativo = False
    db.commit()

    logger.info(f"[CATALOGO] {usuario.nome} desativou agente #{agente_id}: {agente.nome_exibicao}")
    return {"mensagem": f"Agente '{agente.nome_exibicao}' desativado."}


# ============================================================
# ATRIBUIÇÕES
# ============================================================

@router.get("/atribuicoes/meus", response_model=list[AgenteAtribuidoResponse])
def meus_agentes(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista os agentes atribuídos ao usuário logado."""
    return _agentes_do_usuario(usuario.id, db)


@router.get("/atribuicoes/usuario/{usuario_id}", response_model=list[AgenteAtribuidoResponse])
def agentes_do_usuario(
    usuario_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista os agentes atribuídos a um usuário (admin ou próprio)."""
    papeis = set(usuario.papeis or [])
    if usuario.id != usuario_id and not papeis & PAPEIS_ADMIN:
        raise HTTPException(status_code=403, detail="Sem permissão.")
    return _agentes_do_usuario(usuario_id, db)


def _agentes_do_usuario(usuario_id: int, db: Session) -> list[AgenteAtribuidoResponse]:
    """Helper: retorna agentes atribuídos a um usuário."""
    atribuicoes = (
        db.query(AgenteAtribuidoDB)
        .filter_by(usuario_id=usuario_id, ativo=True)
        .order_by(AgenteAtribuidoDB.ordem)
        .all()
    )

    resultado = []
    for a in atribuicoes:
        catalogo = db.query(AgenteCatalogoDB).filter_by(id=a.agente_catalogo_id).first()
        if not catalogo:
            continue
        resultado.append(AgenteAtribuidoResponse(
            id=a.id,
            agente_catalogo_id=a.agente_catalogo_id,
            usuario_id=a.usuario_id,
            nome_agente=catalogo.nome_exibicao,
            perfil_agente=catalogo.perfil_agente,
            categoria=catalogo.categoria,
            icone=catalogo.icone,
            ordem=a.ordem,
            ativo=a.ativo,
            criado_em=a.criado_em,
        ))

    return resultado


@router.post("/atribuicoes", response_model=AgenteAtribuidoResponse)
def atribuir_agente(
    req: AtribuirAgenteRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atribui um agente do catálogo a um usuário (admin only)."""
    _verificar_admin(usuario)

    # Verificar se agente existe
    catalogo = db.query(AgenteCatalogoDB).filter_by(id=req.agente_catalogo_id, ativo=True).first()
    if not catalogo:
        raise HTTPException(status_code=404, detail="Agente não encontrado no catálogo.")

    # Verificar se usuário existe
    user_dest = db.query(UsuarioDB).filter_by(id=req.usuario_id, ativo=True).first()
    if not user_dest:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Verificar duplicata
    ja_existe = db.query(AgenteAtribuidoDB).filter_by(
        agente_catalogo_id=req.agente_catalogo_id,
        usuario_id=req.usuario_id,
        ativo=True,
    ).first()
    if ja_existe:
        raise HTTPException(status_code=409, detail="Agente já atribuído a este usuário.")

    # Calcular próxima ordem
    max_ordem = db.query(func.max(AgenteAtribuidoDB.ordem)).filter_by(
        usuario_id=req.usuario_id, ativo=True
    ).scalar() or 0

    atrib = AgenteAtribuidoDB(
        agente_catalogo_id=req.agente_catalogo_id,
        usuario_id=req.usuario_id,
        atribuido_por_id=usuario.id,
        ordem=max_ordem + 1,
        company_id=usuario.company_id or 1,
    )
    db.add(atrib)

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario.id, email=usuario.email,
        acao="ATRIBUIR_AGENTE",
        descricao=f"Agente '{catalogo.nome_exibicao}' atribuído a {user_dest.nome}",
        ip="api", company_id=usuario.company_id or 1,
    ))
    db.commit()
    db.refresh(atrib)

    # Hot-reload do squad em memória
    _recarregar_squad_usuario(req.usuario_id, db)

    logger.info(f"[ATRIBUICAO] {usuario.nome} atribuiu '{catalogo.nome_exibicao}' a {user_dest.nome}")

    return AgenteAtribuidoResponse(
        id=atrib.id,
        agente_catalogo_id=atrib.agente_catalogo_id,
        usuario_id=atrib.usuario_id,
        nome_agente=catalogo.nome_exibicao,
        perfil_agente=catalogo.perfil_agente,
        categoria=catalogo.categoria,
        icone=catalogo.icone,
        ordem=atrib.ordem,
        ativo=atrib.ativo,
        criado_em=atrib.criado_em,
    )


@router.delete("/atribuicoes/{atribuicao_id}")
def remover_atribuicao(
    atribuicao_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Remove uma atribuição (admin only)."""
    _verificar_admin(usuario)

    atrib = db.query(AgenteAtribuidoDB).filter_by(id=atribuicao_id).first()
    if not atrib:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada.")

    atrib.ativo = False
    db.commit()

    # Hot-reload
    _recarregar_squad_usuario(atrib.usuario_id, db)

    logger.info(f"[ATRIBUICAO] {usuario.nome} removeu atribuição #{atribuicao_id}")
    return {"mensagem": "Atribuição removida."}


# ============================================================
# SOLICITAÇÕES DE AGENTES
# ============================================================

@router.get("/solicitacoes-agente", response_model=list[SolicitacaoAgenteResponse])
def listar_solicitacoes(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista solicitações. Admin vê todas; usuário vê as próprias."""
    papeis = set(usuario.papeis or [])
    if papeis & PAPEIS_ADMIN:
        query = db.query(SolicitacaoAgenteDB)
    else:
        query = db.query(SolicitacaoAgenteDB).filter_by(usuario_id=usuario.id)

    solicitacoes = query.order_by(SolicitacaoAgenteDB.id.desc()).limit(50).all()

    resultado = []
    for s in solicitacoes:
        nome_agente = ""
        if s.agente_catalogo_id:
            cat = db.query(AgenteCatalogoDB).filter_by(id=s.agente_catalogo_id).first()
            if cat:
                nome_agente = cat.nome_exibicao

        resultado.append(SolicitacaoAgenteResponse(
            id=s.id,
            usuario_id=s.usuario_id,
            usuario_nome=s.usuario_nome,
            agente_catalogo_id=s.agente_catalogo_id,
            nome_agente=nome_agente,
            descricao=s.descricao,
            perfil_sugerido=s.perfil_sugerido,
            status=s.status,
            aprovado_por_nome=s.aprovado_por_nome,
            comentario=s.comentario,
            criado_em=s.criado_em,
        ))

    return resultado


@router.post("/solicitacoes-agente", response_model=SolicitacaoAgenteResponse)
def criar_solicitacao(
    req: SolicitacaoAgenteCreateRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria solicitação de agente (qualquer usuário)."""
    sol = SolicitacaoAgenteDB(
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        agente_catalogo_id=req.agente_catalogo_id,
        descricao=req.descricao,
        perfil_sugerido=req.perfil_sugerido,
        company_id=usuario.company_id or 1,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)

    nome_agente = ""
    if req.agente_catalogo_id:
        cat = db.query(AgenteCatalogoDB).filter_by(id=req.agente_catalogo_id).first()
        if cat:
            nome_agente = cat.nome_exibicao

    logger.info(f"[SOLICITACAO] {usuario.nome} solicitou agente: {req.descricao[:50]}")

    return SolicitacaoAgenteResponse(
        id=sol.id, usuario_id=sol.usuario_id, usuario_nome=sol.usuario_nome,
        agente_catalogo_id=sol.agente_catalogo_id, nome_agente=nome_agente,
        descricao=sol.descricao, perfil_sugerido=sol.perfil_sugerido,
        status=sol.status, criado_em=sol.criado_em,
    )


@router.post("/solicitacoes-agente/{sol_id}/acao", response_model=SolicitacaoAgenteResponse)
def acao_solicitacao(
    sol_id: int,
    req: SolicitacaoAgenteAcaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aprovar ou rejeitar solicitação de agente (admin only)."""
    _verificar_admin(usuario)

    sol = db.query(SolicitacaoAgenteDB).filter_by(id=sol_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    if sol.status != "pendente":
        raise HTTPException(status_code=400, detail="Solicitação já processada.")

    sol.status = "aprovado" if req.aprovado else "rejeitado"
    sol.aprovado_por_id = usuario.id
    sol.aprovado_por_nome = usuario.nome
    sol.comentario = req.comentario

    # Se aprovado e tem agente_catalogo_id, atribuir automaticamente
    if req.aprovado and sol.agente_catalogo_id:
        max_ordem = db.query(func.max(AgenteAtribuidoDB.ordem)).filter_by(
            usuario_id=sol.usuario_id, ativo=True
        ).scalar() or 0

        atrib = AgenteAtribuidoDB(
            agente_catalogo_id=sol.agente_catalogo_id,
            usuario_id=sol.usuario_id,
            atribuido_por_id=usuario.id,
            ordem=max_ordem + 1,
            company_id=usuario.company_id or 1,
        )
        db.add(atrib)
        _recarregar_squad_usuario(sol.usuario_id, db)

    db.add(AuditLogDB(
        user_id=usuario.id, email=usuario.email,
        acao="ACAO_SOLICITACAO_AGENTE",
        descricao=f"Solicitação #{sol_id} {'aprovada' if req.aprovado else 'rejeitada'} para {sol.usuario_nome}",
        ip="api", company_id=usuario.company_id or 1,
    ))
    db.commit()

    nome_agente = ""
    if sol.agente_catalogo_id:
        cat = db.query(AgenteCatalogoDB).filter_by(id=sol.agente_catalogo_id).first()
        if cat:
            nome_agente = cat.nome_exibicao

    logger.info(f"[SOLICITACAO] {usuario.nome} {'aprovou' if req.aprovado else 'rejeitou'} solicitação #{sol_id}")

    return SolicitacaoAgenteResponse(
        id=sol.id, usuario_id=sol.usuario_id, usuario_nome=sol.usuario_nome,
        agente_catalogo_id=sol.agente_catalogo_id, nome_agente=nome_agente,
        descricao=sol.descricao, perfil_sugerido=sol.perfil_sugerido,
        status=sol.status, aprovado_por_nome=sol.aprovado_por_nome,
        comentario=sol.comentario, criado_em=sol.criado_em,
    )


# ============================================================
# HOT-RELOAD DE SQUADS
# ============================================================

def _recarregar_squad_usuario(usuario_id: int, db: Session):
    """Recarrega o squad de um usuário em memória após atribuição/remoção."""
    try:
        from api.dependencias import obter_fabrica, carregar_squad_usuario
        fabrica = obter_fabrica()
        carregar_squad_usuario(fabrica, usuario_id, db)
    except Exception as e:
        logger.error(f"[HOT-RELOAD] Erro ao recarregar squad do user {usuario_id}: {e}")
