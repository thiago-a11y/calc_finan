"""
Classificador Dinamico de Mensagens — Smart Router v0.52.0

Analisa cada mensagem e escolhe o provider LLM ideal com base em:
- Complexidade do conteudo (simples, medio, complexo)
- Necessidade de function calling (tools)
- Necessidade de streaming
- Custo otimizado

Execucao pura (regex), sem I/O, < 1ms.

Uso:
    from core.classificador_mensagem import classificar_mensagem
    rec = classificar_mensagem("refatorar a arquitetura do modulo", tem_tools=True)
    # rec.provider = "gpt4o"
    # rec.motivo = "complexo + tools"
    # rec.cadeia_fallback = [...]
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger("synerium.smart_router")


# =====================================================================
# Enums e Dataclass
# =====================================================================

class NivelComplexidade(Enum):
    SIMPLES = "simples"
    MEDIO = "medio"
    COMPLEXO = "complexo"


@dataclass
class ProviderRecomendado:
    """Resultado da classificacao de uma mensagem."""
    provider: str                          # ex: "minimax", "groq", "gpt4o_mini"
    modelo: str                            # ex: "MiniMax-Text-01", "gpt-4o-mini"
    motivo: str                            # ex: "tarefa simples sem tools"
    complexidade: NivelComplexidade
    cadeia_fallback: list = field(default_factory=list)  # providers ordenados


# =====================================================================
# Registro de providers com capacidades
# =====================================================================

PROVIDERS_REGISTRO = {
    "minimax": {
        "modelo": "MiniMax-Text-01",
        "custo_1k_input": 0.0004,
        "system_role": False,
        "function_calling": False,
        "vision": False,  # nao suporta image_url em content
        "streaming": True,
    },
    "groq": {
        "modelo": "llama-3.3-70b-versatile",
        "custo_1k_input": 0.00059,
        "system_role": True,
        "function_calling": False,  # falha com tool_use_failed
        "vision": False,  # Llama text-only no Groq
        "streaming": True,
    },
    "gpt4o_mini": {
        "modelo": "gpt-4o-mini",
        "custo_1k_input": 0.00015,
        "system_role": True,
        "function_calling": True,
        "vision": True,  # suporta image_url — mais barato com vision
        "streaming": True,
    },
    "fireworks": {
        "modelo": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "custo_1k_input": 0.0009,
        "system_role": True,
        "function_calling": False,
        "vision": False,  # Llama text-only
        "streaming": True,
    },
    "together": {
        "modelo": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "custo_1k_input": 0.00088,
        "system_role": True,
        "function_calling": False,
        "vision": False,  # Llama text-only
        "streaming": True,
    },
    "anthropic_sonnet": {
        "modelo": "claude-sonnet-4-20250514",
        "custo_1k_input": 0.003,
        "system_role": True,
        "function_calling": True,
        "vision": True,  # Claude Vision nativo
        "streaming": True,
    },
    "gpt4o": {
        "modelo": "gpt-4o",
        "custo_1k_input": 0.005,
        "system_role": True,
        "function_calling": True,
        "vision": True,  # GPT-4o Vision nativo
        "streaming": True,
    },
    "anthropic_opus": {
        "modelo": "claude-opus-4-6",
        "custo_1k_input": 0.015,
        "system_role": True,
        "function_calling": True,
        "vision": True,  # Claude Vision nativo
        "streaming": True,
    },
}


# =====================================================================
# Palavras-chave para classificacao (consolidadas de llm_router.py)
# =====================================================================

# Tarefas complexas: raciocinio profundo, estrategia, arquitetura
_PALAVRAS_COMPLEXO = [
    # Arquitetura e design
    "arquitetura", "refatorar", "refatoracao", "migracao", "migrar",
    "microservicos", "escalabilidade", "escalar",
    "design pattern", "padrao de projeto", "domain driven",
    # Seguranca
    "vulnerabilidade", "auditoria", "criptografia", "lgpd",
    "penetration", "pentest",
    # Analise profunda
    "analise completa", "root cause", "diagnostico",
    "investigar", "causa raiz", "post-mortem",
    # Estrategia
    "roadmap", "trade-off", "tradeoff", "business case", "roi",
    "estrategia", "visao estrategica", "planejamento estrategico",
    # Codigo complexo
    "algoritmo", "otimizacao", "race condition", "deadlock",
    "concorrencia", "paralelismo", "memory leak",
    # Decisao de alto nivel
    "comparar tecnologias", "avaliar alternativas", "pros e contras",
    "reescrever", "redesenhar",
]

# Tarefas medias: codigo, implementacao, analise
_PALAVRAS_MEDIO = [
    "codigo", "implementar", "implementacao", "desenvolver",
    "api", "endpoint", "rota", "componente", "funcao", "classe",
    "testar", "teste", "bug", "corrigir", "fix", "debug",
    "banco de dados", "query", "sql", "migration",
    "frontend", "backend", "react", "python", "typescript",
    "deploy", "pipeline", "ci/cd", "docker",
    "configurar", "instalar", "setup",
    "documentar", "documentacao",
    "revisar", "review", "code review",
    "criar", "adicionar", "remover", "atualizar",
    "integrar", "integracao", "webhook",
]

# Pre-compilar regex para performance (< 0.1ms)
_RE_COMPLEXO = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _PALAVRAS_COMPLEXO) + r")\b",
    re.IGNORECASE,
)
_RE_MEDIO = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _PALAVRAS_MEDIO) + r")\b",
    re.IGNORECASE,
)


# =====================================================================
# Funcao principal
# =====================================================================

def classificar_mensagem(
    mensagem: str,
    tem_tools: bool = False,
    tem_imagem: bool = False,
    precisa_streaming: bool = False,
    historico_resumo: str = "",
) -> ProviderRecomendado:
    """
    Classifica uma mensagem e retorna o provider ideal.

    Args:
        mensagem: Texto da mensagem do usuario.
        tem_tools: Se o contexto requer function calling (CrewAI com tools).
        tem_imagem: Se a mensagem contem imagem (requer provider com vision).
        precisa_streaming: Se precisa de streaming (Luna chat).
        historico_resumo: Resumo do historico recente (opcional).

    Returns:
        ProviderRecomendado com provider, modelo, motivo e cadeia de fallback.
    """
    # Analisar apenas os primeiros 2000 chars (performance)
    texto = (mensagem + " " + historico_resumo)[:2000].lower()

    # --- Classificar complexidade ---
    matches_complexo = len(_RE_COMPLEXO.findall(texto))
    matches_medio = len(_RE_MEDIO.findall(texto))

    # Prompt longo (> 3000 chars) aumenta complexidade
    bonus_tamanho = 1 if len(mensagem) > 3000 else 0

    if matches_complexo >= 2 or (matches_complexo >= 1 and bonus_tamanho):
        complexidade = NivelComplexidade.COMPLEXO
    elif matches_medio >= 1 or matches_complexo >= 1:
        complexidade = NivelComplexidade.MEDIO
    else:
        complexidade = NivelComplexidade.SIMPLES

    # --- Escolher provider pela matriz de decisao ---

    # Se tem imagem, OBRIGATORIAMENTE usar provider com vision
    if tem_imagem:
        if complexidade == NivelComplexidade.COMPLEXO:
            provider, motivo = "gpt4o", "complexo + imagem (vision)"
        else:
            # gpt4o_mini e o mais barato com vision
            provider, motivo = "gpt4o_mini", f"{complexidade.value} + imagem (vision)"
    elif tem_tools:
        if complexidade == NivelComplexidade.COMPLEXO:
            provider, motivo = "gpt4o", "complexo + tools"
        else:
            provider, motivo = "gpt4o_mini", f"{complexidade.value} + tools"
    else:
        if complexidade == NivelComplexidade.COMPLEXO:
            provider, motivo = "anthropic_sonnet", "raciocinio complexo"
        elif complexidade == NivelComplexidade.MEDIO:
            provider, motivo = "groq", "tarefa media, rapido e barato"
        else:
            provider, motivo = "minimax", "tarefa simples, mais barato"

    # --- Construir cadeia de fallback ---
    cadeia = _construir_cadeia_fallback(provider, tem_tools, tem_imagem)

    modelo = PROVIDERS_REGISTRO[provider]["modelo"]

    resultado = ProviderRecomendado(
        provider=provider,
        modelo=modelo,
        motivo=motivo,
        complexidade=complexidade,
        cadeia_fallback=cadeia,
    )

    logger.info(
        f"[SMART ROUTER] Mensagem → Escolhido: {provider} ({modelo}) | "
        f"Motivo: {motivo} | Complexidade: {complexidade.value} | "
        f"Tools: {tem_tools} | Imagem: {tem_imagem} | Matches: {matches_complexo}C/{matches_medio}M"
    )

    return resultado


def _construir_cadeia_fallback(
    provider_principal: str,
    tem_tools: bool,
    tem_imagem: bool = False,
) -> list[str]:
    """
    Constroi cadeia de fallback ordenada por custo, excluindo providers
    incompativeis com o contexto (tools, vision, system_role).

    O provider principal fica primeiro, depois os demais por custo crescente.
    Anthropic fica no final (sem creditos atualmente).
    """
    cadeia = [provider_principal]

    # Filtrar providers compativeis
    candidatos = []
    for pid, info in PROVIDERS_REGISTRO.items():
        if pid == provider_principal:
            continue
        # Se precisa de tools, excluir providers sem function_calling
        if tem_tools and not info["function_calling"]:
            continue
        # Se tem imagem, excluir providers sem vision
        if tem_imagem and not info.get("vision", False):
            continue
        candidatos.append((pid, info["custo_1k_input"]))

    # Ordenar por custo, mas Anthropic sempre por ultimo
    def _sort_key(item):
        pid, custo = item
        penalty = 1000 if "anthropic" in pid else 0
        return penalty + custo

    candidatos.sort(key=_sort_key)
    cadeia.extend(pid for pid, _ in candidatos)

    return cadeia


# =====================================================================
# Adaptador de mensagens para Minimax (sem system role)
# =====================================================================

def adaptar_mensagens_para_provider(mensagens, provider: str):
    """
    Adapta mensagens para as limitacoes do provider.

    - Minimax: converte SystemMessage em prefixo da primeira HumanMessage.
    - Outros: retorna mensagens sem alteracao.
    """
    if provider != "minimax":
        return mensagens

    from langchain_core.messages import HumanMessage, SystemMessage

    system_content = ""
    outras = []

    for msg in mensagens:
        if isinstance(msg, SystemMessage):
            system_content += msg.content + "\n"
        else:
            outras.append(msg)

    if system_content and outras:
        # Prefixar system content na primeira mensagem humana
        primeira = outras[0]
        if isinstance(primeira, HumanMessage):
            if isinstance(primeira.content, str):
                outras[0] = HumanMessage(
                    content=f"[Instrucoes do sistema]\n{system_content.strip()}\n\n[Mensagem do usuario]\n{primeira.content}"
                )

    return outras if outras else mensagens
