"""
Rota: Usuários do Synerium Factory

GET    /api/usuarios              — Lista todos os usuários
GET    /api/usuarios/aprovadores  — Lista apenas aprovadores
GET    /api/usuarios/{id}         — Perfil de um usuário específico
POST   /api/usuarios              — Criar novo usuário (admin)
PUT    /api/usuarios/perfil       — Editar perfil do usuário autenticado
PUT    /api/usuarios/{id}         — Editar qualquer usuário (admin)
PUT    /api/usuarios/{id}/permissoes — Atualizar permissões de um usuário
DELETE /api/usuarios/{id}         — Desativar usuário (soft delete)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from api.security import hash_senha
from database.session import get_db
from database.models import UsuarioDB, AuditLogDB

logger = logging.getLogger("synerium.usuarios")

router = APIRouter(prefix="/api/usuarios", tags=["Usuários"])


# --- Schemas ---

class AtualizarPerfilRequest(BaseModel):
    """Request para o próprio usuário editar seu perfil."""
    nome: str | None = None
    cargo: str | None = None
    telefone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    social_linkedin: str | None = None
    social_instagram: str | None = None
    social_whatsapp: str | None = None


class CriarUsuarioRequest(BaseModel):
    """Request para criar um novo usuário diretamente (admin)."""
    email: str
    nome: str
    senha: str
    cargo: str = ""
    papeis: list[str] = []
    pode_aprovar: bool = False
    areas_aprovacao: list[str] = []


class EditarUsuarioRequest(BaseModel):
    """Request para admin editar qualquer usuário."""
    nome: str | None = None
    cargo: str | None = None
    email: str | None = None
    telefone: str | None = None
    bio: str | None = None
    ativo: bool | None = None


class AtualizarPermissoesRequest(BaseModel):
    """Request para atualizar permissões de um usuário."""
    papeis: list[str] | None = None
    pode_aprovar: bool | None = None
    areas_aprovacao: list[str] | None = None
    permissoes_granulares: dict | None = None  # Overrides por módulo


# --- Papéis e áreas disponíveis no sistema ---

PAPEIS_DISPONIVEIS = [
    {"id": "ceo", "nome": "CEO", "descricao": "Chief Executive Officer — poder total"},
    {"id": "diretor_tecnico", "nome": "Diretor Técnico", "descricao": "Responsável pela área técnica"},
    {"id": "operations_lead", "nome": "Operations Lead", "descricao": "Poder de override e aprovação final"},
    {"id": "pm_central", "nome": "PM Central", "descricao": "Project Manager — orquestrador dos squads"},
    {"id": "lider", "nome": "Líder de Squad", "descricao": "Lidera um squad específico"},
    {"id": "desenvolvedor", "nome": "Desenvolvedor", "descricao": "Desenvolvimento de software"},
    {"id": "marketing", "nome": "Marketing", "descricao": "Marketing e growth"},
    {"id": "financeiro", "nome": "Financeiro", "descricao": "Controle financeiro e custos"},
    {"id": "suporte", "nome": "Suporte", "descricao": "Suporte ao cliente"},
    {"id": "membro", "nome": "Membro", "descricao": "Membro da equipe"},
]

AREAS_APROVACAO_DISPONIVEIS = [
    {"id": "deploy_producao", "nome": "Deploy Produção", "descricao": "Aprovar deploys em produção"},
    {"id": "gasto_ia", "nome": "Gasto IA", "descricao": "Aprovar gastos de IA acima do limite"},
    {"id": "mudanca_arquitetura", "nome": "Mudança de Arquitetura", "descricao": "Aprovar mudanças estruturais"},
    {"id": "campanha_marketing", "nome": "Campanha Marketing", "descricao": "Aprovar campanhas de marketing"},
    {"id": "outreach_massa", "nome": "Outreach em Massa", "descricao": "Aprovar envios em massa"},
]


# --- Módulos e ações disponíveis ---

@router.get("/modulos-disponiveis")
def listar_modulos_disponiveis(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Lista módulos e ações disponíveis para permissões granulares."""
    from config.permissoes import MODULOS, ACOES, PERMISSOES_POR_PAPEL
    return {
        "modulos": MODULOS,
        "acoes": ACOES,
        "permissoes_por_papel": PERMISSOES_POR_PAPEL,
    }


