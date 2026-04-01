"""
LLM Fallback — Chamada robusta com cadeia de fallback automatica.

Ordem de prioridade (v0.51.0):
1. Minimax (principal — mais barato e rapido)
2. Groq Llama 3.3 (fallback rapido)
3. Anthropic Sonnet (fallback premium)
4. OpenAI GPT-4o (fallback final)

v0.53.1: Retry com backoff exponencial para rate limit (429).
  - Ate 3 tentativas por provider antes de fazer fallback
  - Backoff: 2s, 4s, 8s (base=2, fator=2)
  - Apenas para erros 429/rate_limit (nao para credito/auth)

Uso:
    from core.llm_fallback import chamar_llm_com_fallback
    resposta = chamar_llm_com_fallback(mensagens, max_tokens=2000)
    resposta = await chamar_llm_com_fallback_async(mensagens, max_tokens=2000)
"""

import asyncio
import logging
import os
import time

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("synerium.llm_fallback")

# Configuracao de retry para rate limit
MAX_RETRIES = 3          # Tentativas por provider antes de fallback
BACKOFF_BASE = 2.0       # Segundos base (2s, 4s, 8s)
BACKOFF_MULTIPLIER = 2.0

# Erros que indicam problema de credito/quota (trigger fallback)
ERROS_CREDITO = [
    "credit balance is too low",
    "insufficient_balance",
    "rate_limit_exceeded",
    "billing",
    "quota",
    "overloaded",
    "529",
    "402",
    "429",
    "too many requests",
]

# Cadeia definitiva: Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
CADEIA_FALLBACK = [
    {
        "nome": "minimax",
        "tipo": "minimax",
        "modelo": "MiniMax-Text-01",
        "env_key": "MINIMAX_API_KEY",
        "env_group": "MINIMAX_GROUP_ID",
        "custo_input": 0.0004,
        "custo_output": 0.0016,
        "plano": "Plano Maximo $50/mes",
    },
    {
        "nome": "groq_llama",
        "tipo": "groq",
        "modelo": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "custo_input": 0.00059,
        "custo_output": 0.00079,
    },
    {
        "nome": "fireworks_llama",
        "tipo": "openai_compat",
        "modelo": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "env_key": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "custo_input": 0.0009,
        "custo_output": 0.0009,
    },
    {
        "nome": "together_llama",
        "tipo": "openai_compat",
        "modelo": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "custo_input": 0.00088,
        "custo_output": 0.00088,
    },
    {
        "nome": "anthropic_sonnet",
        "tipo": "anthropic",
        "modelo": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
        "custo_input": 0.003,
        "custo_output": 0.015,
    },
    {
        "nome": "openai_gpt4",
        "tipo": "openai",
        "modelo": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "custo_input": 0.005,
        "custo_output": 0.015,
    },
]


def _eh_erro_credito(erro: Exception) -> bool:
    """Verifica se o erro indica problema de credito/quota."""
    msg = str(erro).lower()
    return any(termo in msg for termo in ERROS_CREDITO)


def _eh_rate_limit(erro: Exception) -> bool:
    """
    Verifica se o erro e especificamente rate limit (429).
    Rate limit = pode dar retry com backoff. Credito/auth = fallback direto.
    """
    msg = str(erro).lower()
    return any(termo in msg for termo in [
        "429", "rate_limit_exceeded", "too many requests",
        "rate limit", "ratelimit", "tokens per min",
    ])


