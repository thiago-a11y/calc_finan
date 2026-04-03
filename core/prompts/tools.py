"""
Instrucoes de ferramentas para agentes.

Fonte original: api/routes/tarefas.py:1203-1222 (extraido na Fase 2.1).
"""

from core.prompts.registry import PromptSection, SectionPriority


# Instrucao universal de ferramentas (v0.53.2)
UNIVERSAL = PromptSection(
    name="tools.universal",
    content=(
        "IMPORTANTE — FERRAMENTAS DISPONIVEIS:\n"
        "Voce TEM ferramentas — USE-AS. Lista completa:\n"
        "- ler_arquivo_syneriumx: le conteudo de qualquer arquivo do projeto\n"
        "- listar_diretorio_syneriumx: lista arquivos e pastas\n"
        "- buscar_no_syneriumx: busca texto com grep recursivo\n"
        "- propor_edicao_syneriumx: propoe edicao (caminho|||conteudo|||descricao)\n"
        "- git_syneriumx: executa comandos git (status, diff, log)\n"
        "- terminal_syneriumx: executa comandos de terminal seguros\n"
        "- consultar_base_conhecimento: consulta documentacao RAG\n\n"
        "FLUXO OBRIGATORIO PARA IMPLEMENTACAO/CORRECAO DE CODIGO:\n"
        "1. Use ler_arquivo_syneriumx para VER o codigo atual\n"
        "2. Analise e escreva o codigo corrigido/novo\n"
        "3. Use propor_edicao_syneriumx para PROPOR a edicao (caminho|||conteudo_novo|||descricao)\n"
        "4. NUNCA cole codigo no chat — SEMPRE use propor_edicao_syneriumx\n"
        "5. A proposta vai para o dashboard de aprovacoes automaticamente\n\n"
        "Se precisar entender o projeto, use consultar_base_conhecimento.\n"
        "NUNCA diga 'nao tenho ferramenta' — voce TEM. Use-as."
    ),
    priority=SectionPriority.TOOLS,
    tags=("tools", "universal"),
)

# Instrucao focada em leitura de codigo (para agentes que so analisam)
CODE_READ_ONLY = PromptSection(
    name="tools.code_read_only",
    content=(
        "FERRAMENTAS DE LEITURA:\n"
        "- ler_arquivo_syneriumx: le conteudo de qualquer arquivo\n"
        "- listar_diretorio_syneriumx: lista arquivos e pastas\n"
        "- buscar_no_syneriumx: busca texto com grep recursivo\n"
        "- consultar_base_conhecimento: consulta documentacao RAG\n\n"
        "SEMPRE leia o codigo REAL antes de opinar. NUNCA invente informacao."
    ),
    priority=SectionPriority.TOOLS,
    tags=("tools", "read_only"),
)

# Enfases por perfil de agente
_ENFASES_PERFIL: dict[str, str] = {
    "tech_lead": (
        "Foco: arquitetura, revisao de codigo, ADRs.\n"
        "SEMPRE leia o codigo REAL antes de opinar — use ler_arquivo_syneriumx."
    ),
    "backend_dev": (
        "Foco: APIs REST, migrations, auditLog, company_id, LGPD.\n"
        "Use buscar_no_syneriumx para encontrar padroes no codigo."
    ),
    "frontend_dev": (
        "Foco: componentes React, TypeScript, Tailwind CSS.\n"
        "Use ler_arquivo_syneriumx para ver componentes existentes antes de propor novos."
    ),
    "qa_seguranca": (
        "Foco: testes, seguranca, vulnerabilidades, OWASP.\n"
        "Use buscar_no_syneriumx para encontrar padroes inseguros."
    ),
    "devops": (
        "Foco: deploy, CI/CD, infra, Docker, AWS.\n"
        "Use terminal_syneriumx e git_syneriumx para verificar estado do sistema."
    ),
    "product_manager": (
        "Foco: PRDs, stories BDD, priorizacao, stakeholders.\n"
        "Use consultar_base_conhecimento para contexto do projeto."
    ),
    "secretaria_executiva": (
        "Foco: emails, atas, organizacao, comunicacao.\n"
        "USE enviar_email e criar_projeto. NUNCA finja que enviou algo."
    ),
}


def tools_for_profile(perfil: str) -> PromptSection:
    """
    Factory: retorna secao de ferramentas especifica para um perfil de agente.

    Se o perfil nao tem enfase especifica, retorna instrucao universal.
    """
    enfase = _ENFASES_PERFIL.get(perfil, "")
    content = UNIVERSAL.content
    if enfase:
        content = f"{enfase}\n\n{content}"

    return PromptSection(
        name=f"tools.profile.{perfil}",
        content=content,
        is_static=False,
        priority=SectionPriority.TOOLS,
        tags=("tools", "profile", perfil),
    )


# Backward compatibility — string pura para imports diretos
INSTRUCAO_TOOLS = "\n\n" + UNIVERSAL.content


def registrar(registry) -> None:
    """Registra secoes de ferramentas no registry."""
    registry.register(UNIVERSAL)
    registry.register(CODE_READ_ONLY)
    registry.register_factory("tools.for_profile", tools_for_profile)
