"""
Rotas: Continuous Factory — Modo Continuo 24/7 (v0.54.0)

GET  /api/continuous-factory           — Status e config do modo continuo
POST /api/continuous-factory/ativar    — Ativa o modo continuo
POST /api/continuous-factory/desativar — Desativa o modo continuo
POST /api/continuous-factory/config    — Atualiza configuracoes
GET  /api/continuous-factory/relatorios — Lista relatorios diarios
POST /api/continuous-factory/relatorio-agora — Gera relatorio manualmente

Quando ativado:
- Gates soft sao auto-aprovados pelo sistema
- Gates hard geram notificacao por email ao CEO
- Relatorio diario gerado as 23:00 com resumo do dia
- Fila de workflows continua executando automaticamente
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual, obter_fabrica
from database.models import (
    UsuarioDB, ContinuousFactoryDB, RelatorioDiarioDB,
    WorkflowAutonomoDB, UsageTrackingDB, EvolucaoFactoryDB,
)
from database.session import get_db, SessionLocal

logger = logging.getLogger("synerium.continuous_factory")

router = APIRouter(prefix="/api/continuous-factory", tags=["Continuous Factory 24/7"])


# =====================================================================
# Schemas
# =====================================================================

class AtivarRequest(BaseModel):
    email_notificacao: str = ""
    auto_aprovar_hard: bool = False
    max_workflows_paralelos: int = 2


class ConfigRequest(BaseModel):
    auto_aprovar_soft: bool = True
    auto_aprovar_hard: bool = False
    notificar_email: bool = True
    email_notificacao: str = ""
    relatorio_diario_ativo: bool = True
    horario_relatorio: str = "23:00"
    max_workflows_paralelos: int = 2
    intervalo_entre_workflows_seg: int = 60


# =====================================================================
# Helpers
# =====================================================================

def _obter_ou_criar_config(db: Session, company_id: int = 1) -> ContinuousFactoryDB:
    """Obtem ou cria a config singleton do modo continuo."""
    config = db.query(ContinuousFactoryDB).filter_by(company_id=company_id).first()
    if not config:
        config = ContinuousFactoryDB(company_id=company_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# =====================================================================
# Endpoints
# =====================================================================

@router.get("")
def status_continuous(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna status e configuracao do modo continuo."""
    config = _obter_ou_criar_config(db, usuario.company_id or 1)

    # Contar workflows ativos
    ativos = db.query(WorkflowAutonomoDB).filter(
        WorkflowAutonomoDB.status.in_(["em_execucao", "aguardando_gate", "aguardando_fila"]),
        WorkflowAutonomoDB.company_id == (usuario.company_id or 1),
    ).count()

    pendentes_gate = db.query(WorkflowAutonomoDB).filter_by(
        status="aguardando_gate",
        company_id=usuario.company_id or 1,
    ).count()

    return {
        "ativo": config.ativo,
        "ativado_por": config.ativado_por,
        "ativado_em": config.ativado_em.isoformat() if config.ativado_em else None,
        "config": {
            "auto_aprovar_soft": config.auto_aprovar_soft,
            "auto_aprovar_hard": config.auto_aprovar_hard,
            "notificar_email": config.notificar_email,
            "email_notificacao": config.email_notificacao,
            "relatorio_diario_ativo": config.relatorio_diario_ativo,
            "horario_relatorio": config.horario_relatorio,
            "max_workflows_paralelos": config.max_workflows_paralelos,
            "intervalo_entre_workflows_seg": config.intervalo_entre_workflows_seg,
        },
        "metricas_hoje": {
            "workflows": config.workflows_hoje,
            "custo_usd": round(config.custo_hoje_usd, 4),
            "fases_completadas": config.fases_completadas_hoje,
            "erros": config.erros_hoje,
        },
        "workflows_ativos": ativos,
        "gates_pendentes": pendentes_gate,
        "ultimo_relatorio": config.ultimo_relatorio_em.isoformat() if config.ultimo_relatorio_em else None,
    }