def _criar_llm(provider: dict, max_tokens: int = 2000, temperature: float = 0.3):
    """Cria instancia de LLM baseado no provider config."""
    nome = provider["nome"]
    tipo = provider.get("tipo", nome)
    modelo = provider["modelo"]
    env_key = provider["env_key"]

    api_key = os.getenv(env_key, "")
    if not api_key:
        return None

    try:
        if tipo == "minimax":
            # Usar API OpenAI-compatible com endpoint GLOBAL (api.minimaxi.chat com i)
            from langchain_openai import ChatOpenAI
            group_id = os.getenv(provider.get("env_group", "MINIMAX_GROUP_ID"), "")
            return ChatOpenAI(
                model=modelo,
                openai_api_key=api_key,
                openai_api_base="https://api.minimaxi.chat/v1",
                max_tokens=max_tokens,
                temperature=temperature,
                model_kwargs={"extra_body": {"group_id": group_id}},
            )
        elif tipo == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=modelo, max_tokens=max_tokens, temperature=temperature)
        elif tipo == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=modelo, max_tokens=max_tokens, temperature=temperature)
        elif tipo == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=modelo, max_tokens=max_tokens, temperature=temperature)
        elif tipo == "openai_compat":
            # Fireworks, Together e outros compatíveis com API OpenAI
            from langchain_openai import ChatOpenAI
            base_url = provider.get("base_url", "")
            return ChatOpenAI(
                model=modelo, max_tokens=max_tokens, temperature=temperature,
                openai_api_key=api_key, openai_api_base=base_url,
            )
        else:
            return None
    except ImportError:
        logger.warning(f"[FALLBACK] Provider {nome} nao disponivel (lib nao instalada)")
        return None
    except Exception as e:
        logger.warning(f"[FALLBACK] Erro ao criar LLM {nome}: {e}")
        return None


def _mensagens_tem_imagem(mensagens) -> bool:
    """Detecta se alguma mensagem contem image_url (content multimodal). Safety net para vision."""
    for msg in mensagens:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


# Providers que NAO suportam vision (image_url em content_parts)
_PROVIDERS_SEM_VISION = {"minimax", "groq_llama", "fireworks_llama", "together_llama"}


def chamar_llm_com_fallback(
    mensagens,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    classificacao=None,
) -> tuple:
    """
    Chama LLM com fallback automatico. Retorna (resposta, provider_usado, modelo_usado).

    v0.53.1: Retry com backoff exponencial para rate limit (429).
    v0.58.0: Safety net — pula providers sem vision quando mensagem contem imagem.
    """
    from core.classificador_mensagem import adaptar_mensagens_para_provider

    cadeia = _reordenar_cadeia(classificacao) if classificacao else list(CADEIA_FALLBACK)
    primeiro = cadeia[0]["nome"]

    # v0.58.0: Detectar imagem nas mensagens (safety net independente do classificador)
    tem_imagem = _mensagens_tem_imagem(mensagens)
    if tem_imagem:
        logger.info("[FALLBACK] Imagem detectada nas mensagens — filtrando providers sem vision")

    erros = []
    for provider in cadeia:
        # v0.58.0: Pular providers sem vision se mensagem contem imagem
        if tem_imagem and provider["nome"] in _PROVIDERS_SEM_VISION:
            logger.info(f"[FALLBACK] Pulando {provider['nome']} — nao suporta vision")
            continue

        msgs = adaptar_mensagens_para_provider(mensagens, provider["nome"])

        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        # Retry loop para rate limit (429)
        for tentativa in range(MAX_RETRIES):
            try:
                resposta = llm.invoke(msgs)
                if provider["nome"] != primeiro:
                    logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']})")
                if tentativa > 0:
                    logger.info(f"[RETRY] {provider['nome']} sucesso na tentativa {tentativa + 1}")
                return (resposta, provider["nome"], provider["modelo"])
            except Exception as e:
                if _eh_rate_limit(e) and tentativa < MAX_RETRIES - 1:
                    # Rate limit — retry com backoff exponencial
                    delay = BACKOFF_BASE * (BACKOFF_MULTIPLIER ** tentativa)
                    logger.warning(
                        f"[RETRY] {provider['nome']} rate limit (429) — "
                        f"tentativa {tentativa + 1}/{MAX_RETRIES}, aguardando {delay:.0f}s"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Erro de credito, auth, ou rate limit esgotou retries → fallback
                    erros.append(f"{provider['nome']}: {str(e)[:100]}")
                    if _eh_erro_credito(e):
                        logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → proximo")
                    elif _eh_rate_limit(e):
                        logger.warning(f"[FALLBACK] {provider['nome']} rate limit persistente ({MAX_RETRIES}x) → proximo")
                    else:
                        logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:80]} → proximo")
                    break  # Sai do retry loop, vai pro proximo provider

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")


