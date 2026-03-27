"""
Smart Router Híbrido — Claude Sonnet + Opus

Decide automaticamente qual modelo usar baseado em:
1. Complexidade do prompt (palavras-chave de alta complexidade)
2. Tamanho do prompt (> 15.000 tokens estimados → Opus)
3. Nível do agente (Tech Lead, Arquiteto, PM, CEO → peso maior para Opus)
4. Override manual (forçar Sonnet ou Opus via parâmetro)

Cadeia de fallback mantida:
  Opus → Sonnet → Groq → Fireworks → Together

Uso:
    from core.llm_router import smart_router
    llm = smart_router.rotear(prompt="...", perfil_agente="tech_lead")
    llm = smart_router.rotear(forcar="opus")   # Override manual
    llm = smart_router.rotear(forcar="sonnet") # Override manual
"""

import os
import re
import logging
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger("synerium.router")


# =====================================================================
# Configuração dos Modelos Claude
# =====================================================================

class ModeloClaudeTier(str, Enum):
    """Tiers de modelo Claude disponíveis."""
    OPUS = "opus"
    SONNET = "sonnet"


# Modelos atuais (março 2026)
MODELOS_CLAUDE = {
    ModeloClaudeTier.OPUS: {
        "modelo": "claude-opus-4-20250514",
        "nome": "Claude Opus 4",
        "custo_por_1k_input": 0.015,
        "custo_por_1k_output": 0.075,
        "max_tokens": 8192,
    },
    ModeloClaudeTier.SONNET: {
        "modelo": "claude-sonnet-4-20250514",
        "nome": "Claude Sonnet 4",
        "custo_por_1k_input": 0.003,
        "custo_por_1k_output": 0.015,
        "max_tokens": 8192,
    },
}


# =====================================================================
# Palavras-chave de Alta Complexidade
# =====================================================================

# Se o prompt contiver N ou mais dessas palavras, usar Opus
PALAVRAS_ALTA_COMPLEXIDADE = {
    # Arquitetura e design
    "arquitetura", "architecture", "refatorar", "refactor", "redesign",
    "migração", "migration", "escalabilidade", "scalability",
    "microserviços", "microservices", "design pattern",

    # Segurança
    "vulnerabilidade", "vulnerability", "auditoria", "audit",
    "penetration", "pentest", "criptografia", "encryption",
    "lgpd", "gdpr", "compliance",

    # Análise profunda
    "análise completa", "análise detalhada", "deep analysis",
    "root cause", "causa raiz", "investigar", "investigate",
    "diagnóstico", "diagnostic",

    # Estratégia e planejamento
    "roadmap", "estratégia", "strategy", "plano de ação",
    "priorização", "prioritization", "trade-off", "tradeoff",
    "business case", "roi", "viabilidade",

    # Código complexo
    "algoritmo", "algorithm", "otimização", "optimization",
    "concorrência", "concurrency", "race condition",
    "deadlock", "memory leak", "performance",
    "recursão", "recursive", "árvore", "grafo", "graph",

    # Multi-sistema
    "integração complexa", "orquestração", "orchestration",
    "pipeline", "workflow", "multi-tenant", "multi-produto",
}

# Limiar: se >= N palavras de alta complexidade aparecem, usar Opus
LIMIAR_PALAVRAS_COMPLEXIDADE = 2

# Limiar de tokens estimados (1 token ~= 4 chars em português)
LIMIAR_TOKENS_OPUS = 15_000
CHARS_POR_TOKEN = 4


# =====================================================================
# Perfis de Agentes e seus Pesos
# =====================================================================

# Agentes de alto nível têm peso maior para usar Opus
PERFIS_ALTO_NIVEL = {
    # Perfil do agente → peso extra (0.0 a 1.0)
    # Se peso >= 0.5, basta 1 palavra-chave para usar Opus
    "tech_lead": 0.6,
    "arquiteto": 0.7,
    "product_manager": 0.5,
    "ceo": 0.8,
    "diretor": 0.7,
    "operations_lead": 0.7,
    "especialista_ia": 0.5,
    "qa_seguranca": 0.4,
    # Agentes operacionais — peso baixo
    "backend_dev": 0.2,
    "frontend_dev": 0.2,
    "devops": 0.3,
    "integracao": 0.2,
    "secretaria_executiva": 0.0,
}


# =====================================================================
# Estatísticas de Roteamento
# =====================================================================

@dataclass
class EstatisticasRouter:
    """Contadores de uso do router."""
    total_chamadas: int = 0
    chamadas_opus: int = 0
    chamadas_sonnet: int = 0
    motivos: dict = field(default_factory=lambda: {
        "palavras_chave": 0,
        "tamanho_prompt": 0,
        "perfil_agente": 0,
        "override_manual": 0,
        "padrao_sonnet": 0,
    })
    ultimo_roteamento: str | None = None
    historico: list = field(default_factory=list)  # Últimos 50 roteamentos


