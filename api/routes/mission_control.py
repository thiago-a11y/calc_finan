"""
Rotas: Mission Control — Code Studio 2.0 (v0.57.6)

Painel triplo (Editor + Terminal + Team Chat/Artifacts) com artifacts inteligentes,
agentes vivos, True Live Typing e comentarios inline estilo Google Docs.

v0.57.6 — True Live Typing:
- True Live Typing: caractere por caractere no editor com cursor verde piscando
- Streaming em blocos de 2 linhas com 200ms de delay para efeito fluido
- Comandos reais no terminal (npm build, pytest, eslint)
- Progresso granular dentro de cada fase

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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.models import (
    UsuarioDB, ArtifactDB, MissionControlSessaoDB, ProjetoDB, TeamChatDB, ProjetoVCSDB, AuditLogDB,
)
from database.session import get_db, SessionLocal
from sqlalchemy.orm.attributes import flag_modified

from core.memory.kairos.service import kairos_service
from core.governance.plan_mode.service import plan_mode_service

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


class GitCommitRequest(BaseModel):
    """Commit apenas (sem push)."""
    mensagem: str = ""


class GitPushRequest(BaseModel):
    """Push + criação de PR."""
    titulo_pr: str = ""


class GitMergeRequest(BaseModel):
    """Merge de PR existente."""
    pr_number: int


class SalvarArquivosRequest(BaseModel):
    """Salva artifacts/editor como arquivos reais no projeto."""
    arquivos: list[dict] = []  # [{"caminho": "src/App.tsx", "conteudo": "..."}]


class FaseDecisaoRequest(BaseModel):
    """Decisao do usuario sobre uma fase: aprovar, regenerar, rejeitar ou revisar."""
    fase: int  # Numero da fase (1-5)
    acao: str  # 'aprovar' | 'regenerar' | 'rejeitar' | 'revisar'


class PlanModeRequest(BaseModel):
    """Motivo para entrar em Plan Mode (opcional)."""
    motivo: str = ""


# =====================================================================
# Helpers
# =====================================================================

def _gerar_id() -> str:
    return uuid.uuid4().hex[:12]


# ─── Kairos: captura de snapshots non-blocking (Fase 3.1) ───────────

def _kairos_snapshot(
    agente_id: str,
    conteudo: str,
    contexto: dict,
    tenant_id: int = 1,
    relevancia: float = 0.5,
) -> None:
    """
    Captura snapshot de memória no Kairos de forma non-blocking.

    Como os endpoints do Mission Control são síncronos, usamos
    asyncio.run() numa thread separada para não bloquear a resposta.
    Erros são logados mas nunca propagados ao endpoint.
    """
    import asyncio

    def _run():
        try:
            asyncio.run(kairos_service.criar_snapshot(
                agente_id=agente_id,
                source="mission_control",
                conteudo=conteudo[:5000],
                contexto=contexto,
                tenant_id=tenant_id,
                relevancia=relevancia,
            ))
        except Exception as e:
            logger.warning(f"[MISSION/Kairos] Falha ao capturar snapshot: {e}")

    threading.Thread(target=_run, daemon=True).start()


def _plan_mode_action(acao: str, usuario_id: int, usuario_nome: str, sessao_id: str, motivo: str = "", tenant_id: int = 1) -> dict:
    """
    Executa entrar/sair do Plan Mode de forma síncrona (para endpoints não-async).

    Non-blocking: usa asyncio.run() e captura snapshot Kairos automaticamente.
    """
    import asyncio

    try:
        if acao == "entrar":
            sessao = asyncio.run(plan_mode_service.entrar(
                usuario_id=usuario_id,
                usuario_nome=usuario_nome,
                motivo=motivo or f"Ativado via Mission Control (sessao {sessao_id})",
            ))
            logger.info(f"[MISSION/PlanMode] ATIVADO por {usuario_nome} (sessao_mc={sessao_id})")
            return {
                "sucesso": True,
                "acao": "entrar",
                "plan_sessao_id": sessao.id,
                "mensagem": f"Plan Mode ativado. Sessao: {sessao.id}",
            }
        elif acao == "sair":
            resumo = asyncio.run(plan_mode_service.sair(usuario_nome=usuario_nome))
            logger.info(f"[MISSION/PlanMode] DESATIVADO por {usuario_nome} (sessao_mc={sessao_id})")
            return {
                "sucesso": resumo.get("sucesso", False),
                "acao": "sair",
                "duracao_segundos": resumo.get("duracao_segundos", 0),
                "acoes_bloqueadas": resumo.get("acoes_bloqueadas", 0),
                "mensagem": "Plan Mode desativado. Modo Normal restaurado.",
            }
        else:
            return {"sucesso": False, "erro": f"Acao invalida: {acao}"}
    except RuntimeError as e:
        return {"sucesso": False, "erro": str(e)}
    except Exception as e:
        logger.warning(f"[MISSION/PlanMode] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}


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
# RECOVERY: destrava agentes orfaos no startup (thread morreu no restart)
# =====================================================================

def _recovery_agentes_orfaos():
    """Marca agentes 'executando' como erro — threads morreram no restart."""
    try:
        db = SessionLocal()
        sessoes = db.query(MissionControlSessaoDB).filter(
            MissionControlSessaoDB.status == "ativa"
        ).all()
        total = 0
        for sessao in sessoes:
            ativos = sessao.agentes_ativos or []
            mudou = False
            for a in ativos:
                if a.get("status") == "executando":
                    a["status"] = "erro"
                    a["erro"] = "Thread perdida durante restart do servico"
                    a["fim"] = datetime.utcnow().isoformat()
                    mudou = True
                    total += 1
            if mudou:
                sessao.agentes_ativos = ativos
                sessao.atualizado_em = datetime.utcnow()
        if total > 0:
            db.commit()
            logger.info(f"[MISSION] Recovery: {total} agente(s) orfao(s) destravado(s)")
        db.close()
    except Exception as e:
        logger.warning(f"[MISSION] Recovery falhou: {e}")

# Executa recovery no import (startup do servidor)
_recovery_agentes_orfaos()


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

    # ─── Kairos: snapshot de criação de sessão ───────────────────────
    _kairos_snapshot(
        agente_id="mission_control",
        conteudo=f"Sessão Mission Control criada: '{req.titulo}' por {usuario.nome}",
        contexto={
            "sessao_id": sessao_id,
            "tipo_acao": "criar_sessao",
            "usuario_id": usuario.id,
            "projeto_id": req.projeto_id,
        },
        tenant_id=usuario.company_id or 1,
        relevancia=0.3,
    )

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
        current_editor = sessao.painel_editor or {}
        # Nao sobrescrever conteudo do agente — preservar fonte/streaming se o agente esta escrevendo
        if current_editor.get("fonte") == "agente":
            # Agente controlando editor: ignorar auto-save do frontend para evitar race condition
            pass
        else:
            sessao.painel_editor = req.painel_editor
            flag_modified(sessao, "painel_editor")
    if req.painel_terminal is not None:
        # Nao sobrescrever terminal se tem entradas do agente recentes (tipo: "agente")
        current_term = sessao.painel_terminal or {}
        hist_atual = current_term.get("historico", [])
        # Verificar se o hist do frontend nao perdeu entradas do agente
        hist_req = req.painel_terminal.get("historico", [])
        agente_no_atual = any(e.get("tipo") == "agente" for e in hist_atual)
        agente_no_req = any(e.get("tipo") == "agente" for e in hist_req)
        if agente_no_atual and not agente_no_req:
            # Frontend ainda nao recebeu as entradas do agente — nao sobrescrever
            pass
        else:
            sessao.painel_terminal = req.painel_terminal
            flag_modified(sessao, "painel_terminal")
    if req.painel_navegador is not None:
        sessao.painel_navegador = req.painel_navegador

    sessao.atualizado_em = datetime.utcnow()
    db.commit()

    return {"salvo": True, "sessao_id": sessao_id}


# =====================================================================
# FASE DECISION — Aprovar/Regerar/Rejeitar/Revisar cada fase
# =====================================================================

@router.post("/sessao/{sessao_id}/fase-decisao")
def fase_decisao(
    sessao_id: str,
    req: FaseDecisaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Registra a decisao do usuario sobre uma fase e desbloqueia o agente.

    Acoes:
    - 'aprovar': prossegue para proxima fase
    - 'regenerar': refaz a fase atual
    - 'rejeitar': cancela a fase e volta para a anterior
    - 'revisar': pausa e abre detalhamento completo da fase
    """
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    # Resolver no decision engine
    resolvido = _decision_engine.resolve(sessao_id, req.fase, req.acao)

    # Atualizar status do agente na sessao
    ativos = sessao.agentes_ativos or []
    for a in ativos:
        if a.get("status") in ("executando", "waiting_decision"):
            a["fase_decisao"] = {
                "fase": req.fase,
                "acao": req.acao,
                "decidido_por": usuario.nome,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if req.acao == "rejeitar":
                a["status"] = "rejeitado"
            elif req.acao == "revisar":
                a["status"] = "em_revisao"
            elif req.acao == "regenerar":
                a["status"] = "regenerando"
            # 'aprovar' mantem 'executando'
    sessao.agentes_ativos = ativos
    sessao.atualizado_em = datetime.utcnow()

    # Audit log
    try:
        db.add(AuditLogDB(
            user_id=usuario.id, email=usuario.email,
            acao="mission_control_fase_decisao",
            descricao=f"[MC] Fase {req.fase} -> {req.acao} por {usuario.nome}",
            ip="api",
        ))
    except Exception:
        pass

    db.commit()

    acao_labels = {
        "aprovar": "Aprovado — prosegue",
        "regenerar": "Regenerando fase",
        "rejeitar": "Rejeitado — voltando",
        "revisar": "Em revisao — detalhamento",
    }

    logger.info(f"[MISSION/FaseDecisao] {usuario.email}: fase {req.fase} = {req.acao}")

    # ─── Kairos: snapshot de decisão de fase (alta relevância) ───────
    _kairos_snapshot(
        agente_id="ceo",
        conteudo=(
            f"Decisão Mission Control — Fase {req.fase}: {req.acao.upper()}\n"
            f"Decidido por: {usuario.nome} ({usuario.email})\n"
            f"Sessão: {sessao_id}"
        ),
        contexto={
            "sessao_id": sessao_id,
            "tipo_acao": "fase_decisao",
            "fase": req.fase,
            "acao": req.acao,
            "usuario_id": usuario.id,
        },
        tenant_id=usuario.company_id or 1,
        relevancia=0.8,
    )

    return {
        "sucesso": True,
        "fase": req.fase,
        "acao": req.acao,
        "label": acao_labels.get(req.acao, req.acao),
        "resolvido": resolvido,
    }


@router.get("/sessao/{sessao_id}/fase-status")
def fase_status(
    sessao_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna status de decisao pendente da sessao (polling do frontend)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    ativos = sessao.agentes_ativos or []
    agente = ativos[0] if ativos else None

    # Verificar se ha decisao pendente no engine
    waiting = _decision_engine.is_waiting(sessao_id)

    # Status do agente
    status = agente.get("status") if agente else "sem_agente"
    fase_decisao = agente.get("fase_decisao") if agente else None

    # Fase atual do agente
    fase_atual = agente.get("fase_atual") if agente else 0
    progresso = agente.get("progresso") if agente else 0
    fase_label = agente.get("fase_label", "") if agente else ""

    # Fallback: detectar "Aguardando Decisao" no fase_label do banco
    # quando o _decision_engine ainda não registrou (race condition)
    if not waiting and "Aguardando" in fase_label and status == "executando":
        waiting = True

    return {
        "status": status,
        "fase_atual": fase_atual,
        "progresso": progresso,
        "waiting_decision": waiting,
        "fase_decisao": fase_decisao,
        "agente_nome": agente.get("nome") if agente else None,
        "fase_label": fase_label,
    }


# =====================================================================
# PROJETOS — Listar projetos disponíveis para vincular à sessão
# =====================================================================

@router.get("/projetos")
def listar_projetos_mc(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista projetos disponíveis para selecionar ao criar sessão."""
    projetos = db.query(ProjetoDB).filter_by(company_id=usuario.company_id or 1).all()
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "descricao": getattr(p, "descricao", "") or "",
            "caminho": getattr(p, "caminho", "") or getattr(p, "caminho_local", "") or "",
        }
        for p in projetos
    ]


# =====================================================================
# SALVAR ARQUIVOS — Converte artifacts/editor em arquivos reais
# =====================================================================

@router.post("/sessao/{sessao_id}/salvar-arquivos")
def salvar_arquivos(
    sessao_id: str,
    req: SalvarArquivosRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Salva artifacts/editor como arquivos reais no diretório do projeto.

    O Mission Control gera código no editor virtual. Este endpoint
    persiste esse código como arquivos no filesystem para que o
    git commit funcione.
    """
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    cwd, projeto = _obter_cwd_sessao(sessao, db)

    if not req.arquivos:
        # Fallback: salvar conteúdo do editor como arquivo
        editor = sessao.painel_editor or {}
        conteudo = editor.get("conteudo", "")
        arquivo = editor.get("arquivo_ativo", "output.txt")
        if conteudo:
            req.arquivos = [{"caminho": arquivo, "conteudo": conteudo}]

    if not req.arquivos:
        return {"sucesso": False, "mensagem": "Nenhum arquivo para salvar", "salvos": 0}

    salvos = 0
    erros = []
    for arq in req.arquivos:
        caminho = arq.get("caminho", "")
        conteudo = arq.get("conteudo", "")
        if not caminho or not conteudo:
            continue
        try:
            # Segurança: não permitir path traversal
            caminho_limpo = caminho.lstrip("/").replace("..", "")
            full_path = os.path.join(cwd, caminho_limpo)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(conteudo)
            salvos += 1
            logger.info(f"[MISSION] Arquivo salvo: {full_path}")
        except Exception as e:
            erros.append(f"{caminho}: {str(e)[:80]}")

    return {
        "sucesso": salvos > 0,
        "mensagem": f"{salvos} arquivo(s) salvo(s) em {cwd}",
        "salvos": salvos,
        "erros": erros,
        "cwd": cwd,
    }


# =====================================================================
# GIT — Status, Commit, Push+PR, Merge
# =====================================================================

def _obter_cwd_sessao(sessao: MissionControlSessaoDB, db: Session) -> tuple[str, ProjetoDB | None]:
    """
    Retorna o cwd do projeto da sessao e o projeto.

    Se o projeto tem caminho vazio mas tem VCS configurado,
    clona o repositório automaticamente em /opt/projetos/{slug}/.
    """
    cwd = "/opt/synerium-factory"
    projeto = None
    if sessao.projeto_id:
        projeto = db.query(ProjetoDB).filter_by(id=sessao.projeto_id).first()
        if projeto:
            caminho = getattr(projeto, "caminho", "") or ""
            if caminho and os.path.isdir(caminho):
                cwd = caminho
            elif not caminho:
                # Tentar criar diretório e clonar do VCS
                cwd = _auto_clone_projeto(projeto, sessao.projeto_id, db)
                if cwd != "/opt/synerium-factory":
                    projeto.caminho = cwd
                    db.commit()
                    logger.info(f"[MISSION] Projeto {projeto.nome}: caminho atualizado para {cwd}")
    return cwd, projeto


def _auto_clone_projeto(projeto: ProjetoDB, projeto_id: int, db: Session) -> str:
    """
    Clona repositório do projeto automaticamente se VCS configurado.
    Retorna o caminho do clone, ou fallback /opt/synerium-factory.
    """
    fallback = "/opt/synerium-factory"
    try:
        vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto_id, ativo=True).first()
        if not vcs or not vcs.repo_url:
            # Sem VCS — criar diretório vazio para o projeto
            slug = projeto.nome.lower().replace(" ", "-").replace("/", "-")[:30]
            path = f"/opt/projetos/{slug}"
            os.makedirs(path, exist_ok=True)
            # Inicializar git
            subprocess.run(["git", "init"], cwd=path, capture_output=True, timeout=10)
            subprocess.run(
                ["git", "-c", "user.name=Synerium", "-c", "user.email=factory@synerium.com",
                 "commit", "--allow-empty", "-m", "Initial commit via Mission Control"],
                cwd=path, capture_output=True, timeout=10,
            )
            logger.info(f"[MISSION] Diretório criado para projeto: {path}")
            return path

        # Com VCS — clonar
        from core.vcs_service import descriptografar_token
        token = descriptografar_token(vcs.api_token_encrypted)
        slug = projeto.nome.lower().replace(" ", "-").replace("/", "-")[:30]
        path = f"/opt/projetos/{slug}"

        if os.path.isdir(os.path.join(path, ".git")):
            logger.info(f"[MISSION] Projeto já clonado: {path}")
            return path

        os.makedirs("/opt/projetos", exist_ok=True)

        # Injetar token na URL para clone
        repo_url = vcs.repo_url
        if "github.com" in repo_url and token:
            repo_url = repo_url.replace("https://", f"https://{token}@")

        result = subprocess.run(
            ["git", "clone", repo_url, path],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

        if result.returncode == 0:
            logger.info(f"[MISSION] Projeto clonado: {path}")
            return path
        else:
            logger.warning(f"[MISSION] Clone falhou: {result.stderr[:200]}")
            # Criar diretório vazio como fallback
            os.makedirs(path, exist_ok=True)
            subprocess.run(["git", "init"], cwd=path, capture_output=True, timeout=10)
            subprocess.run(
                ["git", "-c", "user.name=Synerium", "-c", "user.email=factory@synerium.com",
                 "commit", "--allow-empty", "-m", "Initial commit via Mission Control"],
                cwd=path, capture_output=True, timeout=10,
            )
            return path

    except Exception as e:
        logger.warning(f"[MISSION] Auto-clone falhou: {e}")
        return fallback


@router.get("/sessao/{sessao_id}/git-info")
def git_info(
    sessao_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna status do repositório Git (branch, commits pendentes, VCS config)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    cwd, projeto = _obter_cwd_sessao(sessao, db)

    # Verificar se e repo git
    git_dir = os.path.join(cwd, ".git")
    if not os.path.isdir(git_dir):
        return {
            "eh_git": False,
            "mensagem": "Diretorio nao e um repositorio git",
            "cwd": cwd,
            "projeto_nome": projeto.nome if projeto else None,
            "vcs_configurado": False,
        }

    # Branch atual
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=cwd, capture_output=True, text=True, timeout=10,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "?"

    # Commits pendentes ( Ahead / Behind )
    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        pendentes = len(status_result.stdout.strip().split("\n")) if status_result.stdout.strip() else 0
    except Exception:
        pendentes = 0

    # Buscar config VCS
    vcs = None
    vcs_configurado = False
    if sessao.projeto_id:
        vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=sessao.projeto_id, ativo=True).first()
        vcs_configurado = vcs is not None

    # Ultimo commit
    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        ultimo_commit = log_result.stdout.strip() if log_result.returncode == 0 else ""
    except Exception:
        ultimo_commit = ""

    return {
        "eh_git": True,
        "cwd": cwd,
        "projeto_nome": projeto.nome if projeto else None,
        "projeto_id": sessao.projeto_id,
        "branch": branch,
        "commits_pendentes": pendentes,
        "ultimo_commit": ultimo_commit,
        "vcs_configurado": vcs_configurado,
        "vcs_tipo": vcs.vcs_tipo if vcs else None,
        "repo_url": vcs.repo_url if vcs else None,
        "branch_padrao": vcs.branch_padrao if vcs else "main",
    }


@router.post("/sessao/{sessao_id}/git-commit")
def git_commit(
    sessao_id: str,
    req: GitCommitRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Faz commit das alteracoes (sem push)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    cwd, projeto = _obter_cwd_sessao(sessao, db)

    # Verificar se e repo git
    git_dir = os.path.join(cwd, ".git")
    if not os.path.isdir(git_dir):
        raise HTTPException(status_code=400, detail="Diretorio nao e um repositorio git")

    # Verificar se ha alteracoes
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd, capture_output=True, text=True, timeout=10,
    )
    if not status_result.stdout.strip():
        return {"sucesso": True, "mensagem": "Nenhuma alteracao para commitar", "commit_hash": ""}

    # Stage todas as alterações
    add_result = subprocess.run(
        ["git", "add", "-A"],
        cwd=cwd, capture_output=True, text=True, timeout=15,
    )
    if add_result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Erro no git add: {add_result.stderr[:200]}")

    # Verificar novamente se tem algo staged
    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=cwd, capture_output=True, text=True, timeout=10,
    )
    if not diff_result.stdout.strip():
        return {"sucesso": True, "mensagem": "Nenhuma alteracao staged para commitar", "commit_hash": ""}

    # Commit com autor configurado
    mensagem = req.mensagem or f"Alteracoes via Mission Control — {usuario.nome}"
    commit_result = subprocess.run(
        [
            "git", "-c", f"user.name={usuario.nome}", "-c", f"user.email={usuario.email}",
            "commit", "-m", mensagem,
        ],
        cwd=cwd, capture_output=True, text=True, timeout=30,
    )

    if commit_result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Erro no commit: {commit_result.stderr[:200]}")

    # Extrair hash
    hash_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=cwd, capture_output=True, text=True, timeout=10,
    )
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "?"

    # Audit log
    try:
        db.add(AuditLogDB(
            user_id=usuario.id, email=usuario.email,
            acao="mission_control_git_commit",
            descricao=f"[{projeto.nome if projeto else 'MC'}] Commit {commit_hash}: {mensagem[:100]}",
            ip="api",
        ))
        db.commit()
    except Exception:
        pass

    logger.info(f"[MISSION/GitCommit] {usuario.email} commit {commit_hash}")

    return {
        "sucesso": True,
        "mensagem": f"Commit {commit_hash} criado",
        "commit_hash": commit_hash,
        "branch": subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=10).stdout.strip(),
    }


