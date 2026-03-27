"""
Usage Tracker — Registra CADA chamada de API no banco SQLite.

Nunca reseta. Fonte de verdade para o dashboard de consumo.
Suporta todos os 14 providers do Synerium Factory.

Uso:
    from tools.usage_tracker import tracker
    tracker.registrar("anthropic", tokens_input=500, tokens_output=200, modelo="claude-sonnet-4-20250514")
"""

import logging
from datetime import datetime
from database.session import SessionLocal
from database.models import UsageTrackingDB

logger = logging.getLogger("synerium.usage")

# Custos por provider (USD por 1k tokens ou por request)
CUSTOS = {
    # Anthropic — custos diferenciados por modelo
    "anthropic": {"input": 0.003, "output": 0.015},  # Default (Sonnet)
    "openai": {"input": 0.0001, "output": 0.0001},
    "groq": {"input": 0.00059, "output": 0.00079},
    "fireworks": {"input": 0.0009, "output": 0.0009},
    "together": {"input": 0.00088, "output": 0.00088},
    "tavily": {"por_request": 0.01},
    "exa": {"por_request": 0.005},
    "firecrawl": {"por_request": 0.0},
    "scrapingdog": {"por_request": 0.001},
    "langsmith": {"por_request": 0.0},
    "composio": {"por_request": 0.0},
    "e2b": {"por_request": 0.0001},
    "aws_ses": {"por_request": 0.0001},
    "livekit": {"por_minuto": 0.004},
}

# Custos específicos por modelo (mais preciso que por provider)
CUSTOS_POR_MODELO = {
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "llama-v3p3-70b-instruct": {"input": 0.0009, "output": 0.0009},
    "Llama-3.3-70B-Instruct-Turbo": {"input": 0.00088, "output": 0.00088},
}


class UsageTracker:
    """Registra consumo de APIs no banco SQLite."""

    def registrar(
        self,
        provider_id: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        modelo: str = "",
        tipo: str = "chat",
        agente_nome: str = "",
        squad_nome: str = "",
        usuario_id: int | None = None,
        usuario_nome: str = "",
        detalhes: dict | None = None,
    ) -> None:
        """
        Registra uma chamada de API no banco.

        Args:
            provider_id: ID do provider (anthropic, openai, groq, etc.)
            tokens_input: Tokens de entrada
            tokens_output: Tokens de saída
            modelo: Nome do modelo usado
            tipo: Tipo de operação (chat, reuniao, rag, embedding, busca, email)
            agente_nome: Nome do agente que fez a chamada
            squad_nome: Nome do squad
            usuario_id: ID do usuário
            usuario_nome: Nome do usuário
            detalhes: Dict com informações extras
        """
        try:
            tokens_total = tokens_input + tokens_output
            custo = self._calcular_custo(provider_id, tokens_input, tokens_output, modelo)

            db = SessionLocal()
            try:
                registro = UsageTrackingDB(
                    provider_id=provider_id,
                    provider_nome=self._nome_provider(provider_id),
                    modelo=modelo,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    tokens_total=tokens_total,
                    requests=1,
                    custo_usd=custo,
                    tipo=tipo,
                    agente_nome=agente_nome,
                    squad_nome=squad_nome,
                    usuario_id=usuario_id,
                    usuario_nome=usuario_nome,
                    detalhes=detalhes,
                    criado_em=datetime.utcnow(),
                )
                db.add(registro)
                db.commit()

                logger.debug(
                    f"[USAGE] {provider_id}: {tokens_total} tokens, "
                    f"${custo:.4f}, tipo={tipo}, agente={agente_nome}"
                )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"[USAGE] Erro ao registrar: {e}")

    def _calcular_custo(self, provider_id: str, tokens_in: int, tokens_out: int,
                         modelo: str = "") -> float:
        """Calcula custo baseado no modelo (mais preciso) ou no provider (fallback)."""
        # Primeiro tenta custo por modelo (mais preciso)
        if modelo and modelo in CUSTOS_POR_MODELO:
            custos = CUSTOS_POR_MODELO[modelo]
            return (tokens_in / 1000) * custos["input"] + (tokens_out / 1000) * custos["output"]

        # Fallback: custo por provider
        custos = CUSTOS.get(provider_id, {})
        if "input" in custos and "output" in custos:
            return (tokens_in / 1000) * custos["input"] + (tokens_out / 1000) * custos["output"]
        elif "por_request" in custos:
            return custos["por_request"]
        elif "por_minuto" in custos:
            return custos["por_minuto"] * 5
        return 0.0

    def _nome_provider(self, provider_id: str) -> str:
        """Retorna nome amigável do provider."""
        nomes = {
            "anthropic": "Anthropic (Claude)",
            "openai": "OpenAI",
            "groq": "Groq (Llama)",
            "fireworks": "Fireworks (Llama)",
            "together": "Together.ai (Llama)",
            "tavily": "Tavily",
            "exa": "EXA",
            "firecrawl": "Firecrawl",
            "scrapingdog": "ScrapingDog",
            "langsmith": "LangSmith",
            "composio": "Composio",
            "e2b": "E2B (Sandbox)",
            "aws_ses": "Amazon SES (Email)",
            "livekit": "LiveKit (Video/Áudio)",
        }
        return nomes.get(provider_id, provider_id)


# Instância global — usar em todo o projeto
tracker = UsageTracker()
