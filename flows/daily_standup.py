"""
Daily Standup Automático — CrewAI Flow

Executa automaticamente todo dia às 7h30.
Coleta status de todos os squads, gera relatório em português
e envia para o Operations Lead via WhatsApp/Telegram/email.
"""

import logging
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from config.settings import settings

logger = logging.getLogger("synerium.standup")


class DailyStandup:
    """
    Flow de standup diário automático.

    Coleta informações de cada squad, compila um relatório
    e notifica o Operations Lead.
    """

    def __init__(self):
        self.relator = self._criar_agente_relator()
        self.data_execucao = datetime.now()

    def _criar_agente_relator(self) -> Agent:
        """Cria o agente responsável por compilar o relatório."""
        return Agent(
            role="Relator de Standup Diário",
            goal=(
                "Coletar o status de todos os squads do Synerium Factory, "
                "compilar um relatório conciso em português brasileiro e "
                "destacar bloqueios, riscos e próximos passos."
            ),
            backstory=(
                "Você é o relator oficial do standup diário do Synerium Factory. "
                "Seu papel é garantir que o Operations Lead tenha visibilidade "
                "completa sobre o progresso de todos os squads. Seja direto, "
                "objetivo e destaque problemas antes de conquistas."
            ),
            verbose=True,
        )

    def gerar_relatorio(self, status_squads: list[dict]) -> str:
        """
        Gera o relatório diário baseado no status dos squads.

        Args:
            status_squads: Lista de dicts com {squad, status, bloqueios, proximos_passos}
        """
        tarefa = Task(
            description=(
                f"Data: {self.data_execucao.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Status recebido dos squads:\n"
                f"{self._formatar_status(status_squads)}\n\n"
                "Gere um relatório de standup diário em português brasileiro com:\n"
                "1. Resumo executivo (máximo 3 linhas)\n"
                "2. Status de cada squad (o que fez, o que vai fazer)\n"
                "3. Bloqueios e riscos identificados\n"
                "4. Ações requeridas do Operations Lead\n"
                "5. Métricas relevantes (se disponíveis)"
            ),
            expected_output=(
                "Relatório de standup diário formatado, conciso e em português. "
                "Máximo 1 página. Foco em ações necessárias."
            ),
            agent=self.relator,
        )

        crew = Crew(
            agents=[self.relator],
            tasks=[tarefa],
            process=Process.sequential,
            verbose=True,
        )

        resultado = crew.kickoff()
        self._notificar_operations_lead(str(resultado))
        return str(resultado)

    def _formatar_status(self, status_squads: list[dict]) -> str:
        """Formata o status dos squads para o prompt."""
        linhas = []
        for s in status_squads:
            linhas.append(
                f"- Squad: {s.get('squad', 'N/A')}\n"
                f"  Status: {s.get('status', 'Sem atualização')}\n"
                f"  Bloqueios: {s.get('bloqueios', 'Nenhum')}\n"
                f"  Próximos passos: {s.get('proximos_passos', 'A definir')}"
            )
        return "\n".join(linhas) if linhas else "Nenhum squad reportou status."

    def _notificar_operations_lead(self, relatorio: str):
        """
        Envia o relatório para o Operations Lead.
        TODO: Integrar com WhatsApp/Telegram/email reais.
        """
        logger.info("[STANDUP] Relatório gerado com sucesso.")
        logger.info(f"[STANDUP] Enviando para: {settings.email_operations_lead}")

        # Placeholder para integração real
        # Em produção, aqui vai a chamada para:
        # - API do WhatsApp Business
        # - Bot do Telegram
        # - SMTP para email
        logger.info(f"[STANDUP] Relatório:\n{relatorio[:500]}...")
