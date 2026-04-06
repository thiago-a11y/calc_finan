"""
Skills Catalog — Registra metadados de skills SEM instanciar ferramentas.

Resolve o problema do ChromaDB crash no Ubuntu 22.04:
algumas ferramentas do CrewAI (WebsiteSearchTool, DirectorySearchTool, etc.)
inicializam ChromaDB internamente ao serem instanciadas, causando crash.

Este módulo registra apenas os metadados (nome, descrição, categoria, ícone)
para que a aba Skills do dashboard funcione. As ferramentas reais são
instanciadas apenas quando o agente CrewAI é disparado (lazy loading).

Uso:
    from tools.skills_catalog import registrar_catalogo_skills
    registrar_catalogo_skills()
"""

import logging
import os

from tools.registry import skill_registry, SkillDefinition

logger = logging.getLogger("synerium.skills")


# Catálogo completo de skills (metadados apenas)
SKILLS_CATALOG = [
    # Código e Arquivos
    {"id": "arquivo_ler", "nome": "Ler Arquivo", "descricao": "Lê o conteúdo completo de qualquer arquivo do projeto.", "categoria": "codigo", "icone": "📖"},
    {"id": "diretorio_listar", "nome": "Listar Diretório", "descricao": "Lista todos os arquivos e pastas de um diretório.", "categoria": "codigo", "icone": "📂"},
    {"id": "diretorio_buscar", "nome": "Buscar em Diretório", "descricao": "Busca arquivos por nome ou conteúdo dentro de um diretório.", "categoria": "codigo", "icone": "🔎"},
    {"id": "arquivo_escrever", "nome": "Escrever Arquivo", "descricao": "Cria ou sobrescreve um arquivo.", "categoria": "escrita", "icone": "✏️"},
    {"id": "codigo_executar", "nome": "Executar Código Python", "descricao": "Executa código Python em sandbox seguro.", "categoria": "codigo", "icone": "🐍"},

    # Web e Pesquisa
    {"id": "web_scrape", "nome": "Ler Página Web", "descricao": "Extrai o conteúdo de uma página web.", "categoria": "web", "icone": "🌐"},
    {"id": "web_buscar", "nome": "Buscar em Site", "descricao": "Busca informações dentro de um site específico.", "categoria": "web", "icone": "🔍"},
    {"id": "tavily_buscar", "nome": "Busca Web Inteligente (Tavily)", "descricao": "Busca avançada na web otimizada para agentes IA.", "categoria": "web", "icone": "🧠", "requer_config": True, "env": "TAVILY_API_KEY"},
    {"id": "firecrawl_scrape", "nome": "Scraping Avançado (Firecrawl)", "descricao": "Extrai conteúdo de qualquer site e converte em markdown limpo.", "categoria": "web", "icone": "🔥", "requer_config": True, "env": "FIRECRAWL_API_KEY"},
    {"id": "firecrawl_crawl", "nome": "Crawl Completo (Firecrawl)", "descricao": "Navega por todas as páginas de um site e extrai conteúdo.", "categoria": "web", "icone": "🕷️", "requer_config": True, "env": "FIRECRAWL_API_KEY"},
    {"id": "exa_buscar", "nome": "Busca Semântica Web (EXA)", "descricao": "Busca na web por significado, não por keywords.", "categoria": "web", "icone": "🎯", "requer_config": True, "env": "EXA_API_KEY"},
    {"id": "scrapingdog_google", "nome": "Google Search (ScrapingDog)", "descricao": "Busca real no Google via ScrapingDog.", "categoria": "web", "icone": "🐕", "requer_config": True, "env": "SCRAPINGDOG_API_KEY"},

    # Dados
    {"id": "json_buscar", "nome": "Buscar em JSON", "descricao": "Busca informações em arquivos JSON.", "categoria": "dados", "icone": "📊"},
    {"id": "csv_buscar", "nome": "Buscar em CSV", "descricao": "Busca e analisa dados em arquivos CSV.", "categoria": "dados", "icone": "📈"},
    {"id": "pdf_buscar", "nome": "Buscar em PDF", "descricao": "Extrai e busca informações em arquivos PDF.", "categoria": "dados", "icone": "📑"},
    {"id": "markdown_buscar", "nome": "Buscar em Markdown", "descricao": "Busca em arquivos Markdown (.md/.mdx).", "categoria": "conhecimento", "icone": "📝"},
    {"id": "texto_buscar", "nome": "Buscar em Texto", "descricao": "Busca em arquivos de texto (.txt, .log).", "categoria": "dados", "icone": "📄"},

    # Conhecimento (RAG)
    {"id": "rag_consultar", "nome": "Consultar Base de Conhecimento", "descricao": "Busca semântica nos vaults Obsidian (SyneriumX + Factory).", "categoria": "conhecimento", "icone": "📚", "requer_config": True, "env": "CHROMADB"},

    # GitHub
    {"id": "github_buscar", "nome": "Buscar no GitHub", "descricao": "Busca código, issues e PRs nos repositórios do GitHub.", "categoria": "codigo", "icone": "🐙", "requer_config": True, "env": "GITHUB_TOKEN"},

    # Integrações
    {"id": "composio_hub", "nome": "Composio Hub (200+ Apps)", "descricao": "Hub de integrações: GitHub, Slack, Gmail, Google Calendar, Notion e 200+ apps.", "categoria": "integracao", "icone": "🔌", "requer_config": True, "env": "COMPOSIO_API_KEY"},
    {"id": "e2b_sandbox", "nome": "Sandbox Cloud (E2B)", "descricao": "Executa código Python em sandbox cloud isolado e seguro.", "categoria": "codigo", "icone": "☁️", "requer_config": True, "env": "E2B_API_KEY"},

    # Comunicação
    {"id": "email_enviar", "nome": "Enviar Email (Amazon SES)", "descricao": "Envia emails de texto/HTML via Amazon SES.", "categoria": "comunicacao", "icone": "📧", "requer_config": True, "env": "AWS_SES_SENDER"},
    {"id": "email_enviar_anexo", "nome": "Enviar Email com Anexo (Amazon SES)", "descricao": "Envia email com arquivo anexado via Amazon SES.", "categoria": "comunicacao", "icone": "📎", "requer_config": True, "env": "AWS_SES_SENDER"},

    # Projetos e ZIP
    {"id": "projeto_criar", "nome": "Criar Projeto (múltiplos arquivos)", "descricao": "Cria múltiplos arquivos de um projeto de uma vez.", "categoria": "escrita", "icone": "🏗️"},
    {"id": "zip_criar", "nome": "Criar ZIP", "descricao": "Compacta um diretório ou projeto em .zip.", "categoria": "escrita", "icone": "📦"},

    # SyneriumX
    {"id": "sx_ler_arquivo", "nome": "Ler Arquivo SyneriumX", "descricao": "Lê arquivos do projeto real SyneriumX.", "categoria": "syneriumx", "icone": "📖"},
    {"id": "sx_listar_diretorio", "nome": "Listar Diretório SyneriumX", "descricao": "Lista pastas e arquivos do projeto SyneriumX.", "categoria": "syneriumx", "icone": "📂"},
    {"id": "sx_escrever_arquivo", "nome": "Propor Edição SyneriumX", "descricao": "Propõe edição em arquivo do SyneriumX (requer aprovação).", "categoria": "syneriumx", "icone": "📝"},
    {"id": "sx_buscar", "nome": "Buscar no SyneriumX (grep)", "descricao": "Busca texto em todo o projeto SyneriumX.", "categoria": "syneriumx", "icone": "🔍"},
    {"id": "sx_git", "nome": "Git SyneriumX", "descricao": "Executa git no SyneriumX: status, diff, log, branch, commit.", "categoria": "syneriumx", "icone": "🌿"},
    {"id": "sx_terminal", "nome": "Terminal SyneriumX", "descricao": "Terminal seguro no diretório do SyneriumX.", "categoria": "syneriumx", "icone": "💻"},
]