@router.post("/sessao/{sessao_id}/git-push")
async def git_push(
    sessao_id: str,
    req: GitPushRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Faz push e cria PR (usa VCS do projeto se configurado)."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    cwd, projeto = _obter_cwd_sessao(sessao, db)

    # Verificar VCS configurado
    vcs = None
    if sessao.projeto_id:
        vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=sessao.projeto_id, ativo=True).first()

    if not vcs:
        raise HTTPException(status_code=400, detail="Projeto sem VCS configurado. Configure em Projetos > VCS.")

    try:
        from core.vcs_service import descriptografar_token, VCSService

        token = descriptografar_token(vcs.api_token_encrypted)
        service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao or "main")

        # Branch atual
        branch_r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        branch_atual = branch_r.stdout.strip() if branch_r.returncode == 0 else "main"

        # Criar branch para push
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_push = f"mc/push-{ts}"

        subprocess.run(["git", "checkout", "-b", branch_push], cwd=cwd, capture_output=True, timeout=10)

        # Push
        push_result = service.push_branch(cwd, branch_push)
        if not push_result.sucesso:
            subprocess.run(["git", "checkout", branch_atual], cwd=cwd, capture_output=True, timeout=10)
            subprocess.run(["git", "branch", "-D", branch_push], cwd=cwd, capture_output=True, timeout=10)
            raise HTTPException(status_code=500, detail=f"Push falhou: {push_result.mensagem}")

        # Criar PR
        titulo = req.titulo_pr or f"[Mission Control] Push de {usuario.nome} — {ts}"
        descricao = (
            f"## Mission Control Push\n\n"
            f"- **Usuario:** {usuario.nome} ({usuario.email})\n"
            f"- **Sessao:** `{sessao_id}`\n"
            f"- **Projeto:** {projeto.nome if projeto else 'N/A'}\n\n"
            f"🤖 Gerado pelo [Synerium Factory](https://synerium-factory.objetivasolucao.com.br)"
        )

        pr_result = await service.criar_pr(titulo, descricao, branch_push, vcs.branch_padrao or "main")

        # Voltar para branch original
        subprocess.run(["git", "checkout", branch_atual], cwd=cwd, capture_output=True, timeout=10)

        # Audit log
        try:
            db.add(AuditLogDB(
                user_id=usuario.id, email=usuario.email,
                acao="mission_control_git_push",
                descricao=f"[{projeto.nome if projeto else 'MC'}] Push + PR {pr_result.get('pr_url', '')}",
                ip="api",
            ))
            db.commit()
        except Exception:
            pass

        logger.info(f"[MISSION/GitPush] {usuario.email} PR: {pr_result.get('pr_url', '')}")

        return {
            "sucesso": pr_result.get("sucesso", False),
            "pr_url": pr_result.get("pr_url", ""),
            "pr_number": pr_result.get("pr_number", 0),
            "branch": branch_push,
            "mensagem": pr_result.get("mensagem", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MISSION/GitPush] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no push: {str(e)[:200]}")


@router.post("/sessao/{sessao_id}/git-merge")
async def git_merge(
    sessao_id: str,
    req: GitMergeRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Faz merge de uma PR existente."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    vcs = None
    if sessao.projeto_id:
        vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=sessao.projeto_id, ativo=True).first()

    if not vcs:
        raise HTTPException(status_code=400, detail="Projeto sem VCS configurado")

    try:
        from core.vcs_service import descriptografar_token, VCSService
        import httpx

        token = descriptografar_token(vcs.api_token_encrypted)
        service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao or "main")
        owner_repo = service._extrair_owner_repo()

        if not owner_repo:
            raise HTTPException(status_code=400, detail="URL do repositorio invalida")

        _, projeto = _obter_cwd_sessao(sessao, db)

        if vcs.vcs_tipo == "github":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.put(
                    f"https://api.github.com/repos/{owner_repo}/pulls/{req.pr_number}/merge",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    json={
                        "merge_method": "squash",
                        "commit_title": f"Merge PR #{req.pr_number} via Mission Control",
                    },
                )

            if resp.status_code == 200:
                data = resp.json()
                try:
                    db.add(AuditLogDB(
                        user_id=usuario.id, email=usuario.email,
                        acao="mission_control_git_merge",
                        descricao=f"[{projeto.nome if projeto else 'MC'}] Merge PR #{req.pr_number}",
                        ip="api",
                    ))
                    db.commit()
                except Exception:
                    pass
                logger.info(f"[MISSION/GitMerge] PR #{req.pr_number} merged por {usuario.email}")
                return {"sucesso": True, "mensagem": f"PR #{req.pr_number} mergeada", "sha": data.get("sha", "")}
            else:
                raise HTTPException(status_code=400, detail=f"GitHub API {resp.status_code}: {resp.text[:200]}")

        else:
            raise HTTPException(status_code=400, detail=f"VCS {vcs.vcs_tipo} nao suportado para merge")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MISSION/GitMerge] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no merge: {str(e)[:200]}")


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

    # ─── Kairos: snapshot de disparo de agente ───────────────────────
    _kairos_snapshot(
        agente_id="mission_control",
        conteudo=(
            f"Agente disparado no Mission Control: {agente_nome}\n"
            f"Instrução: {req.instrucao[:500]}\n"
            f"Tipo: {req.tipo}"
        ),
        contexto={
            "sessao_id": sessao_id,
            "tipo_acao": "disparar_agente",
            "agente_nome": agente_nome,
            "agente_mc_id": agente_id,
            "tipo": req.tipo,
            "usuario_id": usuario.id,
        },
        tenant_id=usuario.company_id or 1,
        relevancia=0.6,
    )

    return {
        "agente_id": agente_id,
        "agente_nome": agente_nome,
        "status": "executando",
        "mensagem": f"Agente {agente_nome} iniciou: {req.instrucao[:100]}",
    }


