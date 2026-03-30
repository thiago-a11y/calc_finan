"""
LLM Tracked — Wrapper que registra CADA chamada no UsageTracker.

Como o CrewAI usa factory pattern (LLM() retorna AnthropicCompletion, não LLM),
a abordagem é criar o LLM normalmente e fazer monkey-patch no método call()
para interceptar e registrar cada chamada no banco SQLite.

Uso:
    from core.llm_tracked import criar_llm_tracked
    llm = criar_llm_tracked(
        modelo="anthropic/claude-sonnet-4-20250514",
        api_key="sk-...",
        agente_nome="Tech Lead",
        squad_nome="CEO — Thiago",
        perfil_agente="tech_lead",
        tipo="chat",
    )
    # Usar normalmente — tracking é automático e transparente
"""

import logging
import time
import types
from crewai import LLM

from tools.usage_tracker import tracker

logger = logging.getLogger("synerium.llm_tracked")


# Mapa de provider por prefixo do modelo
PROVIDER_POR_PREFIXO = {
    "anthropic/": "anthropic",
    "groq/": "groq",
    "fireworks_ai/": "fireworks",
    "together_ai/": "together",
    "openai/": "openai",
}


def _extrair_provider(modelo: str) -> str:
    """Extrai o provider_id a partir do nome do modelo."""
    for prefixo, provider_id in PROVIDER_POR_PREFIXO.items():
        if modelo.startswith(prefixo):
            return provider_id
    if "claude" in modelo.lower():
        return "anthropic"
    if "llama" in modelo.lower():
        return "groq"
    return "desconhecido"


def _extrair_modelo_limpo(modelo: str) -> str:
    """Remove prefixo do provider (ex: 'anthropic/claude-sonnet-4' -> 'claude-sonnet-4')."""
    for prefixo in PROVIDER_POR_PREFIXO:
        if modelo.startswith(prefixo):
            return modelo[len(prefixo):]
    return modelo


def _estimar_tokens(texto: str) -> int:
    """Estima tokens (1 token ~= 4 chars em portugues)."""
    if not texto:
        return 0
    return max(1, len(texto) // 4)


def criar_llm_tracked(
    modelo: str,
    api_key: str = "",
    max_tokens: int = 8192,
    agente_nome: str = "",
    squad_nome: str = "",
    perfil_agente: str = "",
    tipo: str = "chat",
    usuario_id: int | None = None,
    usuario_nome: str = "",
):
    """
    Cria uma instancia de LLM com tracking automatico via monkey-patch.

    O CrewAI usa factory pattern: LLM(model="anthropic/...") retorna
    AnthropicCompletion. Nao da pra herdar de LLM. Entao criamos o LLM
    normalmente e substituimos o metodo call() por uma versao que
    intercepta, registra e repassa para o call original.

    Args:
        modelo: Nome do modelo (ex: 'anthropic/claude-sonnet-4-20250514')
        api_key: Chave da API
        max_tokens: Maximo de tokens na resposta
        agente_nome: Nome do agente que vai usar este LLM
        squad_nome: Nome do squad
        perfil_agente: Perfil do agente (tech_lead, backend_dev, etc.)
        tipo: Tipo de operacao (chat, reuniao, rag, etc.)
        usuario_id: ID do usuario
        usuario_nome: Nome do usuario

    Returns:
        Instancia LLM do CrewAI com tracking transparente
    """
    # Criar LLM normalmente (CrewAI retorna o tipo correto)
    kwargs = {"model": modelo, "max_tokens": max_tokens}
    if api_key:
        kwargs["api_key"] = api_key
    llm = LLM(**kwargs)

    # Guardar metadados de tracking na instancia
    llm._tracking_agente = agente_nome
    llm._tracking_squad = squad_nome
    llm._tracking_perfil = perfil_agente
    llm._tracking_tipo = tipo
    llm._tracking_usuario_id = usuario_id
    llm._tracking_usuario_nome = usuario_nome
    llm._tracking_modelo_original = modelo

    # Salvar referencia ao call original
    call_original = llm.call

    def call_tracked(messages, **kwargs):
        """
        Chama o LLM real e registra o consumo no UsageTracker.

        Aceita **kwargs para compatibilidade total com qualquer versao
        do CrewAI (tools, available_tools, available_functions,
        callbacks, tool_choice, etc.).
        """
        # Estimar tokens de input
        texto_input = ""
        if isinstance(messages, list):
            for msg in messages:
                if isinstance(msg, dict):
                    texto_input += str(msg.get("content", ""))
                else:
                    texto_input += str(msg)
        elif isinstance(messages, str):
            texto_input = messages
        else:
            texto_input = str(messages)

        tokens_input = _estimar_tokens(texto_input)
        modelo_ref = getattr(llm, '_tracking_modelo_original', modelo)
        provider_id = _extrair_provider(modelo_ref)
        modelo_limpo = _extrair_modelo_limpo(modelo_ref)

        # Chamar o LLM real (repassando todos os kwargs ao call original)
        inicio = time.time()
        try:
            resultado = call_original(messages=messages, **kwargs)
        except Exception as e:
            # Registrar tentativa falhada
            duracao = time.time() - inicio
            tracker.registrar(
                provider_id=provider_id,
                tokens_input=tokens_input,
                tokens_output=0,
                modelo=modelo_limpo,
                tipo=llm._tracking_tipo,
                agente_nome=llm._tracking_agente,
                squad_nome=llm._tracking_squad,
                usuario_id=llm._tracking_usuario_id,
                usuario_nome=llm._tracking_usuario_nome,
                detalhes={
                    "erro": str(e)[:200],
                    "duracao_seg": round(duracao, 2),
                    "perfil": llm._tracking_perfil,
                },
            )
            logger.warning(
                f"[TRACKED] ERRO {provider_id}/{modelo_limpo} | "
                f"agente={llm._tracking_agente} | {e}"
            )
            raise

        # Estimar tokens de output
        duracao = time.time() - inicio
        texto_output = str(resultado) if resultado else ""
        tokens_output = _estimar_tokens(texto_output)

        # Registrar no tracker
        tracker.registrar(
            provider_id=provider_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            modelo=modelo_limpo,
            tipo=llm._tracking_tipo,
            agente_nome=llm._tracking_agente,
            squad_nome=llm._tracking_squad,
            usuario_id=llm._tracking_usuario_id,
            usuario_nome=llm._tracking_usuario_nome,
            detalhes={
                "duracao_seg": round(duracao, 2),
                "perfil": llm._tracking_perfil,
            },
        )

        logger.info(
            f"[TRACKED] {provider_id}/{modelo_limpo} | "
            f"in={tokens_input} out={tokens_output} | "
            f"{duracao:.1f}s | agente={llm._tracking_agente}"
        )

        return resultado

    # Monkey-patch: substituir call pelo call_tracked
    llm.call = call_tracked

    logger.debug(
        f"[TRACKED] LLM criado com tracking: {modelo} | "
        f"agente={agente_nome} | squad={squad_nome}"
    )

    return llm
