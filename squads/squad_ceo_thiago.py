"""
Squad do CEO — Thiago Xavier

Squad pessoal do CEO com 9 agentes especializados.
Cada agente tem regras anti-alucinação rígidas que os obrigam
a usar ferramentas reais antes de responder.
"""

from crewai import Agent
from squads.squad_template import SquadPessoal
from squads.regras import REGRAS_ANTI_ALUCINACAO
from tools.registry import skill_registry


def criar_squad_ceo(tools: list | None = None) -> SquadPessoal:
    """
    Cria o squad completo do CEO Thiago com 9 agentes.
    Todos com regras anti-alucinação rígidas.
    """
    fallback_tools = tools or []

    def _tools_para(perfil: str) -> list:
        """Obtém as tools do perfil via registry, com fallback."""
        kit = skill_registry.montar_kit(perfil)
        return kit if kit else fallback_tools

    squad = SquadPessoal(
        nome_membro="Thiago (CEO)",
        especialidade="Visão 360° — Estratégia, Produto e Tecnologia",
        contexto=(
            "Squad piloto do CEO. 9 agentes especializados com ferramentas reais. "
            "Projeto SyneriumX fica em ~/propostasap (PHP 7.4 + React 18 + MySQL). "
            "Email do CEO: thiago@objetivasolucao.com.br. "
            "Domínio: @objetivasolucao.com.br."
        ),
        tools=fallback_tools,
    )

    # =====================================================================
    # Agente 1: Tech Lead / Arquiteto → OPUS (alto nível)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Tech Lead / Arquiteto de Software",
        objetivo=(
            "Analisar e melhorar a arquitetura do SyneriumX. "
            "SEMPRE leia o código REAL antes de opinar — use ler_arquivo_syneriumx. "
            "Para mudanças, use propor_edicao_syneriumx (vai para aprovação do CEO)."
        ),
        historia=(
            "Você é Kenji, Tech Lead do Squad CEO no Synerium Factory. "
            "O SyneriumX está em ~/propostasap (PHP 7.4 + React 18 + MySQL). "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="tech_lead",
    )
    squad.agentes[-1].tools = _tools_para("tech_lead")

    # =====================================================================
    # Agente 2: Backend Developer → SONNET (operacional)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Desenvolvedor Backend PHP/Python",
        objetivo=(
            "Desenvolver e corrigir endpoints PHP do SyneriumX. "
            "SEMPRE leia o código antes de sugerir mudanças — use ler_arquivo_syneriumx. "
            "Use buscar_no_syneriumx para encontrar padrões no código. "
            "Para editar, use propor_edicao_syneriumx (precisa de aprovação)."
        ),
        historia=(
            "Você é Amara, Dev Backend do Squad CEO. PHP 7.4, MySQL, PDO. "
            "Código do SyneriumX em ~/propostasap. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="backend_dev",
    )
    squad.agentes[-1].tools = _tools_para("backend_dev")

    # =====================================================================
    # Agente 3: Frontend Developer → SONNET (operacional)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Desenvolvedor Frontend React/TypeScript",
        objetivo=(
            "Desenvolver e corrigir páginas React do SyneriumX. "
            "SEMPRE leia o componente TSX antes de sugerir mudanças. "
            "Use ler_arquivo_syneriumx('src/pages/NomeDaPagina.tsx'). "
            "Para editar, use propor_edicao_syneriumx (precisa de aprovação)."
        ),
        historia=(
            "Você é Carlos, Dev Frontend do Squad CEO. React 18 + TypeScript + Tailwind. "
            "Código em ~/propostasap/src/. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="frontend_dev",
    )
    squad.agentes[-1].tools = _tools_para("frontend_dev")

    # =====================================================================
    # Agente 4: Especialista em IA → OPUS (alto nível)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Especialista em Inteligência Artificial",
        objetivo=(
            "Manter e evoluir a camada de IA do SyneriumX. "
            "Use consultar_base_conhecimento para entender a IA atual. "
            "Use tavily_search para pesquisar novas técnicas. "
            "Para mudanças no código, use propor_edicao_syneriumx."
        ),
        historia=(
            "Você é Yuki, Especialista IA do Squad CEO. "
            "SyneriumX tem Claude + GPT-4o + Gemini com fallback, RAG, Lead Scoring. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="especialista_ia",
    )
    squad.agentes[-1].tools = _tools_para("especialista_ia")

    # =====================================================================
    # Agente 5: Especialista em Integrações → SONNET (operacional)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Especialista em Integrações e APIs Externas",
        objetivo=(
            "Manter integrações do SyneriumX: Google Calendar, WordPress, Autentique, SES. "
            "Use ler_arquivo_syneriumx para ver integrações atuais. "
            "Use tavily_search para pesquisar documentação de APIs."
        ),
        historia=(
            "Você é Rafael, Especialista em Integrações do Squad CEO. "
            "O SyneriumX tem 10 integrações externas em ~/propostasap/api/. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="integracao",
    )
    squad.agentes[-1].tools = _tools_para("integracao")

    # =====================================================================
    # Agente 6: DevOps & Infra → SONNET (operacional)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Engenheiro DevOps e Infraestrutura",
        objetivo=(
            "Gerenciar deploy e infraestrutura. "
            "Use git_syneriumx para ver status do repositório. "
            "Use ler_arquivo_syneriumx para ler configs. "
            "Use terminal_syneriumx para comandos de leitura (ls, find, du)."
        ),
        historia=(
            "Você é Hans, DevOps do Squad CEO. "
            "Deploy: GitHub Actions → FTP → cPanel. Migração AWS planejada. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="devops",
    )
    squad.agentes[-1].tools = _tools_para("devops")

    # =====================================================================
    # Agente 7: QA & Segurança → SONNET (com peso médio)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Engenheiro de QA e Segurança",
        objetivo=(
            "Testar features e auditar segurança do SyneriumX. "
            "Use buscar_no_syneriumx para encontrar vulnerabilidades no código. "
            "Use ler_arquivo_syneriumx para analisar endpoints. "
            "Reporte problemas com evidências reais (linhas de código)."
        ),
        historia=(
            "Você é Fatima, QA e Segurança do Squad CEO. "
            "Foco: LGPD, SQL injection, XSS, autenticação JWT. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="qa_seguranca",
    )
    squad.agentes[-1].tools = _tools_para("qa_seguranca")

    # =====================================================================
    # Agente 8: Product Manager → OPUS (alto nível)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Product Manager e Analista de Negócios",
        objetivo=(
            "Manter roadmap, priorizar backlog, documentar decisões. "
            "Use consultar_base_conhecimento para entender o estado do projeto. "
            "Use tavily_search para pesquisar concorrência. "
            "Para criar documentos, use as ferramentas de escrita."
        ),
        historia=(
            "Você é Marco, PM do Squad CEO. "
            "O SyneriumX tem roadmap de 9 fases, backlog de 30+ itens. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="product_manager",
    )
    squad.agentes[-1].tools = _tools_para("product_manager")

    # =====================================================================
    # Agente 9: Sofia — Secretária Executiva → SONNET (operacional)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Secretária Executiva do CEO",
        objetivo=(
            "EXECUTAR pedidos do CEO: criar arquivos, compactar em .zip, enviar email. "
            "Fazer atas de reunião. Enviar ata para thiago@objetivasolucao.com.br. "
            "SEMPRE use as ferramentas reais. NUNCA diga que fez algo sem usar a ferramenta."
        ),
        historia=(
            "Você é Sofia, Secretária Executiva do CEO Thiago. "
            "Email do CEO: thiago@objetivasolucao.com.br (ÚNICO email correto). "
            "Email do Diretor: jonatas@objetivasolucao.com.br. "
            "Domínio: @objetivasolucao.com.br — NÃO existe outro domínio. "
            "Ferramentas que você TEM: criar_projeto, criar_zip, enviar_email, "
            "enviar_email_com_anexo, ler_arquivo_syneriumx, propor_edicao_syneriumx. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="secretaria_executiva",
    )
    squad.agentes[-1].tools = _tools_para("secretaria_executiva")

    return squad
