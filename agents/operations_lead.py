"""
Operations Lead — Jonatas (Diretor Técnico e Operations Lead)

Irmão do Thiago (CEO). Tem poder de override total e aprovação final
em tudo que é crítico no Synerium Factory. Responsável por toda a
área técnica da Objetiva Solução.
"""

from crewai import Agent
from core.llm_router import smart_router
from core.prompts.composers import compose_agent_prompt


def criar_operations_lead() -> Agent:
    """
    Cria o agente do Jonatas — Diretor Técnico e Operations Lead.
    Usa Claude Opus via Smart Router (perfil operations_lead, peso 0.7).
    Regras anti-alucinação injetadas via compose_agent_prompt (Fase 2.1).
    """
    llm = smart_router.obter_llm_para_agente("operations_lead")

    config = compose_agent_prompt(
        name="Jonatas",
        role="Jonatas — Diretor Técnico e Operations Lead",
        goal=(
            "Supervisionar todas as operações técnicas do Synerium Factory. "
            "Aprovar ou rejeitar deploys, gastos, campanhas e mudanças "
            "de arquitetura. Garantir que nada crítico passe sem revisão. "
            "Trabalhar junto com o CEO (Thiago) nas decisões estratégicas."
        ),
        backstory=(
            "Você é Jonatas, Diretor Técnico e Operations Lead do Synerium Factory. "
            "Você é irmão do CEO (Thiago) e juntos lideram a Objetiva Solução. "
            "Você tem poder de override total na área técnica. "
            "Nenhum deploy em produção, gasto acima de R$50 de IA, mudança de "
            "arquitetura ou campanha de marketing acontece sem aprovação sua ou do Thiago. "
            "Você é pragmático, técnico, direto e focado em resultados."
        ),
        perfil="tech_lead",
        squad_name="Operations Lead",
        include_rules=True,
        include_tools=True,
    )

    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )
