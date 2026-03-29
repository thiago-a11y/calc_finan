"""
Rotas: Projetos e Solicitações de Mudança

GET  /api/projetos                    — Lista todos os projetos
GET  /api/projetos/:id                — Detalhes de um projeto
POST /api/projetos                    — Criar projeto (só CEO)
PUT  /api/projetos/:id                — Editar projeto (só proprietário/CEO)
PUT  /api/projetos/:id/proprietario   — Nomear proprietário (só CEO)
PUT  /api/projetos/:id/lider          — Nomear líder técnico (proprietário/CEO)
PUT  /api/projetos/:id/membros        — Gerenciar membros (proprietário/CEO)

POST /api/projetos/:id/solicitacoes         — Criar solicitação de mudança
GET  /api/projetos/:id/solicitacoes         — Listar solicitações do projeto
PUT  /api/solicitacoes/:id/aprovar          — Aprovar solicitação
PUT  /api/solicitacoes/:id/rejeitar         — Rejeitar solicitação

POST /api/projetos/:id/vcs                  — Cadastrar/atualizar config VCS
GET  /api/projetos/:id/vcs                  — Buscar config VCS (sem token)
POST /api/projetos/:id/vcs/testar           — Testar conexão VCS
DELETE /api/projetos/:id/vcs                — Remover config VCS
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import ProjetoDB, SolicitacaoDB, AuditLogDB, UsuarioDB

logger = logging.getLogger("synerium.projetos")

router = APIRouter(prefix="/api", tags=["Projetos"])


# =====================================================================
# Schemas
# =====================================================================

class CriarProjetoRequest(BaseModel):
    nome: str
    descricao: str = ""
    caminho: str = ""
    repositorio: str = ""
    stack: str = ""
    icone: str = "📁"
    proprietario_id: int | None = None  # CEO pode nomear outro, senão é ele mesmo
    lider_tecnico_id: int | None = None
    fase_atual: str = ""


class EditarProjetoRequest(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    caminho: str | None = None
    repositorio: str | None = None
    stack: str | None = None
    icone: str | None = None
    fase_atual: str | None = None


class NomearProprietarioRequest(BaseModel):
    usuario_id: int


class NomearLiderRequest(BaseModel):
    usuario_id: int


class GerenciarMembrosRequest(BaseModel):
    """Adicionar ou remover membros."""
    acao: str  # "adicionar" ou "remover"
    usuario_id: int
    papel: str = "membro"  # membro, dev, designer, qa, etc.


class AtualizarRegrasRequest(BaseModel):
    """Atualizar regras de aprovação do projeto."""
    regras: dict  # {"pequena": {"aprovador": "...", "descricao": "..."}, ...}


class CriarSolicitacaoRequest(BaseModel):
    titulo: str
    descricao: str
    tipo_mudanca: str = "grande"  # pequena, grande, critica
    categoria: str = "feature"  # feature, bugfix, refactor, deploy, seguranca


class AcaoSolicitacaoRequest(BaseModel):
    comentario: str = ""


# =====================================================================
# Helpers
# =====================================================================

def _eh_ceo(usuario: UsuarioDB) -> bool:
    """Verifica se o usuário é CEO."""
    return "ceo" in (usuario.papeis or [])


def _eh_proprietario(usuario: UsuarioDB, projeto: ProjetoDB) -> bool:
    """Verifica se o usuário é proprietário do projeto."""
    return usuario.id == projeto.proprietario_id


def _eh_lider(usuario: UsuarioDB, projeto: ProjetoDB) -> bool:
    """Verifica se o usuário é líder técnico do projeto."""
    return usuario.id == projeto.lider_tecnico_id


def _pode_gerenciar(usuario: UsuarioDB, projeto: ProjetoDB) -> bool:
    """Verifica se pode gerenciar o projeto (proprietário ou CEO)."""
    return _eh_ceo(usuario) or _eh_proprietario(usuario, projeto)


def _determinar_aprovador(tipo_mudanca: str, projeto: ProjetoDB = None) -> str:
    """Determina quem precisa aprovar baseado no tipo de mudança e regras do projeto."""
    # Se o projeto tem regras customizadas, usar elas
    if projeto and projeto.regras_aprovacao:
        regras = projeto.regras_aprovacao
        regra = regras.get(tipo_mudanca, {})
        if isinstance(regra, dict) and "aprovador" in regra:
            return regra["aprovador"]

    # Regras padrão
    padroes = {"pequena": "lider_tecnico", "grande": "proprietario", "critica": "ambos"}
    return padroes.get(tipo_mudanca, "proprietario")


# =====================================================================
# Rotas: Projetos
# =====================================================================

@router.get("/projetos")
def listar_projetos(
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Lista todos os projetos."""
    projetos = db.query(ProjetoDB).filter_by(
        company_id=usuario.company_id, ativo=True
    ).all()

    return [
        {
            "id": p.id,
            "nome": p.nome,
            "descricao": p.descricao,
            "caminho": p.caminho,
            "repositorio": p.repositorio,
            "stack": p.stack,
            "icone": p.icone,
            "proprietario_id": p.proprietario_id,
            "proprietario_nome": p.proprietario_nome,
            "lider_tecnico_id": p.lider_tecnico_id,
            "lider_tecnico_nome": p.lider_tecnico_nome,
            "membros": p.membros or [],
            "regras_aprovacao": p.regras_aprovacao or {},
            "fase_atual": p.fase_atual,
            "criado_em": p.criado_em.isoformat() if p.criado_em else None,
        }
        for p in projetos
    ]


