"""
Synerium Factory — Orquestrador Principal

Ponto de entrada do sistema. Inicializa:
- PM Agent Central (Alex) com Hierarchical Teams
- Operations Lead com poderes especiais
- Sistema de Approval Gates via LangSmith
- Daily Standup automático via CrewAI Flow
- Squads Pessoais (template pronto para duplicar)

Uso:
    python orchestrator.py
    python orchestrator.py --indexar
    python orchestrator.py --consultar "pergunta"
    python orchestrator.py --standup
    python orchestrator.py --aprovar
"""

import sys
import logging
from datetime import datetime

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

from config.settings import settings
from agents.pm_central import criar_pm_central
from agents.operations_lead import criar_operations_lead
from gates.approval_gates import approval_gate, TipoAprovacao
from flows.daily_standup import DailyStandup
from squads.squad_template import SquadPessoal
from squads.squad_ceo_thiago import criar_squad_ceo
from squads.squad_diretor_jonatas import criar_squad_jonatas
from rag import RAGConfig, RAGIndexer, RAGQuery, RAGAssistant
from tools.rag_tool import ConsultarBaseConhecimento

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/synerium.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("synerium.orchestrator")


class SyneriumFactory:
    """
    Fábrica de SaaS impulsionada por agentes IA.

    Hierarquia:
        CEO (Thiago)
        └── Operations Lead (Irmão do Thiago) — aprovação final
            └── PM Agent Central (Alex) — orquestração
                ├── Squad Dev Backend
                ├── Squad Dev Frontend
                ├── Squad Marketing
                └── Squad [Novo Membro]
    """

    def __init__(self):
        logger.info("=" * 60)
        logger.info("SYNERIUM FACTORY — Inicializando...")
        logger.info(f"Ambiente: {settings.ambiente}")
        logger.info(f"LangSmith Project: {settings.langsmith_project}")
        logger.info("=" * 60)

        # Inicializar RAG (Base de Conhecimento)
        self.rag_config = RAGConfig(
            vaults={
                nome: caminho
                for nome, caminho in {
                    "syneriumx": settings.rag_vault_syneriumx,
                    "factory": settings.rag_vault_factory,
                }.items()
                if caminho  # Ignorar vaults sem caminho configurado
            },
            persist_directory=settings.rag_persist_dir,
        )
        self.rag_indexer = RAGIndexer(self.rag_config)
        self.rag_query = RAGQuery(
            self.rag_indexer.store,
            company_id=self.rag_config.company_id,
        )

        # Assistente RAG com Claude (respostas inteligentes)
        self.rag_assistant = RAGAssistant(
            store=self.rag_indexer.store,
            company_id=self.rag_config.company_id,
        )

        # Ferramenta RAG para os agentes consultarem a base de conhecimento
        self.ferramenta_rag = ConsultarBaseConhecimento(rag_query=self.rag_query)
        logger.info("[OK] RAG (Base de Conhecimento + Assistente IA) inicializado.")

        # Agentes principais — com acesso à base de conhecimento
        self.pm_central = criar_pm_central(tools=[self.ferramenta_rag])
        self.operations_lead = criar_operations_lead()

        # Squads registrados
        self.squads: dict[str, SquadPessoal] = {}

        # Daily standup
        self.standup = DailyStandup()

        logger.info("[OK] PM Agent Central (Alex) inicializado com RAG.")
        logger.info("[OK] Operations Lead inicializado.")

    # ------------------------------------------------------------------
    # Gestão de Squads
    # ------------------------------------------------------------------

    def registrar_squad(self, nome: str, especialidade: str, contexto: str = "") -> SquadPessoal:
        """Registra um novo squad pessoal com acesso à base de conhecimento."""
        squad = SquadPessoal(
            nome_membro=nome,
            especialidade=especialidade,
            contexto=contexto,
            tools=[self.ferramenta_rag],
        )
        squad.criar_agente_principal()
        self.squads[nome] = squad
        logger.info(f"[SQUAD] Registrado: {nome} ({especialidade})")
        return squad

    # ------------------------------------------------------------------
    # Approval Gates
    # ------------------------------------------------------------------

    def solicitar_aprovacao(self, tipo: TipoAprovacao, descricao: str,
                            solicitante: str, valor: float | None = None):
        """Solicita aprovação do Operations Lead via Approval Gate."""
        solicitacao = approval_gate.requer_aprovacao(
            tipo=tipo,
            descricao=descricao,
            solicitante=solicitante,
            valor=valor,
        )

        if solicitacao.aprovado is None:
            print("\n" + "=" * 60)
            print("⏸  AGUARDANDO APROVAÇÃO DO OPERATIONS LEAD")
            print(f"   Tipo: {tipo.value}")
            print(f"   Descrição: {descricao}")
            print(f"   Solicitante: {solicitante}")
            if valor:
                print(f"   Valor estimado: R${valor:.2f}")
            print("=" * 60)

            resposta = input("\n[Operations Lead] Aprovar? (s/n): ").strip().lower()
            if resposta == "s":
                approval_gate.aprovar(solicitacao)
                print("[OK] Aprovado pelo Operations Lead.\n")
            else:
                approval_gate.rejeitar(solicitacao)
                print("[X] Rejeitado pelo Operations Lead.\n")

        return solicitacao

    # ------------------------------------------------------------------
    # Daily Standup
    # ------------------------------------------------------------------

    def executar_standup(self):
        """Executa o standup diário coletando status de todos os squads."""
        logger.info("[STANDUP] Iniciando standup diário...")

        status_squads = []
        for nome, squad in self.squads.items():
            status_squads.append({
                "squad": nome,
                "status": f"Squad {nome} ativo com {len(squad.agentes)} agente(s) e {len(squad.tarefas)} tarefa(s).",
                "bloqueios": "Nenhum reportado.",
                "proximos_passos": "Aguardando atribuição de tarefas.",
            })

        if not status_squads:
            status_squads.append({
                "squad": "Geral",
                "status": "Nenhum squad registrado ainda.",
                "bloqueios": "Nenhum.",
                "proximos_passos": "Registrar squads e atribuir tarefas.",
            })

        relatorio = self.standup.gerar_relatorio(status_squads)
        logger.info("[STANDUP] Relatório gerado e enviado.")
        return relatorio

    # ------------------------------------------------------------------
    # Execução de Tarefas via PM Central
    # ------------------------------------------------------------------

    def executar_tarefa(self, descricao: str, resultado_esperado: str,
                        squad_nome: str | None = None):
        """
        Executa uma tarefa via PM Central.
        Se um squad for especificado, delega para ele.
        """
        if squad_nome and squad_nome in self.squads:
            squad = self.squads[squad_nome]
            agente = squad.agentes[0] if squad.agentes else self.pm_central
        else:
            agente = self.pm_central

        tarefa = Task(
            description=descricao,
            expected_output=resultado_esperado,
            agent=agente,
        )

        crew = Crew(
            agents=[self.pm_central, self.operations_lead, agente],
            tasks=[tarefa],
            process=Process.hierarchical,
            manager_agent=self.pm_central,
            verbose=True,
        )

        logger.info(f"[TAREFA] Iniciando: {descricao[:80]}...")
        resultado = crew.kickoff()
        logger.info(f"[TAREFA] Concluída: {descricao[:80]}")
        return resultado

    # ------------------------------------------------------------------
    # Status Geral
    # ------------------------------------------------------------------

    def mostrar_status(self):
        """Mostra o status geral da fábrica."""
        print("\n" + "=" * 60)
        print("SYNERIUM FACTORY — Status Geral")
        print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(f"Ambiente: {settings.ambiente}")
        print("=" * 60)
        print(f"\nPM Central: Alex (ativo)")
        print(f"Operations Lead: Ativo")
        print(f"Squads registrados: {len(self.squads)}")
        for nome, squad in self.squads.items():
            print(f"  - {nome}: {squad.especialidade} "
                  f"({len(squad.agentes)} agentes, {len(squad.tarefas)} tarefas)")
        print(f"RAG — Vaults configurados: {len(self.rag_config.vaults)}")
        for nome, caminho in self.rag_config.vaults.items():
            print(f"  - {nome}: {caminho}")
        pendentes = approval_gate.listar_pendentes()
        print(f"Aprovações pendentes: {len(pendentes)}")
        print("=" * 60 + "\n")


