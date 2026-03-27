"""
Rota: Squads Pessoais — com isolamento de segurança

GET /api/squads          — Lista squads visíveis para o usuário
GET /api/squads/todos    — Lista TODOS os squads (requer visao_geral)
GET /api/squads/meu      — Retorna APENAS o squad pessoal do usuário

Segurança:
- Todos os endpoints usam obter_usuario_atual()
- Sem visao_geral, usuário só vê: seu squad + squads de área
- Audit log em todo acesso
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from api.dependencias import obter_fabrica, obter_usuario_atual
from api.schemas import SquadResponse
from database.models import UsuarioDB

logger = logging.getLogger("synerium.squads")

router = APIRouter(prefix="/api", tags=["Squads"])

# Mapeamento de email → nome do squad pessoal
SQUAD_POR_EMAIL = {
    "thiago@objetivasolucao.com.br": "CEO — Thiago",
    "jonatas@objetivasolucao.com.br": "Diretor Técnico — Jonatas",
}

# Squads de área — compartilhados (todos veem)
SQUADS_AREA = {"Dev Backend", "Dev Frontend", "Marketing"}

# Papéis que têm visão geral por padrão
PAPEIS_VISAO_GERAL = {"ceo", "diretor_tecnico", "operations_lead"}


def _tem_visao_geral(usuario: UsuarioDB) -> bool:
    """Verifica se o usuário tem permissão de visão geral."""
    papeis = usuario.papeis or []
    # Verificar papéis
    if any(p in PAPEIS_VISAO_GERAL for p in papeis):
        return True
    # Verificar permissão granular
    perms = usuario.permissoes_granulares or {}
    if isinstance(perms, dict):
        squads_perm = perms.get("squads", {})
        if isinstance(squads_perm, dict) and squads_perm.get("visao_geral"):
            return True
    return False


def _squad_pessoal_do_usuario(usuario: UsuarioDB) -> str | None:
    """Retorna o nome do squad pessoal do usuário."""
    return SQUAD_POR_EMAIL.get(usuario.email)


def _montar_resposta(nome: str, squad, usuario: UsuarioDB) -> SquadResponse:
    """Monta o SquadResponse com metadados de propriedade."""
    squad_pessoal = _squad_pessoal_do_usuario(usuario)
    is_area = nome in SQUADS_AREA
    proprietario = ""
    for email, squad_nome in SQUAD_POR_EMAIL.items():
        if squad_nome == nome:
            proprietario = email
            break

    return SquadResponse(
        nome=nome,
        especialidade=squad.especialidade,
        contexto=squad.contexto,
        num_agentes=len(squad.agentes),
        num_tarefas=len(squad.tarefas),
        nomes_agentes=[a.role for a in squad.agentes],
        proprietario_email=proprietario,
        tipo="area" if is_area else "pessoal",
        is_meu=(nome == squad_pessoal),
    )


@router.get("/squads", response_model=list[SquadResponse])
def listar_squads(
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Lista squads visíveis para o usuário logado.
    - Squad pessoal do usuário (sempre visível)
    - Squads de área (sempre visíveis — compartilhados)
    - Squads de outros usuários (só se tem visao_geral)
    """
    visao_geral = _tem_visao_geral(usuario)
    squad_pessoal = _squad_pessoal_do_usuario(usuario)

    logger.info(
        f"[AUDIT] Squads acessados por {usuario.nome} ({usuario.email}) — "
        f"visao_geral={visao_geral}, squad_pessoal={squad_pessoal}"
    )

    resultado = []
    for nome, squad in fabrica.squads.items():
        is_area = nome in SQUADS_AREA
        is_meu = (nome == squad_pessoal)

        # Sempre mostra: meu squad + squads de área
        if is_meu or is_area:
            resultado.append(_montar_resposta(nome, squad, usuario))
        # Visão geral: mostra squads de outros usuários também
        elif visao_geral:
            resultado.append(_montar_resposta(nome, squad, usuario))

    # Ordenar: meu squad primeiro, depois áreas
    resultado.sort(key=lambda s: (0 if s.is_meu else 1 if s.tipo == "pessoal" else 2, s.nome))

    return resultado


@router.get("/squads/todos", response_model=list[SquadResponse])
def listar_todos_squads(
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Lista TODOS os squads (requer visao_geral). Bloqueia sem permissão."""
    if not _tem_visao_geral(usuario):
        logger.warning(
            f"[SEGURANÇA] {usuario.nome} ({usuario.email}) tentou acessar /squads/todos SEM permissão visao_geral"
        )
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para ver todos os squads. Solicite 'visao_geral' ao CEO."
        )

    logger.info(f"[AUDIT] Todos os squads acessados por {usuario.nome} ({usuario.email})")

    return [
        _montar_resposta(nome, squad, usuario)
        for nome, squad in fabrica.squads.items()
    ]


@router.get("/squads/meu")
def meu_squad(
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Retorna APENAS o squad pessoal do usuário logado. Seguro por design."""
    squad_nome = _squad_pessoal_do_usuario(usuario)

    logger.info(f"[AUDIT] Meu squad acessado por {usuario.nome} ({usuario.email}) → {squad_nome or 'nenhum'}")

    if not squad_nome or squad_nome not in fabrica.squads:
        return {"squad": None, "mensagem": "Nenhum squad pessoal encontrado para seu usuário."}

    squad = fabrica.squads[squad_nome]
    return _montar_resposta(squad_nome, squad, usuario)


@router.get("/squads/{squad_nome_param}")
def ver_squad_especifico(
    squad_nome_param: str,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Ver detalhes de um squad específico.
    Segurança: só permite ver o próprio squad ou se tem visao_geral.
    """
    squad_pessoal = _squad_pessoal_do_usuario(usuario)
    is_meu = (squad_nome_param == squad_pessoal)
    is_area = squad_nome_param in SQUADS_AREA
    visao_geral = _tem_visao_geral(usuario)

    if not is_meu and not is_area and not visao_geral:
        logger.warning(
            f"[SEGURANÇA] {usuario.nome} ({usuario.email}) tentou acessar squad '{squad_nome_param}' SEM permissão"
        )
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para ver este squad."
        )

    if squad_nome_param not in fabrica.squads:
        raise HTTPException(status_code=404, detail="Squad não encontrado.")

    squad = fabrica.squads[squad_nome_param]
    return _montar_resposta(squad_nome_param, squad, usuario)
