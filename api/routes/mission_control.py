"""
Rotas: Mission Control — Code Studio 2.0 (v0.55.0)

Painel triplo (Editor + Terminal + Navegador) com artifacts inteligentes,
agentes vivos e comentarios inline estilo Google Docs.

GET  /api/mission-control/sessoes           — Lista sessoes ativas
POST /api/mission-control/sessao             — Cria nova sessao
GET  /api/mission-control/sessao/{id}        — Detalhes da sessao
POST /api/mission-control/sessao/{id}/comando — Executa comando no terminal
POST /api/mission-control/sessao/{id}/agente  — Dispara agente na sessao

GET  /api/mission-control/artifacts/{sessao_id}         — Lista artifacts da sessao
POST /api/mission-control/artifacts/{artifact_id}/comentar — Adiciona comentario inline
POST /api/mission-control/artifacts/{artifact_id}/status   — Atualiza status do artifact
"""

import logging
import os
import subprocess
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.models import (
    UsuarioDB, ArtifactDB, MissionControlSessaoDB, ProjetoDB,
)
from database.session import get_db, SessionLocal

logger = logging.getLogger("synerium.mission_control")

router = APIRouter(prefix="/api/mission-control", tags=["Mission Control"])


# =====================================================================
# Schemas
# =====================================================================

class CriarSessaoRequest(BaseModel):
    titulo: str = "Nova Sessao"
    projeto_id: int | None = None


class ComandoTerminalRequest(BaseModel):
    comando: str
    cwd: str = ""  # Diretorio de trabalho (relativo ao projeto)


class DisparoAgenteRequest(BaseModel):
    instrucao: str
    agente_nome: str = ""  # Se vazio, usa agente padrao do squad
    tipo: str = "tarefa"  # tarefa, analise, implementacao, review


class ComentarioInlineRequest(BaseModel):
    linha: int | None = None
    secao: str = ""
    texto: str
    autor: str = ""


class AtualizarStatusRequest(BaseModel):
    status: str  # revisado, aprovado, rejeitado


class AutoSaveRequest(BaseModel):
    """Salva estado completo dos paineis da sessao."""
    painel_editor: dict | None = None
    painel_terminal: dict | None = None
    painel_navegador: dict | None = None


# =====================================================================
# Helpers
# =====================================================================

def _gerar_id() -> str:
    return uuid.uuid4().hex[:12]


COMANDOS_BLOQUEADOS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){", "fork bomb",
    "shutdown", "reboot", "halt", "poweroff", "init 0", "init 6",
]


def _comando_seguro(cmd: str) -> bool:
    """Verifica se o comando nao e destrutivo."""
    cmd_lower = cmd.lower().strip()
    for bloqueado in COMANDOS_BLOQUEADOS:
        if bloqueado in cmd_lower:
            return False
    return True


# =====================================================================
# SESSOES
# =====================================================================

