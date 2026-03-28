"""
Rotas: Dashboard de Consumo de APIs — dados reais do banco SQLite

GET /api/consumo         — Dados agregados de consumo real por API e período
GET /api/consumo/limites — Limites e saldos configurados

Fonte de dados: tabela usage_tracking (nunca reseta, registra cada chamada)
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.models import UsuarioDB, UsageTrackingDB
from database.session import get_db

logger = logging.getLogger("synerium.consumo")

router = APIRouter(prefix="/api", tags=["Consumo"])

# Configuração dos 15 providers monitorados
APIS_MONITORADAS = [
    {"id": "anthropic", "nome": "Anthropic (Claude)", "icone": "🧠", "cor": "#d97706",
     "modelo": "claude-sonnet-4-20250514", "plano": "Team (Pay-as-you-go)"},
    {"id": "openai", "nome": "OpenAI (GPT-4o)", "icone": "🤖", "cor": "#10b981",
     "modelo": "gpt-4o", "plano": "Pay-as-you-go"},
    {"id": "gemini", "nome": "Google Gemini", "icone": "💎", "cor": "#4285f4",
     "modelo": "gemini-2.0-flash", "plano": "Free tier (1.5M tokens/dia)"},
    {"id": "langsmith", "nome": "LangSmith", "icone": "🔍", "cor": "#3b82f6",
     "plano": "Gratuito (5k traces/mês)"},
    {"id": "tavily", "nome": "Tavily", "icone": "🌐", "cor": "#8b5cf6",
     "plano": "Developer (1k buscas/mês)"},
    {"id": "exa", "nome": "EXA", "icone": "🔎", "cor": "#ec4899",
     "plano": "Free tier"},
    {"id": "firecrawl", "nome": "Firecrawl", "icone": "🔥", "cor": "#ef4444",
     "plano": "Free (500 créditos/mês)"},
    {"id": "scrapingdog", "nome": "ScrapingDog", "icone": "🐕", "cor": "#14b8a6",
     "plano": "Free (1000 créditos)"},
    {"id": "composio", "nome": "Composio", "icone": "🔗", "cor": "#6366f1",
     "plano": "Gratuito"},
    {"id": "groq", "nome": "Groq (Llama)", "icone": "⚡", "cor": "#f97316",
     "modelo": "llama-3.3-70b-versatile", "plano": "Free tier (30 req/min)"},
    {"id": "fireworks", "nome": "Fireworks (Llama)", "icone": "🎆", "cor": "#f43f5e",
     "modelo": "llama-v3p3-70b-instruct", "plano": "Pay-as-you-go"},
    {"id": "together", "nome": "Together.ai (Llama)", "icone": "🤝", "cor": "#a855f7",
     "modelo": "Llama-3.3-70B-Instruct-Turbo", "plano": "Pay-as-you-go"},
    {"id": "livekit", "nome": "LiveKit (Video/Áudio)", "icone": "📹", "cor": "#06b6d4",
     "modelo": "Cloud", "plano": "Free tier (100 participantes)"},
    {"id": "e2b", "nome": "E2B (Sandbox)", "icone": "☁️", "cor": "#0ea5e9",
     "modelo": "Cloud Sandbox", "plano": "Free tier"},
    {"id": "aws_ses", "nome": "Amazon SES (Email)", "icone": "📧", "cor": "#f59e0b",
     "modelo": "us-east-1", "plano": "Pay-as-you-go ($0.10/1000 emails)"},
]


@router.get("/consumo")
def obter_consumo(
    periodo: int = Query(default=30, description="Período em dias"),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna dados agregados de consumo REAL das APIs (do banco SQLite)."""
    data_limite = datetime.utcnow() - timedelta(days=periodo)

    # Agregar por provider
    resultados_por_api = db.query(
        UsageTrackingDB.provider_id,
        func.sum(UsageTrackingDB.requests).label("requests"),
        func.sum(UsageTrackingDB.tokens_input).label("tokens_input"),
        func.sum(UsageTrackingDB.tokens_output).label("tokens_output"),
        func.sum(UsageTrackingDB.tokens_total).label("tokens_total"),
        func.sum(UsageTrackingDB.custo_usd).label("custo"),
    ).filter(
        UsageTrackingDB.criado_em >= data_limite
    ).group_by(
        UsageTrackingDB.provider_id
    ).all()

    # Montar dict de resultados
    dados_por_api = {}
    for r in resultados_por_api:
        dados_por_api[r.provider_id] = {
            "requests": int(r.requests or 0),
            "tokens_input": int(r.tokens_input or 0),
            "tokens_output": int(r.tokens_output or 0),
            "tokens_total": int(r.tokens_total or 0),
            "custo_estimado": float(r.custo or 0),
        }

    # Agregar por dia
    resultados_por_dia = db.query(
        func.date(UsageTrackingDB.criado_em).label("data"),
        func.sum(UsageTrackingDB.requests).label("requests"),
        func.sum(UsageTrackingDB.tokens_total).label("tokens"),
        func.sum(UsageTrackingDB.custo_usd).label("custo"),
    ).filter(
        UsageTrackingDB.criado_em >= data_limite
    ).group_by(
        func.date(UsageTrackingDB.criado_em)
    ).order_by(
        func.date(UsageTrackingDB.criado_em)
    ).all()

    historico_diario = [
        {
            "data": str(r.data),
            "total_requests": int(r.requests or 0),
            "total_tokens": int(r.tokens or 0),
            "custo_total": round(float(r.custo or 0), 4),
        }
        for r in resultados_por_dia
    ]

    # Total geral
    total_registros = db.query(func.count(UsageTrackingDB.id)).filter(
        UsageTrackingDB.criado_em >= data_limite
    ).scalar() or 0

    # Montar resposta com todos os 14 providers (mesmo os com 0)
    custo_total = sum(d["custo_estimado"] for d in dados_por_api.values())
    total_requests = sum(d["requests"] for d in dados_por_api.values())
    total_tokens = sum(d["tokens_total"] for d in dados_por_api.values())

    apis_detalhadas = []
    for api_cfg in APIS_MONITORADAS:
        dados = dados_por_api.get(api_cfg["id"], {
            "requests": 0, "tokens_input": 0, "tokens_output": 0,
            "tokens_total": 0, "custo_estimado": 0.0,
        })
        percentual = round((dados["custo_estimado"] / custo_total * 100) if custo_total > 0 else 0, 1)
        apis_detalhadas.append({
            **api_cfg,
            **dados,
            "percentual_custo": percentual,
        })

    orcamento = 50.0
    return {
        "periodo_dias": periodo,
        "custo_total": round(custo_total, 4),
        "custo_total_brl": round(custo_total * 5.10, 2),
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_registros": total_registros,
        "apis": apis_detalhadas,
        "historico_diario": historico_diario,
        "orcamento_mensal_usd": orcamento,
        "orcamento_restante_usd": round(orcamento - custo_total, 2),
        "percentual_orcamento": round((custo_total / orcamento * 100) if custo_total > 0 else 0, 1),
        "atualizado_em": datetime.now().isoformat(),
        "fonte": "banco_sqlite_real",
    }