# ======================================================================
# Ponto de Entrada
# ======================================================================

def main():
    """Ponto de entrada principal do Synerium Factory."""
    fabrica = SyneriumFactory()

    # ==========================================
    # Squad do CEO — Thiago (8 agentes)
    # ==========================================
    squad_ceo = criar_squad_ceo(tools=[fabrica.ferramenta_rag])
    fabrica.squads["CEO — Thiago"] = squad_ceo
    logger.info(
        f"[SQUAD] Registrado: CEO — Thiago "
        f"({len(squad_ceo.agentes)} agentes especializados)"
    )

    # ==========================================
    # Squad do Jonatas — Diretor Técnico (3 agentes)
    # ==========================================
    squad_jonatas = criar_squad_jonatas(tools=[fabrica.ferramenta_rag])
    fabrica.squads["Diretor Técnico — Jonatas"] = squad_jonatas
    logger.info(
        f"[SQUAD] Registrado: Diretor Técnico — Jonatas "
        f"({len(squad_jonatas.agentes)} agentes)"
    )

    # ==========================================
    # Squads de Área (genéricos)
    # ==========================================
    fabrica.registrar_squad(
        nome="Dev Backend",
        especialidade="Desenvolvimento Backend PHP/Python",
        contexto="Foco em APIs REST, migrations, auditLog, company_id, LGPD.",
    )
    fabrica.registrar_squad(
        nome="Dev Frontend",
        especialidade="Desenvolvimento Frontend React",
        contexto="Foco em UI/UX, componentes reutilizáveis e performance.",
    )
    fabrica.registrar_squad(
        nome="Marketing",
        especialidade="Marketing Digital e Growth",
        contexto="Foco em campanhas, outreach e métricas de crescimento.",
    )

    # Verificar argumentos de linha de comando
    if "--indexar" in sys.argv:
        logger.info("[RAG] Iniciando indexação dos vaults Obsidian...")
        fabrica.rag_indexer.indexar_todos(company_id="synerium")
        logger.info("[RAG] Indexação concluída com sucesso!")
        print("\n[OK] Vaults indexados com sucesso! Os agentes agora podem consultar a base de conhecimento.")
    elif "--consultar" in sys.argv:
        # Pegar a pergunta dos argumentos
        idx = sys.argv.index("--consultar")
        if idx + 1 < len(sys.argv):
            pergunta = sys.argv[idx + 1]
        else:
            pergunta = input("Pergunta: ")
        resultado = fabrica.rag_query.consultar(pergunta)
        print(resultado)
    elif "--standup" in sys.argv:
        fabrica.executar_standup()
    elif "--aprovar" in sys.argv:
        pendentes = approval_gate.listar_pendentes()
        if not pendentes:
            print("Nenhuma aprovação pendente.")
        for p in pendentes:
            print(f"\nPendente: {p.tipo.value} — {p.descricao}")
            resp = input("[Operations Lead] Aprovar? (s/n): ").strip().lower()
            if resp == "s":
                approval_gate.aprovar(p)
            else:
                approval_gate.rejeitar(p)
    elif "--status" in sys.argv:
        fabrica.mostrar_status()
    else:
        # Modo interativo
        fabrica.mostrar_status()
        print("Comandos disponíveis:")
        print("  1. Executar standup diário")
        print("  2. Solicitar aprovação (teste)")
        print("  3. Executar tarefa via PM Central")
        print("  4. Ver status")
        print("  5. Consultar base de conhecimento (RAG)")
        print("  6. Indexar/reindexar vaults Obsidian")
        print("  7. Sair")
        print()

        while True:
            try:
                opcao = input("Escolha uma opção (1-7): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nEncerrando Synerium Factory.")
                break

            if opcao == "1":
                fabrica.executar_standup()
            elif opcao == "2":
                fabrica.solicitar_aprovacao(
                    tipo=TipoAprovacao.DEPLOY_PRODUCAO,
                    descricao="Deploy de teste para validar approval gates.",
                    solicitante="Alex (PM Central)",
                )
            elif opcao == "3":
                desc = input("Descrição da tarefa: ")
                resultado = input("Resultado esperado: ")
                fabrica.executar_tarefa(desc, resultado)
            elif opcao == "4":
                fabrica.mostrar_status()
            elif opcao == "5":
                pergunta = input("Pergunta para a base de conhecimento: ")
                resultado = fabrica.rag_query.consultar(pergunta)
                print(resultado)
            elif opcao == "6":
                print("Indexando vaults Obsidian...")
                fabrica.rag_indexer.indexar_todos(company_id="synerium")
                print("[OK] Vaults indexados com sucesso!")
            elif opcao == "7":
                print("Encerrando Synerium Factory.")
                break
            else:
                print("Opção inválida. Tente 1-7.")


if __name__ == "__main__":
    main()