@router.get("/projetos/{projeto_id}")
def detalhar_projeto(
    projeto_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Detalhes de um projeto com solicitações pendentes."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    solicitacoes = db.query(SolicitacaoDB).filter_by(
        projeto_id=projeto_id
    ).order_by(SolicitacaoDB.criado_em.desc()).limit(20).all()

    return {
        "id": projeto.id,
        "nome": projeto.nome,
        "descricao": projeto.descricao,
        "caminho": projeto.caminho,
        "repositorio": projeto.repositorio,
        "stack": projeto.stack,
        "icone": projeto.icone,
        "proprietario_id": projeto.proprietario_id,
        "proprietario_nome": projeto.proprietario_nome,
        "lider_tecnico_id": projeto.lider_tecnico_id,
        "lider_tecnico_nome": projeto.lider_tecnico_nome,
        "membros": projeto.membros or [],
        "regras_aprovacao": projeto.regras_aprovacao or {},
        "fase_atual": projeto.fase_atual,
        "criado_em": projeto.criado_em.isoformat() if projeto.criado_em else None,
        "eh_proprietario": _eh_proprietario(usuario, projeto),
        "eh_lider": _eh_lider(usuario, projeto),
        "eh_ceo": _eh_ceo(usuario),
        "solicitacoes": [
            {
                "id": s.id,
                "titulo": s.titulo,
                "descricao": s.descricao,
                "tipo_mudanca": s.tipo_mudanca,
                "categoria": s.categoria,
                "status": s.status,
                "aprovador_necessario": s.aprovador_necessario,
                "solicitante_nome": s.solicitante_nome,
                "aprovado_por_nome": s.aprovado_por_nome,
                "comentario_aprovador": s.comentario_aprovador,
                "criado_em": s.criado_em.isoformat() if s.criado_em else None,
                "aprovado_em": s.aprovado_em.isoformat() if s.aprovado_em else None,
            }
            for s in solicitacoes
        ],
    }


