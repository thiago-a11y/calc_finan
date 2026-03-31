"""
Smart Router Global — Roteamento Inteligente Multi-Provider + Multi-Ferramenta

Decide automaticamente qual LLM ou ferramenta externa usar ANTES de qualquer
chamada feita por qualquer agente do Synerium Factory.

Providers de LLM:
  - Anthropic Opus    → raciocínio profundo, estratégia, análise complexa
  - Anthropic Sonnet  → coding, escrita, uso diário (PADRÃO)
  - OpenAI GPT        → tool use avançado, agentes, tarefas criativas
  - Google Gemini     → long context, multimodal, pesquisa em tempo real
  - Together/Groq/Fireworks (Llama) → velocidade extrema, custo mínimo

Ferramentas Externas:
  - Exa              → pesquisa semântica de alta qualidade
  - Tavily           → busca rápida para agentes
  - Firecrawl        → scraping → Markdown/JSON limpo
  - Scrapingdog      → scraping em larga escala ou sites protegidos
  - Composio         → integração de ferramentas externas (Gmail, Slack, etc.)
  - E2B              → execução segura de código em sandbox
  - LiveKit          → vídeo/áudio em tempo real
  - Amazon SES       → envio de emails

Decisão em camadas:
  1. Override manual do usuário (prefixo "Opus:", "Gemini:", etc.)
  2. Análise de intenção do prompt (pesquisa? código? email? multimodal?)
  3. Análise de complexidade (palavras-chave, tamanho, perfil do agente)
  4. Seleção de ferramentas externas necessárias
  5. Fallback inteligente se o provider primário falhar

Uso:
    from core.smart_router_global import router_global
    resultado = router_global.rotear(prompt="...", perfil_agente="tech_lead")
    # resultado.provider → "anthropic_sonnet"
    # resultado.ferramentas → ["tavily"] (se detectou necessidade de pesquisa)
    # resultado.motivo → "coding_task → sonnet"
"""

import os
import re
import logging
import time
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("synerium.router_global")


# =====================================================================
# Providers Disponíveis
# =====================================================================

class Provider(str, Enum):
    """Todos os providers de LLM disponíveis no sistema."""
    # Minimax (principal — mais barato)
    MINIMAX = "minimax"
    # Anthropic
    OPUS = "anthropic_opus"
    SONNET = "anthropic_sonnet"
    # OpenAI
    GPT4 = "openai_gpt4"
    # Google
    GEMINI = "google_gemini"
    # Open-source (velocidade)
    GROQ = "groq_llama"
    FIREWORKS = "fireworks_llama"
    TOGETHER = "together_llama"


class Ferramenta(str, Enum):
    """Ferramentas externas disponíveis."""
    EXA = "exa"                    # Pesquisa semântica
    TAVILY = "tavily"              # Busca rápida
    FIRECRAWL = "firecrawl"        # Scraping → Markdown
    SCRAPINGDOG = "scrapingdog"    # Scraping larga escala
    COMPOSIO = "composio"          # Integrações externas
    E2B = "e2b"                    # Execução de código
    LIVEKIT = "livekit"            # Vídeo/áudio real-time
    AMAZON_SES = "amazon_ses"      # Envio de emails


# =====================================================================
# Configuração dos Providers
# =====================================================================

