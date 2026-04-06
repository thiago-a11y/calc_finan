"""
Template de Squad Pessoal — Fácil de duplicar para cada membro do time.

Cada humano do time terá seu próprio squad dedicado.
Cada squad reporta primeiro ao PM Agent Central (Alex).

Integração com Smart Router:
- Agentes recebem LLM do router automaticamente
- Tech Lead, Arquiteto, PM → Claude Opus (inteligência superior)
- Backend Dev, Frontend Dev, etc. → Claude Sonnet (rápido e barato)
"""

from crewai import Agent, Task, Crew, Process
from core.llm_router import smart_router


class SquadPessoal:
    """
    Squad dedicado a um membro do time.

    Para criar um novo squad, basta instanciar esta classe
    com o nome e especialidade do membro.
    """

    def __init__(self, nome_membro: str, especialidade: str,
                 contexto: str = "", tools: list | None = None):
        """
        Inicializa o squad pessoal.

        Args:
            nome_membro: Nome do funcionário dono do squad.
            especialidade: Área de atuação (ex: "Desenvolvimento Backend").
            contexto: Contexto adicional sobre o foco do squad.
            tools: Ferramentas compartilhadas com os agentes (ex: RAG).
        """
        self.nome_membro = nome_membro
        self.especialidade = especialidade
        self.contexto = contexto
        self.tools = tools or []
        self.agentes: list[Agent] = []
        self.tarefas: list[Task] = []

    def criar_agente_principal(self, perfil_agente: str = "general") -> Agent:
        """Cria o agente principal do squad com LLM do Smart Router (tracking automático)."""
        nome_agente = f"Agente Principal do Squad {self.nome_membro}"
        llm = smart_router.obter_llm_para_agente(
            perfil_agente,
            agente_nome=nome_agente,
            squad_nome=self.nome_membro,
        )
        agente = Agent(
            role=nome_agente,
            goal=(
                f"Auxiliar {self.nome_membro} em todas as tarefas relacionadas a "
                f"{self.especialidade}. Executar com qualidade e reportar ao PM Central."
            ),
            backstory=(
                f"Você é o agente principal dedicado a {self.nome_membro} no "
                f"Synerium Factory. Sua especialidade é {self.especialidade}. "
                f"Você trabalha de forma autônoma, mas sempre reporta ao PM Central (Alex). "
                f"{self.contexto}"
            ),
            verbose=True,
            allow_delegation=True,
            tools=self.tools,
            llm=llm,
        )
        self.agentes.append(agente)
        return agente

    def criar_agente_auxiliar(self, papel: str, objetivo: str, historia: str,
                              perfil_agente: str = "general",
                              include_rules: bool = True) -> Agent:
        """
        Cria um agente auxiliar com LLM do Smart Router (tracking automático).

        Se include_rules=True, injeta regras anti-alucinação e instrução de
        ferramentas via compose_agent_prompt() do sistema de prompts modular.
        """
        llm = smart_router.obter_llm_para_agente(
            perfil_agente,
            agente_nome=papel,
            squad_nome=self.nome_membro,
        )

        # Compor backstory com regras e ferramentas via sistema modular
        backstory_final = historia
        if include_rules:
            from core.prompts.composers import compose_agent_prompt
            config = compose_agent_prompt(
                name=papel, role=papel, goal=objetivo,
                backstory=historia, perfil=perfil_agente,
                squad_name=self.nome_membro,
                include_rules=True, include_tools=True,
            )
            backstory_final = config["backstory"]

        agente = Agent(
            role=papel,
            goal=objetivo,
            backstory=backstory_final,
            verbose=True,
            allow_delegation=False,
            llm=llm,
        )
        self.agentes.append(agente)
        return agente

    def adicionar_tarefa(self, descricao: str, resultado_esperado: str,
                         agente: Agent) -> Task:
        """Adiciona uma tarefa ao squad."""
        tarefa = Task(
            description=descricao,
            expected_output=resultado_esperado,
            agent=agente,
        )
        self.tarefas.append(tarefa)
        return tarefa

    def montar_crew(self) -> Crew:
        """Monta a crew do squad com processo hierárquico."""
        return Crew(
            agents=self.agentes,
            tasks=self.tarefas,
            process=Process.hierarchical,
            manager_agent=self.agentes[0] if self.agentes else None,
            verbose=True,
        )


# --- Exemplo de uso ---
def criar_squad_exemplo() -> SquadPessoal:
    """Exemplo: Squad do desenvolvedor backend."""
    squad = SquadPessoal(
        nome_membro="João",
        especialidade="Desenvolvimento Backend PHP/Python",
        contexto="Foco em APIs REST, migrations e integrações."
    )

    principal = squad.criar_agente_principal()

    squad.criar_agente_auxiliar(
        papel="Revisor de Código",
        objetivo="Revisar código gerado pelo squad para qualidade e segurança.",
        historia="Você é um revisor de código experiente, focado em boas práticas e segurança.",
    )

    squad.adicionar_tarefa(
        descricao="Criar endpoint REST para cadastro de usuários.",
        resultado_esperado="Endpoint POST /api/usuarios funcionando com validação e testes.",
        agente=principal,
    )

    return squad