# =====================================================================
# Smart Router
# =====================================================================

class SmartRouter:
    """
    Router inteligente que decide entre Claude Sonnet e Opus.

    Regras de decisão (em ordem de prioridade):
    1. Override manual → usa o modelo forçado
    2. Prompt > 15.000 tokens → Opus
    3. >= 2 palavras de alta complexidade → Opus
    4. Agente alto nível + >= 1 palavra complexa → Opus
    5. Caso contrário → Sonnet (padrão, rápido e barato)
    """

    def __init__(self):
        self.stats = EstatisticasRouter()
        self._ativo = True  # Se False, sempre usa Sonnet
        logger.info("[Router] Smart Router Sonnet/Opus inicializado")

    def _estimar_tokens(self, texto: str) -> int:
        """Estima tokens de um texto (1 token ~= 4 chars em português)."""
        return len(texto) // CHARS_POR_TOKEN

    def _contar_palavras_complexidade(self, texto: str) -> tuple[int, list[str]]:
        """Conta palavras de alta complexidade no texto."""
        texto_lower = texto.lower()
        encontradas = []
        for palavra in PALAVRAS_ALTA_COMPLEXIDADE:
            if palavra in texto_lower:
                encontradas.append(palavra)
        return len(encontradas), encontradas

    def _peso_perfil(self, perfil_agente: str | None) -> float:
        """Retorna o peso do perfil do agente (0.0 a 1.0)."""
        if not perfil_agente:
            return 0.0
        # Busca exata ou parcial
        perfil_lower = perfil_agente.lower().strip()
        if perfil_lower in PERFIS_ALTO_NIVEL:
            return PERFIS_ALTO_NIVEL[perfil_lower]
        # Busca parcial (ex: "Tech Lead / Arquiteto" contém "tech_lead")
        for chave, peso in PERFIS_ALTO_NIVEL.items():
            chave_limpa = chave.replace("_", " ")
            if chave_limpa in perfil_lower or perfil_lower in chave_limpa:
                return peso
        return 0.1  # Peso default para perfis desconhecidos

    def decidir(
        self,
        prompt: str = "",
        perfil_agente: str | None = None,
        forcar: str | None = None,
    ) -> tuple[ModeloClaudeTier, str]:
        """
        Decide qual modelo usar.

        Args:
            prompt: Texto do prompt a ser enviado.
            perfil_agente: Perfil do agente (ex: "tech_lead", "backend_dev").
            forcar: "opus" ou "sonnet" para override manual.

        Returns:
            Tupla (tier, motivo) com o modelo escolhido e a razão.
        """
        # Router desativado → sempre Sonnet
        if not self._ativo:
            return ModeloClaudeTier.SONNET, "router_desativado"

        # 1. Override manual
        if forcar:
            forcar_lower = forcar.lower().strip()
            if forcar_lower == "opus":
                return ModeloClaudeTier.OPUS, "override_manual"
            elif forcar_lower == "sonnet":
                return ModeloClaudeTier.SONNET, "override_manual"

        # 2. Tamanho do prompt
        tokens_estimados = self._estimar_tokens(prompt)
        if tokens_estimados >= LIMIAR_TOKENS_OPUS:
            return ModeloClaudeTier.OPUS, f"tamanho_prompt ({tokens_estimados} tokens)"

        # 3. Palavras de alta complexidade
        qtd_complexas, palavras = self._contar_palavras_complexidade(prompt)

        # 3a. Muitas palavras complexas → Opus direto
        if qtd_complexas >= LIMIAR_PALAVRAS_COMPLEXIDADE:
            return ModeloClaudeTier.OPUS, f"palavras_chave ({qtd_complexas}: {', '.join(palavras[:5])})"

        # 4. Perfil de agente + complexidade
        peso = self._peso_perfil(perfil_agente)
        if peso >= 0.5 and qtd_complexas >= 1:
            return ModeloClaudeTier.OPUS, f"perfil_agente ({perfil_agente}, peso={peso}) + {palavras[0]}"

        # 5. Padrão → Sonnet
        return ModeloClaudeTier.SONNET, "padrao_sonnet"

    def rotear(
        self,
        prompt: str = "",
        perfil_agente: str | None = None,
        forcar: str | None = None,
    ):
        """
        Decide o modelo e retorna uma instância LLM do CrewAI.

        Args:
            prompt: Texto do prompt.
            perfil_agente: Perfil do agente.
            forcar: "opus" ou "sonnet" para override.

        Returns:
            Instância crewai.LLM configurada com o modelo correto.
        """
        from crewai import LLM

        tier, motivo = self.decidir(prompt, perfil_agente, forcar)
        config = MODELOS_CLAUDE[tier]
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        # Registrar estatísticas
        self.stats.total_chamadas += 1
        if tier == ModeloClaudeTier.OPUS:
            self.stats.chamadas_opus += 1
        else:
            self.stats.chamadas_sonnet += 1

        # Categorizar motivo nas estatísticas
        motivo_base = motivo.split(" ")[0]  # "palavras_chave (2: ...)" → "palavras_chave"
        if motivo_base in self.stats.motivos:
            self.stats.motivos[motivo_base] += 1

        self.stats.ultimo_roteamento = datetime.now().isoformat()

        # Histórico (últimos 50)
        entrada = {
            "timestamp": self.stats.ultimo_roteamento,
            "tier": tier.value,
            "motivo": motivo,
            "perfil": perfil_agente or "desconhecido",
            "tokens_prompt": self._estimar_tokens(prompt),
        }
        self.stats.historico.append(entrada)
        if len(self.stats.historico) > 50:
            self.stats.historico = self.stats.historico[-50:]

        logger.info(
            f"[Router] {config['nome']} | Motivo: {motivo} | "
            f"Perfil: {perfil_agente or 'N/A'} | "
            f"Custo: ${config['custo_por_1k_input']}/1k in"
        )

        # Criar instância LLM
        llm = LLM(
            model=f"anthropic/{config['modelo']}",
            api_key=api_key,
            max_tokens=config["max_tokens"],
        )

        return llm

    def obter_llm_para_agente(self, perfil_agente: str):
        """
        Retorna um LLM pré-configurado para um agente específico.

        Usado na criação do agente (sem prompt ainda).
        Agentes de alto nível recebem Opus; demais recebem Sonnet.
        A decisão final é refinada quando o prompt chega via rotear().
        """
        peso = self._peso_perfil(perfil_agente)
        if peso >= 0.6:
            # Agentes seniores começam com Opus
            return self.rotear(forcar="opus")
        else:
            # Demais começam com Sonnet
            return self.rotear(forcar="sonnet")

    def obter_status(self) -> dict:
        """Retorna status completo do router para a API/dashboard."""
        total = self.stats.total_chamadas or 1  # Evitar divisão por zero
        return {
            "ativo": self._ativo,
            "total_chamadas": self.stats.total_chamadas,
            "chamadas_opus": self.stats.chamadas_opus,
            "chamadas_sonnet": self.stats.chamadas_sonnet,
            "percentual_opus": round(self.stats.chamadas_opus / total * 100, 1),
            "percentual_sonnet": round(self.stats.chamadas_sonnet / total * 100, 1),
            "motivos": self.stats.motivos,
            "ultimo_roteamento": self.stats.ultimo_roteamento,
            "economia_estimada": self._calcular_economia(),
            "modelos": {
                tier.value: {
                    "nome": config["nome"],
                    "modelo": config["modelo"],
                    "custo_input": config["custo_por_1k_input"],
                    "custo_output": config["custo_por_1k_output"],
                }
                for tier, config in MODELOS_CLAUDE.items()
            },
            "historico_recente": self.stats.historico[-10:],
        }

    def _calcular_economia(self) -> dict:
        """Calcula economia estimada vs usar Opus em tudo."""
        opus_custo = MODELOS_CLAUDE[ModeloClaudeTier.OPUS]
        sonnet_custo = MODELOS_CLAUDE[ModeloClaudeTier.SONNET]

        # Supondo 2k tokens médios por chamada
        tokens_medios = 2000
        custo_tudo_opus = (
            self.stats.total_chamadas
            * tokens_medios / 1000
            * (opus_custo["custo_por_1k_input"] + opus_custo["custo_por_1k_output"]) / 2
        )
        custo_hibrido = (
            self.stats.chamadas_opus
            * tokens_medios / 1000
            * (opus_custo["custo_por_1k_input"] + opus_custo["custo_por_1k_output"]) / 2
            +
            self.stats.chamadas_sonnet
            * tokens_medios / 1000
            * (sonnet_custo["custo_por_1k_input"] + sonnet_custo["custo_por_1k_output"]) / 2
        )

        return {
            "custo_se_tudo_opus": round(custo_tudo_opus, 4),
            "custo_hibrido": round(custo_hibrido, 4),
            "economia_usd": round(custo_tudo_opus - custo_hibrido, 4),
            "economia_percentual": round(
                ((custo_tudo_opus - custo_hibrido) / custo_tudo_opus * 100)
                if custo_tudo_opus > 0 else 0, 1
            ),
        }

    def ativar(self):
        """Ativa o Smart Router (usa Sonnet + Opus)."""
        self._ativo = True
        logger.info("[Router] Smart Router ATIVADO")

    def desativar(self):
        """Desativa o Smart Router (sempre Sonnet)."""
        self._ativo = False
        logger.info("[Router] Smart Router DESATIVADO — sempre Sonnet")


# =====================================================================
# Instância Global
# =====================================================================
smart_router = SmartRouter()