PROVIDER_CONFIG = {
    Provider.MINIMAX: {
        "modelo": "MiniMax-Text-01",
        "nome": "MiniMax Text 01",
        "api_key_env": "MINIMAX_API_KEY",
        "custo_input": 0.0004,
        "custo_output": 0.0016,
        "max_tokens": 8192,
        "pontos_fortes": ["coding", "escrita", "uso_diario", "analise_dados",
                          "resumo", "traducao", "documentacao", "velocidade"],
        "velocidade": 5,
        "qualidade": 4,
    },
    Provider.OPUS: {
        "modelo": "claude-opus-4-20250514",
        "nome": "Claude Opus 4",
        "api_key_env": "ANTHROPIC_API_KEY",
        "custo_input": 0.015,
        "custo_output": 0.075,
        "max_tokens": 8192,
        "pontos_fortes": ["raciocinio_profundo", "estrategia", "analise_complexa",
                          "codigo_complexo", "arquitetura", "debugging_dificil"],
        "velocidade": 2,   # 1=lento, 5=ultra-rápido
        "qualidade": 5,    # 1=básico, 5=excepcional
    },
    Provider.SONNET: {
        "modelo": "claude-sonnet-4-20250514",
        "nome": "Claude Sonnet 4",
        "api_key_env": "ANTHROPIC_API_KEY",
        "custo_input": 0.003,
        "custo_output": 0.015,
        "max_tokens": 8192,
        "pontos_fortes": ["coding", "escrita", "uso_diario", "analise_dados",
                          "resumo", "traducao", "documentacao"],
        "velocidade": 4,
        "qualidade": 4,
    },
    Provider.GPT4: {
        "modelo": "gpt-4o",
        "nome": "GPT-4o (OpenAI)",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
        "custo_input": 0.005,
        "custo_output": 0.015,
        "max_tokens": 4096,
        "pontos_fortes": ["tool_use", "agentes", "criativo", "json_estruturado",
                          "funcao_calling"],
        "velocidade": 3,
        "qualidade": 4,
    },
    Provider.GEMINI: {
        "modelo": "gemini-2.5-flash",
        "nome": "Gemini 2.5 Flash (Google)",
        "api_key_env": "GOOGLE_API_KEY",
        "custo_input": 0.00015,
        "custo_output": 0.0006,
        "max_tokens": 8192,
        "pontos_fortes": ["long_context", "multimodal", "pesquisa_tempo_real",
                          "analise_imagem", "video", "grounding"],
        "velocidade": 5,
        "qualidade": 3,
    },
    Provider.GROQ: {
        "modelo": "llama-3.3-70b-versatile",
        "nome": "Llama 3.3 via Groq",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "custo_input": 0.00059,
        "custo_output": 0.00079,
        "max_tokens": 8192,
        "pontos_fortes": ["velocidade_extrema", "tarefas_simples", "pre_processamento"],
        "velocidade": 5,
        "qualidade": 3,
    },
    Provider.FIREWORKS: {
        "modelo": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "nome": "Llama 3.3 via Fireworks",
        "api_key_env": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "custo_input": 0.0009,
        "custo_output": 0.0009,
        "max_tokens": 4096,
        "pontos_fortes": ["velocidade_extrema", "custo_minimo"],
        "velocidade": 5,
        "qualidade": 2,
    },
    Provider.TOGETHER: {
        "modelo": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "nome": "Llama 3.3 via Together",
        "api_key_env": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "custo_input": 0.00088,
        "custo_output": 0.00088,
        "max_tokens": 8192,
        "pontos_fortes": ["velocidade_extrema", "custo_minimo"],
        "velocidade": 5,
        "qualidade": 2,
    },
}


# =====================================================================
# Configuração das Ferramentas
# =====================================================================

FERRAMENTA_CONFIG = {
    Ferramenta.EXA: {
        "nome": "Exa Search",
        "descricao": "Pesquisa semântica de alta qualidade",
        "api_key_env": "EXA_API_KEY",
        "gatilhos": ["pesquisar sobre", "pesquisa semântica", "buscar artigos",
                     "encontrar papers", "fontes confiáveis", "referências"],
    },
    Ferramenta.TAVILY: {
        "nome": "Tavily Search",
        "descricao": "Busca rápida para agentes",
        "api_key_env": "TAVILY_API_KEY",
        "gatilhos": ["buscar na web", "pesquisar", "googlar", "o que é",
                     "notícias sobre", "últimas novidades", "preço de",
                     "buscar online", "procurar na internet"],
    },
    Ferramenta.FIRECRAWL: {
        "nome": "Firecrawl",
        "descricao": "Scraping de sites → Markdown/JSON limpo",
        "api_key_env": "FIRECRAWL_API_KEY",
        "gatilhos": ["extrair conteúdo do site", "scraping", "scrape",
                     "raspar site", "ler página web", "converter site"],
    },
    Ferramenta.SCRAPINGDOG: {
        "nome": "Scrapingdog",
        "descricao": "Scraping em larga escala ou sites protegidos",
        "api_key_env": "SCRAPINGDOG_API_KEY",
        "gatilhos": ["scraping em massa", "scraping protegido", "crawl",
                     "extrair dados em escala", "captcha", "sites bloqueados"],
    },
    Ferramenta.COMPOSIO: {
        "nome": "Composio",
        "descricao": "Integração com ferramentas externas (Gmail, Slack, etc.)",
        "api_key_env": "COMPOSIO_API_KEY",
        "gatilhos": ["gmail", "slack", "trello", "notion", "asana",
                     "google sheets", "google calendar", "hubspot",
                     "integração com", "conectar com"],
    },
    Ferramenta.E2B: {
        "nome": "E2B Sandbox",
        "descricao": "Execução segura de código em sandbox",
        "api_key_env": "E2B_API_KEY",
        "gatilhos": ["executar código", "rodar script", "sandbox",
                     "testar código", "run code", "execute python",
                     "executar python", "rodar python"],
    },
    Ferramenta.LIVEKIT: {
        "nome": "LiveKit",
        "descricao": "Vídeo/áudio em tempo real",
        "api_key_env": "LIVEKIT_API_KEY",
        "gatilhos": ["videochamada", "video call", "áudio", "stream ao vivo",
                     "conferência", "webrtc", "live", "chamada de vídeo"],
    },
    Ferramenta.AMAZON_SES: {
        "nome": "Amazon SES",
        "descricao": "Envio de emails transacionais",
        "api_key_env": "AWS_SES_REGION",
        "gatilhos": ["enviar email", "mandar email", "disparar email",
                     "email para", "notificar por email", "convite por email"],
    },
}


