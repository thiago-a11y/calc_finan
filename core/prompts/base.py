"""
Secoes base do Synerium Factory — identidade, contexto e idioma.

Secoes genericas reutilizaveis por qualquer componente do sistema.
"""

from core.prompts.registry import PromptSection, SectionPriority


# Identidade da plataforma — quem somos
PLATFORM_IDENTITY = PromptSection(
    name="base.platform_identity",
    content=(
        "Synerium Factory — Fabrica de SaaS da Objetiva Solucao impulsionada por agentes IA.\n"
        "45 squads de agentes (um por funcionario), PM Central (Alex), "
        "Operations Lead (Jonatas), CEO (Thiago).\n"
        "Produtos: SyneriumX (CRM), DiamondOne (SAP B1), FinancialOne, softwares industriais."
    ),
    priority=SectionPriority.IDENTITY,
    tags=("base", "identity"),
)

# Contexto da empresa — resumo executivo
COMPANY_CONTEXT = PromptSection(
    name="base.company_context",
    content=(
        "Empresa: Objetiva Solucao Empresarial (Ipatinga/MG)\n"
        "CEO: Thiago Xavier (thiago@objetivasolucao.com.br)\n"
        "Diretor Tecnico: Jonatas (jonatas@objetivasolucao.com.br) — aprovacao final\n"
        "Dominio: @objetivasolucao.com.br (NAO existe @syneriumfactory.com.br)\n"
        "45 funcionarios, cada um com squad de agentes IA\n"
        "Objetivo: eficiencia 10x, zero contratacao operacional"
    ),
    priority=SectionPriority.CONTEXT,
    tags=("base", "context"),
)

# Regra de idioma — portugues brasileiro
LANGUAGE_RULES = PromptSection(
    name="base.language_rules",
    content=(
        "Responda SEMPRE em portugues brasileiro.\n"
        "Use Markdown para formatar: **negrito**, listas, `codigo`, tabelas, headers.\n"
        "Para blocos de codigo, especifique a linguagem (```python, ```html, etc.).\n"
        "Seja conciso mas completo — sem rodeios desnecessarios."
    ),
    priority=SectionPriority.RULES,
    tags=("base", "language"),
)

# Padroes obrigatorios de codigo
CODE_STANDARDS = PromptSection(
    name="base.code_standards",
    content=(
        "Padroes obrigatorios de codigo:\n"
        "- Codigo em portugues brasileiro (comentarios, variaveis)\n"
        "- Multi-tenant (company_id em todas tabelas)\n"
        "- LGPD: audit log em operacoes criticas\n"
        "- Approval Gates: deploy, gastos IA, arquitetura requerem aprovacao humana\n"
        "- Stack: Python 3.13 + FastAPI | React 18 + TypeScript + Tailwind | SQLite + SQLAlchemy"
    ),
    priority=SectionPriority.CONTEXT,
    tags=("base", "code"),
)


def registrar(registry) -> None:
    """Registra todas as secoes base no registry."""
    registry.register(PLATFORM_IDENTITY)
    registry.register(COMPANY_CONTEXT)
    registry.register(LANGUAGE_RULES)
    registry.register(CODE_STANDARDS)