@router.post("/ativar")
def ativar_modo_continuo(
    req: AtivarRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Ativa o Modo Continuo 24/7.
    Apenas CEO ou Operations Lead podem ativar.
    """
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO ou Operations Lead pode ativar o Modo Contínuo.")

    config = _obter_ou_criar_config(db, usuario.company_id or 1)

    if config.ativo:
        return {"mensagem": "Modo Contínuo já está ativo.", "ativo": True}

    config.ativo = True
    config.ativado_por = usuario.nome
    config.ativado_em = datetime.utcnow()
    config.desativado_em = None

    # Aplicar config do request
    if req.email_notificacao:
        config.email_notificacao = req.email_notificacao
    elif not config.email_notificacao:
        config.email_notificacao = usuario.email
    config.auto_aprovar_hard = req.auto_aprovar_hard
    config.max_workflows_paralelos = req.max_workflows_paralelos

    db.commit()

    logger.info(f"[CONTINUOUS] Modo Contínuo ATIVADO por {usuario.nome}")

    # Iniciar background worker
    _iniciar_worker_continuo(usuario.company_id or 1)

    return {
        "mensagem": f"Modo Contínuo 24/7 ativado por {usuario.nome}!",
        "ativo": True,
        "email_notificacao": config.email_notificacao,
    }


@router.post("/desativar")
def desativar_modo_continuo(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Desativa o Modo Continuo 24/7."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO ou Operations Lead pode desativar.")

    config = _obter_ou_criar_config(db, usuario.company_id or 1)

    if not config.ativo:
        return {"mensagem": "Modo Contínuo já está desativado.", "ativo": False}

    config.ativo = False
    config.desativado_em = datetime.utcnow()
    db.commit()

    logger.info(f"[CONTINUOUS] Modo Contínuo DESATIVADO por {usuario.nome}")

    return {"mensagem": "Modo Contínuo desativado.", "ativo": False}


@router.post("/config")
def atualizar_config(
    req: ConfigRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Atualiza configuracoes do modo continuo."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Sem permissao.")

    config = _obter_ou_criar_config(db, usuario.company_id or 1)

    config.auto_aprovar_soft = req.auto_aprovar_soft
    config.auto_aprovar_hard = req.auto_aprovar_hard
    config.notificar_email = req.notificar_email
    config.email_notificacao = req.email_notificacao
    config.relatorio_diario_ativo = req.relatorio_diario_ativo
    config.horario_relatorio = req.horario_relatorio
    config.max_workflows_paralelos = req.max_workflows_paralelos
    config.intervalo_entre_workflows_seg = req.intervalo_entre_workflows_seg

    db.commit()
    logger.info(f"[CONTINUOUS] Config atualizada por {usuario.nome}")

    return {"mensagem": "Configuração atualizada.", "config": req.model_dump()}


@router.get("/relatorios")
def listar_relatorios(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista relatorios diarios dos ultimos 30 dias."""
    relatorios = (
        db.query(RelatorioDiarioDB)
        .filter_by(company_id=usuario.company_id or 1)
        .order_by(RelatorioDiarioDB.criado_em.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": r.id,
            "data": r.data,
            "workflows_executados": r.workflows_executados,
            "workflows_concluidos": r.workflows_concluidos,
            "workflows_erro": r.workflows_erro,
            "custo_total_usd": round(r.custo_total_usd, 4),
            "evolucoes_geradas": r.evolucoes_geradas,
            "resumo": r.resumo,
            "proximos_passos": r.proximos_passos,
            "enviado_por_email": r.enviado_por_email,
            "criado_em": r.criado_em.isoformat() if r.criado_em else None,
        }
        for r in relatorios
    ]


@router.post("/relatorio-agora")
def gerar_relatorio_agora(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Gera relatorio do dia manualmente (sem esperar as 23h)."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Sem permissao.")

    threading.Thread(
        target=_gerar_relatorio_diario,
        args=(usuario.company_id or 1,),
        daemon=True,
    ).start()

    return {"mensagem": "Relatório sendo gerado em background. Aparecerá na lista em instantes."}


# =====================================================================
# AUTO-APPROVAL DE GATES (chamado pelo endpoint aprovar_gate em tarefas.py)
# =====================================================================

def verificar_auto_aprovacao_gate(workflow_id: str, fase: int, company_id: int = 1) -> bool:
    """
    Verifica se o Modo Continuo deve auto-aprovar um gate.

    Retorna True se o gate foi auto-aprovado.
    Retorna False se precisa de aprovacao humana.

    Chamado por _executar_workflow_autonomo_bg quando um gate hard e encontrado.
    """
    db = SessionLocal()
    try:
        config = db.query(ContinuousFactoryDB).filter_by(company_id=company_id).first()
        if not config or not config.ativo:
            return False

        from api.routes.tarefas import GATES_FASE
        gate_tipo = GATES_FASE.get(fase, "soft")

        if gate_tipo == "soft" and config.auto_aprovar_soft:
            logger.info(f"[CONTINUOUS] Auto-aprovando gate SOFT fase {fase} do workflow {workflow_id}")
            return True

        if gate_tipo == "hard" and config.auto_aprovar_hard:
            logger.info(f"[CONTINUOUS] Auto-aprovando gate HARD fase {fase} do workflow {workflow_id}")
            return True

        # Gate hard + notificacao por email
        if gate_tipo == "hard" and config.notificar_email and config.email_notificacao:
            _notificar_gate_pendente(workflow_id, fase, config.email_notificacao, company_id)

        return False
    except Exception as e:
        logger.error(f"[CONTINUOUS] Erro ao verificar auto-aprovacao: {e}")
        return False
    finally:
        db.close()


def _notificar_gate_pendente(workflow_id: str, fase: int, email: str, company_id: int):
    """Envia email notificando que um gate hard precisa de aprovacao."""
    try:
        import boto3
        from config.settings import settings

        if not settings.aws_ses_sender:
            logger.warning("[CONTINUOUS] AWS SES sender nao configurado — notificacao nao enviada")
            return

        db = SessionLocal()
        try:
            wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            titulo = wf.titulo if wf else workflow_id
        finally:
            db.close()

        assunto = f"🏭 Gate Pendente — Fase {fase}: {titulo}"
        corpo = f"""
        <h2>Synerium Factory — Gate de Aprovação Pendente</h2>
        <p>O Modo Contínuo 24/7 encontrou um gate que requer sua aprovação:</p>
        <ul>
            <li><b>Workflow:</b> {titulo}</li>
            <li><b>ID:</b> {workflow_id}</li>
            <li><b>Fase:</b> {fase}</li>
            <li><b>Tipo:</b> Gate HARD (requer aprovação humana)</li>
        </ul>
        <p>Acesse o <b>Command Center</b> do Synerium Factory para aprovar ou rejeitar.</p>
        <p><small>Este email foi enviado automaticamente pelo Modo Contínuo 24/7.</small></p>
        """

        cliente = boto3.client(
            "ses",
            region_name=settings.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        )

        cliente.send_email(
            Source=settings.aws_ses_sender,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": assunto, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": corpo, "Charset": "UTF-8"},
                    "Text": {"Data": f"Gate pendente: Workflow {titulo} — Fase {fase}. Acesse o Command Center.", "Charset": "UTF-8"},
                },
            },
        )

        logger.info(f"[CONTINUOUS] Email de gate pendente enviado para {email}")

    except Exception as e:
        logger.error(f"[CONTINUOUS] Erro ao enviar email de notificacao: {e}")