# Perfis (quais skills cada tipo de agente usa)
PERFIS = {
    "tech_lead": ["rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar", "tavily_buscar", "firecrawl_scrape", "github_buscar", "json_buscar", "markdown_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "backend_dev": ["rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar", "json_buscar", "codigo_executar", "github_buscar", "tavily_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "frontend_dev": ["rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar", "json_buscar", "tavily_buscar", "web_scrape", "markdown_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "especialista_ia": ["rag_consultar", "arquivo_ler", "tavily_buscar", "exa_buscar", "firecrawl_scrape", "codigo_executar", "json_buscar", "csv_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "integracao": ["rag_consultar", "arquivo_ler", "tavily_buscar", "firecrawl_scrape", "firecrawl_crawl", "json_buscar", "codigo_executar", "markdown_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "devops": ["rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar", "tavily_buscar", "github_buscar", "codigo_executar", "json_buscar", "texto_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "qa_seguranca": ["rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar", "codigo_executar", "tavily_buscar", "exa_buscar", "scrapingdog_google", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "secretaria_executiva": ["rag_consultar", "arquivo_ler", "diretorio_listar", "arquivo_escrever", "tavily_buscar", "json_buscar", "csv_buscar", "pdf_buscar", "projeto_criar", "zip_criar", "email_enviar", "email_enviar_anexo", "codigo_executar", "markdown_buscar", "texto_buscar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
    "product_manager": ["rag_consultar", "tavily_buscar", "exa_buscar", "scrapingdog_google", "firecrawl_scrape", "arquivo_escrever", "csv_buscar", "pdf_buscar", "projeto_criar", "zip_criar", "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo", "sx_buscar", "sx_git", "sx_terminal"],
}


def registrar_catalogo_skills() -> None:
    """
    Registra metadados de todas as skills no catálogo global.

    Não instancia nenhuma ferramenta — apenas popula o registry
    com dados para o dashboard. Ferramentas reais são lazy-loaded
    pelo CrewAI quando o agente é disparado.
    """
    logger.info("[SKILLS] Registrando catálogo de skills (metadados apenas)...")

    for s in SKILLS_CATALOG:
        env_key = s.get("env", "")
        requer = s.get("requer_config", False)
        ativa = True

        # Verificar se a env var está configurada
        if env_key and env_key != "CHROMADB":
            ativa = bool(os.getenv(env_key, ""))
        elif env_key == "CHROMADB":
            ativa = False  # RAG desabilitado por ChromaDB crash

        skill_registry.registrar(SkillDefinition(
            id=s["id"],
            nome=s["nome"],
            descricao=s["descricao"],
            categoria=s["categoria"],
            ferramenta=None,  # Lazy — instanciada pelo CrewAI quando o agente roda
            requer_config=requer,
            ativa=ativa,
            icone=s["icone"],
        ))

    # Registrar perfis
    for perfil, skill_ids in PERFIS.items():
        skill_registry.registrar_perfil(perfil, skill_ids)

    logger.info(f"[SKILLS] Catálogo registrado: {skill_registry.total} skills, {len(PERFIS)} perfis")
