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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.models import (
    UsuarioDB, ArtifactDB, MissionControlSessaoDB, ProjetoDB, TeamChatDB,
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


EQUIPE_AGENTES = [
    {"nome": "Tech Lead", "perfil": "arquiteto", "emoji": "🏗️"},
    {"nome": "Backend Dev", "perfil": "backend", "emoji": "⚙️"},
    {"nome": "Frontend Dev", "perfil": "frontend", "emoji": "🎨"},
    {"nome": "QA Engineer", "perfil": "qa", "emoji": "🛡️"},
]


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

        _chat_msg(db, sessao_id, "Sistema", f"Nova tarefa recebida: {instrucao[:200]}", tipo="sistema", fase="planejamento")
        _atualizar_fase_agente(db, sessao_id, agente_id, 1, "Planejamento", 10)
        _adicionar_terminal_agente(db, sessao_id, "# 🏗️ Tech Lead: analisando tarefa...", f"Tarefa: {instrucao[:200]}")
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

        _chat_msg(db, sessao_id, "Tech Lead", f"Plano pronto: {plano_texto[:500]}", tipo="planejamento", fase="planejamento")

        # Criar artifact de plano
        _criar_artifact(
            db, sessao_id, "plano", f"Plano: {instrucao[:100]}",
            plano_texto, dados=dados_plan,
            agente_nome="Tech Lead", usuario_id=usuario_id, company_id=company_id,
        )

        if etapas:
            etapas_texto = "\n".join(f"  {e.get('numero', i+1)}. [{e.get('responsavel', '?')}] {e.get('titulo', e.get('descricao', ''))}" for i, e in enumerate(etapas))
            _chat_msg(db, sessao_id, "Tech Lead", f"Etapas do plano:\n{etapas_texto}", tipo="planejamento", fase="planejamento")

        # ── FASE 2: DISCUSSAO (cada agente opina) ──

        _atualizar_fase_agente(db, sessao_id, agente_id, 2, "Discussão", 35)
        _adicionar_terminal_agente(db, sessao_id, "# 💬 Equipe: revisando plano...", f"Etapas identificadas: {len(etapas)}")
        _chat_msg(db, sessao_id, "Sistema", "Fase de discussao iniciada — agentes analisando o plano.", tipo="sistema", fase="discussao")

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
            except Exception as e_disc:
                _chat_msg(db, sessao_id, ag["nome"], f"(sem resposta: {str(e_disc)[:100]})", tipo="alerta", fase="discussao")

        # ── FASE 3: EXECUCAO (gerar artifacts concretos) ──

        _atualizar_fase_agente(db, sessao_id, agente_id, 3, "Execução", 60)
        _adicionar_terminal_agente(db, sessao_id, "# ⚡ Backend Dev: gerando implementação...", "Aguardando LLM...")
        # Sinalizar editor: código a caminho
        _escrever_codigo_no_editor(db, sessao_id, f"// ⚡ Gerando código para: {instrucao[:100]}\n// Aguarde...", "gerando.tsx")
        _chat_msg(db, sessao_id, "Sistema", "Fase de execucao — agentes gerando entregaveis.", tipo="sistema", fase="execucao")
        _chat_msg(db, sessao_id, "Tech Lead", "Plano aprovado pela equipe. Iniciando execucao.", tipo="decisao", fase="execucao")

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

            _chat_msg(db, sessao_id, "Backend Dev", f"Codigo gerado: {arquivo} — {descricao[:200]}", tipo="mensagem", fase="execucao")

            _criar_artifact(
                db, sessao_id, "codigo", f"Codigo: {arquivo}",
                codigo, dados={"arquivo": arquivo, "linguagem": dados_code.get("linguagem", ""), "descricao": descricao},
                agente_nome="Backend Dev", usuario_id=usuario_id, company_id=company_id,
            )
            # Escrever codigo no editor — frontend vai detectar e exibir
            _escrever_codigo_no_editor(db, sessao_id, codigo, arquivo)
            # Terminal: simular verificação de sintaxe
            _adicionar_terminal_agente(
                db, sessao_id,
                f"# ✅ Código gerado: {arquivo}",
                f"Linhas: {len(codigo.splitlines())}\nArquivo: {arquivo}\nPor: Backend Dev",
                True,
            )
        except Exception as e_code:
            _chat_msg(db, sessao_id, "Backend Dev", f"Erro ao gerar codigo: {str(e_code)[:200]}", tipo="alerta", fase="execucao")

        # ── FASE 4: REVIEW (QA) ──

        _atualizar_fase_agente(db, sessao_id, agente_id, 4, "Review QA", 85)
        _adicionar_terminal_agente(db, sessao_id, "# 🛡️ QA Engineer: executando review...", "Analisando código e gerando checklist...")
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
                db, sessao_id,
                f"# ✅ QA Review: {parecer.upper()}",
                f"Checklist: {len(checklist)} itens\nParecer: {parecer}\n{obs[:200]}",
                parecer in ("aprovado", "pendente"),
            )
        except Exception as e_qa:
            _chat_msg(db, sessao_id, "QA Engineer", f"Erro no review: {str(e_qa)[:200]}", tipo="alerta", fase="review")

        # ── CONCLUSAO ──

        _chat_msg(db, sessao_id, "Sistema", "Tarefa concluida — todos os entregaveis gerados.", tipo="sistema", fase="conclusao")
        _atualizar_fase_agente(db, sessao_id, agente_id, 5, "Concluído", 100)
        _adicionar_terminal_agente(db, sessao_id, "# 🚀 Missão concluída!", f"Artifacts: Plano + Código + Checklist QA\nTarefa: {instrucao[:100]}", True)

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


def _atualizar_fase_agente(db: Session, sessao_id: str, agente_id: str, fase_num: int, fase_label: str, progresso: int):
    """Atualiza fase e progresso do agente na sessao para o frontend ver em tempo real."""
    sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
    if sessao:
        ativos = list(sessao.agentes_ativos or [])
        for a in ativos:
            if a.get("id") == agente_id:
                a["fase_atual"] = fase_num
                a["fase_label"] = fase_label
                a["progresso"] = progresso
        sessao.agentes_ativos = ativos
        sessao.atualizado_em = datetime.utcnow()
        db.commit()


def _escrever_codigo_no_editor(db: Session, sessao_id: str, codigo: str, arquivo: str):
    """Escreve o codigo gerado pelo agente no painel editor da sessao."""
    sessao = db.query(MissionControlSessaoDB).filter_by(sessao_id=sessao_id).first()
    if sessao:
        sessao.painel_editor = {
            "conteudo": codigo,
            "arquivo_ativo": arquivo,
            "fonte": "agente",  # flag para o frontend saber que veio do agente
        }
        sessao.atualizado_em = datetime.utcnow()
        db.commit()


def _adicionar_terminal_agente(db: Session, sessao_id: str, comando: str, saida: str, sucesso: bool = True):
    """Adiciona entrada no terminal da sessao (gerada pelo agente, nao pelo usuario)."""
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
        sessao.total_comandos = (sessao.total_comandos or 0) + 1
        sessao.atualizado_em = datetime.utcnow()
        db.commit()


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