# =====================================================================
# RELATORIO DIARIO
# =====================================================================

def _gerar_relatorio_diario(company_id: int = 1):
    """
    Gera o relatorio diario com resumo do que foi feito.

    Coleta metricas do banco, gera resumo via LLM e salva.
    """
    db = SessionLocal()
    try:
        hoje = datetime.utcnow().strftime("%Y-%m-%d")
        inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        logger.info(f"[RELATORIO] Gerando relatorio diario para {hoje}")

        # === Metricas de workflows ===
        workflows_hoje = db.query(WorkflowAutonomoDB).filter(
            WorkflowAutonomoDB.criado_em >= inicio_dia,
            WorkflowAutonomoDB.company_id == company_id,
        ).all()

        wf_concluidos = [w for w in workflows_hoje if w.status == "concluido"]
        wf_erro = [w for w in workflows_hoje if w.status == "erro"]
        wf_ativos = [w for w in workflows_hoje if w.status in ("em_execucao", "aguardando_gate")]

        # Contar fases completadas
        total_fases = 0
        gates_aprovados = 0
        gates_pendentes = 0
        for wf in workflows_hoje:
            gates = wf.gates or {}
            for g_key, g_val in gates.items():
                status = g_val.get("status", "")
                if status in ("aprovado", "auto_pass"):
                    gates_aprovados += 1
                    total_fases += 1
                elif status == "pendente":
                    gates_pendentes += 1

        # === Metricas de custo ===
        uso_hoje = db.query(UsageTrackingDB).filter(
            UsageTrackingDB.criado_em >= inicio_dia,
            UsageTrackingDB.company_id == company_id,
        ).all()

        custo_total = sum(u.custo_usd for u in uso_hoje)
        tokens_in = sum(u.tokens_input or 0 for u in uso_hoje)
        tokens_out = sum(u.tokens_output or 0 for u in uso_hoje)

        # Provider mais usado
        provider_count = {}
        for u in uso_hoje:
            p = u.provider_id or "unknown"
            provider_count[p] = provider_count.get(p, 0) + 1
        provider_mais = max(provider_count, key=provider_count.get) if provider_count else ""

        # === Evolucoes ===
        evolucoes_hoje = db.query(EvolucaoFactoryDB).filter(
            EvolucaoFactoryDB.criado_em >= inicio_dia,
        ).all()
        total_sugestoes = sum(len(e.sugestoes or []) for e in evolucoes_hoje)

        # === Gerar resumo via LLM ===
        resumo_texto = ""
        proximos = []
        try:
            from core.llm_fallback import chamar_llm_com_fallback
            from langchain_core.messages import HumanMessage, SystemMessage

            titulos_concluidos = [w.titulo for w in wf_concluidos]
            titulos_erro = [w.titulo for w in wf_erro]
            titulos_ativos = [w.titulo for w in wf_ativos]

            prompt = (
                f"Gere um relatorio executivo do dia {hoje} do Synerium Factory.\n\n"
                f"Workflows concluidos ({len(wf_concluidos)}): {', '.join(titulos_concluidos) or 'nenhum'}\n"
                f"Workflows com erro ({len(wf_erro)}): {', '.join(titulos_erro) or 'nenhum'}\n"
                f"Workflows ativos ({len(wf_ativos)}): {', '.join(titulos_ativos) or 'nenhum'}\n"
                f"Fases completadas: {total_fases}\n"
                f"Custo total: ${custo_total:.4f}\n"
                f"Evolucoes geradas: {len(evolucoes_hoje)} ({total_sugestoes} sugestoes)\n\n"
                f"Retorne JSON:\n"
                '{"resumo": "2-3 paragrafos em portugues", "proximos_passos": ["passo1", "passo2", "passo3"]}'
            )

            msgs = [
                SystemMessage(content="Voce e o CEO Assistant do Synerium Factory. Gere relatorios executivos concisos."),
                HumanMessage(content=prompt),
            ]

            from core.classificador_mensagem import classificar_mensagem
            cls = classificar_mensagem(prompt)
            resp, _, _ = chamar_llm_com_fallback(msgs, max_tokens=1000, classificacao=cls)

            import json, re
            json_match = re.search(r'\{[\s\S]*\}', resp.content)
            if json_match:
                dados = json.loads(json_match.group())
                resumo_texto = dados.get("resumo", resp.content)
                proximos = dados.get("proximos_passos", [])
            else:
                resumo_texto = resp.content

        except Exception as llm_err:
            logger.warning(f"[RELATORIO] LLM falhou: {llm_err}")
            resumo_texto = (
                f"Relatorio automatico {hoje}: "
                f"{len(wf_concluidos)} workflows concluidos, "
                f"{len(wf_erro)} erros, custo ${custo_total:.4f}."
            )

        # === Salvar relatorio ===
        relatorio = RelatorioDiarioDB(
            data=hoje,
            workflows_executados=len(workflows_hoje),
            workflows_concluidos=len(wf_concluidos),
            workflows_erro=len(wf_erro),
            fases_completadas=total_fases,
            gates_aprovados=gates_aprovados,
            gates_pendentes=gates_pendentes,
            custo_total_usd=custo_total,
            tokens_input_total=tokens_in,
            tokens_output_total=tokens_out,
            provider_mais_usado=provider_mais,
            evolucoes_geradas=len(evolucoes_hoje),
            sugestoes_total=total_sugestoes,
            resumo=resumo_texto,
            proximos_passos=proximos,
            detalhes={
                "workflows_concluidos": [w.titulo for w in wf_concluidos],
                "workflows_erro": [w.titulo for w in wf_erro],
                "workflows_ativos": [w.titulo for w in wf_ativos],
            },
            company_id=company_id,
        )
        db.add(relatorio)

        # Resetar metricas diarias
        config = db.query(ContinuousFactoryDB).filter_by(company_id=company_id).first()
        if config:
            config.workflows_hoje = 0
            config.custo_hoje_usd = 0.0
            config.fases_completadas_hoje = 0
            config.erros_hoje = 0
            config.ultimo_relatorio_em = datetime.utcnow()

        db.commit()
        db.refresh(relatorio)

        logger.info(f"[RELATORIO] Relatorio #{relatorio.id} gerado: {len(wf_concluidos)} concluidos, ${custo_total:.4f}")

        # Enviar por email
        if config and config.notificar_email and config.email_notificacao:
            _enviar_relatorio_email(relatorio, config.email_notificacao)

    except Exception as e:
        logger.error(f"[RELATORIO] Erro ao gerar relatorio: {e}", exc_info=True)
    finally:
        db.close()


