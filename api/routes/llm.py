"""
Rotas: Gestão de LLM Providers + Smart Router

GET  /api/llm/status          — Status de todos os providers
GET  /api/llm/router/status   — Status do Smart Router Sonnet/Opus
POST /api/llm/router/decidir  — Simular decisão do router (para debug/teste)
POST /api/llm/router/toggle   — Ativar/desativar Smart Router
POST /api/llm/provider-padrao — Trocar provider padrão
POST /api/llm/ativar          — Ativar/desativar provider
POST /api/llm/testar          — Testar um provider com prompt simples
"""

import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencias import obter_usuario_atual
from config.llm_providers import llm_manager, ProviderID
from core.llm_router import smart_router
from core.smart_router_global import router_global
from database.models import UsuarioDB

logger = logging.getLogger("synerium.llm.api")

router = APIRouter(prefix="/api/llm", tags=["LLM Providers"])


@router.get("/status")
def status_providers(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna status de todos os providers + Smart Router."""
    status = llm_manager.obter_status()
    return {
        "provider_padrao": llm_manager.provider_padrao.value,
        "providers": [s.model_dump() for s in status],
        "total_providers": len(status),
        "providers_ativos": sum(1 for s in status if s.ativo and s.configurado),
        "smart_router": smart_router.obter_status(),
    }


# =====================================================================
# Smart Router — Endpoints
# =====================================================================

@router.get("/router/status")
def status_router(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna status completo do Smart Router Sonnet/Opus."""
    return smart_router.obter_status()


class DecidirRouterRequest(BaseModel):
    prompt: str = "Analise a arquitetura do sistema"
    perfil_agente: str | None = None
    forcar: str | None = None


@router.post("/router/decidir")
def simular_decisao_router(
    req: DecidirRouterRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Simula uma decisão do Smart Router sem executar (para debug/teste)."""
    tier, motivo = smart_router.decidir(
        prompt=req.prompt,
        perfil_agente=req.perfil_agente,
        forcar=req.forcar,
    )
    from core.llm_router import MODELOS_CLAUDE, ModeloClaudeTier
    config = MODELOS_CLAUDE[tier]
    tokens_estimados = len(req.prompt) // 4

    return {
        "modelo_escolhido": tier.value,
        "modelo_id": config["modelo"],
        "nome": config["nome"],
        "motivo": motivo,
        "custo_por_1k_input": config["custo_por_1k_input"],
        "custo_por_1k_output": config["custo_por_1k_output"],
        "tokens_estimados": tokens_estimados,
        "perfil_agente": req.perfil_agente,
        "prompt_preview": req.prompt[:100] + ("..." if len(req.prompt) > 100 else ""),
    }


class ToggleRouterRequest(BaseModel):
    ativo: bool


@router.post("/router/toggle")
def toggle_router(
    req: ToggleRouterRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Ativa ou desativa o Smart Router. Desativado = sempre Sonnet."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode alterar o router.")

    if req.ativo:
        smart_router.ativar()
    else:
        smart_router.desativar()

    return {
        "ativo": smart_router._ativo,
        "mensagem": "Smart Router ativado" if req.ativo else "Smart Router desativado (sempre Sonnet)",
    }


class TrocarProviderRequest(BaseModel):
    provider_id: str


@router.post("/provider-padrao")
def trocar_provider_padrao(
    req: TrocarProviderRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Troca o provider padrão de LLM."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode trocar o provider.")

    ok = llm_manager.definir_provider_padrao(req.provider_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Provider '{req.provider_id}' não encontrado.")

    logger.info(f"[LLM] Provider padrão trocado para {req.provider_id} por {usuario.nome}")
    return {"mensagem": f"Provider padrão alterado para {req.provider_id}", "provider_padrao": req.provider_id}


class AtivarProviderRequest(BaseModel):
    provider_id: str
    ativo: bool


@router.post("/ativar")
def ativar_provider(
    req: AtivarProviderRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Ativa ou desativa um provider."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode alterar providers.")

    ok = llm_manager.ativar_desativar(req.provider_id, req.ativo)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Provider '{req.provider_id}' não encontrado.")

    acao = "ativado" if req.ativo else "desativado"
    return {"mensagem": f"Provider {req.provider_id} {acao}"}


class TestarProviderRequest(BaseModel):
    provider_id: str
    prompt: str = "Diga 'Olá, eu sou o Llama!' em português brasileiro."


@router.post("/testar")
def testar_provider(
    req: TestarProviderRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Testa um provider com um prompt simples."""
    try:
        inicio = time.time()
        llm = llm_manager.obter_llm(provider=req.provider_id)

        # Testar chamada
        resposta = llm.call(messages=[{"role": "user", "content": req.prompt}])
        latencia = (time.time() - inicio) * 1000

        # Registrar uso
        llm_manager.registrar_uso(
            provider_id=req.provider_id,
            tokens=100,  # Estimativa
            latencia_ms=latencia,
        )

        return {
            "provider": req.provider_id,
            "modelo": llm_manager.providers[ProviderID(req.provider_id)].modelo,
            "resposta": str(resposta),
            "latencia_ms": round(latencia, 1),
            "status": "ok",
        }

    except Exception as e:
        llm_manager.registrar_uso(
            provider_id=req.provider_id,
            erro=str(e),
        )
        return {
            "provider": req.provider_id,
            "resposta": None,
            "erro": str(e),
            "status": "erro",
        }


# =====================================================================
# Smart Router GLOBAL — Endpoints
# =====================================================================

@router.get("/router-global/status")
def status_router_global(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    """Retorna status completo do Smart Router Global (multi-provider + ferramentas)."""
    return router_global.obter_status()


class RotearGlobalRequest(BaseModel):
    prompt: str = "Pesquise as últimas tendências de IA para ERP"
    perfil_agente: str | None = None
    forcar: str | None = None
    contexto: dict | None = None


@router.post("/router-global/rotear")
def simular_roteamento_global(
    req: RotearGlobalRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """
    Simula uma decisão do Smart Router Global (multi-provider + ferramentas).
    Útil para debug e para entender como o router decide.
    """
    resultado = router_global.rotear(
        prompt=req.prompt,
        perfil_agente=req.perfil_agente,
        forcar=req.forcar,
        contexto=req.contexto or {},
    )
    return resultado.to_dict()


@router.post("/router-global/toggle")
def toggle_router_global(
    req: ToggleRouterRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Ativa ou desativa o Smart Router Global."""
    papeis = usuario.papeis or []
    if not any(p in papeis for p in ["ceo", "diretor_tecnico", "operations_lead"]):
        raise HTTPException(status_code=403, detail="Apenas CEO/Diretor pode alterar o router.")

    if req.ativo:
        router_global.ativar()
    else:
        router_global.desativar()

    return {
        "ativo": router_global._ativo,
        "mensagem": "Router Global ativado" if req.ativo else "Router Global desativado",
    }
