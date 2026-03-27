"""
Squad do Diretor Técnico — Jonatas

Squad pessoal do Diretor Técnico e Operations Lead.
Começa com 3 agentes básicos que ele pode customizar depois.
Todos com regras anti-alucinação rígidas.
"""

from crewai import Agent
from squads.squad_template import SquadPessoal
from squads.squad_ceo_thiago import REGRAS_ANTI_ALUCINACAO
from tools.registry import skill_registry


def criar_squad_jonatas(tools: list | None = None) -> SquadPessoal:
    """
    Cria o squad básico do Jonatas (Diretor Técnico).
    3 agentes iniciais — ele pode pedir mais depois.
    """
    fallback_tools = tools or []

    def _tools_para(perfil: str) -> list:
        kit = skill_registry.montar_kit(perfil)
        return kit if kit else fallback_tools

    squad = SquadPessoal(
        nome_membro="Jonatas (Diretor Técnico)",
        especialidade="Gestão Técnica — Revisão, QA, Arquitetura e DevOps",
        contexto=(
            "Squad do Diretor Técnico e Operations Lead. "
            "Foco em supervisão técnica, revisão de código, segurança e infraestrutura. "
            "Projeto SyneriumX fica em ~/propostasap (PHP 7.4 + React 18 + MySQL). "
            "Email: jonatas@objetivasolucao.com.br. "
            "Domínio: @objetivasolucao.com.br."
        ),
        tools=fallback_tools,
    )

    # =====================================================================
    # Agente 1: Revisor de Código → OPUS (alto nível, revisão crítica)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Revisor de Código Senior",
        objetivo=(
            "Revisar todo código do SyneriumX antes de ir para produção. "
            "SEMPRE leia o código REAL com ler_arquivo_syneriumx antes de opinar. "
            "Verifique: padrões PHP 7.4, prepared statements, company_id, audit log, LGPD. "
            "Para sugerir correções, use propor_edicao_syneriumx."
        ),
        historia=(
            "Você é o Revisor de Código do Squad do Jonatas no Synerium Factory. "
            "Seu papel é garantir qualidade de código em todo o SyneriumX. "
            "Código em ~/propostasap. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="diretor",
    )
    squad.agentes[-1].tools = _tools_para("qa_seguranca")

    # =====================================================================
    # Agente 2: Arquiteto de Infraestrutura → OPUS (alto nível)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Arquiteto de Infraestrutura e DevOps",
        objetivo=(
            "Gerenciar infraestrutura, deploy e CI/CD do SyneriumX. "
            "Use git_syneriumx para verificar status do repositório. "
            "Use terminal_syneriumx para comandos de diagnóstico. "
            "Planejar migração para AWS (Fase 9)."
        ),
        historia=(
            "Você é o Arquiteto de Infra do Squad do Jonatas. "
            "Deploy atual: GitHub Actions → FTP → cPanel. "
            "Próximo: migração para AWS com PostgreSQL, Redis, CDN. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="arquiteto",
    )
    squad.agentes[-1].tools = _tools_para("devops")

    # =====================================================================
    # Agente 3: Analista de Segurança → SONNET (com peso médio)
    # =====================================================================
    squad.criar_agente_auxiliar(
        papel="Analista de Segurança e LGPD",
        objetivo=(
            "Auditar segurança do SyneriumX e garantir compliance LGPD. "
            "Use buscar_no_syneriumx para encontrar vulnerabilidades. "
            "Use ler_arquivo_syneriumx para analisar endpoints sensíveis. "
            "Reporte com evidências reais (linhas de código, arquivos)."
        ),
        historia=(
            "Você é o Analista de Segurança do Squad do Jonatas. "
            "Foco: SQL injection, XSS, CSRF, JWT, 2FA, audit log, LGPD. "
            "O SyneriumX usa JWT HMAC-SHA256 puro, bcrypt cost 12, rate limiting. "
            + REGRAS_ANTI_ALUCINACAO
        ),
        perfil_agente="qa_seguranca",
    )
    squad.agentes[-1].tools = _tools_para("qa_seguranca")

    return squad
