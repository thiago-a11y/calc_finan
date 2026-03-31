"""
LLM Fallback — Chamada robusta com cadeia de fallback automatica.

Ordem de prioridade (v0.51.0):
1. Minimax (principal — mais barato e rapido)
2. Groq Llama 3.3 (fallback rapido)
3. Anthropic Sonnet (fallback premium)
4. OpenAI GPT-4o (fallback final)

Uso:
    from core.llm_fallback import chamar_llm_com_fallback
    resposta = chamar_llm_com_fallback(mensagens, max_tokens=2000)
    resposta = await chamar_llm_com_fallback_async(mensagens, max_tokens=2000)
"""

import logging
import os

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("synerium.llm_fallback")

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
            from langchain_community.chat_models import MiniMaxChat
            group_id = os.getenv(provider.get("env_group", "MINIMAX_GROUP_ID"), "")
            return MiniMaxChat(
                model=modelo,
                minimax_api_key=api_key,
                minimax_group_id=group_id,
                max_tokens=max_tokens,
                temperature=temperature,
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


def chamar_llm_com_fallback(
    mensagens,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> tuple:
    """
    Chama LLM com fallback automatico. Retorna (resposta, provider_usado, modelo_usado).

    Prioridade: Minimax → Groq → Anthropic → OpenAI
    """
    cadeia = list(CADEIA_FALLBACK)
    primeiro = cadeia[0]["nome"]

    erros = []
    for provider in cadeia:
        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        try:
            resposta = llm.invoke(mensagens)
            if provider["nome"] != primeiro:
                logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']})")
            return (resposta, provider["nome"], provider["modelo"])
        except Exception as e:
            erros.append(f"{provider['nome']}: {str(e)[:100]}")
            if _eh_erro_credito(e):
                logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → tentando proximo")
            else:
                logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:80]} → tentando proximo")
            continue

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")


async def chamar_llm_com_fallback_async(
    mensagens,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> tuple:
    """
    Versao async do fallback. Retorna (resposta, provider_usado, modelo_usado).
    Prioridade: Minimax → Groq → Anthropic → OpenAI
    """
    cadeia = list(CADEIA_FALLBACK)
    primeiro = cadeia[0]["nome"]

    erros = []
    for provider in cadeia:
        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        try:
            resposta = await llm.ainvoke(mensagens)
            if provider["nome"] != primeiro:
                logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']})")
            return (resposta, provider["nome"], provider["modelo"])
        except Exception as e:
            erros.append(f"{provider['nome']}: {str(e)[:100]}")
            if _eh_erro_credito(e):
                logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → tentando proximo")
            else:
                logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:80]} → tentando proximo")
            continue

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")