def _enviar_relatorio_email(relatorio: RelatorioDiarioDB, email: str):
    """Envia o relatorio diario por email."""
    try:
        import boto3
        from config.settings import settings

        if not settings.aws_ses_sender:
            return

        assunto = f"📊 Relatório Diário — Synerium Factory — {relatorio.data}"
        corpo = f"""
        <h2>📊 Relatório Diário — {relatorio.data}</h2>
        <h3>Resumo</h3>
        <p>{relatorio.resumo or 'Sem resumo disponível.'}</p>

        <h3>Métricas do Dia</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
            <tr><td><b>Workflows executados</b></td><td>{relatorio.workflows_executados}</td></tr>
            <tr><td><b>Workflows concluídos</b></td><td>{relatorio.workflows_concluidos}</td></tr>
            <tr><td><b>Workflows com erro</b></td><td>{relatorio.workflows_erro}</td></tr>
            <tr><td><b>Fases completadas</b></td><td>{relatorio.fases_completadas}</td></tr>
            <tr><td><b>Custo total</b></td><td>${relatorio.custo_total_usd:.4f}</td></tr>
            <tr><td><b>Evoluções geradas</b></td><td>{relatorio.evolucoes_geradas}</td></tr>
            <tr><td><b>Provider mais usado</b></td><td>{relatorio.provider_mais_usado}</td></tr>
        </table>

        <h3>Próximos Passos</h3>
        <ul>
            {''.join(f'<li>{p}</li>' for p in (relatorio.proximos_passos or ['Nenhum próximo passo definido.']))}
        </ul>

        <p><small>Gerado automaticamente pelo Modo Contínuo 24/7 do Synerium Factory.</small></p>
        """

        cliente = boto3.client(
            "ses",
            region_name=settings.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        )

        cliente.send_email(
            Source=settings.aws_ses_sender,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": assunto, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": corpo, "Charset": "UTF-8"},
                },
            },
        )

        # Marcar como enviado
        db = SessionLocal()
        try:
            r = db.query(RelatorioDiarioDB).filter_by(id=relatorio.id).first()
            if r:
                r.enviado_por_email = True
                r.email_destino = email
                db.commit()
        finally:
            db.close()

        logger.info(f"[RELATORIO] Email enviado para {email}")

    except Exception as e:
        logger.error(f"[RELATORIO] Erro ao enviar email: {e}")


