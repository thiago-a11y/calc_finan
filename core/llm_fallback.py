"""
LLM Fallback — Chamada robusta com cadeia de fallback automatica.

Quando Anthropic falha (sem creditos, rate limit, 402, 429),
automaticamente tenta Groq → Fireworks → Together → OpenAI.

Uso:
    from core.llm_fallback import chamar_llm_com_fallback
    resposta = chamar_llm_com_fallback(mensagens, max_tokens=2000)
    resposta = await chamar_llm_com_fallback_async(mensagens, max_tokens=2000)
"""

import logging
import os

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
]

# Cadeia de fallback: Anthropic → Groq → Fireworks → Together → OpenAI
CADEIA_FALLBACK = [
    {
        "nome": "anthropic_sonnet",
        "classe": "langchain_anthropic.ChatAnthropic",
        "modelo": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
    },
    {
        "nome": "groq_llama",
        "classe": "langchain_groq.ChatGroq",
        "modelo": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    {
        "nome": "openai_gpt4",
        "classe": "langchain_openai.ChatOpenAI",
        "modelo": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
    },
]


def _eh_erro_credito(erro: Exception) -> bool:
    """Verifica se o erro indica problema de credito/quota."""
    msg = str(erro).lower()
    return any(termo in msg for termo in ERROS_CREDITO)


def _criar_llm(provider: dict, max_tokens: int = 2000, temperature: float = 0.3):
    """Cria instancia de LLM baseado no provider config."""
    nome = provider["nome"]
    modelo = provider["modelo"]
    env_key = provider["env_key"]

    # Verificar se API key esta configurada
    api_key = os.getenv(env_key, "")
    if not api_key:
        return None

    try:
        if "anthropic" in nome:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=modelo, max_tokens=max_tokens, temperature=temperature)
        elif "groq" in nome:
            from langchain_groq import ChatGroq
            return ChatGroq(model=modelo, max_tokens=max_tokens, temperature=temperature)
        elif "openai" in nome:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=modelo, max_tokens=max_tokens, temperature=temperature)
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
    modelo_preferido: str = "claude-sonnet-4-20250514",
) -> tuple:
    """
    Chama LLM com fallback automatico. Retorna (resposta, provider_usado, modelo_usado).

    Se Anthropic falhar por credito/quota, tenta Groq → OpenAI automaticamente.
    """
    # Montar cadeia com modelo preferido primeiro
    cadeia = list(CADEIA_FALLBACK)

    erros = []
    for provider in cadeia:
        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        try:
            resposta = llm.invoke(mensagens)
            if provider["nome"] != "anthropic_sonnet":
                logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']}) — Anthropic indisponivel")
            return (resposta, provider["nome"], provider["modelo"])
        except Exception as e:
            erros.append(f"{provider['nome']}: {str(e)[:100]}")
            if _eh_erro_credito(e):
                logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → tentando proximo")
                continue
            else:
                logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:100]} → tentando proximo")
                continue

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")


async def chamar_llm_com_fallback_async(
    mensagens,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> tuple:
    """
    Versao async do fallback. Retorna (resposta, provider_usado, modelo_usado).
    """
    cadeia = list(CADEIA_FALLBACK)

    erros = []
    for provider in cadeia:
        llm = _criar_llm(provider, max_tokens, temperature)
        if not llm:
            continue

        try:
            resposta = await llm.ainvoke(mensagens)
            if provider["nome"] != "anthropic_sonnet":
                logger.info(f"[FALLBACK] Usando {provider['nome']} ({provider['modelo']}) — Anthropic indisponivel")
            return (resposta, provider["nome"], provider["modelo"])
        except Exception as e:
            erros.append(f"{provider['nome']}: {str(e)[:100]}")
            if _eh_erro_credito(e):
                logger.warning(f"[FALLBACK] {provider['nome']} sem credito/quota → tentando proximo")
                continue
            else:
                logger.warning(f"[FALLBACK] {provider['nome']} erro: {str(e)[:100]} → tentando proximo")
                continue

    raise RuntimeError(f"Todos os providers falharam: {'; '.join(erros)}")