@router.get("/sessoes")
def listar_sessoes(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista sessoes ativas do Mission Control."""
    sessoes = (
        db.query(MissionControlSessaoDB)
        .filter_by(usuario_id=usuario.id, company_id=usuario.company_id or 1)
        .order_by(MissionControlSessaoDB.atualizado_em.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "sessao_id": s.sessao_id,
            "titulo": s.titulo,
            "status": s.status,
            "projeto_id": s.projeto_id,
            "agentes_ativos": s.agentes_ativos or [],
            "total_artifacts": s.total_artifacts,
            "total_comandos": s.total_comandos,
            "criado_em": s.criado_em.isoformat() if s.criado_em else None,
            "atualizado_em": s.atualizado_em.isoformat() if s.atualizado_em else None,
        }
        for s in sessoes
    ]


@router.post("/sessao")
def criar_sessao(
    req: CriarSessaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria nova sessao do Mission Control."""
    sessao_id = _gerar_id()

    sessao = MissionControlSessaoDB(
        sessao_id=sessao_id,
        titulo=req.titulo,
        projeto_id=req.projeto_id,
        usuario_id=usuario.id,
        company_id=usuario.company_id or 1,
        painel_editor={"arquivos_abertos": [], "arquivo_ativo": None},
        painel_terminal={"historico": [], "cwd": ""},
        painel_navegador={"url_atual": "", "screenshots": []},
        agentes_ativos=[],
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)

    logger.info(f"[MISSION] Sessao {sessao_id} criada por {usuario.nome}: {req.titulo}")

    return {
        "sessao_id": sessao_id,
        "titulo": sessao.titulo,
        "status": "ativa",
        "projeto_id": req.projeto_id,
    }


@router.get("/sessao/{sessao_id}")
def obter_sessao(
    sessao_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Detalhes completos de uma sessao."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    # Buscar artifacts da sessao
    artifacts = db.query(ArtifactDB).filter_by(sessao_id=sessao_id).order_by(ArtifactDB.criado_em.desc()).all()

    return {
        "sessao_id": sessao.sessao_id,
        "titulo": sessao.titulo,
        "status": sessao.status,
        "projeto_id": sessao.projeto_id,
        "painel_editor": sessao.painel_editor,
        "painel_terminal": sessao.painel_terminal,
        "painel_navegador": sessao.painel_navegador,
        "agentes_ativos": sessao.agentes_ativos or [],
        "total_artifacts": sessao.total_artifacts,
        "total_comandos": sessao.total_comandos,
        "total_arquivos_editados": sessao.total_arquivos_editados,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "tipo": a.tipo,
                "titulo": a.titulo,
                "conteudo": a.conteudo[:2000] if a.conteudo else None,
                "dados": a.dados,
                "status": a.status,
                "agente_nome": a.agente_nome,
                "comentarios_inline": a.comentarios_inline or [],
                "criado_em": a.criado_em.isoformat() if a.criado_em else None,
            }
            for a in artifacts
        ],
        "criado_em": sessao.criado_em.isoformat() if sessao.criado_em else None,
    }


# =====================================================================
# AUTO-SAVE
# =====================================================================