# =====================================================================
# BACKGROUND WORKER — Motor do Modo Continuo
# =====================================================================

_worker_ativo = False
_worker_lock = threading.Lock()


def _iniciar_worker_continuo(company_id: int = 1):
    """Inicia o worker background que gerencia o modo continuo."""
    global _worker_ativo
    with _worker_lock:
        if _worker_ativo:
            logger.info("[CONTINUOUS] Worker ja esta ativo")
            return
        _worker_ativo = True

    threading.Thread(
        target=_worker_loop,
        args=(company_id,),
        daemon=True,
        name="continuous-factory-worker",
    ).start()
    logger.info("[CONTINUOUS] Worker background iniciado")


def _worker_loop(company_id: int):
    """
    Loop principal do Modo Continuo.

    A cada 30 segundos:
    1. Verifica se modo continuo ainda esta ativo
    2. Auto-aprova gates pendentes (se configurado)
    3. Verifica se e hora do relatorio diario
    4. Atualiza metricas
    """
    global _worker_ativo
    logger.info("[CONTINUOUS] Worker loop iniciado")

    while True:
        try:
            db = SessionLocal()
            try:
                config = db.query(ContinuousFactoryDB).filter_by(company_id=company_id).first()
                if not config or not config.ativo:
                    logger.info("[CONTINUOUS] Modo Continuo desativado — worker encerrando")
                    break

                # === 1. Auto-aprovar gates hard pendentes ===
                if config.auto_aprovar_hard:
                    _auto_aprovar_gates_hard(db, company_id)

                # === 2. Verificar horario do relatorio diario ===
                if config.relatorio_diario_ativo:
                    _verificar_horario_relatorio(config, company_id)

                # === 3. Atualizar metricas do dia ===
                _atualizar_metricas_dia(config, db, company_id)

                db.commit()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"[CONTINUOUS] Erro no worker loop: {e}")

        time.sleep(30)  # Verifica a cada 30 segundos

    with _worker_lock:
        _worker_ativo = False
    logger.info("[CONTINUOUS] Worker encerrado")