@router.get("/consumo/limites")
def obter_limites(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna limites e saldos das APIs."""
    return {
        "apis": [
            {**api, "saldo": "Ativo"}
            for api in APIS_MONITORADAS
        ],
        "orcamento_mensal_usd": 50.0,
        "limite_gasto_ia_sem_aprovacao": 50.0,
    }


@router.get("/consumo/por-agente")
def consumo_por_agente(
    periodo: int = Query(default=30),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Consumo agrupado por agente — quem está gastando mais."""
    data_limite = datetime.utcnow() - timedelta(days=periodo)

    resultados = db.query(
        UsageTrackingDB.agente_nome,
        UsageTrackingDB.squad_nome,
        func.sum(UsageTrackingDB.requests).label("requests"),
        func.sum(UsageTrackingDB.tokens_total).label("tokens"),
        func.sum(UsageTrackingDB.custo_usd).label("custo"),
    ).filter(
        UsageTrackingDB.criado_em >= data_limite,
        UsageTrackingDB.agente_nome != "",
    ).group_by(
        UsageTrackingDB.agente_nome,
        UsageTrackingDB.squad_nome,
    ).order_by(
        func.sum(UsageTrackingDB.custo_usd).desc()
    ).limit(20).all()

    return [
        {
            "agente": r.agente_nome,
            "squad": r.squad_nome,
            "requests": int(r.requests or 0),
            "tokens": int(r.tokens or 0),
            "custo_usd": round(float(r.custo or 0), 4),
        }
        for r in resultados
    ]


@router.get("/consumo/por-tipo")
def consumo_por_tipo(
    periodo: int = Query(default=30),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Consumo agrupado por tipo de operação (chat, reuniao, rag, etc.)."""
    data_limite = datetime.utcnow() - timedelta(days=periodo)

    resultados = db.query(
        UsageTrackingDB.tipo,
        func.sum(UsageTrackingDB.requests).label("requests"),
        func.sum(UsageTrackingDB.tokens_total).label("tokens"),
        func.sum(UsageTrackingDB.custo_usd).label("custo"),
    ).filter(
        UsageTrackingDB.criado_em >= data_limite,
    ).group_by(
        UsageTrackingDB.tipo,
    ).order_by(
        func.sum(UsageTrackingDB.custo_usd).desc()
    ).all()

    return [
        {
            "tipo": r.tipo,
            "requests": int(r.requests or 0),
            "tokens": int(r.tokens or 0),
            "custo_usd": round(float(r.custo or 0), 4),
        }
        for r in resultados
    ]