@router.patch("/sessao/{sessao_id}/save")
def auto_save_sessao(
    sessao_id: str,
    req: AutoSaveRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Auto-save: salva estado dos paineis da sessao (chamado a cada 10s)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if req.painel_editor is not None:
        sessao.painel_editor = req.painel_editor
    if req.painel_terminal is not None:
        sessao.painel_terminal = req.painel_terminal
    if req.painel_navegador is not None:
        sessao.painel_navegador = req.painel_navegador

    sessao.atualizado_em = datetime.utcnow()
    db.commit()

    return {"salvo": True, "sessao_id": sessao_id}


# =====================================================================
# TERMINAL
# =====================================================================

@router.post("/sessao/{sessao_id}/comando")
def executar_comando_terminal(
    sessao_id: str,
    req: ComandoTerminalRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Executa comando no terminal da sessao (sandboxed)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if not _comando_seguro(req.comando):
        raise HTTPException(status_code=400, detail="Comando bloqueado por seguranca")

    # Determinar diretorio de trabalho
    cwd = "/opt/synerium-factory"
    if sessao.projeto_id:
        projeto = db.query(ProjetoDB).filter_by(id=sessao.projeto_id).first()
        if projeto:
            cwd = getattr(projeto, "caminho_local", cwd) or cwd
    if req.cwd:
        cwd = os.path.join(cwd, req.cwd)

    try:
        resultado = subprocess.run(
            req.comando,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        saida = resultado.stdout + resultado.stderr
        sucesso = resultado.returncode == 0

        # Atualizar sessao
        terminal = sessao.painel_terminal or {}
        historico = terminal.get("historico", [])
        historico.append({
            "comando": req.comando,
            "saida": saida[:5000],
            "sucesso": sucesso,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Manter apenas ultimos 50 comandos
        if len(historico) > 50:
            historico = historico[-50:]
        terminal["historico"] = historico
        terminal["cwd"] = cwd
        sessao.painel_terminal = terminal
        sessao.total_comandos = (sessao.total_comandos or 0) + 1
        sessao.atualizado_em = datetime.utcnow()
        db.commit()

        # Gerar artifact de terminal se saida significativa
        if len(saida) > 200:
            _criar_artifact(
                db, sessao_id, "terminal",
                f"Terminal: {req.comando[:80]}",
                f"$ {req.comando}\n\n{saida[:5000]}",
                agente_nome="Terminal",
                usuario_id=usuario.id,
                company_id=usuario.company_id or 1,
            )

        return {
            "sucesso": sucesso,
            "saida": saida[:10000],
            "returncode": resultado.returncode,
            "comando": req.comando,
        }

    except subprocess.TimeoutExpired:
        return {"sucesso": False, "saida": "Timeout: comando excedeu 30 segundos", "returncode": -1}
    except Exception as e:
        return {"sucesso": False, "saida": str(e), "returncode": -1}


# =====================================================================
# AGENTES
# =====================================================================

@router.post("/sessao/{sessao_id}/agente")
def disparar_agente(
    sessao_id: str,
    req: DisparoAgenteRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Dispara um agente para trabalhar na sessao."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    agente_id = _gerar_id()
    agente_nome = req.agente_nome or "Mission Control Agent"

    # Atualizar agentes ativos
    ativos = sessao.agentes_ativos or []
    ativos.append({
        "id": agente_id,
        "nome": agente_nome,
        "status": "executando",
        "tarefa": req.instrucao[:200],
        "tipo": req.tipo,
        "inicio": datetime.utcnow().isoformat(),
    })
    sessao.agentes_ativos = ativos
    sessao.atualizado_em = datetime.utcnow()
    db.commit()

    # Executar agente em background
    threading.Thread(
        target=_executar_agente_mission_control,
        args=(sessao_id, agente_id, agente_nome, req.instrucao, req.tipo, sessao.projeto_id, usuario.id, usuario.company_id or 1),
        daemon=True,
    ).start()

    logger.info(f"[MISSION] Agente {agente_nome} disparado na sessao {sessao_id}: {req.instrucao[:80]}")

    return {
        "agente_id": agente_id,
        "agente_nome": agente_nome,
        "status": "executando",
        "mensagem": f"Agente {agente_nome} iniciou: {req.instrucao[:100]}",
    }


def _executar_agente_mission_control(
    sessao_id: str, agente_id: str, agente_nome: str,
    instrucao: str, tipo: str, projeto_id: int | None,
    usuario_id: int, company_id: int,
):
    """Executa agente em background e gera artifacts."""
    db = SessionLocal()
    try:
        # Chamar LLM com contexto do projeto
        from core.llm_fallback import chamar_llm_com_fallback
        from langchain_core.messages import HumanMessage, SystemMessage
        from core.classificador_mensagem import classificar_mensagem

        # Montar contexto do projeto
        contexto_projeto = ""
        if projeto_id:
            projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
            if projeto:
                contexto_projeto = f"Projeto: {projeto.nome}\nDescrição: {projeto.descricao or ''}\n"

        system_msg = (
            f"Voce e o {agente_nome}, agente do Mission Control do Synerium Factory.\n"
            f"Tipo de tarefa: {tipo}\n"
            f"{contexto_projeto}\n"
            "Gere um plano detalhado com checklist de tarefas.\n"
            "Retorne JSON:\n"
            '{"plano": "descricao do plano", "checklist": [{"item": "...", "feito": false}], '
            '"arquivos_impactados": ["arquivo1.tsx", "arquivo2.py"], '
            '"comandos_sugeridos": ["npm run build", "pytest"]}'
        )

        msgs = [
            SystemMessage(content=system_msg),
            HumanMessage(content=instrucao),
        ]

        cls = classificar_mensagem(instrucao)
        resposta, provider, modelo = chamar_llm_com_fallback(msgs, max_tokens=2000, classificacao=cls)
        texto = resposta.content

        logger.info(f"[MISSION] Agente {agente_nome} respondeu via {provider}/{modelo}")

        # Extrair JSON se possivel
        import json, re
        dados = {}
        json_match = re.search(r'\{[\s\S]*\}', texto)
        if json_match:
            try:
                dados = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Criar artifact: plano
        _criar_artifact(
            db, sessao_id, "plano",
            f"Plano: {instrucao[:100]}",
            dados.get("plano", texto[:3000]),
            dados=dados,
            agente_nome=agente_nome,
            usuario_id=usuario_id,
            company_id=company_id,
            workflow_id=None,
        )

        # Criar artifact: checklist
        checklist = dados.get("checklist", [])
        if checklist:
            _criar_artifact(
                db, sessao_id, "checklist",
                f"Checklist: {instrucao[:80]}",
                "\n".join(f"- [ ] {c.get('item', c) if isinstance(c, dict) else c}" for c in checklist),
                dados={"items": checklist},
                agente_nome=agente_nome,
                usuario_id=usuario_id,
                company_id=company_id,
            )

        # Atualizar status do agente na sessao
        sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
        if sessao:
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "concluido"
                    a["fim"] = datetime.utcnow().isoformat()
                    a["resultado"] = f"Gerou {1 + (1 if checklist else 0)} artifacts"
            sessao.agentes_ativos = ativos
            sessao.atualizado_em = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"[MISSION] Erro no agente {agente_nome}: {e}")
        # Marcar agente como erro
        try:
            sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
            if sessao:
                ativos = sessao.agentes_ativos or []
                for a in ativos:
                    if a.get("id") == agente_id:
                        a["status"] = "erro"
                        a["erro"] = str(e)[:200]
                sessao.agentes_ativos = ativos
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# =====================================================================
# ARTIFACTS
# =====================================================================

def _criar_artifact(
    db: Session, sessao_id: str, tipo: str, titulo: str,
    conteudo: str, dados: dict = None, agente_nome: str = "",
    usuario_id: int = None, company_id: int = 1,
    workflow_id: str = None,
) -> ArtifactDB:
    """Cria um artifact e incrementa contador da sessao."""
    artifact = ArtifactDB(
        artifact_id=_gerar_id(),
        sessao_id=sessao_id,
        workflow_id=workflow_id,
        agente_nome=agente_nome,
        tipo=tipo,
        titulo=titulo,
        conteudo=conteudo,
        dados=dados or {},
        usuario_id=usuario_id,
        company_id=company_id,
    )
    db.add(artifact)

    sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
    if sessao:
        sessao.total_artifacts = (sessao.total_artifacts or 0) + 1
        sessao.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(artifact)
    return artifact


@router.get("/artifacts/{sessao_id}")
def listar_artifacts(
    sessao_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista artifacts de uma sessao."""
    artifacts = (
        db.query(ArtifactDB)
        .filter_by(sessao_id=sessao_id, company_id=usuario.company_id or 1)
        .order_by(ArtifactDB.criado_em.desc())
        .all()
    )
    return [
        {
            "artifact_id": a.artifact_id,
            "tipo": a.tipo,
            "titulo": a.titulo,
            "conteudo": a.conteudo,
            "dados": a.dados,
            "status": a.status,
            "agente_nome": a.agente_nome,
            "comentarios_inline": a.comentarios_inline or [],
            "criado_em": a.criado_em.isoformat() if a.criado_em else None,
        }
        for a in artifacts
    ]


@router.post("/artifacts/{artifact_id}/comentar")
def comentar_artifact(
    artifact_id: str,
    req: ComentarioInlineRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Adiciona comentario inline num artifact (estilo Google Docs)."""
    artifact = db.query(ArtifactDB).filter_by(artifact_id=artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact nao encontrado")

    comentarios = artifact.comentarios_inline or []
    comentarios.append({
        "id": _gerar_id(),
        "linha": req.linha,
        "secao": req.secao,
        "texto": req.texto,
        "autor": req.autor or usuario.nome,
        "data": datetime.utcnow().isoformat(),
        "resolvido": False,
    })
    artifact.comentarios_inline = comentarios
    artifact.atualizado_em = datetime.utcnow()
    db.commit()

    logger.info(f"[MISSION] Comentario adicionado ao artifact {artifact_id} por {usuario.nome}")

    return {"mensagem": "Comentário adicionado.", "total_comentarios": len(comentarios)}


@router.post("/artifacts/{artifact_id}/status")
def atualizar_status_artifact(
    artifact_id: str,
    req: AtualizarStatusRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atualiza status de um artifact (revisado, aprovado, rejeitado)."""
    artifact = db.query(ArtifactDB).filter_by(artifact_id=artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact nao encontrado")

    artifact.status = req.status
    artifact.revisado_por = usuario.nome
    artifact.atualizado_em = datetime.utcnow()
    db.commit()

    return {"mensagem": f"Artifact atualizado para: {req.status}"}
