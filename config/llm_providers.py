"""
Sistema Multi-Provider de LLM com Fallback Inteligente + Smart Router.

Ordem de prioridade (do mais inteligente para o mais rápido/barato):
1. Claude Opus (Anthropic) — Tarefas complexas (via Smart Router)
2. Claude Sonnet (Anthropic) — Padrão, rápido e eficiente
3. Groq Llama — Fallback 1, mais rápido
4. Fireworks Llama — Fallback 2
5. Together.ai Llama — Fallback 3

Funcionalidades:
- Smart Router Sonnet/Opus (decide automaticamente por complexidade)
- Fallback automático na ordem configurada
- Logging de qual modelo foi usado em cada chamada
- Monitoramento de latência e erros por provider
- Possibilidade de trocar o provider padrão em tempo real
"""

import os
import time
import logging
from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("synerium.llm")


class ProviderID(str, Enum):
    """Identificadores dos providers de LLM."""
    ANTHROPIC_OPUS = "anthropic_opus"
    ANTHROPIC_SONNET = "anthropic_sonnet"
    ANTHROPIC = "anthropic"  # Alias legado → redireciona para Sonnet
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    FIREWORKS = "fireworks"
    TOGETHER = "together"


class ProviderConfig(BaseModel):
    """Configuração de um provider de LLM."""
    id: ProviderID
    nome: str
    icone: str
    modelo: str
    api_key_env: str  # Nome da variável de ambiente
    base_url: str | None = None  # URL da API (OpenAI-compatible)
    custo_por_1k_input: float = 0.0
    custo_por_1k_output: float = 0.0
    max_tokens: int = 4096
    ativo: bool = True
    prioridade: int = 0  # Menor = maior prioridade


class ProviderStatus(BaseModel):
    """Status em tempo real de um provider."""
    id: str
    nome: str
    icone: str
    modelo: str
    ativo: bool
    configurado: bool  # API key presente
    total_chamadas: int = 0
    total_erros: int = 0
    total_tokens: int = 0
    custo_estimado: float = 0.0
    latencia_media_ms: float = 0.0
    ultimo_uso: str | None = None
    ultimo_erro: str | None = None


# =====================================================================
# Configuração dos Providers
# =====================================================================

PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        id=ProviderID.ANTHROPIC_OPUS,
        nome="Claude Opus 4 (Anthropic)",
        icone="🧠",
        modelo="claude-opus-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
        custo_por_1k_input=0.015,
        custo_por_1k_output=0.075,
        max_tokens=8192,
        prioridade=0,  # Mais inteligente — usado pelo Smart Router para tarefas complexas
    ),
    ProviderConfig(
        id=ProviderID.ANTHROPIC_SONNET,
        nome="Claude Sonnet 4 (Anthropic)",
        icone="⚡",
        modelo="claude-sonnet-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
        custo_por_1k_input=0.003,
        custo_por_1k_output=0.015,
        max_tokens=8192,
        prioridade=1,  # Padrão — rápido e eficiente
    ),
    ProviderConfig(
        id=ProviderID.OPENAI,
        nome="GPT-4o (OpenAI)",
        icone="🤖",
        modelo="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        custo_por_1k_input=0.0025,
        custo_por_1k_output=0.01,
        max_tokens=4096,
        prioridade=2,
    ),
    ProviderConfig(
        id=ProviderID.GEMINI,
        nome="Gemini 2.5 Flash (Google)",
        icone="💎",
        modelo="gemini-2.5-flash",
        api_key_env="GOOGLE_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        custo_por_1k_input=0.00015,
        custo_por_1k_output=0.0006,
        max_tokens=8192,
        prioridade=3,
    ),
    ProviderConfig(
        id=ProviderID.GROQ,
        nome="Llama via Groq",
        icone="⚡",
        modelo="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        custo_por_1k_input=0.00059,
        custo_por_1k_output=0.00079,
        max_tokens=8192,
        prioridade=4,
    ),
    ProviderConfig(
        id=ProviderID.FIREWORKS,
        nome="Llama via Fireworks",
        icone="🔥",
        modelo="accounts/fireworks/models/llama-v3p3-70b-instruct",
        api_key_env="FIREWORKS_API_KEY",
        base_url="https://api.fireworks.ai/inference/v1",
        custo_por_1k_input=0.0009,
        custo_por_1k_output=0.0009,
        max_tokens=4096,
        prioridade=5,
    ),
    ProviderConfig(
        id=ProviderID.TOGETHER,
        nome="Llama via Together.ai",
        icone="🤝",
        modelo="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        api_key_env="TOGETHER_API_KEY",
        base_url="https://api.together.xyz/v1",
        custo_por_1k_input=0.00088,
        custo_por_1k_output=0.00088,
        max_tokens=8192,
        prioridade=6,
    ),
]


