"""
Rota: Tarefas dos Agentes (persistido em SQLite)

POST /api/tarefas/executar         — Executa uma tarefa em um agente
POST /api/tarefas/reuniao          — Inicia reunião com rodadas
POST /api/tarefas/{id}/continuar   — Continua reunião com feedback do usuário
GET  /api/tarefas/historico        — Lista histórico
GET  /api/tarefas/{id}             — Detalhes + rodadas em tempo real
"""

import logging
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_fabrica, obter_usuario_atual
from database.session import get_db, SessionLocal
from database.models import UsuarioDB, TarefaDB

logger = logging.getLogger("synerium.tarefas")

router = APIRouter(prefix="/api/tarefas", tags=["Tarefas"])


# --- Schemas ---

class ExecutarTarefaRequest(BaseModel):
    squad_nome: str
    agente_indice: int
    descricao: str
    resultado_esperado: str = "Resposta completa em português brasileiro."


class ReuniaoRequest(BaseModel):
    squad_nome: str
    agentes_indices: list[int]
    pauta: str


class ContinuarReuniaoRequest(BaseModel):
    feedback: str  # Feedback/direcionamento do usuário para a próxima rodada


class RodadaItem(BaseModel):
    rodada: int
    agente: str
    resposta: str
    timestamp: str


class TarefaResponse(BaseModel):
    id: str
    squad_nome: str
    agente_nome: str
    agente_indice: int
    descricao: str
    resultado: str | None = None
    status: str = "pendente"
    erro: str | None = None
    usuario_id: int
    usuario_nome: str
    criado_em: str
    concluido_em: str | None = None
    tipo: str = "tarefa"
    participantes: list[str] | None = None
    rodadas: list[RodadaItem] | None = None
    rodada_atual: int = 1
    agente_atual: str | None = None


def _to_response(t: TarefaDB) -> TarefaResponse:
    """Converte modelo do banco para response."""
    rodadas_parsed = None
    if t.rodadas:
        rodadas_parsed = [RodadaItem(**r) for r in t.rodadas]

    return TarefaResponse(
        id=t.id,
        squad_nome=t.squad_nome,
        agente_nome=t.agente_nome,
        agente_indice=t.agente_indice,
        descricao=t.descricao,
        resultado=t.resultado,
        status=t.status,
        erro=t.erro,
        usuario_id=t.usuario_id,
        usuario_nome=t.usuario_nome,
        criado_em=t.criado_em.isoformat() if t.criado_em else "",
        concluido_em=t.concluido_em.isoformat() if t.concluido_em else None,
        tipo=t.tipo or "tarefa",
        participantes=t.participantes,
        rodadas=rodadas_parsed,
        rodada_atual=t.rodada_atual or 1,
        agente_atual=t.agente_atual,
    )


# --- Background: Tarefa simples ---

def _executar_tarefa_bg(tarefa_id: str, squad_nome: str, agente_idx: int,
                         descricao: str, resultado_esperado: str, fabrica):
    from crewai import Task, Crew, Process

    db = SessionLocal()
    try:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if not tarefa:
            return

        tarefa.status = "executando"
        db.commit()

        squad = fabrica.squads.get(squad_nome)
        if not squad or agente_idx >= len(squad.agentes):
            tarefa.status = "erro"
            tarefa.erro = "Squad ou agente não encontrado."
            db.commit()
            return

        agente = squad.agentes[agente_idx]
        tarefa.agente_atual = agente.role
        db.commit()

        crewai_tarefa = Task(
            description=descricao,
            expected_output=resultado_esperado,
            agent=agente,
        )
        crew = Crew(agents=[agente], tasks=[crewai_tarefa],
                     process=Process.sequential, verbose=True)
        resultado = crew.kickoff()

        tarefa.resultado = str(resultado)
        tarefa.status = "concluida"
        tarefa.agente_atual = None
        tarefa.concluido_em = datetime.utcnow()
        db.commit()

    except Exception as e:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if tarefa:
            tarefa.status = "erro"
            tarefa.erro = str(e)
            tarefa.agente_atual = None
            tarefa.concluido_em = datetime.utcnow()
            db.commit()
        logger.error(f"[TAREFA] Erro: {e}")
    finally:
        db.close()