# =====================================================================
# Padrões de Intenção do Prompt
# =====================================================================

PADROES_INTENCAO = {
    "pesquisa": {
        "padrao": re.compile(
            r"(pesquis|busc|procur|googl|notícia|novidade|o que é|quem é|"
            r"quando foi|onde fica|tendência|mercado atual|dados recentes|"
            r"search|find|lookup|latest)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [Ferramenta.TAVILY],
    },
    "pesquisa_profunda": {
        "padrao": re.compile(
            r"(pesquisa semântica|papers|artigos científicos|fontes confiáveis|"
            r"referências acadêmic|estudo sobre|análise de mercado profunda|"
            r"deep research|semantic search)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.OPUS,
        "ferramentas": [Ferramenta.EXA],
    },
    "scraping": {
        "padrao": re.compile(
            r"(scrap|raspar|extrair do site|ler página|converter site|"
            r"crawl|extrair conteúdo da url|pegar dados do site)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [Ferramenta.FIRECRAWL],
    },
    "codigo": {
        "padrao": re.compile(
            r"(criar função|implementar|código|programar|debugar|refatorar|"
            r"bug|erro no código|fix|unit test|integration test|api endpoint|"
            r"create function|implement|write code|develop)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [],
    },
    "codigo_complexo": {
        "padrao": re.compile(
            r"(arquitetura|design pattern|microserviç|migração|"
            r"algorithm|otimização|concorrência|race condition|"
            r"refatorar sistema|reescrever|multi-tenant|pipeline|"
            r"orquestração|workflow complexo|deadlock|memory leak)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.OPUS,
        "ferramentas": [],
    },
    "execucao_codigo": {
        "padrao": re.compile(
            r"(executar código|rodar script|sandbox|testar código|"
            r"run code|execute python|rodar python|executar python|"
            r"testar o código|verificar output)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [Ferramenta.E2B],
    },
    "email": {
        "padrao": re.compile(
            r"(enviar email|mandar email|disparar email|"
            r"email para|notificar por email|convite|send email)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [Ferramenta.AMAZON_SES],
    },
    "integracao": {
        "padrao": re.compile(
            r"(gmail|slack|trello|notion|asana|google sheets|"
            r"google calendar|hubspot|zapier|integrar com|conectar com)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.GPT4,
        "ferramentas": [Ferramenta.COMPOSIO],
    },
    "multimodal": {
        "padrao": re.compile(
            r"(analisar imagem|descrever foto|ocr|transcrever|"
            r"vídeo|imagem|visual|screenshot|print|analyze image)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.GEMINI,
        "ferramentas": [],
    },
    "long_context": {
        "padrao": re.compile(
            r"(analisar documento longo|ler todo o arquivo|"
            r"resumir livro|analisar relatório completo|"
            r"full document|entire codebase|all files)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.GEMINI,
        "ferramentas": [],
    },
    "videochamada": {
        "padrao": re.compile(
            r"(videochamada|video call|conferência|webrtc|"
            r"live|chamada de vídeo|stream|áudio em tempo real)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.SONNET,
        "ferramentas": [Ferramenta.LIVEKIT],
    },
    "criativo": {
        "padrao": re.compile(
            r"(criar história|escrever poema|narrativa|"
            r"brainstorm|ideia criativa|slogan|marketing|"
            r"copywriting|headline|story|creative)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.GPT4,
        "ferramentas": [],
    },
    "estrategia": {
        "padrao": re.compile(
            r"(estratégia|roadmap|plano de ação|business case|"
            r"roi|viabilidade|priorização|trade-off|análise swot|"
            r"planejamento estratégico|strategy|prioritization)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.OPUS,
        "ferramentas": [],
    },
    "velocidade": {
        "padrao": re.compile(
            r"(rápido|fast|quick|simples|resumir|traduzir|"
            r"classificar|categorizar|extrair dados|formatar|"
            r"converter formato|listar)",
            re.IGNORECASE
        ),
        "provider_ideal": Provider.GROQ,
        "ferramentas": [],
    },
}


# =====================================================================
# Prefixos de Override do Usuário
# =====================================================================

PREFIXOS_OVERRIDE = {
    "opus:": Provider.OPUS,
    "sonnet:": Provider.SONNET,
    "gpt:": Provider.GPT4,
    "openai:": Provider.GPT4,
    "gemini:": Provider.GEMINI,
    "google:": Provider.GEMINI,
    "groq:": Provider.GROQ,
    "llama:": Provider.GROQ,
    "fireworks:": Provider.FIREWORKS,
    "together:": Provider.TOGETHER,
    "rápido:": Provider.GROQ,
    "rapido:": Provider.GROQ,
    "fast:": Provider.GROQ,
}


# =====================================================================
# Perfis de Agentes
# =====================================================================

PERFIS_AGENTE = {
    # Alto nível → tendência Opus
    "ceo": {"peso": 0.8, "provider_padrao": Provider.OPUS},
    "operations_lead": {"peso": 0.7, "provider_padrao": Provider.OPUS},
    "diretor": {"peso": 0.7, "provider_padrao": Provider.OPUS},
    "tech_lead": {"peso": 0.6, "provider_padrao": Provider.SONNET},
    "arquiteto": {"peso": 0.7, "provider_padrao": Provider.OPUS},
    "product_manager": {"peso": 0.5, "provider_padrao": Provider.SONNET},
    "especialista_ia": {"peso": 0.5, "provider_padrao": Provider.SONNET},
    # Operacional → tendência Sonnet/rápido
    "qa_seguranca": {"peso": 0.4, "provider_padrao": Provider.SONNET},
    "backend_dev": {"peso": 0.3, "provider_padrao": Provider.SONNET},
    "frontend_dev": {"peso": 0.3, "provider_padrao": Provider.SONNET},
    "devops": {"peso": 0.3, "provider_padrao": Provider.SONNET},
    "integracao": {"peso": 0.2, "provider_padrao": Provider.SONNET},
    "secretaria_executiva": {"peso": 0.1, "provider_padrao": Provider.GROQ},
    "consultora_estrategica": {"peso": 0.4, "provider_padrao": Provider.SONNET},  # Luna
}

# Cadeia de fallback por provider
CADEIA_FALLBACK = {
    Provider.OPUS: [Provider.SONNET, Provider.GROQ, Provider.FIREWORKS, Provider.TOGETHER],
    Provider.SONNET: [Provider.GROQ, Provider.FIREWORKS, Provider.TOGETHER],
    Provider.GPT4: [Provider.SONNET, Provider.GROQ, Provider.FIREWORKS],
    Provider.GEMINI: [Provider.SONNET, Provider.GROQ, Provider.FIREWORKS],
    Provider.GROQ: [Provider.FIREWORKS, Provider.TOGETHER, Provider.SONNET],
    Provider.FIREWORKS: [Provider.TOGETHER, Provider.GROQ, Provider.SONNET],
    Provider.TOGETHER: [Provider.GROQ, Provider.FIREWORKS, Provider.SONNET],
}


# =====================================================================
# Resultado do Roteamento
# =====================================================================

@dataclass
class ResultadoRoteamento:
    """Resultado completo de uma decisão de roteamento."""
    provider: Provider
    modelo: str
    nome_provider: str
    motivo: str
    ferramentas: list[Ferramenta] = field(default_factory=list)
    fallbacks: list[Provider] = field(default_factory=list)
    intencao_detectada: str = "geral"
    confianca: float = 0.9  # 0.0 a 1.0
    tempo_decisao_ms: float = 0.0
    prompt_limpo: str = ""  # Prompt sem prefixo de override
    override_manual: bool = False

    def to_dict(self) -> dict:
        """Serializa para JSON/log."""
        return {
            "provider": self.provider.value,
            "modelo": self.modelo,
            "nome": self.nome_provider,
            "motivo": self.motivo,
            "ferramentas": [f.value for f in self.ferramentas],
            "fallbacks": [f.value for f in self.fallbacks],
            "intencao": self.intencao_detectada,
            "confianca": self.confianca,
            "tempo_ms": round(self.tempo_decisao_ms, 2),
            "override": self.override_manual,
        }


# =====================================================================
# Estatísticas
# =====================================================================

@dataclass
class EstatisticasGlobal:
    """Estatísticas do router global."""
    total_chamadas: int = 0
    por_provider: dict = field(default_factory=lambda: {p.value: 0 for p in Provider})
    por_intencao: dict = field(default_factory=dict)
    por_ferramenta: dict = field(default_factory=lambda: {f.value: 0 for f in Ferramenta})
    overrides_manuais: int = 0
    tempo_medio_ms: float = 0.0
    historico: list = field(default_factory=list)


# =====================================================================
# Smart Router Global
# =====================================================================

class SmartRouterGlobal:
    """
    Router inteligente global que decide qual LLM E quais ferramentas
    usar antes de qualquer chamada no Synerium Factory.

    Camadas de decisão (em ordem de prioridade):
    1. Override manual do usuário (prefixo "Opus:", "Gemini:", etc.)
    2. Análise de intenção do prompt (pesquisa? código? email? multimodal?)
    3. Análise de complexidade (palavras-chave, tamanho, perfil do agente)
    4. Detecção de ferramentas externas necessárias
    5. Verificação de disponibilidade (API key configurada?)
    6. Fallback inteligente se provider primário indisponível
    """

    def __init__(self):
        self.stats = EstatisticasGlobal()
        self._ativo = True
        self._providers_disponiveis: dict[Provider, bool] = {}
        self._ferramentas_disponiveis: dict[Ferramenta, bool] = {}
        self._verificar_disponibilidade()
        logger.info("[RouterGlobal] Inicializado com %d providers e %d ferramentas",
                    sum(1 for v in self._providers_disponiveis.values() if v),
                    sum(1 for v in self._ferramentas_disponiveis.values() if v))

    # -----------------------------------------------------------------
    # Verificação de Disponibilidade
    # -----------------------------------------------------------------

    def _verificar_disponibilidade(self):
        """Verifica quais providers e ferramentas têm API key configurada."""
        for provider, config in PROVIDER_CONFIG.items():
            chave = os.environ.get(config["api_key_env"], "").strip()
            self._providers_disponiveis[provider] = bool(chave)

        for ferramenta, config in FERRAMENTA_CONFIG.items():
            chave = os.environ.get(config["api_key_env"], "").strip()
            self._ferramentas_disponiveis[ferramenta] = bool(chave)

    def provider_disponivel(self, provider: Provider) -> bool:
        """Verifica se um provider está disponível."""
        return self._providers_disponiveis.get(provider, False)

    def ferramenta_disponivel(self, ferramenta: Ferramenta) -> bool:
        """Verifica se uma ferramenta está disponível."""
        return self._ferramentas_disponiveis.get(ferramenta, False)

    # -----------------------------------------------------------------
    # Decisão Principal
    # -----------------------------------------------------------------

    def rotear(
        self,
        prompt: str = "",
        perfil_agente: str | None = None,
        forcar: str | None = None,
        agente_nome: str = "",
        squad_nome: str = "",
        contexto: dict[str, Any] | None = None,
    ) -> ResultadoRoteamento:
        """
        Decide qual provider de LLM e quais ferramentas usar.

        Args:
            prompt: Texto do prompt a ser processado.
            perfil_agente: Perfil do agente (ex: "tech_lead", "backend_dev").
            forcar: Nome do provider para override manual (ex: "opus", "gemini").
            agente_nome: Nome do agente (para tracking).
            squad_nome: Nome do squad (para tracking).
            contexto: Dados extras (ex: {"tem_imagem": True, "tamanho_arquivo": 50000}).

        Returns:
            ResultadoRoteamento com provider, ferramentas e metadados.
        """
        inicio = time.time()
        contexto = contexto or {}
        prompt_original = prompt

        # Router desativado → Sonnet sem análise
        if not self._ativo:
            return self._criar_resultado(
                Provider.SONNET, "router_desativado", prompt, inicio
            )

        # ─── 1. Override manual via parâmetro ───
        if forcar:
            provider = self._resolver_override(forcar)
            if provider:
                return self._criar_resultado(
                    provider, f"override_manual ({forcar})",
                    prompt, inicio, override=True
                )

        # ─── 2. Override manual via prefixo no prompt ───
        provider_prefixo, prompt_limpo = self._detectar_prefixo(prompt)
        if provider_prefixo:
            resultado = self._criar_resultado(
                provider_prefixo,
                f"prefixo_usuario ({prompt[:prompt.find(':')].strip()}:)",
                prompt_limpo, inicio, override=True
            )
            resultado.prompt_limpo = prompt_limpo
            return resultado
        prompt = prompt_limpo or prompt

        # ─── 3. Contexto multimodal (imagem/vídeo) ───
        if contexto.get("tem_imagem") or contexto.get("tem_video"):
            provider = Provider.GEMINI if self.provider_disponivel(Provider.GEMINI) else Provider.SONNET
            return self._criar_resultado(
                provider, "multimodal_detectado",
                prompt, inicio, intencao="multimodal"
            )

        # ─── 4. Análise de intenção do prompt ───
        intencao, provider_ideal, ferramentas = self._analisar_intencao(prompt)

        # ─── 5. Análise de complexidade (refina a escolha) ───
        provider_final = self._refinar_por_complexidade(
            prompt, provider_ideal, perfil_agente
        )

        # ─── 6. Verificar disponibilidade e aplicar fallback ───
        provider_final = self._garantir_disponibilidade(provider_final)

        # ─── 7. Filtrar ferramentas disponíveis ───
        ferramentas_disponiveis = [
            f for f in ferramentas
            if self.ferramenta_disponivel(f)
        ]

        # ─── 8. Resultado final ───
        resultado = self._criar_resultado(
            provider_final,
            f"intencao={intencao} → {provider_final.value}",
            prompt, inicio, intencao=intencao
        )
        resultado.ferramentas = ferramentas_disponiveis
        resultado.prompt_limpo = prompt

        # ─── 9. Registrar estatísticas ───
        self._registrar_stats(resultado, perfil_agente, agente_nome)

        return resultado

    # -----------------------------------------------------------------
    # Análise de Intenção
    # -----------------------------------------------------------------

    def _analisar_intencao(self, prompt: str) -> tuple[str, Provider, list[Ferramenta]]:
        """
        Analisa o prompt e retorna (intenção, provider_ideal, ferramentas).
        Retorna a PRIMEIRA intenção que bate, em ordem de especificidade.
        """
        # Ordem de prioridade (mais específico primeiro)
        ordem = [
            "codigo_complexo", "pesquisa_profunda", "execucao_codigo",
            "videochamada", "integracao", "scraping", "multimodal",
            "long_context", "estrategia", "email", "pesquisa",
            "criativo", "codigo", "velocidade",
        ]

        for nome_intencao in ordem:
            config = PADROES_INTENCAO.get(nome_intencao)
            if config and config["padrao"].search(prompt):
                return (
                    nome_intencao,
                    config["provider_ideal"],
                    config.get("ferramentas", []),
                )

        # Nenhuma intenção detectada → padrão Sonnet
        return "geral", Provider.SONNET, []

    # -----------------------------------------------------------------
    # Refinamento por Complexidade
    # -----------------------------------------------------------------

    def _refinar_por_complexidade(
        self,
        prompt: str,
        provider_base: Provider,
        perfil_agente: str | None,
    ) -> Provider:
        """
        Refina a escolha do provider baseado na complexidade do prompt
        e no perfil do agente. Pode fazer upgrade (Sonnet → Opus) ou
        downgrade (Opus → Sonnet) dependendo da análise.
        """
        # Tokens estimados
        tokens = len(prompt) // 4

        # Prompt muito longo → precisa de modelo mais capaz
        if tokens >= 15_000:
            if provider_base in (Provider.GROQ, Provider.FIREWORKS, Provider.TOGETHER):
                return Provider.SONNET  # Upgrade de Llama → Sonnet
            return Provider.OPUS  # Upgrade para Opus

        # Perfil do agente pode forçar upgrade
        if perfil_agente:
            perfil_config = PERFIS_AGENTE.get(perfil_agente.lower().strip())
            if perfil_config:
                peso = perfil_config["peso"]
                # Agentes de alto nível com provider base Sonnet → pode ir para Opus
                if peso >= 0.6 and provider_base == Provider.SONNET:
                    # Verificar se tem pelo menos 1 indicador de complexidade
                    from core.llm_router import PALAVRAS_ALTA_COMPLEXIDADE
                    prompt_lower = prompt.lower()
                    tem_complexidade = any(
                        p in prompt_lower for p in PALAVRAS_ALTA_COMPLEXIDADE
                    )
                    if tem_complexidade:
                        return Provider.OPUS

        return provider_base

    # -----------------------------------------------------------------
    # Override e Prefixo
    # -----------------------------------------------------------------

    def _resolver_override(self, forcar: str) -> Provider | None:
        """Resolve um override manual para um Provider."""
        forcar_lower = forcar.lower().strip()
        # Busca direta
        for prefixo, provider in PREFIXOS_OVERRIDE.items():
            nome = prefixo.rstrip(":")
            if forcar_lower == nome:
                return provider
        # Busca parcial
        for provider in Provider:
            if forcar_lower in provider.value:
                return provider
        return None

    def _detectar_prefixo(self, prompt: str) -> tuple[Provider | None, str]:
        """Detecta prefixo de override no início do prompt."""
        prompt_stripped = prompt.strip()
        prompt_lower = prompt_stripped.lower()
        for prefixo, provider in PREFIXOS_OVERRIDE.items():
            if prompt_lower.startswith(prefixo):
                prompt_limpo = prompt_stripped[len(prefixo):].strip()
                return provider, prompt_limpo
        return None, prompt

    # -----------------------------------------------------------------
    # Disponibilidade e Fallback
    # -----------------------------------------------------------------

    def _garantir_disponibilidade(self, provider: Provider) -> Provider:
        """
        Verifica se o provider está disponível. Se não, percorre a
        cadeia de fallback até encontrar um disponível.
        """
        if self.provider_disponivel(provider):
            return provider

        logger.warning("[RouterGlobal] Provider %s indisponível, buscando fallback",
                       provider.value)

        cadeia = CADEIA_FALLBACK.get(provider, [])
        for fallback in cadeia:
            if self.provider_disponivel(fallback):
                logger.info("[RouterGlobal] Fallback: %s → %s",
                            provider.value, fallback.value)
                return fallback

        # Último recurso: qualquer provider disponível
        for p in Provider:
            if self.provider_disponivel(p):
                logger.warning("[RouterGlobal] Fallback emergencial: %s", p.value)
                return p

        # Nada disponível — retorna Sonnet e deixa falhar na chamada
        logger.error("[RouterGlobal] NENHUM provider disponível!")
        return Provider.SONNET

    # -----------------------------------------------------------------
    # Construção do Resultado
    # -----------------------------------------------------------------

    def _criar_resultado(
        self,
        provider: Provider,
        motivo: str,
        prompt: str,
        inicio: float,
        intencao: str = "geral",
        override: bool = False,
    ) -> ResultadoRoteamento:
        """Cria o objeto ResultadoRoteamento com todos os metadados."""
        config = PROVIDER_CONFIG[provider]
        tempo_ms = (time.time() - inicio) * 1000

        return ResultadoRoteamento(
            provider=provider,
            modelo=config["modelo"],
            nome_provider=config["nome"],
            motivo=motivo,
            fallbacks=CADEIA_FALLBACK.get(provider, []),
            intencao_detectada=intencao,
            confianca=0.95 if override else 0.8,
            tempo_decisao_ms=tempo_ms,
            prompt_limpo=prompt,
            override_manual=override,
        )

    # -----------------------------------------------------------------
    # Estatísticas
    # -----------------------------------------------------------------

    def _registrar_stats(
        self,
        resultado: ResultadoRoteamento,
        perfil_agente: str | None,
        agente_nome: str,
    ):
        """Registra estatísticas da decisão."""
        self.stats.total_chamadas += 1
        self.stats.por_provider[resultado.provider.value] = (
            self.stats.por_provider.get(resultado.provider.value, 0) + 1
        )
        self.stats.por_intencao[resultado.intencao_detectada] = (
            self.stats.por_intencao.get(resultado.intencao_detectada, 0) + 1
        )
        for f in resultado.ferramentas:
            self.stats.por_ferramenta[f.value] = (
                self.stats.por_ferramenta.get(f.value, 0) + 1
            )
        if resultado.override_manual:
            self.stats.overrides_manuais += 1

        # Tempo médio
        n = self.stats.total_chamadas
        self.stats.tempo_medio_ms = (
            (self.stats.tempo_medio_ms * (n - 1) + resultado.tempo_decisao_ms) / n
        )

        # Histórico (últimos 100)
        self.stats.historico.append({
            "timestamp": datetime.now().isoformat(),
            "agente": agente_nome or perfil_agente or "desconhecido",
            **resultado.to_dict(),
        })
        if len(self.stats.historico) > 100:
            self.stats.historico = self.stats.historico[-100:]

        # Log
        ferramentas_str = (
            f" + ferramentas: {[f.value for f in resultado.ferramentas]}"
            if resultado.ferramentas else ""
        )
        logger.info(
            "[RouterGlobal] %s | %s | %s | %.1fms%s",
            resultado.nome_provider,
            resultado.motivo,
            perfil_agente or "N/A",
            resultado.tempo_decisao_ms,
            ferramentas_str,
        )

    # -----------------------------------------------------------------
    # API Pública
    # -----------------------------------------------------------------

    def obter_status(self) -> dict:
        """Retorna status completo para API/dashboard."""
        total = self.stats.total_chamadas or 1
        return {
            "ativo": self._ativo,
            "total_chamadas": self.stats.total_chamadas,
            "por_provider": self.stats.por_provider,
            "por_intencao": self.stats.por_intencao,
            "por_ferramenta": self.stats.por_ferramenta,
            "overrides_manuais": self.stats.overrides_manuais,
            "tempo_medio_decisao_ms": round(self.stats.tempo_medio_ms, 2),
            "providers_disponiveis": {
                p.value: disponivel
                for p, disponivel in self._providers_disponiveis.items()
            },
            "ferramentas_disponiveis": {
                f.value: disponivel
                for f, disponivel in self._ferramentas_disponiveis.items()
            },
            "historico_recente": self.stats.historico[-15:],
        }

    def obter_llm_para_agente(
        self,
        perfil_agente: str,
        agente_nome: str = "",
        squad_nome: str = "",
    ):
        """
        Compatibilidade com SmartRouter antigo.
        Retorna LLMTracked pré-configurado para um agente.
        """
        from core.llm_router import smart_router
        return smart_router.obter_llm_para_agente(
            perfil_agente, agente_nome, squad_nome
        )

    def criar_llm(self, resultado: ResultadoRoteamento, **kwargs):
        """
        Cria uma instância LLM baseada no resultado do roteamento.
        Usa LLMTracked para tracking automático.
        """
        from core.llm_tracked import criar_llm_tracked

        config = PROVIDER_CONFIG[resultado.provider]
        api_key = os.environ.get(config["api_key_env"], "")

        params = {
            "modelo": config["modelo"],
            "api_key": api_key,
            "max_tokens": config.get("max_tokens", 8192),
            **kwargs,
        }

        # Providers OpenAI-compatible
        if config.get("base_url"):
            params["base_url"] = config["base_url"]

        # Provider Anthropic
        if resultado.provider in (Provider.OPUS, Provider.SONNET):
            params["modelo"] = f"anthropic/{config['modelo']}"
        # Provider Google
        elif resultado.provider == Provider.GEMINI:
            params["modelo"] = f"google/{config['modelo']}"

        return criar_llm_tracked(**params)

    def ativar(self):
        """Ativa o router global."""
        self._ativo = True
        logger.info("[RouterGlobal] ATIVADO")

    def desativar(self):
        """Desativa — sempre usa Sonnet."""
        self._ativo = False
        logger.info("[RouterGlobal] DESATIVADO — sempre Sonnet")

    def recarregar_disponibilidade(self):
        """Recarrega verificação de API keys (útil após mudar .env)."""
        self._verificar_disponibilidade()
        logger.info("[RouterGlobal] Disponibilidade recarregada")


# =====================================================================
# Instância Global
# =====================================================================
router_global = SmartRouterGlobal()