def _auto_aprovar_gates_hard(db: Session, company_id: int):
    """Auto-aprova todos os gates hard pendentes."""
    pendentes = db.query(WorkflowAutonomoDB).filter_by(
        status="aguardando_gate",
        company_id=company_id,
    ).all()

    for wf in pendentes:
        try:
            fase = wf.fase_atual
            gates = wf.gates or {}

            # Verificar se ja foi aprovado
            gate_key = f"fase_{fase}"
            if gate_key in gates and gates[gate_key].get("status") in ("aprovado", "auto_pass"):
                continue

            gates[gate_key] = {
                "status": "aprovado",
                "por": "Modo Contínuo 24/7",
                "feedback": "Auto-aprovado pelo Modo Contínuo",
            }
            wf.gates = gates

            proxima_fase = fase + 1
            if proxima_fase > 4:
                wf.status = "concluido"
                wf.atualizado_em = datetime.utcnow()
                db.commit()

                # Disparar review session
                try:
                    from api.routes.tarefas import _executar_review_session
                    threading.Thread(target=_executar_review_session, args=(wf.id,), daemon=True).start()
                except Exception:
                    pass

                logger.info(f"[CONTINUOUS] Workflow {wf.id} CONCLUIDO (auto-aprovado)")
            else:
                wf.fase_atual = proxima_fase
                wf.status = "em_execucao"
                wf.atualizado_em = datetime.utcnow()
                db.commit()

                # Continuar execucao
                from api.dependencias import obter_fabrica
                try:
                    fabrica = obter_fabrica()
                    from api.routes.tarefas import _executar_workflow_autonomo_bg
                    threading.Thread(
                        target=_executar_workflow_autonomo_bg,
                        args=(wf.id, wf.squad_nome, wf.titulo, wf.descricao or "", proxima_fase, fabrica),
                        daemon=True,
                    ).start()
                    logger.info(f"[CONTINUOUS] Gate fase {fase} auto-aprovado → fase {proxima_fase} para workflow {wf.id}")
                except Exception as fe:
                    logger.error(f"[CONTINUOUS] Erro ao continuar workflow: {fe}")

        except Exception as e:
            logger.error(f"[CONTINUOUS] Erro ao auto-aprovar gate: {e}")