# --- Background: Reunião com rodadas ---

def _executar_reuniao_bg(tarefa_id: str, squad_nome: str,
                          agentes_indices: list[int], pauta: str,
                          fabrica, rodada_num: int = 1,
                          feedback_anterior: str = ""):
    """Executa uma rodada da reunião — cada agente responde individualmente."""
    from crewai import Task, Crew, Process

    db = SessionLocal()
    try:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if not tarefa:
            return

        tarefa.status = "executando"
        tarefa.rodada_atual = rodada_num
        db.commit()

        squad = fabrica.squads.get(squad_nome)
        if not squad:
            tarefa.status = "erro"
            tarefa.erro = "Squad não encontrado."
            db.commit()
            return

        agentes = [squad.agentes[i] for i in agentes_indices if i < len(squad.agentes)]
        if not agentes:
            tarefa.status = "erro"
            tarefa.erro = "Nenhum agente válido."
            db.commit()
            return

        rodadas = tarefa.rodadas or []

        # Montar contexto com rodadas anteriores
        contexto_anterior = ""
        if rodadas:
            contexto_anterior = "\n\n--- RODADAS ANTERIORES ---\n"
            for r in rodadas:
                contexto_anterior += f"\n[Rodada {r['rodada']}] {r['agente']}:\n{r['resposta']}\n"

        if feedback_anterior:
            contexto_anterior += f"\n\n--- FEEDBACK DO CEO (Thiago) ---\n{feedback_anterior}\n"

        # Cada agente responde individualmente
        for i, agente in enumerate(agentes):
            tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
            tarefa_db.agente_atual = f"{agente.role} ({i+1}/{len(agentes)})"
            db.commit()

            logger.info(f"[REUNIÃO] Rodada {rodada_num} — {agente.role} respondendo...")

            prompt = (
                f"REUNIÃO DE EQUIPE — Rodada {rodada_num}\n"
                f"Pauta: {pauta}\n"
                f"{contexto_anterior}\n\n"
                f"Você é {agente.role}. Contribua com sua perspectiva especializada. "
                f"Seja objetivo e prático. Responda em português brasileiro."
            )

            try:
                crewai_tarefa = Task(
                    description=prompt,
                    expected_output=f"Contribuição de {agente.role} — objetiva e prática.",
                    agent=agente,
                )
                crew = Crew(agents=[agente], tasks=[crewai_tarefa],
                             process=Process.sequential, verbose=True)
                resultado = crew.kickoff()

                rodadas.append({
                    "rodada": rodada_num,
                    "agente": agente.role,
                    "resposta": str(resultado),
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Salvar progresso a cada agente
                tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                tarefa_db.rodadas = rodadas
                db.commit()

            except Exception as e:
                rodadas.append({
                    "rodada": rodada_num,
                    "agente": agente.role,
                    "resposta": f"[Erro: {str(e)}]",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                tarefa_db.rodadas = rodadas
                db.commit()

        # =====================================================
        # Sofia (Secretária Executiva) — ATA + execução de pedidos
        # =====================================================
        sofia = None
        for ag in agentes:
            if "Secretária" in ag.role or "Sofia" in ag.role:
                sofia = ag
                break

        if not sofia:
            # Buscar Sofia no squad completo (pode não estar nos participantes)
            for ag_name, squad in fabrica.squads.items():
                for ag in squad.agentes:
                    if "Secretária" in ag.role or "Sofia" in ag.role:
                        sofia = ag
                        break
                if sofia:
                    break

        if sofia:
            tarefa_db_s = db.query(TarefaDB).filter_by(id=tarefa_id).first()
            tarefa_db_s.agente_atual = f"Sofia — Secretária Executiva (compilando ata)"
            db.commit()

            logger.info(f"[REUNIÃO] Rodada {rodada_num} — Sofia compilando ATA e executando pedidos...")

            # Compilar o que cada agente disse nesta rodada
            contribuicoes = ""
            for r in rodadas:
                if r["rodada"] == rodada_num:
                    contribuicoes += f"\n{r['agente']}:\n{r['resposta']}\n"

            prompt_sofia = (
                f"REUNIÃO DE EQUIPE — Rodada {rodada_num}\n"
                f"Pauta: {pauta}\n\n"
                f"--- CONTRIBUIÇÕES DOS AGENTES ---\n{contribuicoes}\n\n"
                f"{'--- FEEDBACK DO CEO ---' + chr(10) + feedback_anterior + chr(10) if feedback_anterior else ''}"
                f"Você é Sofia, a Secretária Executiva. Faça EXATAMENTE isto:\n"
                f"1. COMPILE uma ATA profissional desta rodada com: resumo, decisões, pendências e próximos passos\n"
                f"2. Se o CEO pediu algo prático (criar landing page, .zip, enviar email, etc.), EXECUTE AGORA usando suas ferramentas\n"
                f"3. Se criou arquivos, compacte em .zip e envie por email para thiago@objetivasolucao.com.br\n"
                f"4. Seja objetiva e eficiente. Responda em português brasileiro."
            )

            try:
                crewai_tarefa_sofia = Task(
                    description=prompt_sofia,
                    expected_output="ATA da reunião + execução de pedidos práticos.",
                    agent=sofia,
                )
                crew_sofia = Crew(agents=[sofia], tasks=[crewai_tarefa_sofia],
                                  process=Process.sequential, verbose=True)
                resultado_sofia = crew_sofia.kickoff()

                rodadas.append({
                    "rodada": rodada_num,
                    "agente": "📋 Sofia — Secretária Executiva (ATA)",
                    "resposta": str(resultado_sofia),
                    "timestamp": datetime.utcnow().isoformat(),
                })

                tarefa_db_s = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                tarefa_db_s.rodadas = rodadas
                db.commit()

            except Exception as e:
                rodadas.append({
                    "rodada": rodada_num,
                    "agente": "📋 Sofia — Secretária Executiva (ATA)",
                    "resposta": f"[Erro na ata: {str(e)}]",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                tarefa_db_s = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                tarefa_db_s.rodadas = rodadas
                db.commit()

            logger.info(f"[REUNIÃO] Sofia concluiu ATA da rodada {rodada_num}.")

        # Rodada concluída — aguardar feedback
        tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        tarefa_db.rodadas = rodadas
        tarefa_db.agente_atual = None
        tarefa_db.status = "aguardando_feedback"

        # Compilar resultado da rodada
        resultado_rodada = f"=== RODADA {rodada_num} ===\n\n"
        for r in rodadas:
            if r["rodada"] == rodada_num:
                resultado_rodada += f"**{r['agente']}:**\n{r['resposta']}\n\n"

        tarefa_db.resultado = resultado_rodada
        db.commit()

        logger.info(f"[REUNIÃO] Rodada {rodada_num} concluída — aguardando feedback do CEO.")

    except Exception as e:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if tarefa:
            tarefa.status = "erro"
            tarefa.erro = str(e)
            tarefa.agente_atual = None
            tarefa.concluido_em = datetime.utcnow()
            db.commit()
        logger.error(f"[REUNIÃO] Erro: {e}")
    finally:
        db.close()


# --- Endpoints ---

@router.post("/executar", response_model=TarefaResponse)
def executar_tarefa(
    req: ExecutarTarefaRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Executa uma tarefa em um agente específico (background)."""
    squad = fabrica.squads.get(req.squad_nome)
    if not squad:
        raise HTTPException(status_code=404, detail=f"Squad '{req.squad_nome}' não encontrado.")
    if req.agente_indice >= len(squad.agentes):
        raise HTTPException(status_code=400, detail=f"Agente #{req.agente_indice} não existe.")

    agente = squad.agentes[req.agente_indice]
    tarefa_id = str(uuid.uuid4())[:8]

    tarefa = TarefaDB(
        id=tarefa_id, squad_nome=req.squad_nome, agente_nome=agente.role,
        agente_indice=req.agente_indice, descricao=req.descricao,
        status="pendente", tipo="tarefa",
        usuario_id=usuario.id, usuario_nome=usuario.nome,
        company_id=usuario.company_id,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)

    threading.Thread(
        target=_executar_tarefa_bg,
        args=(tarefa_id, req.squad_nome, req.agente_indice,
              req.descricao, req.resultado_esperado, fabrica),
        daemon=True,
    ).start()

    return _to_response(tarefa)


@router.post("/reuniao", response_model=TarefaResponse)
def executar_reuniao(
    req: ReuniaoRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Inicia uma reunião com rodadas. Rodada 1 executa automaticamente."""
    squad = fabrica.squads.get(req.squad_nome)
    if not squad:
        raise HTTPException(status_code=404, detail=f"Squad '{req.squad_nome}' não encontrado.")
    for idx in req.agentes_indices:
        if idx >= len(squad.agentes):
            raise HTTPException(status_code=400, detail=f"Agente #{idx} não existe.")

    nomes = [squad.agentes[i].role for i in req.agentes_indices]
    tarefa_id = str(uuid.uuid4())[:8]

    tarefa = TarefaDB(
        id=tarefa_id, squad_nome=req.squad_nome, agente_nome="Reunião",
        agente_indice=-1, descricao=req.pauta,
        status="pendente", tipo="reuniao",
        participantes=nomes, agentes_indices=req.agentes_indices,
        rodadas=[], rodada_atual=1,
        usuario_id=usuario.id, usuario_nome=usuario.nome,
        company_id=usuario.company_id,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)

    threading.Thread(
        target=_executar_reuniao_bg,
        args=(tarefa_id, req.squad_nome, req.agentes_indices, req.pauta, fabrica),
        daemon=True,
    ).start()

    return _to_response(tarefa)


@router.post("/{tarefa_id}/continuar", response_model=TarefaResponse)
def continuar_reuniao(
    tarefa_id: str,
    req: ContinuarReuniaoRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Continua uma reunião com feedback do usuário → nova rodada."""
    tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    if tarefa.tipo != "reuniao":
        raise HTTPException(status_code=400, detail="Apenas reuniões podem ser continuadas.")
    if tarefa.status != "aguardando_feedback":
        raise HTTPException(status_code=400, detail=f"Reunião não está aguardando feedback (status: {tarefa.status}).")

    # Salvar feedback como rodada especial
    rodadas = tarefa.rodadas or []
    rodadas.append({
        "rodada": tarefa.rodada_atual,
        "agente": f"CEO ({usuario.nome})",
        "resposta": req.feedback,
        "timestamp": datetime.utcnow().isoformat(),
    })
    tarefa.rodadas = rodadas

    nova_rodada = (tarefa.rodada_atual or 1) + 1
    tarefa.rodada_atual = nova_rodada
    tarefa.status = "executando"
    db.commit()

    agentes_indices = tarefa.agentes_indices or []

    threading.Thread(
        target=_executar_reuniao_bg,
        args=(tarefa_id, tarefa.squad_nome, agentes_indices,
              tarefa.descricao, fabrica, nova_rodada, req.feedback),
        daemon=True,
    ).start()

    logger.info(f"[REUNIÃO] Rodada {nova_rodada} iniciada com feedback: {req.feedback[:60]}...")
    db.refresh(tarefa)
    return _to_response(tarefa)


@router.post("/{tarefa_id}/encerrar", response_model=TarefaResponse)
def encerrar_reuniao(
    tarefa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Encerra uma reunião que está aguardando feedback."""
    tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    tarefa.status = "concluida"
    tarefa.agente_atual = None
    tarefa.concluido_em = datetime.utcnow()
    db.commit()
    db.refresh(tarefa)

    logger.info(f"[REUNIÃO] Encerrada: {tarefa_id}")
    return _to_response(tarefa)


@router.post("/{tarefa_id}/reabrir", response_model=TarefaResponse)
def reabrir_reuniao(
    tarefa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Reabre uma reunião encerrada — volta para aguardando_feedback."""
    tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    if tarefa.tipo != "reuniao":
        raise HTTPException(status_code=400, detail="Apenas reuniões podem ser reabertas.")

    tarefa.status = "aguardando_feedback"
    tarefa.concluido_em = None
    db.commit()
    db.refresh(tarefa)

    logger.info(f"[REUNIÃO] Reaberta: {tarefa_id}")
    return _to_response(tarefa)


@router.get("/historico", response_model=list[TarefaResponse])
def listar_historico(
    limite: int = 50,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista histórico filtrado por usuário (mais recentes primeiro)."""
    # Auto-limpeza: resetar tarefas travadas há mais de 10 min
    from datetime import timezone, timedelta
    agora = datetime.now(timezone.utc)
    limite_timeout = agora - timedelta(minutes=TIMEOUT_MINUTOS)

    travadas = db.query(TarefaDB).filter(
        TarefaDB.status == "executando",
        TarefaDB.usuario_id == usuario.id,
    ).all()
    for t in travadas:
        criado = t.criado_em
        if criado and criado.tzinfo is None:
            criado = criado.replace(tzinfo=timezone.utc)
        if criado and criado < limite_timeout:
            t.status = "erro"
            t.erro = f"Timeout ({TIMEOUT_MINUTOS} min). Resetada automaticamente."
            t.agente_atual = None
            t.concluido_em = agora.replace(tzinfo=None)
            logger.info(f"[AUTO-TIMEOUT] Tarefa {t.id} resetada (>{TIMEOUT_MINUTOS}min)")
    if travadas:
        db.commit()

    tarefas = (
        db.query(TarefaDB)
        .filter_by(usuario_id=usuario.id)
        .order_by(TarefaDB.criado_em.desc())
        .limit(limite)
        .all()
    )
    return [_to_response(t) for t in tarefas]


@router.get("/{tarefa_id}", response_model=TarefaResponse)
def buscar_tarefa(
    tarefa_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Busca detalhes com rodadas em tempo real."""
    tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return _to_response(tarefa)


# =====================================================================
# Timeout automático — reseta reuniões travadas
# =====================================================================

TIMEOUT_MINUTOS = 10  # Reuniões executando há mais de 10 min são resetadas


@router.post("/limpar-travadas")
def limpar_travadas(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Reseta manualmente todas as tarefas/reuniões travadas."""
    from datetime import timezone, timedelta

    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(minutes=TIMEOUT_MINUTOS)

    travadas = db.query(TarefaDB).filter(
        TarefaDB.status.in_(["executando", "pendente"]),
    ).all()

    resetadas = 0
    for t in travadas:
        # Se criada há mais de TIMEOUT_MINUTOS ou se não tem agente_atual (travou)
        criado = t.criado_em
        if criado and criado.tzinfo is None:
            from datetime import timezone as tz
            criado = criado.replace(tzinfo=tz.utc)

        if not t.agente_atual or (criado and criado < limite):
            t.status = "erro"
            t.erro = f"Timeout automático ({TIMEOUT_MINUTOS} min). Reunião resetada."
            t.agente_atual = None
            t.concluido_em = agora.replace(tzinfo=None)
            resetadas += 1

    db.commit()
    logger.info(f"[LIMPEZA] {resetadas} tarefa(s) travada(s) resetada(s) por {usuario.nome}")

    return {"resetadas": resetadas, "mensagem": f"{resetadas} tarefa(s) resetada(s)."}