async def chamar_llm_com_fallback_async(
    mensagens,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    classificacao=None,
) -> tuple:
    """
    Versao async do fallback. Retorna (resposta, provider_usado, modelo_usado).

    v0.53.1: Retry com backoff exponencial para rate limit (429).
    v0.58.0: Safety net — pula providers sem vision quando mensagem contem imagem.
    """
    from core.classificador_mensagem import adaptar_mensagens_para_provider

    cadeia = _reordenar_cadeia(classificacao) if classificacao else list(CADEIA_FALLBACK)
    primeiro = cadeia[0]["nome"]

    # v0.58.0: Detectar imagem nas mensagens (safety net)
    tem_imagem = _mensagens_tem_imagem(mensagens)

    erros = []
    for provider in cadeia:
        # v0.58.0: Pular providers sem vision se mensagem contem imagem
        if tem_imagem and provider["nome"] in _PROVIDERS_SEM_VISION:
            logger.info(f"[FALLBACK] Pulando {provider['nome']} — nao suporta vision (async)")
            continue

        msgs = adaptar_mensagens_para_provider(mensagens, provider["nome"])

        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        # Retry loop para rate limit (429)
        for tentativa in range(MAX_RETRIES):
            try:
                resposta = await llm.ainvoke(msgs)
                if provider["nome"] != primeiro:
                    logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']})")
                if tentativa > 0:
                    logger.info(f"[RETRY] {provider['nome']} sucesso na tentativa {tentativa + 1}")
                return (resposta, provider["nome"], provider["modelo"])
            except Exception as e:
                if _eh_rate_limit(e) and tentativa < MAX_RETRIES - 1:
                    delay = BACKOFF_BASE * (BACKOFF_MULTIPLIER ** tentativa)
                    logger.warning(
                        f"[RETRY] {provider['nome']} rate limit (429) — "
                        f"tentativa {tentativa + 1}/{MAX_RETRIES}, aguardando {delay:.0f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    erros.append(f"{provider['nome']}: {str(e)[:100]}")
                    if _eh_erro_credito(e):
                        logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → proximo")
                    elif _eh_rate_limit(e):
                        logger.warning(f"[FALLBACK] {provider['nome']} rate limit persistente ({MAX_RETRIES}x) → proximo")
                    else:
                        logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:80]} → proximo")
                    break

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")


def _reordenar_cadeia(classificacao) -> list[dict]:
    """
    Reordena CADEIA_FALLBACK conforme recomendacao do classificador.
    O provider recomendado fica primeiro, depois os demais na ordem da cadeia de fallback.
    """
    # Mapear nomes da cadeia_fallback do classificador para configs do CADEIA_FALLBACK
    cadeia_por_nome = {p["nome"]: p for p in CADEIA_FALLBACK}

    # Mapeamento de nomes do classificador para nomes do fallback
    MAPA_NOMES = {
        "minimax": "minimax",
        "groq": "groq_llama",
        "gpt4o_mini": "openai_gpt4",  # usa mesma config, modelo diferente
        "gpt4o": "openai_gpt4",
        "fireworks": "fireworks_llama",
        "together": "together_llama",
        "anthropic_sonnet": "anthropic_sonnet",
        "anthropic_opus": "anthropic_sonnet",  # fallback usa sonnet
    }

    resultado = []
    adicionados = set()

    # 1. Provider principal recomendado
    for nome_class in classificacao.cadeia_fallback:
        nome_fb = MAPA_NOMES.get(nome_class, nome_class)
        if nome_fb in cadeia_por_nome and nome_fb not in adicionados:
            config = dict(cadeia_por_nome[nome_fb])
            # Para gpt4o_mini, sobrescrever modelo
            if nome_class == "gpt4o_mini":
                config = dict(config)
                config["modelo"] = "gpt-4o-mini"
            resultado.append(config)
            adicionados.add(nome_fb)

    # 2. Adicionar os que sobraram (safety net)
    for p in CADEIA_FALLBACK:
        if p["nome"] not in adicionados:
            resultado.append(p)

    return resultado
