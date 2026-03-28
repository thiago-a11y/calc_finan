# Skills — Ferramentas dos Agentes

> **Status:** ✅ Implementado (v0.8.0)
> **Catálogo:** `/skills` no dashboard
> **Registro:** `tools/registry.py`

## Visão Geral

Cada agente do Synerium Factory possui skills (ferramentas) que lhe dão capacidades reais — não apenas raciocínio via LLM, mas ações concretas como ler código, pesquisar na web, executar scripts, etc.

## Skills Disponíveis (20 no total)

### Busca e Pesquisa (4)
| Skill | Fonte | Custo | Para quê serve |
|-------|-------|-------|----------------|
| TavilySearchTool | Tavily API | Paga | Busca web premium — resultados estruturados e relevantes |
| EXASearchTool | EXA API | Free tier | Busca semântica — encontra conteúdo por significado, não só palavras |
| ScrapingDogSERP | ScrapingDog | 1000 créditos free | Google SERP — resultados reais do Google (organic + snippet) |
| WebsiteSearchTool | CrewAI built-in | Grátis | Busca dentro de um site específico |

### Leitura e Análise (5)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| FileReadTool | CrewAI built-in | Lê qualquer arquivo (PHP, TSX, JSON, YAML, etc.) |
| DirectoryReadTool | CrewAI built-in | Lista conteúdo de diretórios |
| JSONSearchTool | CrewAI built-in | Busca dentro de arquivos JSON |
| CSVSearchTool | CrewAI built-in | Busca e análise de arquivos CSV |
| PDFSearchTool | CrewAI built-in | Extração de texto e busca em PDFs |

### Scraping e Extração (2)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| ScrapeWebsiteTool | CrewAI built-in | Scraping básico de páginas web |
| FirecrawlScrapeWebsiteTool | Firecrawl API | Scraping avançado — bypassa JS dinâmico |

### Código e Execução (2)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| CodeInterpreterTool | CrewAI built-in | Executa código Python em sandbox local |
| FileWriterTool | CrewAI built-in | Escreve/cria arquivos (documentação, configs) |

### GitHub (1)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| GithubSearchTool | CrewAI built-in | Busca em repositórios GitHub (PRs, issues, código) |

### Conhecimento (1)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| ConsultarBaseConhecimento | Custom (RAG) | Consulta os vaults Obsidian do SyneriumX e Factory |

### Documentação (1)
| Skill | Fonte | Para quê serve |
|-------|-------|----------------|
| EscreverObsidian | Custom | Escreve notas no vault SyneriumFactory-notes |

## Distribuição por Agente

| # | Agente | Skills atribuídas |
|---|--------|-------------------|
| 1 | Tech Lead | FileRead, DirectoryRead, Tavily, EXA, ScrapeWebsite, Firecrawl, RAG |
| 2 | Backend | FileRead, DirectoryRead, CodeInterpreter, JSON, CSV, RAG |
| 3 | Frontend | FileRead, DirectoryRead, WebsiteSearch, ScrapeWebsite, RAG |
| 4 | IA | Tavily, EXA, CodeInterpreter, CSV, ScrapeWebsite, Firecrawl, RAG |
| 5 | Integrações | Tavily, ScrapeWebsite, Firecrawl, JSON, CodeInterpreter, RAG |
| 6 | DevOps | FileRead, DirectoryRead, CodeInterpreter, Tavily, GitHub, RAG |
| 7 | QA | FileRead, DirectoryRead, CodeInterpreter, Tavily, ScrapingDogSERP, RAG |
| 8 | PM | Tavily, EXA, FileWriter, EscreverObsidian, CSV, PDF, RAG |

## APIs Configuradas

| Serviço | Variável .env | Status |
|---------|--------------|--------|
| Tavily | TAVILY_API_KEY | ✅ Paga |
| EXA | EXA_API_KEY | ✅ Free tier |
| Firecrawl | FIRECRAWL_API_KEY | ✅ Free tier |
| ScrapingDog | SCRAPINGDOG_API_KEY | ✅ 1000 créditos free |
| GitHub | GITHUB_TOKEN | ✅ Full access |
| Composio | COMPOSIO_API_KEY | ✅ Configurada (uso futuro) |
| E2B | E2B_API_KEY | ✅ Configurada (sandbox cloud futura) |

## Marketplace (Futuro)

O sistema de Skills foi projetado para evoluir para um marketplace onde:
1. Novas skills podem ser instaladas pelo dashboard
2. Cada funcionário pode customizar as skills do seu squad
3. Skills podem ser compartilhadas entre squads
4. Métricas de uso e custo por skill

---

*Criado em: 24/03/2026*
