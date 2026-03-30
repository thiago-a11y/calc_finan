"""
Rota: Tarefas dos Agentes (persistido em SQLite)

POST /api/tarefas/executar         — Executa uma tarefa em um agente
POST /api/tarefas/reuniao          — Inicia reunião com rodadas
POST /api/tarefas/{id}/continuar   — Continua reunião com feedback do usuário
GET  /api/tarefas/historico        — Lista histórico
GET  /api/tarefas/{id}             — Detalhes + rodadas em tempo real
"""

import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_fabrica, obter_usuario_atual
from database.session import get_db, SessionLocal
from database.models import UsuarioDB, TarefaDB, AgenteCatalogoDB, WorkflowAutonomoDB

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
    paralelo: bool = True  # True = agentes respondem em paralelo (mais rapido)


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

        # Enriquecer descricao com regras de comportamento
        descricao_enriquecida = (
            f"{descricao}\n\n"
            "REGRAS OBRIGATORIAS:\n"
            "- NUNCA envie emails sem o usuario pedir explicitamente\n"
            "- Se nao conseguir acessar arquivos do projeto, informe ao usuario e sugira usar o Code Studio\n"
            "- Responda de forma direta e objetiva em portugues brasileiro\n"
            "- NAO invente informacoes — use suas ferramentas para consultar dados reais"
        )

        crewai_tarefa = Task(
            description=descricao_enriquecida,
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


# --- Helper: executa 1 agente isolado (para uso em thread pool) ---

def _executar_agente_isolado(agente, prompt, resultado_esperado, rodada_num):
    """Executa 1 agente em thread separada. Retorna dict com resultado."""
    from crewai import Task, Crew, Process
    try:
        crewai_tarefa = Task(
            description=prompt,
            expected_output=resultado_esperado,
            agent=agente,
        )
        crew = Crew(agents=[agente], tasks=[crewai_tarefa],
                     process=Process.sequential, verbose=True)
        resultado = crew.kickoff()
        return {
            "rodada": rodada_num,
            "agente": agente.role,
            "resposta": str(resultado),
            "timestamp": datetime.utcnow().isoformat(),
            "sucesso": True,
        }
    except Exception as e:
        return {
            "rodada": rodada_num,
            "agente": agente.role,
            "resposta": f"[Erro: {str(e)}]",
            "timestamp": datetime.utcnow().isoformat(),
            "sucesso": False,
        }


# --- Background: Reunião PARALELA ---

def _executar_reuniao_paralela_bg(tarefa_id: str, squad_nome: str,
                                   agentes_indices: list[int], pauta: str,
                                   fabrica, rodada_num: int = 1,
                                   feedback_anterior: str = ""):
    """Executa uma rodada da reunião com agentes em PARALELO (ThreadPoolExecutor)."""
    db = SessionLocal()
    try:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if not tarefa:
            return

        tarefa.status = "executando"
        tarefa.rodada_atual = rodada_num
        tarefa.agente_atual = f"⚡ {len(agentes_indices)} agentes em paralelo"
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

        # Preparar prompts para todos os agentes
        prompts = []
        for agente in agentes:
            prompt = (
                f"REUNIÃO DE EQUIPE — Rodada {rodada_num} (modo paralelo)\n"
                f"Pauta: {pauta}\n"
                f"{contexto_anterior}\n\n"
                f"Você é {agente.role}. Contribua com sua perspectiva especializada. "
                f"Seja objetivo e prático. Responda em português brasileiro."
            )
            prompts.append((agente, prompt))

        logger.info(f"[REUNIÃO-PARALELA] Rodada {rodada_num} — {len(agentes)} agentes em paralelo...")

        # Executar todos os agentes em paralelo
        with ThreadPoolExecutor(max_workers=min(len(agentes), 4)) as executor:
            futures = {
                executor.submit(
                    _executar_agente_isolado,
                    agente, prompt,
                    f"Contribuição de {agente.role} — objetiva e prática.",
                    rodada_num,
                ): agente
                for agente, prompt in prompts
            }

            for future in as_completed(futures):
                resultado = future.result()
                rodadas.append(resultado)

                # Salvar progresso incremental (cada agente que termina)
                tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                nomes_concluidos = [r["agente"] for r in rodadas if r["rodada"] == rodada_num]
                tarefa_db.agente_atual = f"⚡ {len(nomes_concluidos)}/{len(agentes)} concluídos"
                tarefa_db.rodadas = rodadas
                db.commit()

                logger.info(f"[REUNIÃO-PARALELA] {resultado['agente']} concluiu ({len(nomes_concluidos)}/{len(agentes)})")

        # Sofia faz ATA (sequencial — precisa de todas as respostas)
        sofia = None
        for ag in agentes:
            if "Secretária" in ag.role or "Sofia" in ag.role:
                sofia = ag
                break
        if not sofia:
            for sq in fabrica.squads.values():
                for ag in sq.agentes:
                    if "Secretária" in ag.role or "Sofia" in ag.role:
                        sofia = ag
                        break
                if sofia:
                    break

        if sofia:
            tarefa_db_s = db.query(TarefaDB).filter_by(id=tarefa_id).first()
            tarefa_db_s.agente_atual = "Sofia — compilando ATA"
            db.commit()

            contribuicoes = "\n".join([
                f"{r['agente']}:\n{r['resposta']}"
                for r in rodadas if r["rodada"] == rodada_num
            ])

            prompt_sofia = (
                f"REUNIÃO DE EQUIPE — Rodada {rodada_num}\nPauta: {pauta}\n\n"
                f"--- CONTRIBUIÇÕES (paralelas) ---\n{contribuicoes}\n\n"
                f"{'--- FEEDBACK DO CEO ---' + chr(10) + feedback_anterior + chr(10) if feedback_anterior else ''}"
                f"Compile uma ATA profissional: resumo, decisões, pendências, próximos passos. "
                f"Responda em português brasileiro."
            )

            resultado_sofia = _executar_agente_isolado(
                sofia, prompt_sofia, "ATA da reunião.", rodada_num
            )
            resultado_sofia["agente"] = "📋 Sofia — Secretária Executiva (ATA)"
            rodadas.append(resultado_sofia)

            tarefa_db_s = db.query(TarefaDB).filter_by(id=tarefa_id).first()
            tarefa_db_s.rodadas = rodadas
            db.commit()

        # Rodada concluída
        tarefa_db = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        tarefa_db.rodadas = rodadas
        tarefa_db.agente_atual = None
        tarefa_db.status = "aguardando_feedback"

        resultado_rodada = f"=== RODADA {rodada_num} (⚡ PARALELO) ===\n\n"
        for r in rodadas:
            if r["rodada"] == rodada_num:
                resultado_rodada += f"**{r['agente']}:**\n{r['resposta']}\n\n"
        tarefa_db.resultado = resultado_rodada
        db.commit()

        logger.info(f"[REUNIÃO-PARALELA] Rodada {rodada_num} concluída — {len(agentes)} agentes.")

    except Exception as e:
        tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
        if tarefa:
            tarefa.status = "erro"
            tarefa.erro = str(e)
            tarefa.agente_atual = None
            tarefa.concluido_em = datetime.utcnow()
            db.commit()
        logger.error(f"[REUNIÃO-PARALELA] Erro: {e}")
    finally:
        db.close()


# --- Background: Reunião com rodadas (SEQUENCIAL — original) ---

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

    # Escolher modo de execução: paralelo (default) ou sequencial
    func_bg = _executar_reuniao_paralela_bg if req.paralelo else _executar_reuniao_bg
    modo = "paralelo" if req.paralelo else "sequencial"
    logger.info(f"[REUNIÃO] Iniciada ({modo}): {len(nomes)} agentes — {req.pauta[:60]}...")

    threading.Thread(
        target=func_bg,
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

    # Continuar no mesmo modo (paralelo por default)
    threading.Thread(
        target=_executar_reuniao_paralela_bg,
        args=(tarefa_id, tarefa.squad_nome, agentes_indices,
              tarefa.descricao, fabrica, nova_rodada, req.feedback),
        daemon=True,
    ).start()

    logger.info(f"[REUNIÃO] Rodada {nova_rodada} (paralelo) com feedback: {req.feedback[:60]}...")
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


@router.post("/{tarefa_id}/retomar", response_model=TarefaResponse)
def retomar_tarefa(
    tarefa_id: str,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retoma uma tarefa/reuniao que deu erro ou timeout — re-executa do ponto onde parou."""
    tarefa = db.query(TarefaDB).filter_by(id=tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    if tarefa.status not in ("erro", "concluida"):
        raise HTTPException(status_code=400, detail=f"Tarefa não pode ser retomada (status: {tarefa.status}).")

    if tarefa.tipo == "reuniao":
        # Reuniao: reabrir para feedback + nova rodada
        tarefa.status = "aguardando_feedback"
        tarefa.erro = None
        tarefa.concluido_em = None
        db.commit()
        db.refresh(tarefa)
        logger.info(f"[RETOMAR] Reunião {tarefa_id} reaberta para continuar.")
        return _to_response(tarefa)
    else:
        # Tarefa simples: re-executar em background
        tarefa.status = "pendente"
        tarefa.erro = None
        tarefa.resultado = None
        tarefa.concluido_em = None
        db.commit()

        threading.Thread(
            target=_executar_tarefa_bg,
            args=(tarefa_id, tarefa.squad_nome, tarefa.agente_indice,
                  tarefa.descricao, "Resposta completa em português brasileiro.", fabrica),
            daemon=True,
        ).start()

        db.refresh(tarefa)
        logger.info(f"[RETOMAR] Tarefa {tarefa_id} re-executada.")
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

TIMEOUT_MINUTOS = 30  # Reuniões executando há mais de 30 min são resetadas


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


# =====================================================================
# Dynamic Team Assembly — Montagem inteligente de time
# =====================================================================

# Indicadores de problema que sugerem necessidade de time
_INDICADORES_PROBLEMA = [
    re.compile(r'(deu|dá|ta dando|está dando)\s*(pau|erro|bug|problema)', re.IGNORECASE),
    re.compile(r'quebr(ou|ando|a|ei)', re.IGNORECASE),
    re.compile(r'não\s*(funciona|roda|compila|builda|deploy)', re.IGNORECASE),
    re.compile(r'preciso de ajuda|me ajuda', re.IGNORECASE),
    re.compile(r'emergência|urgente|crítico|urgencia', re.IGNORECASE),
    re.compile(r'refatorar|migrar|arquitetura|redesign', re.IGNORECASE),
    re.compile(r'deploy.*(falh|err|prob)|prod.*(caiu|fora)', re.IGNORECASE),
    re.compile(r'segurança|vulnerabilidade|vazamento', re.IGNORECASE),
    re.compile(r'performance|lento|timeout|memory|memória', re.IGNORECASE),
    re.compile(r'test(e|es|ar|ando)|cobertura|coverage|unit test', re.IGNORECASE),
    re.compile(r'pull request|PR|merge|branch|conflito', re.IGNORECASE),
    re.compile(r'git(hub|bucket)|reposit(ório|orio)|commit|push', re.IGNORECASE),
    re.compile(r'pipeline|ci.?cd|actions|workflow', re.IGNORECASE),
]

# Mapa categoria → perfis recomendados
_CATEGORIA_PERFIS = {
    "codigo": ["backend_dev", "frontend_dev", "qa_seguranca"],
    "infraestrutura": ["devops", "tech_lead", "qa_seguranca"],
    "seguranca": ["qa_seguranca", "tech_lead", "backend_dev"],
    "performance": ["backend_dev", "devops", "tech_lead"],
    "arquitetura": ["tech_lead", "arquiteto", "backend_dev"],
    "negocio": ["product_manager", "tech_lead", "secretaria_executiva"],
    "frontend": ["frontend_dev", "tech_lead", "qa_seguranca"],
    "deploy": ["devops", "qa_seguranca", "tech_lead"],
    "testes": ["qa_seguranca", "backend_dev", "tech_lead"],
    "github": ["devops", "tech_lead", "qa_seguranca"],
    "gitbucket": ["devops", "tech_lead", "qa_seguranca"],
    "pr": ["devops", "qa_seguranca", "tech_lead"],
    "merge": ["devops", "tech_lead", "qa_seguranca"],
}


class MontarTimeRequest(BaseModel):
    mensagem: str
    squad_nome: str
    agente_atual_idx: int = -1
    contexto: str = ""


def _detectar_necessidade_time(mensagem: str) -> bool:
    """Detecta se a mensagem indica problema que precisa de time (regex, custo zero)."""
    for padrao in _INDICADORES_PROBLEMA:
        if padrao.search(mensagem):
            return True
    return False


async def _selecionar_agentes_llm(mensagem: str, agentes_catalogo: list[dict]) -> dict:
    """Usa Sonnet para selecionar os agentes mais adequados (~$0.01)."""
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        lista_agentes = "\n".join([
            f"- ID:{a['id']} | {a['nome']} ({a['perfil']}) — categoria: {a['categoria']}"
            for a in agentes_catalogo
        ])

        system = (
            "Voce e um seletor de agentes do Synerium Factory. "
            "Dado um problema, selecione 2-3 agentes do catalogo que melhor podem resolver. "
            "Retorne APENAS um JSON valido (sem markdown) no formato: "
            '{"agentes": [{"id": N, "razao": "breve"}], "razao_geral": "resumo", "confianca": 0.9}'
        )
        prompt = (
            f"Problema do usuario:\n{mensagem[:500]}\n\n"
            f"Agentes disponiveis:\n{lista_agentes}\n\n"
            f"Selecione 2-3 agentes mais relevantes. JSON:"
        )

        llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=500, temperature=0)
        resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=prompt)])

        import json
        # Extrair JSON da resposta (pode vir com texto extra)
        texto = resp.content.strip()
        # Tentar encontrar JSON na resposta
        inicio = texto.find("{")
        fim = texto.rfind("}") + 1
        if inicio >= 0 and fim > inicio:
            return json.loads(texto[inicio:fim])
        return {"agentes": [], "razao_geral": "Nao foi possivel analisar", "confianca": 0}

    except Exception as e:
        logger.warning(f"[MontarTime] Erro LLM: {e}")
        return {"agentes": [], "razao_geral": f"Erro: {str(e)[:100]}", "confianca": 0}


@router.post("/montar-time")
async def montar_time(
    req: MontarTimeRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Analisa a mensagem do usuario e sugere um time de agentes para resolver o problema.
    Usa regex (custo zero) + LLM Sonnet (~$0.01) para selecao inteligente.
    """
    # 1. Buscar agentes do catalogo
    agentes_db = db.query(AgenteCatalogoDB).filter_by(ativo=True).all()
    if not agentes_db:
        return {
            "necessita_time": False,
            "razao": "Nenhum agente no catalogo",
            "agentes": [],
        }

    agentes_lista = [
        {
            "id": a.id,
            "nome": a.nome_exibicao,
            "perfil": a.perfil_agente,
            "categoria": a.categoria,
            "papel": a.papel,
            "icone": a.icone,
        }
        for a in agentes_db
    ]

    # 2. Deteccao rapida (regex)
    necessita = _detectar_necessidade_time(req.mensagem)

    if not necessita:
        # Mesmo sem indicador forte, permitir montagem manual
        return {
            "necessita_time": False,
            "razao": "Mensagem nao indica problema complexo. Clique 'Montar Time' para forcar.",
            "agentes": agentes_lista,  # Retorna catalogo completo para selecao manual
        }

    # 3. Selecao inteligente via LLM
    resultado_llm = await _selecionar_agentes_llm(req.mensagem, agentes_lista)

    # 4. Enriquecer com dados do catalogo
    agentes_selecionados = []
    for sel in resultado_llm.get("agentes", []):
        agente_db = next((a for a in agentes_lista if a["id"] == sel.get("id")), None)
        if agente_db:
            agentes_selecionados.append({
                **agente_db,
                "razao": sel.get("razao", ""),
            })

    confianca = resultado_llm.get("confianca", 0)

    return {
        "necessita_time": True,
        "razao_geral": resultado_llm.get("razao_geral", ""),
        "agentes_sugeridos": agentes_selecionados,
        "confianca": confianca,
        "auto_iniciar": confianca >= 0.85,
        "catalogo_completo": agentes_lista,  # Para ajuste manual
    }


# =====================================================================
# AUTONOMOUS SQUADS — Workflow BMAD completo automatizado
# =====================================================================

# Nomes das fases BMAD
FASES_BMAD = {
    1: "Analise",
    2: "Planejamento",
    3: "Solucao",
    4: "Implementacao",
}

# Prompts por fase (o que cada fase deve produzir)
PROMPTS_FASE = {
    1: (
        "FASE 1 — ANALISE\n"
        "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
        "Voce deve:\n"
        "1. Analisar o problema/feature solicitado\n"
        "2. Pesquisar viabilidade tecnica\n"
        "3. Identificar riscos e dependencias\n"
        "4. Produzir um Product Brief com escopo, objetivo e criterios de sucesso\n"
        "Responda de forma estruturada em portugues brasileiro."
    ),
    2: (
        "FASE 2 — PLANEJAMENTO\n"
        "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
        "Resultado da Fase 1 (Analise):\n{output_anterior}\n\n"
        "Voce deve:\n"
        "1. Criar um PRD (Product Requirements Document) completo\n"
        "2. Definir requisitos funcionais e nao-funcionais\n"
        "3. Criar epicos e stories com criterios de aceitacao BDD (Given/When/Then)\n"
        "4. Priorizar e estimar complexidade\n"
        "Responda de forma estruturada em portugues brasileiro."
    ),
    3: (
        "FASE 3 — SOLUCAO (Arquitetura)\n"
        "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
        "Resultado do Planejamento:\n{output_anterior}\n\n"
        "Voce deve:\n"
        "1. Definir arquitetura tecnica (componentes, patterns, stack)\n"
        "2. Criar ADRs (Architecture Decision Records) para decisoes criticas\n"
        "3. Fazer Implementation Readiness Check\n"
        "4. Listar arquivos que serao criados/modificados\n"
        "Responda de forma estruturada em portugues brasileiro."
    ),
    4: (
        "FASE 4 — IMPLEMENTACAO\n"
        "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
        "Arquitetura definida:\n{output_anterior}\n\n"
        "Voce deve:\n"
        "1. Implementar a solucao seguindo a arquitetura\n"
        "2. Escrever testes para cada componente\n"
        "3. Fazer code review cruzado\n"
        "4. Validar que todos os criterios de aceitacao passam\n"
        "5. Preparar para deploy\n"
        "Responda com codigo completo quando aplicavel. Portugues brasileiro."
    ),
}

# Agentes por fase (perfis do catalogo)
AGENTES_POR_FASE = {
    1: ["product_manager", "tech_lead"],
    2: ["product_manager", "frontend_dev", "tech_lead"],
    3: ["tech_lead", "backend_dev", "qa_seguranca"],
    4: ["backend_dev", "frontend_dev", "qa_seguranca"],
}

# Gates por fase
GATES_FASE = {
    1: "soft",   # Auto-pass (opcional)
    2: "hard",   # CEO/Operations Lead deve aprovar PRD
    3: "hard",   # Implementation Readiness Check
    4: "hard",   # Deploy requer aprovacao
}


class IniciarAutonomoRequest(BaseModel):
    titulo: str
    descricao: str = ""
    squad_nome: str
    projeto_id: int = 0
    pular_analise: bool = False


class AprovarGateRequest(BaseModel):
    decisao: str  # "aprovar", "rejeitar", "ajustar"
    feedback: str = ""


@router.post("/autonomo")
def iniciar_autonomo(
    req: IniciarAutonomoRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Inicia workflow autonomo BMAD completo."""
    squad = fabrica.squads.get(req.squad_nome)
    if not squad:
        raise HTTPException(status_code=404, detail=f"Squad '{req.squad_nome}' nao encontrado.")

    workflow_id = str(uuid.uuid4())[:8]
    fase_inicial = 2 if req.pular_analise else 1

    workflow = WorkflowAutonomoDB(
        id=workflow_id,
        titulo=req.titulo,
        descricao=req.descricao,
        fase_atual=fase_inicial,
        status="em_execucao",
        agentes_ids=[],
        outputs={},
        gates={},
        projeto_id=req.projeto_id,
        squad_nome=req.squad_nome,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        company_id=usuario.company_id or 1,
    )

    if req.pular_analise:
        workflow.gates["fase_1"] = {"status": "pulado", "por": "usuario"}

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    # Iniciar execucao em background
    threading.Thread(
        target=_executar_workflow_autonomo_bg,
        args=(workflow_id, req.squad_nome, req.titulo, req.descricao, fase_inicial, fabrica),
        daemon=True,
    ).start()

    logger.info(f"[AUTONOMO] Workflow {workflow_id} iniciado: {req.titulo} (fase {fase_inicial})")

    return {
        "id": workflow_id,
        "titulo": req.titulo,
        "fase_atual": fase_inicial,
        "status": "em_execucao",
    }


@router.get("/autonomo/{workflow_id}")
def buscar_autonomo(
    workflow_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Busca status completo do workflow autonomo."""
    wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow nao encontrado.")

    # Buscar tarefa atual (reuniao em andamento)
    tarefa_atual = None
    if wf.tarefa_atual_id:
        t = db.query(TarefaDB).filter_by(id=wf.tarefa_atual_id).first()
        if t:
            tarefa_atual = {
                "id": t.id,
                "status": t.status,
                "agente_atual": t.agente_atual,
                "rodadas": t.rodadas or [],
                "resultado": t.resultado,
            }

    return {
        "id": wf.id,
        "titulo": wf.titulo,
        "descricao": wf.descricao,
        "fase_atual": wf.fase_atual,
        "fase_nome": FASES_BMAD.get(wf.fase_atual, "?"),
        "status": wf.status,
        "outputs": wf.outputs or {},
        "gates": wf.gates or {},
        "agentes_ids": wf.agentes_ids or [],
        "tarefa_atual": tarefa_atual,
        "projeto_id": wf.projeto_id,
        "criado_em": wf.criado_em.isoformat() if wf.criado_em else "",
        "atualizado_em": wf.atualizado_em.isoformat() if wf.atualizado_em else "",
    }


@router.get("/autonomo")
def listar_autonomos(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista workflows autonomos do usuario."""
    wfs = (
        db.query(WorkflowAutonomoDB)
        .filter_by(usuario_id=usuario.id)
        .order_by(WorkflowAutonomoDB.criado_em.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": wf.id,
            "titulo": wf.titulo,
            "fase_atual": wf.fase_atual,
            "fase_nome": FASES_BMAD.get(wf.fase_atual, "?"),
            "status": wf.status,
            "criado_em": wf.criado_em.isoformat() if wf.criado_em else "",
        }
        for wf in wfs
    ]


@router.post("/autonomo/{workflow_id}/aprovar-gate")
def aprovar_gate(
    workflow_id: str,
    req: AprovarGateRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aprova, rejeita ou ajusta um gate do workflow."""
    wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow nao encontrado.")
    if wf.status != "aguardando_gate":
        raise HTTPException(status_code=400, detail=f"Workflow nao esta aguardando gate (status: {wf.status})")

    fase = wf.fase_atual
    gates = wf.gates or {}

    if req.decisao == "aprovar":
        gates[f"fase_{fase}"] = {"status": "aprovado", "por": usuario.nome, "feedback": req.feedback}
        wf.gates = gates
        proxima_fase = fase + 1

        if proxima_fase > 4:
            wf.status = "concluido"
            wf.atualizado_em = datetime.utcnow()
            db.commit()
            logger.info(f"[AUTONOMO] Workflow {workflow_id} CONCLUIDO!")
            return {"mensagem": "Workflow concluido com sucesso!", "status": "concluido"}

        wf.fase_atual = proxima_fase
        wf.status = "em_execucao"
        wf.atualizado_em = datetime.utcnow()
        db.commit()

        # Continuar execucao em background
        threading.Thread(
            target=_executar_workflow_autonomo_bg,
            args=(workflow_id, wf.squad_nome, wf.titulo, wf.descricao, proxima_fase, fabrica),
            daemon=True,
        ).start()

        logger.info(f"[AUTONOMO] Gate fase {fase} aprovado → iniciando fase {proxima_fase}")
        return {"mensagem": f"Fase {fase} aprovada! Iniciando fase {proxima_fase}.", "status": "em_execucao", "fase": proxima_fase}

    elif req.decisao == "rejeitar":
        gates[f"fase_{fase}"] = {"status": "rejeitado", "por": usuario.nome, "feedback": req.feedback}
        wf.gates = gates
        wf.status = "em_execucao"
        wf.atualizado_em = datetime.utcnow()
        db.commit()

        # Refazer a mesma fase com feedback
        threading.Thread(
            target=_executar_workflow_autonomo_bg,
            args=(workflow_id, wf.squad_nome, wf.titulo, wf.descricao + f"\n\nFEEDBACK DO CEO: {req.feedback}", fase, fabrica),
            daemon=True,
        ).start()

        return {"mensagem": f"Fase {fase} rejeitada. Refazendo com feedback.", "status": "em_execucao"}

    elif req.decisao == "cancelar":
        wf.status = "cancelado"
        wf.atualizado_em = datetime.utcnow()
        db.commit()
        return {"mensagem": "Workflow cancelado.", "status": "cancelado"}

    raise HTTPException(status_code=400, detail="Decisao invalida. Use: aprovar, rejeitar, cancelar")


@router.post("/autonomo/{workflow_id}/cancelar")
def cancelar_autonomo(
    workflow_id: str,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cancela workflow em andamento."""
    wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow nao encontrado.")
    wf.status = "cancelado"
    wf.atualizado_em = datetime.utcnow()
    db.commit()
    return {"mensagem": "Workflow cancelado.", "status": "cancelado"}


def _executar_workflow_autonomo_bg(
    workflow_id: str,
    squad_nome: str,
    titulo: str,
    descricao: str,
    fase_inicial: int,
    fabrica,
):
    """
    Executa o workflow BMAD autonomo em background.
    Para cada fase: monta time → executa reuniao → salva output → verifica gate.
    """
    from crewai import Task, Crew, Process

    db = SessionLocal()
    try:
        wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if not wf or wf.status == "cancelado":
            return

        squad = fabrica.squads.get(squad_nome)
        if not squad:
            wf.status = "erro"
            wf.outputs = {**(wf.outputs or {}), "erro": f"Squad '{squad_nome}' nao encontrado"}
            db.commit()
            return

        fase = fase_inicial
        outputs = wf.outputs or {}

        while fase <= 4:
            if wf.status == "cancelado":
                break

            logger.info(f"[AUTONOMO] Workflow {workflow_id} — Iniciando Fase {fase}: {FASES_BMAD[fase]}")

            # Atualizar status
            wf.fase_atual = fase
            wf.status = "em_execucao"
            wf.atualizado_em = datetime.utcnow()
            db.commit()

            # Selecionar agentes para esta fase
            perfis_fase = AGENTES_POR_FASE.get(fase, ["tech_lead", "backend_dev"])
            agentes_disponiveis = [
                a for i, a in enumerate(squad.agentes)
                if i < len(squad.agentes)
            ]

            # Usar ate 3 agentes (limite de economia)
            agentes_fase = agentes_disponiveis[:min(3, len(agentes_disponiveis))]
            if not agentes_fase:
                wf.status = "erro"
                outputs[f"fase_{fase}"] = "Erro: nenhum agente disponivel no squad"
                wf.outputs = outputs
                db.commit()
                break

            # Montar prompt da fase
            output_anterior = outputs.get(f"fase_{fase - 1}", "")
            prompt = PROMPTS_FASE.get(fase, "").format(
                titulo=titulo,
                descricao=descricao,
                output_anterior=output_anterior[:3000],
            )

            # Executar agentes em paralelo
            resultados_fase = []
            tarefa_id = str(uuid.uuid4())[:8]
            tarefa_db = TarefaDB(
                id=tarefa_id, squad_nome=squad_nome, agente_nome=f"Fase {fase}: {FASES_BMAD[fase]}",
                agente_indice=-1, descricao=prompt,
                status="executando", tipo="reuniao",
                participantes=[a.role for a in agentes_fase],
                rodadas=[], rodada_atual=1,
                usuario_id=wf.usuario_id, usuario_nome=wf.usuario_nome,
                company_id=wf.company_id,
            )
            db.add(tarefa_db)
            wf.tarefa_atual_id = tarefa_id
            db.commit()

            with ThreadPoolExecutor(max_workers=3) as executor:
                def executar_agente(agente, idx):
                    try:
                        tarefa_upd = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                        if tarefa_upd:
                            tarefa_upd.agente_atual = f"⚡ {agente.role}"
                            db.commit()

                        crewai_tarefa = Task(
                            description=prompt,
                            expected_output=f"Resultado da {FASES_BMAD[fase]} — completo e estruturado.",
                            agent=agente,
                        )
                        crew = Crew(agents=[agente], tasks=[crewai_tarefa],
                                     process=Process.sequential, verbose=True)
                        resultado = crew.kickoff()
                        return {"agente": agente.role, "resposta": str(resultado), "sucesso": True}
                    except Exception as e:
                        return {"agente": agente.role, "resposta": f"Erro: {str(e)[:200]}", "sucesso": False}

                futures = {executor.submit(executar_agente, ag, i): ag for i, ag in enumerate(agentes_fase)}
                for future in as_completed(futures):
                    result = future.result()
                    resultados_fase.append(result)

                    # Salvar progresso incremental
                    tarefa_upd = db.query(TarefaDB).filter_by(id=tarefa_id).first()
                    if tarefa_upd:
                        rodadas = tarefa_upd.rodadas or []
                        rodadas.append({
                            "rodada": 1,
                            "agente": result["agente"],
                            "resposta": result["resposta"],
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        tarefa_upd.rodadas = rodadas
                        tarefa_upd.agente_atual = f"⚡ {len(resultados_fase)}/{len(agentes_fase)} concluidos"
                        db.commit()

            # Compilar output da fase
            output_fase = f"=== FASE {fase}: {FASES_BMAD[fase].upper()} ===\n\n"
            for r in resultados_fase:
                output_fase += f"**{r['agente']}:**\n{r['resposta']}\n\n"

            outputs[f"fase_{fase}"] = output_fase
            wf.outputs = outputs

            # Finalizar tarefa
            tarefa_upd = db.query(TarefaDB).filter_by(id=tarefa_id).first()
            if tarefa_upd:
                tarefa_upd.status = "concluida"
                tarefa_upd.resultado = output_fase[:5000]
                tarefa_upd.agente_atual = None
                tarefa_upd.concluido_em = datetime.utcnow()

            db.commit()
            logger.info(f"[AUTONOMO] Fase {fase} concluida ({len(resultados_fase)} agentes)")

            # Verificar gate
            gate_tipo = GATES_FASE.get(fase, "soft")
            if gate_tipo == "soft":
                gates = wf.gates or {}
                gates[f"fase_{fase}"] = {"status": "auto_pass", "por": "sistema"}
                wf.gates = gates
                db.commit()
                fase += 1
                continue

            # Gate hard — pausar e aguardar aprovacao
            wf.status = "aguardando_gate"
            wf.atualizado_em = datetime.utcnow()
            db.commit()
            logger.info(f"[AUTONOMO] Workflow {workflow_id} — Aguardando aprovacao do gate da Fase {fase}")
            break  # Sai do loop — sera retomado quando CEO aprovar

        # Se completou todas as fases
        wf_final = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if wf_final and wf_final.fase_atual > 4:
            wf_final.status = "concluido"
            wf_final.atualizado_em = datetime.utcnow()
            db.commit()
            logger.info(f"[AUTONOMO] Workflow {workflow_id} CONCLUIDO!")

    except Exception as e:
        wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if wf:
            wf.status = "erro"
            outputs = wf.outputs or {}
            outputs["erro"] = str(e)[:500]
            wf.outputs = outputs
            wf.atualizado_em = datetime.utcnow()
            db.commit()
        logger.error(f"[AUTONOMO] Erro: {e}")
    finally:
        db.close()
