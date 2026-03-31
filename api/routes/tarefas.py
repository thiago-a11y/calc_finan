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
from database.models import UsuarioDB, TarefaDB, AgenteCatalogoDB, WorkflowAutonomoDB, EvolucaoFactoryDB

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

        # Enriquecer descricao com regras de comportamento (v0.53.0)
        descricao_enriquecida = (
            f"{descricao}\n\n"
            "REGRAS OBRIGATORIAS:\n"
            "- NUNCA envie emails sem o usuario pedir explicitamente\n"
            "- Voce TEM ferramentas disponiveis — USE-AS para ler arquivos, buscar codigo, consultar a base de conhecimento\n"
            "- Responda de forma direta e objetiva em portugues brasileiro\n"
            "- NAO invente informacoes — use suas ferramentas para consultar dados reais\n"
            "- NUNCA diga que nao tem ferramenta — voce tem\n\n"
            "FLUXO OBRIGATORIO PARA IMPLEMENTACAO/CORRECAO DE CODIGO:\n"
            "Quando o usuario pedir para implementar, corrigir ou alterar codigo, siga ESTE fluxo:\n"
            "1. Use a ferramenta de leitura (read_a_files_content) para VER o codigo atual do arquivo\n"
            "2. Analise o problema e escreva o codigo corrigido/novo\n"
            "3. Use a ferramenta propor_edicao_syneriumx para PROPOR a edicao formalmente\n"
            "   Formato: caminho_do_arquivo|||conteudo_novo_completo|||descricao_da_mudanca\n"
            "4. NUNCA cole codigo diretamente no chat — SEMPRE use propor_edicao_syneriumx\n"
            "5. A proposta sera enviada ao dashboard de aprovacoes para o CEO/lider aprovar\n"
            "6. Apos aprovacao, o sistema faz build, commit e deploy automaticamente"
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
                f"Você é {agente.role}. Contribua com sua perspectiva especializada.\n\n"
                f"REGRAS OBRIGATORIAS:\n"
                f"- Voce TEM ferramentas disponiveis — USE-AS para ler arquivos, buscar codigo, consultar a base de conhecimento\n"
                f"- NAO invente informacoes — use suas ferramentas para consultar dados reais\n"
                f"- NUNCA diga que nao tem ferramenta — voce tem\n"
                f"- NUNCA envie emails sem o usuario pedir explicitamente\n"
                f"- Responda em portugues brasileiro, de forma direta e pratica\n\n"
                f"FLUXO OBRIGATORIO PARA IMPLEMENTACAO/CORRECAO DE CODIGO:\n"
                f"1. Use read_a_files_content para VER o codigo atual\n"
                f"2. Analise e escreva o codigo corrigido\n"
                f"3. Use propor_edicao_syneriumx para PROPOR a edicao (caminho|||conteudo|||descricao)\n"
                f"4. NUNCA cole codigo no chat — SEMPRE use propor_edicao_syneriumx\n"
                f"5. A proposta vai para o dashboard de aprovacoes automaticamente"
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
                f"Você é {agente.role}. Contribua com sua perspectiva especializada.\n\n"
                f"REGRAS OBRIGATORIAS:\n"
                f"- Voce TEM ferramentas disponiveis — USE-AS para ler arquivos, buscar codigo, consultar a base de conhecimento\n"
                f"- NAO invente informacoes — use suas ferramentas para consultar dados reais\n"
                f"- NUNCA diga que nao tem ferramenta — voce tem\n"
                f"- NUNCA envie emails sem o usuario pedir explicitamente\n"
                f"- Responda em portugues brasileiro, de forma direta e pratica\n\n"
                f"FLUXO OBRIGATORIO PARA IMPLEMENTACAO/CORRECAO DE CODIGO:\n"
                f"1. Use read_a_files_content para VER o codigo atual\n"
                f"2. Analise e escreva o codigo corrigido\n"
                f"3. Use propor_edicao_syneriumx para PROPOR a edicao (caminho|||conteudo|||descricao)\n"
                f"4. NUNCA cole codigo no chat — SEMPRE use propor_edicao_syneriumx\n"
                f"5. A proposta vai para o dashboard de aprovacoes automaticamente"
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


# IMPORTANTE: Esta rota usa path parameter generico {tarefa_id}
# Deve ficar DEPOIS de todas as rotas com nomes fixos (command-center, evolucoes, autonomo)
# para nao interceptar requests como /command-center → tarefa_id="command-center"
@router.get("/detalhe/{tarefa_id}", response_model=TarefaResponse)
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

        from core.llm_fallback import chamar_llm_com_fallback_async
        from core.classificador_mensagem import classificar_mensagem
        _cls = classificar_mensagem(prompt)
        resp, _, _ = await chamar_llm_com_fallback_async(
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            max_tokens=500, temperature=0, classificacao=_cls,
        )

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


# Lock global para gate approval (evita race condition)
_gate_lock = threading.Lock()


@router.post("/autonomo/{workflow_id}/aprovar-gate")
def aprovar_gate(
    workflow_id: str,
    req: AprovarGateRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aprova, rejeita ou ajusta um gate do workflow. Apenas CEO/Operations Lead."""
    # Verificar permissao — so CEO ou Operations Lead podem aprovar gates
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO ou Operations Lead podem aprovar gates.")

    with _gate_lock:
        # Refresh para evitar stale read
        db.expire_all()
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
            squad_nome_local = wf.squad_nome
            db.commit()
            logger.info(f"[AUTONOMO] Workflow {workflow_id} CONCLUIDO (via gate approval)!")

            # Disparar review session (Self-Evolving Factory)
            try:
                threading.Thread(target=_executar_review_session, args=(workflow_id,), daemon=True).start()
                logger.info(f"[EVOLUCAO] Review session iniciada para workflow {workflow_id}")
            except Exception:
                pass

            # Avancar fila: iniciar proximo workflow aguardando
            try:
                proximo = db.query(WorkflowAutonomoDB).filter_by(
                    status="aguardando_fila", squad_nome=squad_nome_local,
                ).order_by(WorkflowAutonomoDB.criado_em.asc()).first()
                if proximo:
                    proximo.status = "em_execucao"
                    db.commit()
                    logger.info(f"[FILA] Iniciando proximo: {proximo.id} — {proximo.titulo}")
                    threading.Thread(
                        target=_executar_workflow_autonomo_bg,
                        args=(proximo.id, proximo.squad_nome, proximo.titulo, proximo.descricao or "", 1, fabrica),
                        daemon=True,
                    ).start()
            except Exception as fe:
                logger.warning(f"[FILA] Erro ao avancar fila: {fe}")

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
    IMPORTANTE: Cada fase usa SessionLocal() ISOLADA para evitar erros de thread.
    Ao concluir/falhar, inicia proximo workflow da fila automaticamente.
    """
    from crewai import Task, Crew, Process

    squad = fabrica.squads.get(squad_nome)
    if not squad:
        db_err = SessionLocal()
        try:
            wf = db_err.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if wf:
                wf.status = "erro"
                wf.outputs = {**(wf.outputs or {}), "erro": f"Squad '{squad_nome}' nao encontrado"}
                db_err.commit()
        finally:
            db_err.close()
        return

    fase = fase_inicial
    outputs = {}

    # Carregar outputs existentes
    db_init = SessionLocal()
    try:
        wf = db_init.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if not wf or wf.status == "cancelado":
            return
        outputs = wf.outputs or {}
    finally:
        db_init.close()

    while fase <= 4:
        logger.info(f"[AUTONOMO] Workflow {workflow_id} — Iniciando Fase {fase}: {FASES_BMAD[fase]}")

        # === Session isolada para atualizar status ===
        db_status = SessionLocal()
        try:
            wf = db_status.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if not wf or wf.status == "cancelado":
                break
            wf.fase_atual = fase
            wf.status = "em_execucao"
            wf.atualizado_em = datetime.utcnow()
            db_status.commit()

            usuario_id = wf.usuario_id
            usuario_nome = wf.usuario_nome
            company_id = wf.company_id
        finally:
            db_status.close()

        # Selecionar agentes
        agentes_fase = squad.agentes[:min(3, len(squad.agentes))]
        if not agentes_fase:
            db_err = SessionLocal()
            try:
                wf = db_err.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
                if wf:
                    wf.status = "erro"
                    outputs[f"fase_{fase}"] = "Erro: nenhum agente disponivel"
                    wf.outputs = outputs
                    db_err.commit()
            finally:
                db_err.close()
            break

        # Montar prompt
        output_anterior = outputs.get(f"fase_{fase - 1}", "")
        prompt = PROMPTS_FASE.get(fase, "").format(
            titulo=titulo,
            descricao=descricao,
            output_anterior=output_anterior[:3000],
        )

        # === Session isolada para criar tarefa ===
        tarefa_id = str(uuid.uuid4())[:8]
        db_tarefa = SessionLocal()
        try:
            tarefa_db = TarefaDB(
                id=tarefa_id, squad_nome=squad_nome,
                agente_nome=f"Fase {fase}: {FASES_BMAD[fase]}",
                agente_indice=-1, descricao=prompt,
                status="executando", tipo="reuniao",
                participantes=[a.role for a in agentes_fase],
                rodadas=[], rodada_atual=1,
                usuario_id=usuario_id, usuario_nome=usuario_nome,
                company_id=company_id,
            )
            db_tarefa.add(tarefa_db)
            wf = db_tarefa.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if wf:
                wf.tarefa_atual_id = tarefa_id
            db_tarefa.commit()
        finally:
            db_tarefa.close()

        # === Executar agentes em paralelo (cada agente usa sua propria session) ===
        resultados_fase = []

        def executar_agente(agente, idx):
            # Session isolada por agente
            db_ag = SessionLocal()
            try:
                t = db_ag.query(TarefaDB).filter_by(id=tarefa_id).first()
                if t:
                    t.agente_atual = f"⚡ {agente.role}"
                    db_ag.commit()
            except Exception:
                pass
            finally:
                db_ag.close()

            try:
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

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(executar_agente, ag, i): ag for i, ag in enumerate(agentes_fase)}
            for future in as_completed(futures):
                result = future.result()
                resultados_fase.append(result)

                # Salvar progresso com session isolada
                db_prog = SessionLocal()
                try:
                    t = db_prog.query(TarefaDB).filter_by(id=tarefa_id).first()
                    if t:
                        rodadas = t.rodadas or []
                        rodadas.append({
                            "rodada": 1,
                            "agente": result["agente"],
                            "resposta": result["resposta"],
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        t.rodadas = rodadas
                        t.agente_atual = f"⚡ {len(resultados_fase)}/{len(agentes_fase)} concluidos"
                        db_prog.commit()
                except Exception:
                    pass
                finally:
                    db_prog.close()

        # === Session isolada para salvar output da fase ===
        output_fase = f"=== FASE {fase}: {FASES_BMAD[fase].upper()} ===\n\n"
        for r in resultados_fase:
            output_fase += f"**{r['agente']}:**\n{r['resposta']}\n\n"
        outputs[f"fase_{fase}"] = output_fase

        db_save = SessionLocal()
        try:
            wf = db_save.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if wf:
                wf.outputs = outputs

            t = db_save.query(TarefaDB).filter_by(id=tarefa_id).first()
            if t:
                t.status = "concluida"
                t.resultado = output_fase[:5000]
                t.agente_atual = None
                t.concluido_em = datetime.utcnow()

            db_save.commit()
        finally:
            db_save.close()

        logger.info(f"[AUTONOMO] Fase {fase} concluida ({len(resultados_fase)} agentes)")

        # === Verificar gate ===
        gate_tipo = GATES_FASE.get(fase, "soft")
        if gate_tipo == "soft":
            db_gate = SessionLocal()
            try:
                wf = db_gate.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
                if wf:
                    gates = wf.gates or {}
                    gates[f"fase_{fase}"] = {"status": "auto_pass", "por": "sistema"}
                    wf.gates = gates
                    db_gate.commit()
            finally:
                db_gate.close()
            fase += 1
            continue

        # Gate hard — pausar
        db_gate = SessionLocal()
        try:
            wf = db_gate.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if wf:
                wf.status = "aguardando_gate"
                wf.atualizado_em = datetime.utcnow()
                db_gate.commit()
        finally:
            db_gate.close()
        logger.info(f"[AUTONOMO] Workflow {workflow_id} — Aguardando gate Fase {fase}")
        break  # Retomado quando CEO aprovar

    # === Verificar se concluiu todas as fases ===
    db_final = SessionLocal()
    try:
        wf = db_final.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if wf and fase > 4 and wf.status == "em_execucao":
            wf.status = "concluido"
            wf.atualizado_em = datetime.utcnow()
            db_final.commit()
            logger.info(f"[AUTONOMO] Workflow {workflow_id} CONCLUIDO!")

            # Auto-review
            try:
                threading.Thread(target=_executar_review_session, args=(workflow_id,), daemon=True).start()
            except Exception:
                pass

        # === FILA: Iniciar proximo workflow aguardando_fila ===
        if wf and wf.status in ("concluido", "erro"):
            proximo = db_final.query(WorkflowAutonomoDB).filter_by(
                status="aguardando_fila",
                squad_nome=squad_nome,
            ).order_by(WorkflowAutonomoDB.criado_em.asc()).first()

            if proximo:
                proximo.status = "em_execucao"
                db_final.commit()
                logger.info(f"[FILA] Iniciando proximo workflow: {proximo.id} — {proximo.titulo}")
                threading.Thread(
                    target=_executar_workflow_autonomo_bg,
                    args=(proximo.id, proximo.squad_nome, proximo.titulo, proximo.descricao or "", 1, fabrica),
                    daemon=True,
                ).start()

    except Exception as e:
        logger.error(f"[AUTONOMO] Erro final: {e}")
        try:
            wf = db_final.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
            if wf and wf.status == "em_execucao":
                wf.status = "erro"
                wf.outputs = {**(wf.outputs or {}), "erro": str(e)[:500]}
                wf.atualizado_em = datetime.utcnow()
                db_final.commit()

            # FILA: Mesmo com erro, iniciar proximo
            proximo = db_final.query(WorkflowAutonomoDB).filter_by(
                status="aguardando_fila", squad_nome=squad_nome,
            ).order_by(WorkflowAutonomoDB.criado_em.asc()).first()
            if proximo:
                proximo.status = "em_execucao"
                db_final.commit()
                logger.info(f"[FILA] Workflow {workflow_id} falhou → iniciando proximo: {proximo.id}")
                threading.Thread(
                    target=_executar_workflow_autonomo_bg,
                    args=(proximo.id, proximo.squad_nome, proximo.titulo, proximo.descricao or "", 1, fabrica),
                    daemon=True,
                ).start()
        except Exception:
            pass
    finally:
        db_final.close()


# =====================================================================
# COMMAND CENTER — Visao geral da fabrica + comando estrategico
# =====================================================================

class ComandoEstrategicoRequest(BaseModel):
    visao: str             # "Lancar PlaniFactory completo em 30 dias"
    squad_nome: str        # Squad do CEO
    projeto_id: int = 0
    paralelo: bool = False # True = todos ao mesmo tempo (custa mais)


@router.get("/command-center")
def command_center(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna visao completa da fabrica: workflows, tarefas, custos."""
    # Workflows autonomos ativos
    workflows = (
        db.query(WorkflowAutonomoDB)
        .filter(WorkflowAutonomoDB.status.in_(["em_execucao", "aguardando_gate", "montando_time"]))
        .order_by(WorkflowAutonomoDB.criado_em.desc())
        .all()
    )

    wf_ativos = []
    for wf in workflows:
        tarefa_atual = None
        if wf.tarefa_atual_id:
            t = db.query(TarefaDB).filter_by(id=wf.tarefa_atual_id).first()
            if t:
                tarefa_atual = {
                    "agente_atual": t.agente_atual,
                    "status": t.status,
                }
        # Calcular progresso percentual (cada fase = 25%)
        progresso = min(100, max(0, (wf.fase_atual - 1) * 25))
        if wf.status == "concluido":
            progresso = 100
        elif wf.status == "aguardando_gate":
            progresso = wf.fase_atual * 25  # Fase concluida, aguardando gate

        wf_ativos.append({
            "id": wf.id,
            "titulo": wf.titulo,
            "fase_atual": wf.fase_atual,
            "fase_nome": FASES_BMAD.get(wf.fase_atual, "?"),
            "status": wf.status,
            "progresso": progresso,
            "squad_nome": wf.squad_nome,
            "tarefa_atual": tarefa_atual,
            "criado_em": wf.criado_em.isoformat() if wf.criado_em else "",
        })

    # Workflows recentes (concluidos/erro)
    wf_recentes = (
        db.query(WorkflowAutonomoDB)
        .filter(WorkflowAutonomoDB.status.in_(["concluido", "erro", "cancelado"]))
        .order_by(WorkflowAutonomoDB.atualizado_em.desc())
        .limit(10)
        .all()
    )
    historico = [{
        "id": wf.id,
        "titulo": wf.titulo,
        "status": wf.status,
        "fase_atual": wf.fase_atual,
        "criado_em": wf.criado_em.isoformat() if wf.criado_em else "",
    } for wf in wf_recentes]

    # Tarefas/reunioes ativas
    tarefas_ativas = db.query(TarefaDB).filter(
        TarefaDB.status.in_(["executando", "pendente", "aguardando_feedback"])
    ).count()

    # Custo estimado (do usage tracking)
    from database.models import UsageTrackingDB
    from sqlalchemy import func
    custo_hoje = db.query(func.sum(UsageTrackingDB.custo_usd)).filter(
        func.date(UsageTrackingDB.criado_em) == func.date(datetime.utcnow())
    ).scalar() or 0

    custo_total = db.query(func.sum(UsageTrackingDB.custo_usd)).scalar() or 0

    return {
        "workflows_ativos": wf_ativos,
        "historico": historico,
        "total_ativos": len(wf_ativos),
        "tarefas_ativas": tarefas_ativas,
        "custo_hoje_usd": round(float(custo_hoje), 4),
        "custo_total_usd": round(float(custo_total), 4),

        # Evolucoes recentes
        "evolucoes": [
            {
                "id": e.id,
                "workflow_titulo": e.workflow_titulo,
                "analise": (e.analise or "")[:200],
                "sugestoes_count": len(e.sugestoes or []),
                "status": e.status,
                "criado_em": e.criado_em.isoformat() if e.criado_em else "",
            }
            for e in db.query(EvolucaoFactoryDB).order_by(
                EvolucaoFactoryDB.criado_em.desc()
            ).limit(5).all()
        ],
    }


@router.post("/command-center/estrategia")
def comando_estrategico(
    req: ComandoEstrategicoRequest,
    fabrica=Depends(obter_fabrica),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    CEO da um comando de alto nivel e o sistema quebra em features
    e spawna Autonomous Squads para cada uma.
    """
    # Usar LLM para quebrar a visao em features
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage
        import json as json_mod

        from core.llm_fallback import chamar_llm_com_fallback
        msgs = [
            SystemMessage(content=(
                "Voce e o PM Central (Alex) do Synerium Factory. "
                "O CEO deu um comando estrategico. Quebre em features independentes com roadmap. "
                "Retorne APENAS JSON:\n"
                "{\"roadmap\": \"descricao resumida do roadmap (1-2 frases)\",\n"
                " \"estimativa_dias\": 30,\n"
                " \"custo_estimado_usd\": 5.0,\n"
                " \"features\": [{\"titulo\": \"...\", \"descricao\": \"...\", \"prioridade\": 1, \"complexidade\": \"media\"}]}\n"
                "Maximo 5 features. Cada feature deve ser autocontida e implementavel por um squad."
            )),
            HumanMessage(content=f"Comando do CEO: {req.visao}"),
        ]
        from core.classificador_mensagem import classificar_mensagem
        _cls_visao = classificar_mensagem(req.visao)
        resposta, _, _ = chamar_llm_com_fallback(msgs, max_tokens=2000, temperature=0.3, classificacao=_cls_visao)
        texto = resposta.content

        # Extrair JSON
        import re as re_mod
        json_match = re_mod.search(r'\{[\s\S]*\}', texto)
        roadmap = ""
        estimativa_dias = 0
        custo_estimado = 0.0
        if json_match:
            dados = json_mod.loads(json_match.group())
            features = dados.get("features", [])[:5]
            roadmap = dados.get("roadmap", "")
            estimativa_dias = dados.get("estimativa_dias", 0)
            custo_estimado = dados.get("custo_estimado_usd", 0.0)
        else:
            features = [{"titulo": req.visao, "descricao": ""}]

    except Exception as e:
        logger.warning(f"[CommandCenter] LLM falhou: {e}")
        features = [{"titulo": req.visao, "descricao": "Feature unica"}]
        roadmap = ""
        estimativa_dias = 0
        custo_estimado = 0.0

    # Criar workflows para cada feature
    workflows_criados = []
    for feat in features:
        workflow_id = str(uuid.uuid4())[:8]
        wf = WorkflowAutonomoDB(
            id=workflow_id,
            titulo=feat["titulo"],
            descricao=feat.get("descricao", ""),
            fase_atual=1,
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
        db.add(wf)
        db.commit()
        workflows_criados.append({"id": workflow_id, "titulo": feat["titulo"]})

        # Iniciar execucao (sequencial por padrao, paralelo se solicitado)
        if req.paralelo or len(features) == 1:
            threading.Thread(
                target=_executar_workflow_autonomo_bg,
                args=(workflow_id, req.squad_nome, feat["titulo"], feat.get("descricao", ""), 1, fabrica),
                daemon=True,
            ).start()

    # Se sequencial, iniciar apenas o primeiro (os proximos sao iniciados ao concluir)
    if not req.paralelo and len(features) > 1:
        primeiro = workflows_criados[0]
        threading.Thread(
            target=_executar_workflow_autonomo_bg,
            args=(primeiro["id"], req.squad_nome, features[0]["titulo"], features[0].get("descricao", ""), 1, fabrica),
            daemon=True,
        ).start()
        # Marcar os demais como "aguardando"
        for wf_info in workflows_criados[1:]:
            wf_db = db.query(WorkflowAutonomoDB).filter_by(id=wf_info["id"]).first()
            if wf_db:
                wf_db.status = "aguardando_fila"
                db.commit()

    logger.info(f"[CommandCenter] Estrategia: {len(workflows_criados)} features criadas a partir de: {req.visao[:60]}")

    return {
        "visao": req.visao,
        "roadmap": roadmap,
        "estimativa_dias": estimativa_dias,
        "custo_estimado_usd": custo_estimado,
        "features": features,
        "workflows": workflows_criados,
        "total": len(workflows_criados),
        "modo": "paralelo" if req.paralelo else "sequencial",
    }


# =====================================================================
# SELF-EVOLVING FACTORY — Review Session pos-workflow
# =====================================================================

def _executar_review_session(workflow_id: str):
    """
    Review automatica pos-workflow: Factory Optimizer analisa a execucao
    e gera sugestoes de melhoria (PDCA + Kaizen).

    Chamada automaticamente quando um workflow autonomo conclui.
    Resultado salvo em EvolucaoFactoryDB para aprovacao do CEO.

    v0.53.1: Robustez — SEMPRE salva registro no banco, mesmo se LLM falhar.
    Garante que EvolucaoFactoryDB e criado em QUALQUER cenario.
    """
    db = SessionLocal()
    evolucao = None  # Referencia fora do try para garantir commit no finally
    try:
        wf = db.query(WorkflowAutonomoDB).filter_by(id=workflow_id).first()
        if not wf:
            logger.warning(f"[EVOLUCAO] Workflow {workflow_id} nao encontrado para review")
            return

        logger.info(f"[EVOLUCAO] Iniciando review session para workflow {workflow_id}: {wf.titulo}")

        # Calcular metricas
        tempo_total = 0
        if wf.criado_em and wf.atualizado_em:
            tempo_total = int((wf.atualizado_em - wf.criado_em).total_seconds())

        outputs = wf.outputs or {}
        gates = wf.gates or {}
        total_fases_executadas = len([k for k in outputs if k.startswith("fase_")])

        # ============================================================
        # PASSO 1: Criar registro IMEDIATAMENTE no banco (antes de LLM)
        # Garante que sempre existe um registro, mesmo se LLM falhar
        # ============================================================
        evolucao = EvolucaoFactoryDB(
            workflow_id=workflow_id,
            workflow_titulo=wf.titulo,
            tempo_total_seg=tempo_total,
            total_fases=total_fases_executadas,
            total_agentes=len(wf.agentes_ids or []),
            status="analisando",
            usuario_id=wf.usuario_id,
            company_id=wf.company_id,
            metricas={
                "tempo_total_seg": tempo_total,
                "fases_executadas": total_fases_executadas,
                "gates": {k: v.get("status", "?") for k, v in gates.items()},
            },
        )
        db.add(evolucao)
        db.commit()
        db.refresh(evolucao)
        logger.info(f"[EVOLUCAO] Registro #{evolucao.id} criado no banco para workflow {workflow_id}")

        # ============================================================
        # PASSO 2: Chamar LLM para review (pode falhar — nao perde registro)
        # ============================================================
        resumo_outputs = ""
        for fase_key in sorted(outputs.keys()):
            if fase_key.startswith("fase_"):
                conteudo = outputs[fase_key]
                resumo_outputs += f"\n{fase_key}: {conteudo[:500]}...\n"

        try:
            from core.llm_fallback import chamar_llm_com_fallback
            from langchain_core.messages import HumanMessage, SystemMessage
            import json as json_mod

            system = (
                "Voce e o Factory Optimizer do Synerium Factory — nivel Distinguished Engineer. "
                "Analise a execucao do workflow e gere sugestoes de melhoria concretas.\n\n"
                "Retorne APENAS JSON no formato:\n"
                '{"analise": "texto da analise (2-3 paragrafos)", '
                '"sugestoes": [{"tipo": "PROMPT|CUSTO|FLUXO|QUALIDADE|SKILL", '
                '"descricao": "...", "prioridade": "alta|media|baixa", '
                '"auto_aplicavel": false}], '
                '"nota_geral": 7.5, "erros_encontrados": 0}'
            )

            prompt = (
                f"Workflow: {wf.titulo}\n"
                f"Tempo total: {tempo_total}s ({tempo_total // 60}min)\n"
                f"Fases executadas: {total_fases_executadas}/4\n"
                f"Gates: {json_mod.dumps({k: v.get('status', '?') for k, v in gates.items()})}\n\n"
                f"Outputs resumidos:\n{resumo_outputs[:2000]}\n\n"
                f"Analise e sugira melhorias."
            )

            msgs_review = [SystemMessage(content=system), HumanMessage(content=prompt)]
            from core.classificador_mensagem import classificar_mensagem
            _cls_review = classificar_mensagem(prompt)
            resposta, provider_usado, modelo_usado = chamar_llm_com_fallback(
                msgs_review, max_tokens=2000, classificacao=_cls_review
            )
            texto = resposta.content
            logger.info(f"[EVOLUCAO] Review gerada via {provider_usado}/{modelo_usado}")

            # Extrair JSON
            import re as re_mod
            json_match = re_mod.search(r'\{[\s\S]*\}', texto)
            if json_match:
                try:
                    dados = json_mod.loads(json_match.group())
                    evolucao.analise = dados.get("analise", texto)
                    evolucao.sugestoes = dados.get("sugestoes", [])
                    evolucao.erros_encontrados = dados.get("erros_encontrados", 0)
                    metricas = evolucao.metricas or {}
                    metricas["nota_geral"] = dados.get("nota_geral", 0)
                    metricas["provider"] = provider_usado
                    metricas["modelo"] = modelo_usado
                    evolucao.metricas = metricas
                except json_mod.JSONDecodeError:
                    evolucao.analise = texto
                    evolucao.sugestoes = []
            else:
                evolucao.analise = texto
                evolucao.sugestoes = []

            evolucao.status = "aguardando_aprovacao"

        except Exception as llm_err:
            logger.warning(f"[EVOLUCAO] LLM review falhou: {llm_err}")
            evolucao.analise = f"Review automatica falhou: {str(llm_err)[:200]}"
            evolucao.sugestoes = []
            # AINDA salva como aguardando_aprovacao — CEO ve que LLM falhou mas registro existe
            evolucao.status = "aguardando_aprovacao"

        # ============================================================
        # PASSO 3: Commit final — SEMPRE executa (registro ja existe no banco)
        # ============================================================
        db.commit()
        logger.info(
            f"[EVOLUCAO] Review concluida para workflow {workflow_id} — "
            f"{len(evolucao.sugestoes or [])} sugestoes — status: {evolucao.status}"
        )

    except Exception as e:
        logger.error(f"[EVOLUCAO] Erro na review session: {e}", exc_info=True)
        # Tentar salvar registro parcial se evolucao foi criada
        if evolucao and evolucao.id:
            try:
                evolucao.status = "erro"
                evolucao.analise = f"Erro na review session: {str(e)[:300]}"
                db.commit()
                logger.info(f"[EVOLUCAO] Registro #{evolucao.id} salvo com status 'erro'")
            except Exception:
                db.rollback()
        else:
            # Evolucao nem foi criada — criar registro minimo de erro
            try:
                evolucao_erro = EvolucaoFactoryDB(
                    workflow_id=workflow_id,
                    workflow_titulo=f"[ERRO] Review falhou",
                    status="erro",
                    analise=f"Erro fatal na review session: {str(e)[:300]}",
                    sugestoes=[],
                    metricas={"erro": str(e)[:200]},
                )
                db.add(evolucao_erro)
                db.commit()
                logger.info(f"[EVOLUCAO] Registro de erro criado para workflow {workflow_id}")
            except Exception:
                db.rollback()
    finally:
        db.close()


# =====================================================================
# Endpoints de Evolucao
# =====================================================================

@router.get("/evolucoes")
def listar_evolucoes(
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista todas as evolucoes da fabrica."""
    evolucoes = (
        db.query(EvolucaoFactoryDB)
        .order_by(EvolucaoFactoryDB.criado_em.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": e.id,
            "workflow_id": e.workflow_id,
            "workflow_titulo": e.workflow_titulo,
            "tempo_total_seg": e.tempo_total_seg,
            "total_fases": e.total_fases,
            "erros_encontrados": e.erros_encontrados,
            "analise": e.analise,
            "sugestoes": e.sugestoes or [],
            "metricas": e.metricas or {},
            "status": e.status,
            "criado_em": e.criado_em.isoformat() if e.criado_em else "",
        }
        for e in evolucoes
    ]


@router.post("/evolucoes/{evolucao_id}/aprovar")
def aprovar_evolucao(
    evolucao_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """CEO aprova sugestoes de evolucao."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO ou Operations Lead podem aprovar evolucoes.")

    evolucao = db.query(EvolucaoFactoryDB).filter_by(id=evolucao_id).first()
    if not evolucao:
        raise HTTPException(status_code=404, detail="Evolucao nao encontrada.")

    evolucao.status = "aplicado"
    evolucao.aplicado_por = usuario.nome
    evolucao.aplicado_em = datetime.utcnow()
    db.commit()

    logger.info(f"[EVOLUCAO] Evolucao {evolucao_id} aprovada por {usuario.nome}")
    return {"mensagem": "Evolucao aprovada e registrada.", "status": "aplicado"}


@router.post("/evolucoes/{evolucao_id}/rejeitar")
def rejeitar_evolucao(
    evolucao_id: int,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """CEO rejeita sugestoes de evolucao."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO ou Operations Lead.")

    evolucao = db.query(EvolucaoFactoryDB).filter_by(id=evolucao_id).first()
    if not evolucao:
        raise HTTPException(status_code=404, detail="Evolucao nao encontrada.")

    evolucao.status = "rejeitado"
    db.commit()
    return {"mensagem": "Evolucao rejeitada.", "status": "rejeitado"}


# =====================================================================
# Recovery: Workflows travados (chamado no startup)
# =====================================================================

def recuperar_workflows_travados():
    """
    Detecta e marca como erro workflows que ficaram em 'em_execucao'
    por mais de 30 minutos (servidor crashou, thread morreu, etc).
    Deve ser chamado no startup do servidor.
    """
    from datetime import timezone, timedelta
    db = SessionLocal()
    try:
        agora = datetime.now(timezone.utc)
        limite = agora - timedelta(minutes=30)

        travados = db.query(WorkflowAutonomoDB).filter(
            WorkflowAutonomoDB.status.in_(["em_execucao", "montando_time"]),
        ).all()

        recuperados = 0
        for wf in travados:
            criado = wf.criado_em
            atualizado = wf.atualizado_em or wf.criado_em
            if atualizado and atualizado.tzinfo is None:
                atualizado = atualizado.replace(tzinfo=timezone.utc)
            if atualizado and atualizado < limite:
                wf.status = "erro"
                outputs = wf.outputs or {}
                outputs["erro_recovery"] = f"Workflow travado detectado no startup ({atualizado.isoformat()}). Resetado automaticamente."
                wf.outputs = outputs
                wf.atualizado_em = datetime.utcnow()
                recuperados += 1
                logger.info(f"[RECOVERY] Workflow {wf.id} ({wf.titulo}) resetado — estava travado desde {atualizado}")

        if recuperados:
            db.commit()
            logger.info(f"[RECOVERY] {recuperados} workflow(s) travado(s) recuperado(s)")
        else:
            logger.info("[RECOVERY] Nenhum workflow travado encontrado")

    except Exception as e:
        logger.error(f"[RECOVERY] Erro na recuperacao: {e}")
    finally:
        db.close()