class LLMProviderManager:
    """
    Gerenciador de providers de LLM com fallback inteligente.

    Uso:
        manager = LLMProviderManager()
        llm = manager.obter_llm()  # Retorna o melhor LLM disponível
        llm = manager.obter_llm(provider="groq")  # Forçar provider específico
    """

    def __init__(self):
        self.providers = {p.id: p for p in PROVIDERS}
        self.provider_padrao: ProviderID = ProviderID.ANTHROPIC_SONNET
        self._estatisticas: dict[str, dict] = {}

        # Inicializar estatísticas
        for p in PROVIDERS:
            self._estatisticas[p.id] = {
                "chamadas": 0,
                "erros": 0,
                "tokens": 0,
                "custo": 0.0,
                "latencias": [],
                "ultimo_uso": None,
                "ultimo_erro": None,
            }

        logger.info(
            f"[LLM] Provider Manager inicializado. "
            f"Padrão: {self.provider_padrao.value}. "
            f"Fallbacks: {', '.join(p.id.value for p in sorted(PROVIDERS, key=lambda x: x.prioridade))}"
        )

    def _provider_configurado(self, provider: ProviderConfig) -> bool:
        """Verifica se o provider tem API key configurada."""
        key = os.environ.get(provider.api_key_env, "")
        return bool(key and len(key) > 5)

    def obter_llm(self, provider: str | None = None):
        """
        Retorna uma instância de LLM com fallback automático.

        Para CrewAI, retorna um objeto LLM compatível.
        """
        from crewai import LLM

        # Ordem de tentativa
        if provider:
            ordem = [self.providers.get(ProviderID(provider))]
            ordem = [p for p in ordem if p]
            # Adicionar fallbacks
            for p in sorted(PROVIDERS, key=lambda x: x.prioridade):
                if p not in ordem:
                    ordem.append(p)
        else:
            ordem = sorted(PROVIDERS, key=lambda x: x.prioridade)

        # Tentar cada provider na ordem
        for p in ordem:
            if not p.ativo or not self._provider_configurado(p):
                continue

            try:
                api_key = os.environ.get(p.api_key_env, "")

                if p.id in (ProviderID.ANTHROPIC_OPUS, ProviderID.ANTHROPIC_SONNET, ProviderID.ANTHROPIC):
                    llm = LLM(
                        model=f"anthropic/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                elif p.id == ProviderID.OPENAI:
                    llm = LLM(
                        model=f"openai/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                elif p.id == ProviderID.GEMINI:
                    llm = LLM(
                        model=f"gemini/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                elif p.id == ProviderID.GROQ:
                    llm = LLM(
                        model=f"groq/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                elif p.id == ProviderID.FIREWORKS:
                    llm = LLM(
                        model=f"fireworks_ai/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                elif p.id == ProviderID.TOGETHER:
                    llm = LLM(
                        model=f"together_ai/{p.modelo}",
                        api_key=api_key,
                        max_tokens=p.max_tokens,
                    )
                else:
                    llm = LLM(
                        model=p.modelo,
                        api_key=api_key,
                        base_url=p.base_url,
                        max_tokens=p.max_tokens,
                    )

                logger.info(f"[LLM] Usando: {p.nome} ({p.modelo})")
                return llm

            except Exception as e:
                self._estatisticas[p.id]["erros"] += 1
                self._estatisticas[p.id]["ultimo_erro"] = str(e)
                logger.warning(f"[LLM] Falha no {p.nome}: {e}. Tentando próximo...")
                continue

        # Se nenhum funcionar, retornar o padrão (vai dar erro ao usar)
        logger.error("[LLM] NENHUM provider disponível!")
        return LLM(model="anthropic/claude-sonnet-4-20250514")

    def registrar_uso(self, provider_id: str, tokens: int = 0,
                      latencia_ms: float = 0, erro: str | None = None):
        """Registra uso de um provider para estatísticas."""
        if provider_id not in self._estatisticas:
            return

        stats = self._estatisticas[provider_id]
        stats["chamadas"] += 1
        stats["tokens"] += tokens
        stats["ultimo_uso"] = datetime.now().isoformat()

        if latencia_ms > 0:
            stats["latencias"].append(latencia_ms)
            # Manter só últimas 100 medições
            if len(stats["latencias"]) > 100:
                stats["latencias"] = stats["latencias"][-100:]

        if erro:
            stats["erros"] += 1
            stats["ultimo_erro"] = erro

        # Calcular custo
        p = self.providers.get(ProviderID(provider_id))
        if p:
            stats["custo"] += (tokens / 1000) * (p.custo_por_1k_input + p.custo_por_1k_output) / 2

    def obter_status(self) -> list[ProviderStatus]:
        """Retorna status de todos os providers."""
        resultado = []
        for p in sorted(PROVIDERS, key=lambda x: x.prioridade):
            stats = self._estatisticas.get(p.id, {})
            latencias = stats.get("latencias", [])

            resultado.append(ProviderStatus(
                id=p.id.value,
                nome=p.nome,
                icone=p.icone,
                modelo=p.modelo,
                ativo=p.ativo,
                configurado=self._provider_configurado(p),
                total_chamadas=stats.get("chamadas", 0),
                total_erros=stats.get("erros", 0),
                total_tokens=stats.get("tokens", 0),
                custo_estimado=round(stats.get("custo", 0.0), 6),
                latencia_media_ms=round(sum(latencias) / len(latencias), 1) if latencias else 0,
                ultimo_uso=stats.get("ultimo_uso"),
                ultimo_erro=stats.get("ultimo_erro"),
            ))
        return resultado

    def definir_provider_padrao(self, provider_id: str):
        """Muda o provider padrão."""
        try:
            pid = ProviderID(provider_id)
            if pid in self.providers:
                self.provider_padrao = pid
                # Atualizar prioridade — o escolhido fica com prioridade 0
                for p in PROVIDERS:
                    if p.id == pid:
                        p.prioridade = 0
                    elif p.prioridade == 0:
                        p.prioridade = 1
                logger.info(f"[LLM] Provider padrão alterado para: {self.providers[pid].nome}")
                return True
        except ValueError:
            pass
        return False

    def ativar_desativar(self, provider_id: str, ativo: bool):
        """Ativa ou desativa um provider."""
        try:
            pid = ProviderID(provider_id)
            if pid in self.providers:
                self.providers[pid].ativo = ativo
                logger.info(f"[LLM] {self.providers[pid].nome}: {'ativado' if ativo else 'desativado'}")
                return True
        except ValueError:
            pass
        return False


# Instância global
llm_manager = LLMProviderManager()
