"""
Skills Setup — Inicializa todas as skills e atribui aos perfis de agentes.

Este arquivo é o ponto central para:
1. Criar instâncias de todas as ferramentas disponíveis
2. Registrar no catálogo (SkillRegistry)
3. Definir quais skills cada perfil de agente usa

Ferramentas usadas:
- CrewAI Tools (built-in): FileReadTool, DirectoryReadTool, ScrapeWebsiteTool, etc.
- Custom: ConsultarBaseConhecimento, EscreverObsidian, AnalisarSeguranca
"""

import logging
from pathlib import Path

from tools.registry import SkillRegistry, SkillDefinition, skill_registry

logger = logging.getLogger("synerium.skills")


def inicializar_skills(rag_query=None, vault_factory_path: str = "") -> SkillRegistry:
    """
    Inicializa todas as skills e registra no catálogo global.

    Args:
        rag_query: Instância de RAGQuery para a skill de base de conhecimento.
        vault_factory_path: Caminho do vault Obsidian do Factory para escrita.

    Returns:
        SkillRegistry com todas as skills registradas.
    """
    logger.info("[SKILLS] Inicializando catálogo de skills...")

    # ==============================================================
    # 1. SKILL: Base de Conhecimento (RAG) — já existente
    # ==============================================================
    if rag_query:
        from tools.rag_tool import ConsultarBaseConhecimento
        skill_registry.registrar(SkillDefinition(
            id="rag_consultar",
            nome="Consultar Base de Conhecimento",
            descricao="Busca semântica nos vaults Obsidian (SyneriumX + Factory). Encontra arquitetura, decisões, roadmap, bugs e toda documentação.",
            categoria="conhecimento",
            ferramenta=ConsultarBaseConhecimento(rag_query=rag_query),
            icone="📚",
        ))

    # ==============================================================
    # 2. SKILLS: Leitura de Código e Arquivos
    # ==============================================================
    from crewai_tools import FileReadTool, DirectoryReadTool, DirectorySearchTool

    skill_registry.registrar(SkillDefinition(
        id="arquivo_ler",
        nome="Ler Arquivo",
        descricao="Lê o conteúdo completo de qualquer arquivo do projeto. Útil para analisar código PHP, React, configs, migrations.",
        categoria="codigo",
        ferramenta=FileReadTool(),
        icone="📖",
    ))

    skill_registry.registrar(SkillDefinition(
        id="diretorio_listar",
        nome="Listar Diretório",
        descricao="Lista todos os arquivos e pastas de um diretório. Útil para entender estrutura de projetos.",
        categoria="codigo",
        ferramenta=DirectoryReadTool(),
        icone="📂",
    ))

    skill_registry.registrar(SkillDefinition(
        id="diretorio_buscar",
        nome="Buscar em Diretório",
        descricao="Busca arquivos por nome ou conteúdo dentro de um diretório. Encontra classes, funções, configs.",
        categoria="codigo",
        ferramenta=DirectorySearchTool(),
        icone="🔎",
    ))

    # ==============================================================
    # 3. SKILLS: Web e Pesquisa
    # ==============================================================
    import os
    from crewai_tools import ScrapeWebsiteTool, WebsiteSearchTool

    skill_registry.registrar(SkillDefinition(
        id="web_scrape",
        nome="Ler Página Web",
        descricao="Extrai o conteúdo de uma página web. Útil para ler documentação, artigos, changelogs de libs.",
        categoria="web",
        ferramenta=ScrapeWebsiteTool(),
        icone="🌐",
    ))

    skill_registry.registrar(SkillDefinition(
        id="web_buscar",
        nome="Buscar em Site",
        descricao="Busca informações dentro de um site específico. Útil para pesquisar documentação técnica.",
        categoria="web",
        ferramenta=WebsiteSearchTool(),
        icone="🔍",
    ))

    # Tavily — Busca web premium feita para agentes IA
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        from crewai_tools import TavilySearchTool
        skill_registry.registrar(SkillDefinition(
            id="tavily_buscar",
            nome="Busca Web Inteligente (Tavily)",
            descricao="Busca avançada na web otimizada para agentes IA. Retorna resultados relevantes do Google com resumo. Muito superior a scraping simples.",
            categoria="web",
            ferramenta=TavilySearchTool(),
            icone="🧠",
        ))
        logger.info("[SKILL] Tavily ativada com sucesso!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="tavily_buscar",
            nome="Busca Web Inteligente (Tavily)",
            descricao="Busca avançada na web. Requer TAVILY_API_KEY no .env.",
            categoria="web",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🧠",
        ))

    # Firecrawl — Scraping avançado (converte qualquer site em markdown limpo)
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")
    if firecrawl_key:
        from crewai_tools import FirecrawlScrapeWebsiteTool, FirecrawlCrawlWebsiteTool
        skill_registry.registrar(SkillDefinition(
            id="firecrawl_scrape",
            nome="Scraping Avançado (Firecrawl)",
            descricao="Extrai conteúdo de qualquer site e converte em markdown limpo. Funciona com JS, SPAs e sites complexos. Superior ao scraping básico.",
            categoria="web",
            ferramenta=FirecrawlScrapeWebsiteTool(),
            icone="🔥",
        ))
        skill_registry.registrar(SkillDefinition(
            id="firecrawl_crawl",
            nome="Crawl Completo (Firecrawl)",
            descricao="Navega por todas as páginas de um site e extrai conteúdo. Útil para mapear documentação completa de APIs e libs.",
            categoria="web",
            ferramenta=FirecrawlCrawlWebsiteTool(),
            icone="🕷️",
        ))
        logger.info("[SKILL] Firecrawl ativado com sucesso!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="firecrawl_scrape",
            nome="Scraping Avançado (Firecrawl)",
            descricao="Requer FIRECRAWL_API_KEY no .env.",
            categoria="web",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🔥",
        ))

    # EXA — Busca semântica (encontra por significado, não por keywords)
    exa_key = os.getenv("EXA_API_KEY", "")
    if exa_key:
        from crewai_tools import EXASearchTool
        skill_registry.registrar(SkillDefinition(
            id="exa_buscar",
            nome="Busca Semântica Web (EXA)",
            descricao="Busca na web por significado, não por keywords. Encontra artigos, papers e conteúdo relevante mesmo com termos diferentes. Ideal para pesquisa técnica e de concorrência.",
            categoria="web",
            ferramenta=EXASearchTool(),
            icone="🎯",
        ))
        logger.info("[SKILL] EXA ativada com sucesso!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="exa_buscar",
            nome="Busca Semântica Web (EXA)",
            descricao="Requer EXA_API_KEY no .env.",
            categoria="web",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🎯",
        ))

    # Composio — Hub de 200+ integrações (Slack, Gmail, Calendar, Notion, GitHub, etc.)
    composio_key = os.getenv("COMPOSIO_API_KEY", "")
    if composio_key:
        try:
            from composio_crewai import CrewAIProvider
            from composio import Composio
            composio_client = Composio(api_key=composio_key)
            composio_toolset = CrewAIProvider(client=composio_client)

            # Registrar Composio como hub disponível
            skill_registry.registrar(SkillDefinition(
                id="composio_hub",
                nome="Composio Hub (200+ Apps)",
                descricao="Hub de integrações: GitHub, Slack, Gmail, Google Calendar, Notion e 200+ apps. Configurar conexões em composio.dev.",
                categoria="integracao",
                ferramenta=None,  # Ferramentas individuais são adicionadas via composio.dev
                ativa=True,
                icone="🔌",
            ))
            logger.info("[SKILL] Composio ativado com sucesso! Configure conexões em composio.dev.")
        except Exception as e:
            logger.warning(f"[SKILL] Composio: erro na inicialização — {e}")
    else:
        skill_registry.registrar(SkillDefinition(
            id="composio_github",
            nome="GitHub via Composio",
            descricao="Requer COMPOSIO_API_KEY no .env.",
            categoria="integracao",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🐙",
        ))

    # ==============================================================
    # 4. SKILLS: Escrita de Arquivos
    # ==============================================================
    from crewai_tools import FileWriterTool

    skill_registry.registrar(SkillDefinition(
        id="arquivo_escrever",
        nome="Escrever Arquivo",
        descricao="Cria ou sobrescreve um arquivo. Útil para gerar relatórios, documentação, código.",
        categoria="escrita",
        ferramenta=FileWriterTool(),
        icone="✏️",
    ))

    # ==============================================================
    # 5. SKILLS: Análise de Dados
    # ==============================================================
    from crewai_tools import JSONSearchTool, CSVSearchTool, PDFSearchTool

    skill_registry.registrar(SkillDefinition(
        id="json_buscar",
        nome="Buscar em JSON",
        descricao="Busca informações em arquivos JSON. Útil para analisar configs, package.json, APIs.",
        categoria="dados",
        ferramenta=JSONSearchTool(),
        icone="📊",
    ))

    skill_registry.registrar(SkillDefinition(
        id="csv_buscar",
        nome="Buscar em CSV",
        descricao="Busca e analisa dados em arquivos CSV. Útil para relatórios, métricas, exports.",
        categoria="dados",
        ferramenta=CSVSearchTool(),
        icone="📈",
    ))

    skill_registry.registrar(SkillDefinition(
        id="pdf_buscar",
        nome="Buscar em PDF",
        descricao="Extrai e busca informações em arquivos PDF. Útil para contratos, documentação técnica.",
        categoria="dados",
        ferramenta=PDFSearchTool(),
        icone="📑",
    ))

    # ==============================================================
    # 6. SKILLS: Código
    # ==============================================================
    from crewai_tools import CodeInterpreterTool

    skill_registry.registrar(SkillDefinition(
        id="codigo_executar",
        nome="Executar Código Python",
        descricao="Executa código Python em sandbox seguro. Útil para cálculos, análises, protótipos, testes.",
        categoria="codigo",
        ferramenta=CodeInterpreterTool(),
        icone="🐍",
    ))

    # E2B — Sandbox de código cloud (mais seguro e poderoso que local)
    e2b_key = os.getenv("E2B_API_KEY", "")
    if e2b_key:
        # E2B funciona como backend do CodeInterpreterTool quando a env var está presente
        # O CrewAI CodeInterpreterTool detecta automaticamente E2B_API_KEY
        skill_registry.registrar(SkillDefinition(
            id="e2b_sandbox",
            nome="Sandbox Cloud (E2B)",
            descricao="Executa código Python em sandbox cloud isolado e seguro. Suporta pip install, manipulação de arquivos e análises complexas. Mais seguro que execução local.",
            categoria="codigo",
            ferramenta=None,  # E2B é ativado automaticamente pelo CodeInterpreterTool via env var
            ativa=True,
            icone="☁️",
        ))
        logger.info("[SKILL] E2B configurado — CodeInterpreterTool usará sandbox cloud!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="e2b_sandbox",
            nome="Sandbox Cloud (E2B)",
            descricao="Requer E2B_API_KEY no .env.",
            categoria="codigo",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="☁️",
        ))

    # ==============================================================
    # 7. SKILLS: GitHub
    # ==============================================================
    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token:
        from crewai_tools import GithubSearchTool
        skill_registry.registrar(SkillDefinition(
            id="github_buscar",
            nome="Buscar no GitHub",
            descricao="Busca código, issues e PRs nos repositórios do GitHub. Acesso completo a repos privados e públicos.",
            categoria="codigo",
            ferramenta=GithubSearchTool(
                gh_token=github_token,
                content_types=["code", "issue", "pr"],
            ),
            icone="🐙",
        ))
        logger.info("[SKILL] GitHub ativado com sucesso!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="github_buscar",
            nome="Buscar no GitHub",
            descricao="Requer GITHUB_TOKEN no .env.",
            categoria="codigo",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🐙",
        ))

    # ScrapingDog — Google SERP API (rápido e barato)
    scrapingdog_key = os.getenv("SCRAPINGDOG_API_KEY", "")
    if scrapingdog_key:
        from tools.scrapingdog_tool import ScrapingDogSearchTool
        skill_registry.registrar(SkillDefinition(
            id="scrapingdog_google",
            nome="Google Search (ScrapingDog)",
            descricao="Busca real no Google via ScrapingDog. Retorna títulos, links e snippets. Rápido (~1.25s). Ideal para SEO, concorrência e pesquisa técnica.",
            categoria="web",
            ferramenta=ScrapingDogSearchTool(),
            icone="🐕",
        ))
        logger.info("[SKILL] ScrapingDog ativado com sucesso!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="scrapingdog_google",
            nome="Google Search (ScrapingDog)",
            descricao="Requer SCRAPINGDOG_API_KEY no .env.",
            categoria="web",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="🐕",
        ))

    # ==============================================================
    # 8. SKILLS: Markdown/Docs
    # ==============================================================
    from crewai_tools import MDXSearchTool, TXTSearchTool

    skill_registry.registrar(SkillDefinition(
        id="markdown_buscar",
        nome="Buscar em Markdown",
        descricao="Busca em arquivos Markdown (.md/.mdx). Útil para pesquisar documentação do projeto.",
        categoria="conhecimento",
        ferramenta=MDXSearchTool(),
        icone="📝",
    ))

    skill_registry.registrar(SkillDefinition(
        id="texto_buscar",
        nome="Buscar em Texto",
        descricao="Busca em arquivos de texto (.txt, .log). Útil para analisar logs e outputs.",
        categoria="dados",
        ferramenta=TXTSearchTool(),
        icone="📄",
    ))

    # ==============================================================
    # 9. SKILLS: Comunicação (Email + Email com Anexo)
    # ==============================================================
    aws_access = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_sender = os.getenv("AWS_SES_SENDER", "")
    if aws_access and aws_secret and aws_sender:
        from tools.email_tool import EnviarEmailTool, EnviarEmailComAnexoTool
        skill_registry.registrar(SkillDefinition(
            id="email_enviar",
            nome="Enviar Email (Amazon SES)",
            descricao=(
                "Envia emails de texto/HTML via Amazon SES. "
                "Formato: destinatario|assunto|corpo. "
                "Limite: 10 emails por execução."
            ),
            categoria="comunicacao",
            ferramenta=EnviarEmailTool(
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key=aws_access,
                aws_secret_key=aws_secret,
                remetente=aws_sender,
            ),
            icone="📧",
        ))
        skill_registry.registrar(SkillDefinition(
            id="email_enviar_anexo",
            nome="Enviar Email com Anexo (Amazon SES)",
            descricao=(
                "Envia email com arquivo anexado (.zip, .pdf, etc.) via Amazon SES. "
                "Formato: destinatario|assunto|corpo|caminho_do_anexo. "
                "Máximo 10 MB por anexo. Caminho relativo à pasta output/."
            ),
            categoria="comunicacao",
            ferramenta=EnviarEmailComAnexoTool(
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key=aws_access,
                aws_secret_key=aws_secret,
                remetente=aws_sender,
            ),
            icone="📎",
        ))
        logger.info("[SKILL] Email + Email com Anexo (Amazon SES) ativados!")
    else:
        skill_registry.registrar(SkillDefinition(
            id="email_enviar",
            nome="Enviar Email (Amazon SES)",
            descricao="Requer AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY e AWS_SES_SENDER no .env.",
            categoria="comunicacao",
            ferramenta=None,
            requer_config=True,
            ativa=False,
            icone="📧",
        ))

    # ==============================================================
    # 10. SKILLS: Criação de Projetos e ZIP
    # ==============================================================
    from tools.zip_tool import CriarProjetoTool, CriarZipTool

    skill_registry.registrar(SkillDefinition(
        id="projeto_criar",
        nome="Criar Projeto (múltiplos arquivos)",
        descricao=(
            "Cria múltiplos arquivos de um projeto de uma vez (HTML, CSS, JS, etc.). "
            "Formato: nome_projeto|||arquivo1:::conteudo1|||arquivo2:::conteudo2. "
            "Arquivos salvos em output/nome_projeto/."
        ),
        categoria="escrita",
        ferramenta=CriarProjetoTool(),
        icone="🏗️",
    ))

    skill_registry.registrar(SkillDefinition(
        id="zip_criar",
        nome="Criar ZIP",
        descricao=(
            "Compacta um diretório ou projeto em .zip. "
            "Formato: caminho_diretorio|nome_do_zip. "
            "Exemplo: meu_projeto|meu_projeto.zip. "
            "ZIP salvo em output/."
        ),
        categoria="escrita",
        ferramenta=CriarZipTool(),
        icone="📦",
    ))
    logger.info("[SKILL] Criar Projeto + ZIP ativados!")

    # ==============================================================
    # 11. SKILLS: Edição Real do SyneriumX (~/propostasap)
    # ==============================================================
    from tools.syneriumx_tools import (
        LerArquivoSyneriumX, ListarDiretorioSyneriumX,
        ProporEdicaoSyneriumX, BuscarNoSyneriumX,
        GitSyneriumX, TerminalSyneriumX,
    )

    skill_registry.registrar(SkillDefinition(
        id="sx_ler_arquivo",
        nome="Ler Arquivo SyneriumX",
        descricao="Lê arquivos do projeto real SyneriumX em ~/propostasap. Código PHP, React, configs, etc.",
        categoria="syneriumx",
        ferramenta=LerArquivoSyneriumX(),
        icone="📖",
    ))

    skill_registry.registrar(SkillDefinition(
        id="sx_listar_diretorio",
        nome="Listar Diretório SyneriumX",
        descricao="Lista pastas e arquivos do projeto SyneriumX. Navegação completa no repositório.",
        categoria="syneriumx",
        ferramenta=ListarDiretorioSyneriumX(),
        icone="📂",
    ))

    skill_registry.registrar(SkillDefinition(
        id="sx_escrever_arquivo",
        nome="Propor Edição SyneriumX",
        descricao="Propõe edição em arquivo do SyneriumX. NÃO aplica direto — gera solicitação que o proprietário aprova no dashboard.",
        categoria="syneriumx",
        ferramenta=ProporEdicaoSyneriumX(),
        icone="📝",
    ))

    skill_registry.registrar(SkillDefinition(
        id="sx_buscar",
        nome="Buscar no SyneriumX (grep)",
        descricao="Busca texto em todo o projeto SyneriumX. Grep recursivo por termo, diretório e extensão.",
        categoria="syneriumx",
        ferramenta=BuscarNoSyneriumX(),
        icone="🔍",
    ))

    skill_registry.registrar(SkillDefinition(
        id="sx_git",
        nome="Git SyneriumX",
        descricao="Executa git no SyneriumX: status, diff, log, branch, add, commit. Push/merge requerem aprovação.",
        categoria="syneriumx",
        ferramenta=GitSyneriumX(),
        icone="🌿",
    ))

    skill_registry.registrar(SkillDefinition(
        id="sx_terminal",
        nome="Terminal SyneriumX",
        descricao="Terminal seguro no diretório do SyneriumX. Comandos destrutivos bloqueados. Para find, wc, cat, head, etc.",
        categoria="syneriumx",
        ferramenta=TerminalSyneriumX(),
        icone="💻",
    ))

    logger.info("[SKILL] SyneriumX Tools (6 ferramentas) ativadas — base: ~/propostasap")

    # ==============================================================
    # PERFIS DE AGENTES — Quais skills cada um recebe
    # ==============================================================

    # Skills compartilhadas — todos os agentes tem acesso
    # NOTA: email removido dos comuns para evitar envio automatico sem aprovacao
    # Apenas Sofia (secretaria_executiva) pode enviar emails
    _skills_comuns = ["projeto_criar", "zip_criar"]

    # Skills do SyneriumX — acesso ao repositório real
    _skills_syneriumx = [
        "sx_ler_arquivo", "sx_listar_diretorio", "sx_escrever_arquivo",
        "sx_buscar", "sx_git", "sx_terminal",
    ]

    skill_registry.registrar_perfil("tech_lead", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar",
        "tavily_buscar", "firecrawl_scrape", "github_buscar", "json_buscar", "markdown_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("backend_dev", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar",
        "json_buscar", "codigo_executar", "github_buscar", "tavily_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("frontend_dev", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar",
        "json_buscar", "tavily_buscar", "web_scrape", "markdown_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("especialista_ia", [
        "rag_consultar", "arquivo_ler", "tavily_buscar", "exa_buscar", "firecrawl_scrape",
        "codigo_executar", "json_buscar", "csv_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("integracao", [
        "rag_consultar", "arquivo_ler", "tavily_buscar", "firecrawl_scrape", "firecrawl_crawl",
        "json_buscar", "codigo_executar", "markdown_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("devops", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar",
        "tavily_buscar", "github_buscar", "codigo_executar", "json_buscar", "texto_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    skill_registry.registrar_perfil("qa_seguranca", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "diretorio_buscar",
        "codigo_executar", "tavily_buscar", "exa_buscar", "scrapingdog_google",
    ] + _skills_comuns + _skills_syneriumx)

    # Sofia — Secretária Executiva: TEM TUDO
    skill_registry.registrar_perfil("secretaria_executiva", [
        "rag_consultar", "arquivo_ler", "diretorio_listar", "arquivo_escrever",
        "tavily_buscar", "json_buscar", "csv_buscar", "pdf_buscar",
        "projeto_criar", "zip_criar", "email_enviar", "email_enviar_anexo",
        "codigo_executar", "markdown_buscar", "texto_buscar",
    ] + _skills_syneriumx)

    skill_registry.registrar_perfil("product_manager", [
        "rag_consultar", "tavily_buscar", "exa_buscar", "scrapingdog_google",
        "firecrawl_scrape", "arquivo_escrever", "csv_buscar", "pdf_buscar",
    ] + _skills_comuns + _skills_syneriumx)

    logger.info(f"[SKILLS] {skill_registry.total} skills registradas com sucesso.")
    return skill_registry