# --- Helpers ---

def _usuario_para_dict(u: UsuarioDB) -> dict:
    """Converte um UsuarioDB para dict de resposta com permissões efetivas."""
    from config.permissoes import calcular_permissoes_efetivas
    return {
        "id": str(u.id),
        "nome": u.nome,
        "email": u.email,
        "cargo": u.cargo or "",
        "papeis": u.papeis or [],
        "areas_aprovacao": u.areas_aprovacao or [],
        "pode_aprovar": u.pode_aprovar,
        "telefone": u.telefone or "",
        "bio": u.bio or "",
        "avatar_url": u.avatar_url or "",
        "social_linkedin": u.social_linkedin or "",
        "social_instagram": u.social_instagram or "",
        "social_whatsapp": u.social_whatsapp or "",
        "ativo": u.ativo,
        "criado_em": u.criado_em.isoformat() if u.criado_em else "",
        "permissoes_granulares": u.permissoes_granulares or None,
        "permissoes_efetivas": calcular_permissoes_efetivas(
            papeis=u.papeis or [],
            overrides=u.permissoes_granulares,
        ),
    }


def _verificar_admin(usuario: UsuarioDB):
    """Verifica se o usuário tem permissão de admin (CEO ou Operations Lead)."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead", "diretor_tecnico"]):
        raise HTTPException(
            status_code=403,
            detail="Apenas CEO, Diretor Técnico ou Operations Lead podem executar esta ação."
        )


# --- Rotas ---

@router.get("/papeis-disponiveis")
def listar_papeis():
    """Retorna a lista de papéis disponíveis no sistema."""
    return PAPEIS_DISPONIVEIS


@router.get("/areas-aprovacao-disponiveis")
def listar_areas_aprovacao():
    """Retorna a lista de áreas de aprovação disponíveis."""
    return AREAS_APROVACAO_DISPONIVEIS


@router.get("")
def listar(incluir_inativos: bool = False, db: Session = Depends(get_db)):
    """Lista todos os usuários. Por padrão só ativos."""
    query = db.query(UsuarioDB)
    if not incluir_inativos:
        query = query.filter_by(ativo=True)
    usuarios = query.order_by(UsuarioDB.nome).all()
    return [_usuario_para_dict(u) for u in usuarios]


@router.get("/aprovadores")
def aprovadores(db: Session = Depends(get_db)):
    """Lista usuários com poder de aprovação."""
    usuarios = db.query(UsuarioDB).filter_by(ativo=True, pode_aprovar=True).all()
    return [_usuario_para_dict(u) for u in usuarios]


@router.post("")
def criar_usuario(
    req: CriarUsuarioRequest,
    request: Request,
    usuario_admin: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria um novo usuário diretamente no sistema (somente admin)."""
    _verificar_admin(usuario_admin)

    # Verificar se email já existe
    existente = db.query(UsuarioDB).filter_by(email=req.email).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Email '{req.email}' já está cadastrado.")

    # Validar senha
    if len(req.senha) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres.")

    # Criar usuário
    novo = UsuarioDB(
        email=req.email,
        password_hash=hash_senha(req.senha),
        nome=req.nome,
        cargo=req.cargo,
        papeis=req.papeis,
        pode_aprovar=req.pode_aprovar,
        areas_aprovacao=req.areas_aprovacao if req.pode_aprovar else [],
        company_id=usuario_admin.company_id,
    )
    db.add(novo)

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario_admin.id,
        email=usuario_admin.email,
        acao="CRIAR_USUARIO",
        descricao=f"Criou usuário: {req.nome} ({req.email})",
        ip=request.client.host if request.client else "",
        company_id=usuario_admin.company_id,
    ))

    db.commit()
    db.refresh(novo)

    logger.info(f"[USUARIO] Criado: {novo.nome} ({novo.email}) por {usuario_admin.nome}")

    return _usuario_para_dict(novo)