def _verificar_horario_relatorio(config: ContinuousFactoryDB, company_id: int):
    """Verifica se e hora de gerar o relatorio diario."""
    agora = datetime.utcnow()
    horario_config = config.horario_relatorio or "23:00"

    try:
        hora, minuto = map(int, horario_config.split(":"))
    except ValueError:
        hora, minuto = 23, 0

    # Verificar se e a hora certa (com janela de 2 min)
    if agora.hour == hora and abs(agora.minute - minuto) <= 2:
        # Verificar se ja gerou hoje
        if config.ultimo_relatorio_em:
            ultimo = config.ultimo_relatorio_em
            if ultimo.date() == agora.date():
                return  # Ja gerou hoje

        logger.info("[CONTINUOUS] Hora do relatorio diario — gerando...")
        threading.Thread(
            target=_gerar_relatorio_diario,
            args=(company_id,),
            daemon=True,
        ).start()


def _atualizar_metricas_dia(config: ContinuousFactoryDB, db: Session, company_id: int):
    """Atualiza contadores do dia na config."""
    inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    workflows = db.query(WorkflowAutonomoDB).filter(
        WorkflowAutonomoDB.criado_em >= inicio_dia,
        WorkflowAutonomoDB.company_id == company_id,
    ).all()

    config.workflows_hoje = len(workflows)
    config.erros_hoje = sum(1 for w in workflows if w.status == "erro")

    # Custo — consultar usage tracking
    uso = db.query(UsageTrackingDB).filter(
        UsageTrackingDB.criado_em >= inicio_dia,
        UsageTrackingDB.company_id == company_id,
    ).all()
    config.custo_hoje_usd = sum(u.custo_usd for u in uso)


# =====================================================================
# STARTUP — Recuperar modo continuo ao reiniciar o servidor
# =====================================================================

def recuperar_modo_continuo():
    """
    Chamado no lifespan do FastAPI.
    Se o modo continuo estava ativo quando o servidor reiniciou,
    reinicia o worker automaticamente.
    """
    db = SessionLocal()
    try:
        configs = db.query(ContinuousFactoryDB).filter_by(ativo=True).all()
        for config in configs:
            logger.info(f"[CONTINUOUS] Recuperando modo continuo para company {config.company_id}")
            _iniciar_worker_continuo(config.company_id)
    except Exception as e:
        logger.warning(f"[CONTINUOUS] Erro ao recuperar modo continuo: {e}")
    finally:
        db.close()