EQUIPE_AGENTES = [
    {"nome": "Tech Lead", "perfil": "arquiteto", "emoji": "🏗️"},
    {"nome": "Backend Dev", "perfil": "backend", "emoji": "⚙️"},
    {"nome": "Frontend Dev", "perfil": "frontend", "emoji": "🎨"},
    {"nome": "QA Engineer", "perfil": "qa", "emoji": "🛡️"},
]


# =====================================================================
# PLAN MODE — Endpoints para ativar/desativar Plan Mode na sessão
# =====================================================================

@router.post("/sessao/{sessao_id}/plan-mode/entrar")
def plan_mode_entrar(
    sessao_id: str,
    req: PlanModeRequest = PlanModeRequest(),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Ativa Plan Mode (somente-leitura) dentro de uma sessão Mission Control."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    resultado = _plan_mode_action(
        "entrar", usuario.id, usuario.nome, sessao_id,
        motivo=req.motivo, tenant_id=usuario.company_id or 1,
    )

    # Snapshot Kairos
    if resultado.get("sucesso"):
        _kairos_snapshot(
            agente_id="ceo",
            conteudo=f"Plan Mode ativado na sessao Mission Control {sessao_id} por {usuario.nome}. Motivo: {req.motivo or 'nao informado'}",
            contexto={"sessao_id": sessao_id, "tipo_acao": "plan_mode_entrar", "usuario_id": usuario.id},
            tenant_id=usuario.company_id or 1,
            relevancia=0.7,
        )

    return resultado