@router.put("/perfil")
def atualizar_perfil(
    req: AtualizarPerfilRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atualiza o perfil do usuário autenticado."""
    campos = req.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    for campo, valor in campos.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)

    return _usuario_para_dict(usuario)


@router.put("/{user_id}")
def editar_usuario(
    user_id: int,
    req: EditarUsuarioRequest,
    request: Request,
    usuario_admin: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Edita dados de qualquer usuário (somente admin)."""
    _verificar_admin(usuario_admin)

    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    campos = req.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    # Se mudou email, verificar duplicata
    if req.email and req.email != usuario.email:
        existente = db.query(UsuarioDB).filter_by(email=req.email).first()
        if existente:
            raise HTTPException(status_code=409, detail=f"Email '{req.email}' já está em uso.")

    for campo, valor in campos.items():
        setattr(usuario, campo, valor)

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario_admin.id,
        email=usuario_admin.email,
        acao="EDITAR_USUARIO",
        descricao=f"Editou usuário {usuario.nome} (id={user_id}): {list(campos.keys())}",
        ip=request.client.host if request.client else "",
        company_id=usuario_admin.company_id,
    ))

    db.commit()
    db.refresh(usuario)

    logger.info(f"[USUARIO] Editado: {usuario.nome} por {usuario_admin.nome}")

    return _usuario_para_dict(usuario)


@router.put("/{user_id}/permissoes")
def atualizar_permissoes(
    user_id: int,
    req: AtualizarPermissoesRequest,
    request: Request,
    usuario_admin: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atualiza papéis e permissões de um usuário (somente admin)."""
    _verificar_admin(usuario_admin)

    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if req.papeis is not None:
        usuario.papeis = req.papeis
    if req.pode_aprovar is not None:
        usuario.pode_aprovar = req.pode_aprovar
    if req.areas_aprovacao is not None:
        usuario.areas_aprovacao = req.areas_aprovacao

    # Se desativou aprovação, limpar áreas
    if req.pode_aprovar is False:
        usuario.areas_aprovacao = []

    # Permissões granulares (overrides por módulo)
    if req.permissoes_granulares is not None:
        usuario.permissoes_granulares = req.permissoes_granulares

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario_admin.id,
        email=usuario_admin.email,
        acao="ALTERAR_PERMISSOES",
        descricao=(
            f"Alterou permissões de {usuario.nome} (id={user_id}): "
            f"papeis={req.papeis}, pode_aprovar={req.pode_aprovar}, "
            f"areas={req.areas_aprovacao}, granulares={'sim' if req.permissoes_granulares else 'não'}"
        ),
        ip=request.client.host if request.client else "",
        company_id=usuario_admin.company_id,
    ))

    db.commit()
    db.refresh(usuario)

    logger.info(f"[PERMISSOES] Atualizadas: {usuario.nome} por {usuario_admin.nome}")

    return _usuario_para_dict(usuario)


@router.delete("/{user_id}")
def desativar_usuario(
    user_id: int,
    request: Request,
    usuario_admin: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Desativa um usuário (soft delete — somente admin)."""
    _verificar_admin(usuario_admin)

    if usuario_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta.")

    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    usuario.ativo = False

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario_admin.id,
        email=usuario_admin.email,
        acao="DESATIVAR_USUARIO",
        descricao=f"Desativou usuário: {usuario.nome} ({usuario.email})",
        ip=request.client.host if request.client else "",
        company_id=usuario_admin.company_id,
    ))

    db.commit()

    logger.info(f"[USUARIO] Desativado: {usuario.nome} por {usuario_admin.nome}")

    return {"mensagem": f"Usuário '{usuario.nome}' desativado com sucesso."}


@router.get("/{user_id}")
def perfil(user_id: int, db: Session = Depends(get_db)):
    """Retorna o perfil de um usuário específico."""
    usuario = db.query(UsuarioDB).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=f"Usuário '{user_id}' não encontrado.")
    return _usuario_para_dict(usuario)