@router.post("/projetos")
def criar_projeto(
    req: CriarProjetoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Cria um novo projeto. Só CEO pode criar."""
    if not _eh_ceo(usuario):
        raise HTTPException(status_code=403, detail="Apenas o CEO pode criar projetos.")

    # Verificar duplicata
    existente = db.query(ProjetoDB).filter_by(nome=req.nome).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Projeto '{req.nome}' já existe.")

    # Proprietário: pode ser o CEO ou outro nomeado
    proprietario_id = req.proprietario_id or usuario.id
    proprietario = db.query(UsuarioDB).filter_by(id=proprietario_id).first()
    if not proprietario:
        raise HTTPException(status_code=404, detail="Proprietário não encontrado.")

    # Líder técnico (opcional)
    lider_nome = ""
    if req.lider_tecnico_id:
        lider = db.query(UsuarioDB).filter_by(id=req.lider_tecnico_id).first()
        if lider:
            lider_nome = lider.nome

    projeto = ProjetoDB(
        nome=req.nome,
        descricao=req.descricao,
        caminho=req.caminho,
        repositorio=req.repositorio,
        stack=req.stack,
        icone=req.icone,
        proprietario_id=proprietario_id,
        proprietario_nome=proprietario.nome,
        lider_tecnico_id=req.lider_tecnico_id,
        lider_tecnico_nome=lider_nome,
        fase_atual=req.fase_atual,
        company_id=usuario.company_id,
    )
    db.add(projeto)

    # Audit log
    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="CRIAR_PROJETO",
        descricao=f"Projeto '{req.nome}' criado. Proprietário: {proprietario.nome}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    db.refresh(projeto)

    logger.info(f"[PROJETO] Criado: {req.nome} (proprietário: {proprietario.nome})")
    return {"mensagem": f"Projeto '{req.nome}' criado com sucesso!", "id": projeto.id}


@router.put("/projetos/{projeto_id}")
def editar_projeto(
    projeto_id: int,
    req: EditarProjetoRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Edita detalhes do projeto. Proprietário ou CEO."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    if not _pode_gerenciar(usuario, projeto):
        raise HTTPException(status_code=403, detail="Apenas o proprietário ou CEO pode editar o projeto.")

    if req.nome is not None:
        projeto.nome = req.nome
    if req.descricao is not None:
        projeto.descricao = req.descricao
    if req.caminho is not None:
        projeto.caminho = req.caminho
    if req.repositorio is not None:
        projeto.repositorio = req.repositorio
    if req.stack is not None:
        projeto.stack = req.stack
    if req.icone is not None:
        projeto.icone = req.icone
    if req.fase_atual is not None:
        projeto.fase_atual = req.fase_atual

    db.commit()
    logger.info(f"[PROJETO] Editado: {projeto.nome}")
    return {"mensagem": f"Projeto '{projeto.nome}' atualizado."}


@router.put("/projetos/{projeto_id}/proprietario")
def nomear_proprietario(
    projeto_id: int,
    req: NomearProprietarioRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Nomeia o proprietário de um projeto. SÓ O CEO pode fazer isso."""
    if not _eh_ceo(usuario):
        raise HTTPException(status_code=403, detail="Apenas o CEO pode nomear proprietários de projetos.")

    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    novo_proprietario = db.query(UsuarioDB).filter_by(id=req.usuario_id).first()
    if not novo_proprietario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    antigo = projeto.proprietario_nome
    projeto.proprietario_id = novo_proprietario.id
    projeto.proprietario_nome = novo_proprietario.nome

    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="NOMEAR_PROPRIETARIO",
        descricao=f"Projeto '{projeto.nome}': proprietário alterado de {antigo} para {novo_proprietario.nome}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    logger.info(f"[PROJETO] Proprietário: {projeto.nome} → {novo_proprietario.nome}")
    return {"mensagem": f"'{novo_proprietario.nome}' agora é proprietário do projeto '{projeto.nome}'."}


@router.put("/projetos/{projeto_id}/lider")
def nomear_lider(
    projeto_id: int,
    req: NomearLiderRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Nomeia o líder técnico. Proprietário ou CEO."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    if not _pode_gerenciar(usuario, projeto):
        raise HTTPException(status_code=403, detail="Apenas o proprietário ou CEO pode nomear líder técnico.")

    lider = db.query(UsuarioDB).filter_by(id=req.usuario_id).first()
    if not lider:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    projeto.lider_tecnico_id = lider.id
    projeto.lider_tecnico_nome = lider.nome
    db.commit()

    logger.info(f"[PROJETO] Líder técnico: {projeto.nome} → {lider.nome}")
    return {"mensagem": f"'{lider.nome}' agora é líder técnico do projeto '{projeto.nome}'."}


@router.put("/projetos/{projeto_id}/membros")
def gerenciar_membros(
    projeto_id: int,
    req: GerenciarMembrosRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Adiciona ou remove membros. Proprietário ou CEO."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    if not _pode_gerenciar(usuario, projeto):
        raise HTTPException(status_code=403, detail="Apenas o proprietário ou CEO pode gerenciar membros.")

    membro = db.query(UsuarioDB).filter_by(id=req.usuario_id).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    membros = projeto.membros or []

    if req.acao == "adicionar":
        # Verificar se já é membro
        if any(m["id"] == req.usuario_id for m in membros):
            return {"mensagem": f"'{membro.nome}' já é membro do projeto."}
        membros.append({"id": membro.id, "nome": membro.nome, "papel": req.papel})
        projeto.membros = membros
        db.commit()
        return {"mensagem": f"'{membro.nome}' adicionado como {req.papel} no projeto '{projeto.nome}'."}

    elif req.acao == "remover":
        membros = [m for m in membros if m["id"] != req.usuario_id]
        projeto.membros = membros
        db.commit()
        return {"mensagem": f"'{membro.nome}' removido do projeto '{projeto.nome}'."}

    raise HTTPException(status_code=400, detail="Ação inválida. Use 'adicionar' ou 'remover'.")


@router.put("/projetos/{projeto_id}/regras")
def atualizar_regras(
    projeto_id: int,
    req: AtualizarRegrasRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Atualiza regras de aprovação do projeto. Proprietário ou CEO."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    if not _pode_gerenciar(usuario, projeto):
        raise HTTPException(status_code=403, detail="Apenas o proprietário ou CEO pode alterar as regras.")

    # Validar regras
    aprovadores_validos = {"lider_tecnico", "proprietario", "ambos", "nenhum"}
    for tipo, regra in req.regras.items():
        if tipo not in ("pequena", "grande", "critica"):
            raise HTTPException(status_code=400, detail=f"Tipo '{tipo}' inválido. Use: pequena, grande, critica")
        if isinstance(regra, dict):
            if regra.get("aprovador") not in aprovadores_validos:
                raise HTTPException(status_code=400, detail=f"Aprovador '{regra.get('aprovador')}' inválido.")
        else:
            raise HTTPException(status_code=400, detail="Formato de regra inválido.")

    projeto.regras_aprovacao = req.regras

    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="ATUALIZAR_REGRAS_APROVACAO",
        descricao=f"Regras de aprovação do projeto '{projeto.nome}' alteradas por {usuario.nome}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    logger.info(f"[PROJETO] Regras de aprovação atualizadas: {projeto.nome} por {usuario.nome}")
    return {"mensagem": f"Regras de aprovação do projeto '{projeto.nome}' atualizadas!"}


# =====================================================================
# Rotas: Solicitações de Mudança
# =====================================================================

@router.post("/projetos/{projeto_id}/solicitacoes")
def criar_solicitacao(
    projeto_id: int,
    req: CriarSolicitacaoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Cria uma solicitação de mudança no projeto."""
    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    # Se o solicitante é o proprietário ou CEO, auto-aprova
    if _eh_proprietario(usuario, projeto) or _eh_ceo(usuario):
        status = "aprovada"
        aprovador = usuario.nome
    else:
        status = "pendente"
        aprovador = ""

    aprovador_necessario = _determinar_aprovador(req.tipo_mudanca, projeto)

    # Se regra é "nenhum", auto-aprova para todos
    if aprovador_necessario == "nenhum":
        status = "aprovada"
        aprovador = usuario.nome

    solicitacao = SolicitacaoDB(
        projeto_id=projeto.id,
        projeto_nome=projeto.nome,
        solicitante_id=usuario.id,
        solicitante_nome=usuario.nome,
        titulo=req.titulo,
        descricao=req.descricao,
        tipo_mudanca=req.tipo_mudanca,
        categoria=req.categoria,
        status=status,
        aprovador_necessario=aprovador_necessario,
        aprovado_por_nome=aprovador,
        aprovado_por_id=usuario.id if status == "aprovada" else None,
        aprovado_em=datetime.now(timezone.utc) if status == "aprovada" else None,
        company_id=usuario.company_id,
    )
    db.add(solicitacao)

    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="CRIAR_SOLICITACAO",
        descricao=f"Solicitação '{req.titulo}' no projeto '{projeto.nome}' ({req.tipo_mudanca})",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    db.refresh(solicitacao)

    logger.info(f"[SOLICITAÇÃO] Criada: '{req.titulo}' em {projeto.nome} por {usuario.nome} [{status}]")
    return {
        "mensagem": f"Solicitação criada com sucesso! Status: {status}",
        "id": solicitacao.id,
        "status": status,
        "aprovador_necessario": aprovador_necessario,
    }


@router.get("/projetos/{projeto_id}/solicitacoes")
def listar_solicitacoes(
    projeto_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Lista solicitações de mudança de um projeto."""
    solicitacoes = db.query(SolicitacaoDB).filter_by(
        projeto_id=projeto_id
    ).order_by(SolicitacaoDB.criado_em.desc()).all()

    return [
        {
            "id": s.id,
            "titulo": s.titulo,
            "descricao": s.descricao,
            "tipo_mudanca": s.tipo_mudanca,
            "categoria": s.categoria,
            "status": s.status,
            "aprovador_necessario": s.aprovador_necessario,
            "solicitante_nome": s.solicitante_nome,
            "aprovado_por_nome": s.aprovado_por_nome,
            "comentario_aprovador": s.comentario_aprovador,
            "criado_em": s.criado_em.isoformat() if s.criado_em else None,
            "aprovado_em": s.aprovado_em.isoformat() if s.aprovado_em else None,
        }
        for s in solicitacoes
    ]


@router.put("/solicitacoes/{solicitacao_id}/aprovar")
def aprovar_solicitacao(
    solicitacao_id: int,
    req: AcaoSolicitacaoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Aprova uma solicitação de mudança."""
    sol = db.query(SolicitacaoDB).filter_by(id=solicitacao_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    if sol.status != "pendente":
        raise HTTPException(status_code=400, detail=f"Solicitação já está '{sol.status}'.")

    projeto = db.query(ProjetoDB).filter_by(id=sol.projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    # Verificar permissão de aprovação
    pode = False
    if _eh_ceo(usuario):
        pode = True
    elif sol.aprovador_necessario == "lider_tecnico" and _eh_lider(usuario, projeto):
        pode = True
    elif sol.aprovador_necessario == "proprietario" and _eh_proprietario(usuario, projeto):
        pode = True
    elif sol.aprovador_necessario == "ambos" and (
        _eh_proprietario(usuario, projeto) or _eh_lider(usuario, projeto)
    ):
        pode = True

    if not pode:
        raise HTTPException(
            status_code=403,
            detail=f"Você não tem permissão para aprovar. Requer: {sol.aprovador_necessario}."
        )

    sol.status = "aprovada"
    sol.aprovado_por_id = usuario.id
    sol.aprovado_por_nome = usuario.nome
    sol.comentario_aprovador = req.comentario
    sol.aprovado_em = datetime.now(timezone.utc)

    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="APROVAR_SOLICITACAO",
        descricao=f"Aprovada: '{sol.titulo}' no projeto '{sol.projeto_nome}'",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    logger.info(f"[SOLICITAÇÃO] Aprovada: '{sol.titulo}' por {usuario.nome}")
    return {"mensagem": f"Solicitação aprovada por {usuario.nome}!"}


@router.put("/solicitacoes/{solicitacao_id}/rejeitar")
def rejeitar_solicitacao(
    solicitacao_id: int,
    req: AcaoSolicitacaoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Rejeita uma solicitação de mudança."""
    sol = db.query(SolicitacaoDB).filter_by(id=solicitacao_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    if sol.status != "pendente":
        raise HTTPException(status_code=400, detail=f"Solicitação já está '{sol.status}'.")

    projeto = db.query(ProjetoDB).filter_by(id=sol.projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    # Mesma lógica de permissão
    pode = _eh_ceo(usuario) or _eh_proprietario(usuario, projeto) or _eh_lider(usuario, projeto)
    if not pode:
        raise HTTPException(status_code=403, detail="Sem permissão para rejeitar.")

    sol.status = "rejeitada"
    sol.aprovado_por_id = usuario.id
    sol.aprovado_por_nome = usuario.nome
    sol.comentario_aprovador = req.comentario
    sol.aprovado_em = datetime.now(timezone.utc)

    db.add(AuditLogDB(
        user_id=usuario.id,
        email=usuario.email,
        acao="REJEITAR_SOLICITACAO",
        descricao=f"Rejeitada: '{sol.titulo}' no projeto '{sol.projeto_nome}'. Motivo: {req.comentario}",
        ip=request.client.host if request.client else "",
        company_id=usuario.company_id,
    ))

    db.commit()
    logger.info(f"[SOLICITAÇÃO] Rejeitada: '{sol.titulo}' por {usuario.nome}")
    return {"mensagem": f"Solicitação rejeitada por {usuario.nome}."}


# ============================================================
# Version Control (VCS) — GitHub + GitBucket
# ============================================================

class VCSConfigRequest(BaseModel):
    vcs_tipo: str  # "github" ou "gitbucket"
    repo_url: str
    api_token: str
    branch_padrao: str = "main"


@router.post("/{projeto_id}/vcs")
async def configurar_vcs(
    projeto_id: int,
    dados: VCSConfigRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cadastra ou atualiza configuração de Version Control do projeto."""
    from database.models import ProjetoVCSDB
    from core.vcs_service import criptografar_token

    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Só proprietário ou CEO pode configurar VCS
    eh_dono = projeto.proprietario_id == usuario.id
    eh_ceo = any(p in (usuario.papeis or []) for p in ["ceo", "operations_lead"])
    if not eh_dono and not eh_ceo:
        raise HTTPException(status_code=403, detail="Sem permissão para configurar VCS")

    # Validar tipo
    if dados.vcs_tipo not in ("github", "gitbucket"):
        raise HTTPException(status_code=400, detail="Tipo VCS deve ser 'github' ou 'gitbucket'")

    # Criptografar token
    token_enc = criptografar_token(dados.api_token)

    # Verificar se já existe config para este projeto
    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto_id).first()
    if vcs:
        vcs.vcs_tipo = dados.vcs_tipo
        vcs.repo_url = dados.repo_url
        vcs.api_token_encrypted = token_enc
        vcs.branch_padrao = dados.branch_padrao
        vcs.ativo = True
        vcs.atualizado_em = datetime.now(timezone.utc)
    else:
        vcs = ProjetoVCSDB(
            projeto_id=projeto_id,
            vcs_tipo=dados.vcs_tipo,
            repo_url=dados.repo_url,
            api_token_encrypted=token_enc,
            branch_padrao=dados.branch_padrao,
            company_id=usuario.company_id,
        )
        db.add(vcs)

    # Audit log
    db.add(AuditLogDB(
        usuario_id=usuario.id,
        acao="vcs_configurar",
        detalhes=f"VCS {dados.vcs_tipo} configurado para projeto {projeto.nome}: {dados.repo_url}",
        ip="api",
        company_id=usuario.company_id,
    ))

    db.commit()
    logger.info(f"[VCS] {usuario.nome} configurou {dados.vcs_tipo} para projeto {projeto.nome}")
    return {"mensagem": "VCS configurado com sucesso", "tipo": dados.vcs_tipo, "repo": dados.repo_url}


@router.get("/{projeto_id}/vcs")
async def buscar_vcs(
    projeto_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Busca configuração VCS do projeto (sem expor o token)."""
    from database.models import ProjetoVCSDB

    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto_id, ativo=True).first()
    if not vcs:
        return {"configurado": False}

    return {
        "configurado": True,
        "vcs_tipo": vcs.vcs_tipo,
        "repo_url": vcs.repo_url,
        "branch_padrao": vcs.branch_padrao,
        "token_status": "***configurado***",
        "criado_em": vcs.criado_em.isoformat() if vcs.criado_em else None,
        "atualizado_em": vcs.atualizado_em.isoformat() if vcs.atualizado_em else None,
    }


@router.post("/{projeto_id}/vcs/testar")
async def testar_vcs(
    projeto_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Testa conexão VCS do projeto."""
    from database.models import ProjetoVCSDB
    from core.vcs_service import descriptografar_token, VCSService

    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto_id, ativo=True).first()
    if not vcs:
        raise HTTPException(status_code=404, detail="VCS não configurado para este projeto")

    token = descriptografar_token(vcs.api_token_encrypted)
    service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao)
    resultado = await service.testar_conexao()

    return {
        "sucesso": resultado.sucesso,
        "mensagem": resultado.mensagem,
        "repo_nome": resultado.repo_nome,
        "branch_padrao": resultado.branch_padrao,
    }


@router.delete("/{projeto_id}/vcs")
async def remover_vcs(
    projeto_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Remove configuração VCS do projeto."""
    from database.models import ProjetoVCSDB

    projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    eh_dono = projeto.proprietario_id == usuario.id
    eh_ceo = any(p in (usuario.papeis or []) for p in ["ceo", "operations_lead"])
    if not eh_dono and not eh_ceo:
        raise HTTPException(status_code=403, detail="Sem permissão")

    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto_id).first()
    if vcs:
        vcs.ativo = False
        db.commit()

    logger.info(f"[VCS] {usuario.nome} removeu VCS do projeto {projeto.nome}")
    return {"mensagem": "VCS removido"}