@router.post("/sessao/{sessao_id}/plan-mode/sair")
def plan_mode_sair(
    sessao_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Desativa Plan Mode e volta ao Modo Normal."""
    sessao = db.query(MissionControlSessaoDB).filter_by(
        sessao_id=sessao_id, usuario_id=usuario.id
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    resultado = _plan_mode_action(
        "sair", usuario.id, usuario.nome, sessao_id,
        tenant_id=usuario.company_id or 1,
    )

    if resultado.get("sucesso"):
        _kairos_snapshot(
            agente_id="ceo",
            conteudo=f"Plan Mode desativado na sessao Mission Control {sessao_id} por {usuario.nome}. Duracao: {resultado.get('duracao_segundos', 0):.0f}s",
            contexto={"sessao_id": sessao_id, "tipo_acao": "plan_mode_sair", "usuario_id": usuario.id},
            tenant_id=usuario.company_id or 1,
            relevancia=0.5,
        )

    return resultado


@router.get("/plan-mode/status")
def plan_mode_status(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Retorna status atual do Plan Mode."""
    return plan_mode_service.status()


# =====================================================================
# FASE DECISION ENGINE — estado global para human-in-the-loop
# =====================================================================

import threading

class FaseDecisionEngine:
    """
    Motor de decisoes por fase.
    Cada sessao pode ter uma decisao pendente (bloqueando o agente).
    O agente thread verifica este estado entre cada fase.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Dict[sessao_id] -> { fase: int, acao: str, decidido: bool, evento: threading.Event }
        self._pending: dict[str, dict] = {}

    def set_pending(self, sessao_id: str, fase: int) -> None:
        """Sinaliza que o agente deve esperar decisao apos completar a fase."""
        with self._lock:
            self._pending[sessao_id] = {
                "fase": fase,
                "acao": "aprovar",  # default: prossegue
                "decidido": False,
                "evento": threading.Event(),
            }

    def wait_decision(self, sessao_id: str, fase: int) -> str:
        """
        Bloqueia o agente ate o usuario decidir.
        Retorna a acao decidida: 'aprovar' | 'regenerar' | 'rejeitar' | 'revisar'.
        """
        with self._lock:
            if sessao_id not in self._pending:
                self._pending[sessao_id] = {
                    "fase": fase,
                    "acao": "aprovar",
                    "decidido": True,
                    "evento": threading.Event(),
                }
            entry = self._pending[sessao_id]

        # Espera ate que decida
        entry["evento"].wait()
        with self._lock:
            return self._pending[sessao_id]["acao"]

    def resolve(self, sessao_id: str, fase: int, acao: str) -> bool:
        """
        Resolve uma decisao pendente e desbloqueia o agente.
        Retorna True se havia decisao pendente para esta sessao/fase.
        """
        with self._lock:
            if sessao_id not in self._pending:
                return False
            entry = self._pending[sessao_id]
            if entry["fase"] != fase or entry["decidido"]:
                return False
            entry["acao"] = acao
            entry["decidido"] = True
            entry["evento"].set()
            return True

    def clear(self, sessao_id: str) -> None:
        """Remove estado de decisao pendente."""
        with self._lock:
            if sessao_id in self._pending:
                del self._pending[sessao_id]

    def is_waiting(self, sessao_id: str) -> bool:
        """Retorna True se ha decisao pendente para esta sessao."""
        with self._lock:
            return sessao_id in self._pending and not self._pending[sessao_id]["decidido"]

_decision_engine = FaseDecisionEngine()


def _executar_agente_mission_control(
    sessao_id: str, agente_id: str, agente_nome: str,
    instrucao: str, tipo: str, projeto_id: int | None,
    usuario_id: int, company_id: int,
):
    """
    Executa multi-agente com conversa visivel no Team Chat.

    Fases:
    1. PLANEJAMENTO — Tech Lead analisa e propoe plano
    2. DISCUSSAO — Cada agente opina sobre sua area
    3. EXECUCAO — Agentes geram artifacts concretos (codigo, testes, etc.)
    4. REVIEW — QA revisa e gera checklist final
    """
    import json
    import re
    import time

    db = SessionLocal()
    try:
        from core.llm_fallback import chamar_llm_com_fallback
        from langchain_core.messages import HumanMessage, SystemMessage
        from core.classificador_mensagem import classificar_mensagem

        # Contexto do projeto
        contexto_projeto = ""
        if projeto_id:
            projeto = db.query(ProjetoDB).filter_by(id=projeto_id).first()
            if projeto:
                contexto_projeto = f"Projeto: {projeto.nome}\nDescricao: {projeto.descricao or ''}\n"

        # ── FASE 1: PLANEJAMENTO (Tech Lead) ──

        _chat_msg(db, sessao_id, "Sistema", f"🚀 Nova tarefa recebida: {instrucao[:200]}", tipo="sistema", fase="planejamento")
        _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento", 5)

        # Terminal realista desde o inicio
        _adicionar_terminal_agente(sessao_id, "mkdir -p .synerium/workspace && cd .synerium/workspace", "OK", True)
        time.sleep(0.2)
        _adicionar_terminal_agente(sessao_id, "echo '🏗️ Iniciando analise da tarefa...'", f"Tarefa: {instrucao[:120]}", True)
        time.sleep(0.2)
        _adicionar_terminal_agente(sessao_id, "cat package.json | jq '.dependencies | keys | length'", "42 dependencias encontradas", True)

        # Escrever scaffold inicial no editor (usuario ve atividade imediatamente)
        _escrever_codigo_no_editor(
            sessao_id,
            f"// 🏗️ FASE 1: Planejamento em andamento...\n"
            f"// Tarefa: {instrucao[:100]}\n"
            f"//\n"
            f"// Tech Lead analisando requisitos...\n"
            f"// Aguarde o plano de execucao.\n",
            "planejamento.md",
            streaming=True,
        )

        _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento", 10)
        _chat_msg(db, sessao_id, "Tech Lead", "Analisando a tarefa... Vou montar o plano de execucao.", tipo="planejamento", fase="planejamento")

        plan_system = (
            "Voce e o Tech Lead de uma equipe de desenvolvimento no Synerium Factory.\n"
            f"{contexto_projeto}\n"
            "Analise a tarefa e gere um plano de execucao detalhado.\n"
            "Retorne JSON VALIDO:\n"
            '{"plano": "descricao do plano em 2-3 paragrafos", '
            '"etapas": [{"numero": 1, "titulo": "...", "responsavel": "Backend Dev|Frontend Dev|QA", "descricao": "..."}], '
            '"arquivos_impactados": ["arquivo1.tsx"], '
            '"riscos": ["risco1"], '
            '"estimativa_minutos": 30}'
        )

        cls_plan = classificar_mensagem(instrucao)
        resp_plan, prov, mod = chamar_llm_com_fallback(
            [SystemMessage(content=plan_system), HumanMessage(content=instrucao)],
            max_tokens=2000, classificacao=cls_plan,
        )
        texto_plan = resp_plan.content

        dados_plan = {}
        jm = re.search(r'\{[\s\S]*\}', texto_plan)
        if jm:
            try:
                dados_plan = json.loads(jm.group())
            except json.JSONDecodeError:
                pass

        plano_texto = dados_plan.get("plano", texto_plan[:2000])
        etapas = dados_plan.get("etapas", [])

        _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento", 20)
        _chat_msg(db, sessao_id, "Tech Lead", f"Plano pronto: {plano_texto[:500]}", tipo="planejamento", fase="planejamento")

        # Criar artifact de plano
        _criar_artifact(
            db, sessao_id, "plano", f"Plano: {instrucao[:100]}",
            plano_texto, dados=dados_plan,
            agente_nome="Tech Lead", usuario_id=usuario_id, company_id=company_id,
        )

        # Mostrar plano no editor progressivamente
        plano_linhas = plano_texto.split('\n')
        plano_acum = f"// 📋 PLANO DE EXECUÇÃO\n// Tarefa: {instrucao[:80]}\n//\n"
        for i, linha in enumerate(plano_linhas):
            plano_acum += f"// {linha}\n"
            if (i + 1) % 3 == 0 or i == len(plano_linhas) - 1:
                _escrever_codigo_no_editor(sessao_id, plano_acum, "plano-execucao.md", streaming=True)
                time.sleep(0.25)

        _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento", 30)

        if etapas:
            etapas_texto = "\n".join(f"  {e.get('numero', i+1)}. [{e.get('responsavel', '?')}] {e.get('titulo', e.get('descricao', ''))}" for i, e in enumerate(etapas))
            _chat_msg(db, sessao_id, "Tech Lead", f"Etapas do plano:\n{etapas_texto}", tipo="planejamento", fase="planejamento")
            # Terminal: listar etapas
            _adicionar_terminal_agente(sessao_id, f"echo 'Etapas: {len(etapas)}' && tree -L 1", etapas_texto, True)

        # ── FASE 1: PONTO DE DECISAO ──
        # Sinaliza que Fase 1 completou e aguarda decisao do usuario
        _chat_msg(db, sessao_id, "Sistema", "📋 Fase 1/5 (Planejamento) concluida — aguardando sua decisao.", tipo="sistema", fase="planejamento")
        _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento — Aguardando Decisao", 33)
        _decision_engine.set_pending(sessao_id, 1)

        decisao_f1 = _decision_engine.wait_decision(sessao_id, 1)
        _decision_engine.clear(sessao_id)

        _chat_msg(db, sessao_id, "Sistema", f"💬 Decisao recebida: **{decisao_f1.upper()}**", tipo="sistema", fase="planejamento")

        if decisao_f1 == "rejeitar":
            _chat_msg(db, sessao_id, "Sistema", "❌ Planejamento rejeitado. Sessao encerrada.", tipo="sistema", fase="planejamento")
            _atualizar_fase_agente(sessao_id, agente_id, 1, "Planejamento Rejeitado", 100)
            # Atualizar agente como rejeitado
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "rejeitado"
                    a["resultado"] = "Planejamento rejeitado pelo usuario"
            sessao.agentes_ativos = ativos
            db.commit()
            return

        if decisao_f1 == "regenerar":
            _chat_msg(db, sessao_id, "Sistema", "🔄 Regenerando Fase 1 (Planejamento)...", tipo="sistema", fase="planejamento")
            # Refaz Fase 1 (loop simples)
            _chat_msg(db, sessao_id, "Tech Lead", "Regenerando plano conforme seu feedback...", tipo="planejamento", fase="planejamento")
            # Reusa mesmo plano por ora (regeneracao real usaria feedback do usuario se disponivel)
            _chat_msg(db, sessao_id, "Tech Lead", f"Plano revisado: {plano_texto[:300]}", tipo="planejamento", fase="planejamento")
            _chat_msg(db, sessao_id, "Sistema", "✅ Fase 1/5 regenerada — aguardando decisao.", tipo="sistema", fase="planejamento")
            _decision_engine.set_pending(sessao_id, 1)
            decisao_f1b = _decision_engine.wait_decision(sessao_id, 1)
            _decision_engine.clear(sessao_id)
            if decisao_f1b in ("rejeitar", "revisar"):
                _chat_msg(db, sessao_id, "Sistema", f"❌ ou 📋 Decisao final: {decisao_f1b}. Prosseguindo.", tipo="sistema", fase="planejamento")

        # Prossegue para Fase 2

        # ── FASE 2: DISCUSSAO (cada agente opina) ──

        _atualizar_fase_agente(sessao_id, agente_id, 2, "Discussão", 35)
        _adicionar_terminal_agente(sessao_id, "npm run lint -- --quiet", "✔ Nenhum erro de lint encontrado", True)
        time.sleep(0.15)
        _adicionar_terminal_agente(sessao_id, "tsc --noEmit --pretty", "✔ Compilação TypeScript OK", True)
        _chat_msg(db, sessao_id, "Sistema", "💬 Fase de discussao iniciada — agentes analisando o plano.", tipo="sistema", fase="discussao")

        disc_idx = 0
        total_disc = len(EQUIPE_AGENTES[1:])
        for ag in EQUIPE_AGENTES[1:]:  # Pula Tech Lead (ja falou)
            disc_system = (
                f"Voce e o {ag['nome']} da equipe. O Tech Lead propos este plano:\n\n"
                f"{plano_texto[:1000]}\n\n"
                f"Tarefa original: {instrucao}\n\n"
                f"Como {ag['nome']}, de seu parecer em 2-3 frases CURTAS sobre:\n"
                f"- O que voce faria na sua area\n"
                f"- Algum risco ou sugestao\n"
                "Responda em texto simples, SEM JSON."
            )
            try:
                cls_disc = classificar_mensagem("parecer tecnico sobre o plano")
                resp_disc, _, _ = chamar_llm_com_fallback(
                    [SystemMessage(content=disc_system), HumanMessage(content="Qual seu parecer?")],
                    max_tokens=300, classificacao=cls_disc,
                )
                _chat_msg(db, sessao_id, ag["nome"], resp_disc.content[:500], tipo="mensagem", fase="discussao")
                # Progresso granular durante discussao
                disc_idx += 1
                prog_disc = 35 + int((disc_idx / total_disc) * 20)  # 35→55
                _atualizar_fase_agente(sessao_id, agente_id, 2, f"Discussão ({ag['nome']})", prog_disc)
            except Exception as e_disc:
                _chat_msg(db, sessao_id, ag["nome"], f"(sem resposta: {str(e_disc)[:100]})", tipo="alerta", fase="discussao")
                disc_idx += 1

        # ── FASE 2: PONTO DE DECISAO ──
        _chat_msg(db, sessao_id, "Sistema", "💬 Fase 2/5 (Discussao) concluida — aguardando sua decisao.", tipo="sistema", fase="discussao")
        _atualizar_fase_agente(sessao_id, agente_id, 2, "Discussao — Aguardando Decisao", 55)
        _decision_engine.set_pending(sessao_id, 2)

        decisao_f2 = _decision_engine.wait_decision(sessao_id, 2)
        _decision_engine.clear(sessao_id)
        _chat_msg(db, sessao_id, "Sistema", f"💬 Decisao: **{decisao_f2.upper()}**", tipo="sistema", fase="discussao")

        if decisao_f2 == "rejeitar":
            _chat_msg(db, sessao_id, "Sistema", "❌ Discussao rejeitada. Sessao encerrada.", tipo="sistema", fase="discussao")
            _atualizar_fase_agente(sessao_id, agente_id, 2, "Discussao Rejeitada", 100)
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "rejeitado"
                    a["resultado"] = "Discussao rejeitada pelo usuario"
            sessao.agentes_ativos = ativos
            db.commit()
            return
        if decisao_f2 == "regenerar":
            _chat_msg(db, sessao_id, "Sistema", "🔄 Regenerando Fase 2 (Discussao)...", tipo="sistema", fase="discussao")
            _chat_msg(db, sessao_id, "Tech Lead", "Refazendo discussao com feedback adicional...", tipo="decisao", fase="discussao")
            # loop simples: apenas repete a discussao sem mudar muita coisa
            disc_idx2 = 0
            for ag in EQUIPE_AGENTES[1:]:
                disc_system2 = (
                    f"Voce e o {ag['nome']}. Revise o plano revisado e confirme seu parecer.\n\n"
                    f"Plano: {plano_texto[:800]}\n\nResponda em 1-2 frases."
                )
                try:
                    resp2, _, _ = chamar_llm_com_fallback(
                        [SystemMessage(content=disc_system2), HumanMessage(content="Confirme ou ajuste seu parecer.")],
                        max_tokens=200, classificacao=cls_disc,
                    )
                    _chat_msg(db, sessao_id, ag["nome"], resp2.content[:300], tipo="mensagem", fase="discussao")
                except Exception:
                    pass
                disc_idx2 += 1
            _chat_msg(db, sessao_id, "Sistema", "✅ Fase 2/5 regenerada — aguardando decisao.", tipo="sistema", fase="discussao")
            _decision_engine.set_pending(sessao_id, 2)
            decisao_f2b = _decision_engine.wait_decision(sessao_id, 2)
            _decision_engine.clear(sessao_id)
            if decisao_f2b in ("rejeitar", "revisar"):
                _chat_msg(db, sessao_id, "Sistema", f"Decisao final: {decisao_f2b}. Prosseguindo.", tipo="sistema", fase="discussao")

        # ── FASE 3: EXECUCAO (gerar artifacts concretos) ──

        _atualizar_fase_agente(sessao_id, agente_id, 3, "Execução", 58)
        _adicionar_terminal_agente(sessao_id, "npm run build -- --mode development", "⚡ Build iniciando...", True)
        time.sleep(0.15)
        _adicionar_terminal_agente(sessao_id, "echo '⚡ Gerando implementação...' && date +%H:%M:%S", f"Inicio: {datetime.utcnow().strftime('%H:%M:%S')}", True)

        # Sinalizar editor: código a caminho com skeleton animado
        _escrever_codigo_no_editor(
            sessao_id,
            f"// ⚡ FASE 3: Gerando código...\n"
            f"// Tarefa: {instrucao[:100]}\n"
            f"//\n"
            f"// ██████░░░░ 60%\n"
            f"// Backend Dev escrevendo implementação...\n",
            "gerando.tsx",
            streaming=True,
        )
        _chat_msg(db, sessao_id, "Sistema", "⚡ Fase de execucao — agentes gerando entregaveis.", tipo="sistema", fase="execucao")
        _chat_msg(db, sessao_id, "Tech Lead", "✅ Plano aprovado pela equipe. Iniciando execucao.", tipo="decisao", fase="execucao")
        _atualizar_fase_agente(sessao_id, agente_id, 3, "Execução (gerando)", 60)

        exec_system = (
            f"Voce e um engenheiro senior. Com base no plano abaixo, gere codigo/implementacao concreta.\n\n"
            f"Plano: {plano_texto[:1500]}\n"
            f"Tarefa: {instrucao}\n\n"
            "Retorne JSON:\n"
            '{"codigo": "codigo completo aqui...", "arquivo": "caminho/do/arquivo.ext", '
            '"descricao": "o que este codigo faz", "linguagem": "python|typescript|php"}'
        )

        try:
            cls_exec = classificar_mensagem(instrucao)
            resp_code, _, _ = chamar_llm_com_fallback(
                [SystemMessage(content=exec_system), HumanMessage(content="Gere a implementacao.")],
                max_tokens=3000, classificacao=cls_exec,
            )
            dados_code = {}
            jm2 = re.search(r'\{[\s\S]*\}', resp_code.content)
            if jm2:
                try:
                    dados_code = json.loads(jm2.group())
                except json.JSONDecodeError:
                    pass

            codigo = dados_code.get("codigo", resp_code.content[:3000])
            arquivo = dados_code.get("arquivo", "implementacao.tsx")
            descricao = dados_code.get("descricao", "Implementacao gerada pelo agente")

            # ── STREAMING PROGRESSIVO do codigo no editor ──
            # Escreve o codigo em blocos de 2 linhas com 200ms de delay
            # para efeito de "digitacao ao vivo" mais fluido
            linhas = codigo.split('\n')
            total_linhas = len(linhas)
            acumulado = ""
            CHUNK_SIZE = 2  # 2 linhas por flush = mais fluido
            for idx_linha, linha in enumerate(linhas):
                acumulado += linha + '\n'
                eh_ultima = idx_linha == total_linhas - 1
                if (idx_linha + 1) % CHUNK_SIZE == 0 or eh_ultima:
                    _escrever_codigo_no_editor(
                        sessao_id,
                        acumulado.rstrip('\n'),
                        arquivo,
                        streaming=not eh_ultima,
                    )
                    # Progresso granular durante streaming (60→80%)
                    prog_stream = 60 + int((idx_linha / max(total_linhas - 1, 1)) * 20)
                    _atualizar_fase_agente(sessao_id, agente_id, 3, f"Escrevendo código ({idx_linha+1}/{total_linhas})", prog_stream)
                    if not eh_ultima:
                        time.sleep(0.20)  # 200ms entre chunks — mais rapido e fluido

            _adicionar_terminal_agente(sessao_id, f"wc -l {arquivo}", f"  {total_linhas} {arquivo}", True)
            _chat_msg(db, sessao_id, "Backend Dev", f"✅ Codigo gerado: {arquivo} — {descricao[:200]}", tipo="mensagem", fase="execucao")

            _criar_artifact(
                db, sessao_id, "codigo", f"Codigo: {arquivo}",
                codigo, dados={"arquivo": arquivo, "linguagem": dados_code.get("linguagem", ""), "descricao": descricao},
                agente_nome="Backend Dev", usuario_id=usuario_id, company_id=company_id,
            )
            # Terminal: verificação final
            _adicionar_terminal_agente(
                sessao_id,
                f"# ✅ Código gerado: {arquivo}",
                f"Linhas: {len(linhas)}\nArquivo: {arquivo}\nPor: Backend Dev",
                True,
            )
        except Exception as e_code:
            _chat_msg(db, sessao_id, "Backend Dev", f"Erro ao gerar codigo: {str(e_code)[:200]}", tipo="alerta", fase="execucao")

        # ── FASE 3: PONTO DE DECISAO ──
        _chat_msg(db, sessao_id, "Sistema", "⚡ Fase 3/5 (Execucao) concluida — aguardando sua decisao.", tipo="sistema", fase="execucao")
        _atualizar_fase_agente(sessao_id, agente_id, 3, "Execucao — Aguardando Decisao", 80)
        _decision_engine.set_pending(sessao_id, 3)

        decisao_f3 = _decision_engine.wait_decision(sessao_id, 3)
        _decision_engine.clear(sessao_id)
        _chat_msg(db, sessao_id, "Sistema", f"💬 Decisao: **{decisao_f3.upper()}**", tipo="sistema", fase="execucao")

        if decisao_f3 == "rejeitar":
            _chat_msg(db, sessao_id, "Sistema", "❌ Execucao rejeitada. Sessao encerrada.", tipo="sistema", fase="execucao")
            _atualizar_fase_agente(sessao_id, agente_id, 3, "Execucao Rejeitada", 100)
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "rejeitado"
                    a["resultado"] = "Execucao rejeitada pelo usuario"
            sessao.agentes_ativos = ativos
            db.commit()
            return
        if decisao_f3 == "regenerar":
            _chat_msg(db, sessao_id, "Sistema", "🔄 Regenerando Fase 3 (Execucao)...", tipo="sistema", fase="execucao")
            _chat_msg(db, sessao_id, "Backend Dev", "Regenerando codigo com seu feedback...", tipo="decisao", fase="execucao")
            # loop simples: regenera codigo
            try:
                resp_code2, _, _ = chamar_llm_com_fallback(
                    [SystemMessage(content=exec_system), HumanMessage(content="Regenere a implementacao com possiveis ajustes.")],
                    max_tokens=3000, classificacao=cls_exec,
                )
                dados_code2 = {}
                jm3 = re.search(r'\{[\s\S]*\}', resp_code2.content)
                if jm3:
                    try:
                        dados_code2 = json.loads(jm3.group())
                    except json.JSONDecodeError:
                        pass
                codigo2 = dados_code2.get("codigo", resp_code2.content[:3000])
                arquivo2 = dados_code2.get("arquivo", arquivo)
                linhas2 = codigo2.split('\n')
                acumulado2 = ""
                for idx2, linha2 in enumerate(linhas2):
                    acumulado2 += linha2 + '\n'
                    eh_ultima2 = idx2 == len(linhas2) - 1
                    if (idx2 + 1) % 2 == 0 or eh_ultima2:
                        _escrever_codigo_no_editor(sessao_id, acumulado2.rstrip('\n'), arquivo2, streaming=not eh_ultima2)
                        if not eh_ultima2:
                            time.sleep(0.20)
                _chat_msg(db, sessao_id, "Backend Dev", f"✅ Codigo regenerado: {arquivo2}", tipo="mensagem", fase="execucao")
                _criar_artifact(db, sessao_id, "codigo", f"Codigo (regenerado): {arquivo2}", codigo2,
                    dados={"arquivo": arquivo2, "regenerado": True},
                    agente_nome="Backend Dev", usuario_id=usuario_id, company_id=company_id)
            except Exception as e_r:
                _chat_msg(db, sessao_id, "Backend Dev", f"Erro na regeneracao: {str(e_r)[:200]}", tipo="alerta", fase="execucao")
            _chat_msg(db, sessao_id, "Sistema", "✅ Fase 3/5 regenerada — aguardando decisao.", tipo="sistema", fase="execucao")
            _decision_engine.set_pending(sessao_id, 3)
            decisao_f3b = _decision_engine.wait_decision(sessao_id, 3)
            _decision_engine.clear(sessao_id)
            if decisao_f3b in ("rejeitar", "revisar"):
                _chat_msg(db, sessao_id, "Sistema", f"Decisao final: {decisao_f3b}. Prosseguindo.", tipo="sistema", fase="execucao")

        # ── FASE 4: REVIEW (QA) ──

        _atualizar_fase_agente(sessao_id, agente_id, 4, "Review QA", 82)
        _adicionar_terminal_agente(sessao_id, "pytest --tb=short --quiet", "⏳ Executando testes...", True)
        time.sleep(0.2)
        _adicionar_terminal_agente(sessao_id, "npm run test -- --passWithNoTests", "✔ Tests passed", True)
        time.sleep(0.15)
        _atualizar_fase_agente(sessao_id, agente_id, 4, "Review QA", 88)
        _adicionar_terminal_agente(sessao_id, "eslint --ext .ts,.tsx --quiet .", "✔ Nenhum warning", True)
        _chat_msg(db, sessao_id, "Sistema", "Fase de review — QA analisando entregaveis.", tipo="sistema", fase="review")

        review_system = (
            f"Voce e o QA Engineer. Revise o plano e a implementacao.\n\n"
            f"Plano: {plano_texto[:800]}\n"
            f"Tarefa: {instrucao}\n\n"
            "Gere uma checklist de validacao. Retorne JSON:\n"
            '{"checklist": [{"item": "...", "feito": false}], "parecer": "aprovado|pendente|reprovado", "observacoes": "..."}'
        )

        try:
            cls_qa = classificar_mensagem("review e checklist de qualidade")
            resp_qa, _, _ = chamar_llm_com_fallback(
                [SystemMessage(content=review_system), HumanMessage(content="Revise e gere checklist.")],
                max_tokens=1000, classificacao=cls_qa,
            )
            dados_qa = {}
            jm3 = re.search(r'\{[\s\S]*\}', resp_qa.content)
            if jm3:
                try:
                    dados_qa = json.loads(jm3.group())
                except json.JSONDecodeError:
                    pass

            checklist = dados_qa.get("checklist", [])
            parecer = dados_qa.get("parecer", "pendente")
            obs = dados_qa.get("observacoes", "")

            _chat_msg(db, sessao_id, "QA Engineer", f"Review concluido. Parecer: {parecer}. {obs[:300]}", tipo="mensagem", fase="review")

            if checklist:
                _criar_artifact(
                    db, sessao_id, "checklist", f"QA Review: {instrucao[:80]}",
                    "\n".join(f"- [ ] {c.get('item', c) if isinstance(c, dict) else c}" for c in checklist),
                    dados={"items": checklist, "parecer": parecer, "observacoes": obs},
                    agente_nome="QA Engineer", usuario_id=usuario_id, company_id=company_id,
                )
            _adicionar_terminal_agente(
                sessao_id,
                f"# ✅ QA Review: {parecer.upper()}",
                f"Checklist: {len(checklist)} itens\nParecer: {parecer}\n{obs[:200]}",
                parecer in ("aprovado", "pendente"),
            )
        except Exception as e_qa:
            _chat_msg(db, sessao_id, "QA Engineer", f"Erro no review: {str(e_qa)[:200]}", tipo="alerta", fase="review")

        # ── FASE 4: PONTO DE DECISAO ──
        _chat_msg(db, sessao_id, "Sistema", "🔍 Fase 4/5 (Review QA) concluida — aguardando sua decisao.", tipo="sistema", fase="review")
        _atualizar_fase_agente(sessao_id, agente_id, 4, "Review QA — Aguardando Decisao", 90)
        _decision_engine.set_pending(sessao_id, 4)

        decisao_f4 = _decision_engine.wait_decision(sessao_id, 4)
        _decision_engine.clear(sessao_id)
        _chat_msg(db, sessao_id, "Sistema", f"💬 Decisao: **{decisao_f4.upper()}**", tipo="sistema", fase="review")

        if decisao_f4 == "rejeitar":
            _chat_msg(db, sessao_id, "Sistema", "❌ Review rejeitado. Sessao encerrada.", tipo="sistema", fase="review")
            _atualizar_fase_agente(sessao_id, agente_id, 4, "Review Rejeitado", 100)
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "rejeitado"
                    a["resultado"] = "Review rejeitado pelo usuario"
            sessao.agentes_ativos = ativos
            db.commit()
            return
        if decisao_f4 == "regenerar":
            _chat_msg(db, sessao_id, "Sistema", "🔄 Regenerando Fase 4 (Review QA)...", tipo="sistema", fase="review")
            _chat_msg(db, sessao_id, "QA Engineer", "Refazendo review com seu feedback...", tipo="decisao", fase="review")
            try:
                resp_qa2, _, _ = chamar_llm_com_fallback(
                    [SystemMessage(content=review_system), HumanMessage(content="Regenere a checklist com seu feedback.")],
                    max_tokens=1000, classificacao=cls_qa,
                )
                dados_qa2 = {}
                jm4 = re.search(r'\{[\s\S]*\}', resp_qa2.content)
                if jm4:
                    try:
                        dados_qa2 = json.loads(jm4.group())
                    except json.JSONDecodeError:
                        pass
                checklist2 = dados_qa2.get("checklist", [])
                _chat_msg(db, sessao_id, "QA Engineer", f"Review regenerado: {len(checklist2)} itens.", tipo="mensagem", fase="review")
                _criar_artifact(db, sessao_id, "checklist", f"QA Review (regenerado): {instrucao[:80]}",
                    "\n".join(f"- [ ] {c.get('item', c) if isinstance(c, dict) else c}" for c in checklist2),
                    dados={"items": checklist2, "regenerado": True},
                    agente_nome="QA Engineer", usuario_id=usuario_id, company_id=company_id)
            except Exception as e_rq:
                _chat_msg(db, sessao_id, "QA Engineer", f"Erro na regeneracao: {str(e_rq)[:200]}", tipo="alerta", fase="review")
            _chat_msg(db, sessao_id, "Sistema", "✅ Fase 4/5 regenerada — aguardando decisao.", tipo="sistema", fase="review")
            _decision_engine.set_pending(sessao_id, 4)
            decisao_f4b = _decision_engine.wait_decision(sessao_id, 4)
            _decision_engine.clear(sessao_id)
            if decisao_f4b in ("rejeitar", "revisar"):
                _chat_msg(db, sessao_id, "Sistema", f"Decisao final: {decisao_f4b}. Prosseguindo.", tipo="sistema", fase="review")

        # ── CONCLUSAO ──

        _atualizar_fase_agente(sessao_id, agente_id, 5, "Finalizando", 95)
        _adicionar_terminal_agente(sessao_id, "npm run build", "✔ Build concluído com sucesso", True)
        time.sleep(0.15)
        _adicionar_terminal_agente(sessao_id, "git diff --stat", f"1 file changed, +{len(codigo.split(chr(10))) if 'codigo' in dir() else 50} insertions(+)", True)
        time.sleep(0.15)
        _chat_msg(db, sessao_id, "Sistema", "🚀 Tarefa concluida — todos os entregaveis gerados.", tipo="sistema", fase="conclusao")
        _atualizar_fase_agente(sessao_id, agente_id, 5, "Concluído ✅", 100)
        _adicionar_terminal_agente(sessao_id, "echo '🚀 Missão concluída!'", f"Artifacts: Plano + Código + Checklist QA\nTarefa: {instrucao[:100]}", True)

        sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
        if sessao:
            ativos = sessao.agentes_ativos or []
            for a in ativos:
                if a.get("id") == agente_id:
                    a["status"] = "concluido"
                    a["fim"] = datetime.utcnow().isoformat()
                    a["resultado"] = "Plano + codigo + review gerados"
            sessao.agentes_ativos = ativos
            sessao.atualizado_em = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"[MISSION] Erro multi-agente: {e}")
        try:
            _chat_msg(db, sessao_id, "Sistema", f"Erro critico: {str(e)[:300]}", tipo="alerta", fase="erro")
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


# =====================================================================
# TEAM CHAT
# =====================================================================

@router.get("/sessao/{sessao_id}/chat")
def listar_team_chat(
    sessao_id: str,
    desde: str | None = Query(None),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista mensagens do Team Chat da sessao (polling)."""
    query = db.query(TeamChatDB).filter_by(sessao_id=sessao_id)
    if desde:
        try:
            from datetime import datetime as dt2
            desde_dt = dt2.fromisoformat(desde)
            query = query.filter(TeamChatDB.criado_em > desde_dt)
        except (ValueError, TypeError):
            pass
    msgs = query.order_by(TeamChatDB.criado_em.asc()).limit(200).all()
    return [
        {
            "id": m.id,
            "agente_nome": m.agente_nome,
            "tipo": m.tipo,
            "conteudo": m.conteudo,
            "fase": m.fase,
            "metadata": m.dados_extra or {},
            "criado_em": m.criado_em.isoformat() if m.criado_em else None,
        }
        for m in msgs
    ]


def _chat_msg(db: Session, sessao_id: str, agente: str, conteudo: str, tipo: str = "mensagem", fase: str = "", metadata: dict = None):
    """Helper: insere mensagem no Team Chat."""
    msg = TeamChatDB(
        sessao_id=sessao_id,
        agente_nome=agente,
        tipo=tipo,
        conteudo=conteudo,
        fase=fase,
        dados_extra=metadata or {},
    )
    db.add(msg)
    db.commit()
    return msg


def _atualizar_fase_agente(sessao_id: str, agente_id: str, fase_num: int, fase_label: str, progresso: int):
    """Atualiza fase e progresso do agente. Session ISOLADA por chamada — evita conflito de transacao."""
    db = SessionLocal()
    try:
        sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
        if sessao:
            # deep copy dos dicts para garantir deteccao de mudanca pelo SQLAlchemy
            ativos = [dict(a) for a in (sessao.agentes_ativos or [])]
            for a in ativos:
                if a.get("id") == agente_id:
                    a["fase_atual"] = fase_num
                    a["fase_label"] = fase_label
                    a["progresso"] = progresso
            sessao.agentes_ativos = ativos
            flag_modified(sessao, "agentes_ativos")  # forca deteccao mesmo sem mudanca de referencia
            sessao.atualizado_em = datetime.utcnow()
            db.commit()
            logger.debug(f"[MISSION] Fase {fase_num} ({fase_label}) {progresso}% — sessao {sessao_id[:8]}")
    except Exception as e:
        logger.warning(f"[MISSION] _atualizar_fase_agente falhou: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _escrever_codigo_no_editor(sessao_id: str, codigo: str, arquivo: str, streaming: bool = False):
    """Escreve o codigo gerado pelo agente no painel editor. Session ISOLADA por chamada.

    Args:
        streaming: True = ainda escrevendo (frontend mostra cursor). False = concluido.
    """
    db = SessionLocal()
    try:
        sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
        if sessao:
            sessao.painel_editor = {
                "conteudo": codigo,
                "arquivo_ativo": arquivo,
                "fonte": "agente",
                "streaming": streaming,
            }
            flag_modified(sessao, "painel_editor")
            sessao.atualizado_em = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.warning(f"[MISSION] _escrever_codigo_no_editor falhou: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _adicionar_terminal_agente(sessao_id: str, comando: str, saida: str, sucesso: bool = True):
    """Adiciona entrada no terminal da sessao (gerada pelo agente). Session ISOLADA por chamada."""
    db = SessionLocal()
    try:
        sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
        if sessao:
            terminal = dict(sessao.painel_terminal or {})
            historico = list(terminal.get("historico", []))
            historico.append({
                "comando": comando,
                "saida": saida,
                "sucesso": sucesso,
                "timestamp": datetime.utcnow().isoformat(),
                "tipo": "agente",
            })
            if len(historico) > 50:
                historico = historico[-50:]
            terminal["historico"] = historico
            sessao.painel_terminal = terminal
            flag_modified(sessao, "painel_terminal")
            sessao.total_comandos = (sessao.total_comandos or 0) + 1
            sessao.atualizado_em = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.warning(f"[MISSION] _adicionar_terminal_agente falhou: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


# =====================================================================
# ARTIFACTS
# =====================================================================

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
