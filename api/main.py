"""
Synerium Factory — API REST (FastAPI)

Servidor HTTP que expõe os dados da fábrica para o Dashboard Web.
Reutiliza as mesmas classes do orchestrator.py (SyneriumFactory,
ApprovalGate, RAGQuery, etc.)

Uso:
    python -m uvicorn api.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencias import inicializar_fabrica, inicializar_banco
from api.routes import status, squads, aprovacoes, rag, standup, usuarios, auth, convites, tarefas, skills, projetos, propostas, uploads, consumo, llm, deploy, videocall, catalogo, luna, code_studio, continuous_factory, mission_control, master_control

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/synerium.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("synerium.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan do FastAPI — inicializa o SyneriumFactory uma única vez.

    Tudo que está antes do 'yield' roda no startup.
    Tudo que está depois do 'yield' roda no shutdown.
    """
    logger.info("[API] Iniciando Synerium Factory API...")

    try:
        inicializar_banco()
        inicializar_fabrica()

        # Recovery: detectar e resetar workflows travados
        try:
            from api.routes.tarefas import recuperar_workflows_travados
            recuperar_workflows_travados()
        except Exception as re:
            logger.warning(f"[API] Recovery de workflows falhou: {re}")

        # Recovery: reiniciar Modo Continuo se estava ativo
        try:
            from api.routes.continuous_factory import recuperar_modo_continuo
            recuperar_modo_continuo()
        except Exception as ce:
            logger.warning(f"[API] Recovery do Modo Contínuo falhou: {ce}")

        # Kairos: iniciar AutoDream em background (consolidação de memórias)
        try:
            from core.memory.kairos.service import kairos_service
            kairos_service.iniciar_auto_dream()
            status_k = kairos_service.status()
            logger.info(
                f"[API] Kairos AutoDream ativado "
                f"(intervalo: {status_k['config']['dream_interval_min']}min, "
                f"snapshots pendentes: {status_k['snapshots_pendentes']})"
            )
        except Exception as ke:
            logger.warning(f"[API] Kairos AutoDream não iniciou: {ke}")

        logger.info("[API] API pronta para receber requisições.")
    except Exception as e:
        logger.error(f"[API] Erro ao inicializar: {e}")
        raise

    yield

    # Shutdown: parar AutoDream gracefully
    try:
        from core.memory.kairos.service import kairos_service
        kairos_service.parar_auto_dream()
        logger.info("[API] Kairos AutoDream parado.")
    except Exception:
        pass

    logger.info("[API] Encerrando Synerium Factory API.")


# --- App FastAPI ---

app = FastAPI(
    title="Synerium Factory API",
    description=(
        "API REST do Synerium Factory — Centro de Comando da fábrica de SaaS "
        "impulsionada por agentes IA. Expõe dados de squads, aprovações, "
        "RAG e standup diário para o Dashboard Web."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

# CORS — permitir o frontend React (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev
        "http://localhost:3000",    # Alternativo
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(status.router)
app.include_router(squads.router)
app.include_router(aprovacoes.router)
app.include_router(rag.router)
app.include_router(standup.router)
app.include_router(usuarios.router)
app.include_router(auth.router)
app.include_router(convites.router)
app.include_router(tarefas.router)
app.include_router(skills.router)
app.include_router(projetos.router)
app.include_router(propostas.router)
app.include_router(uploads.router)
app.include_router(consumo.router)
app.include_router(llm.router)
app.include_router(deploy.router)
app.include_router(videocall.router)
app.include_router(catalogo.router)
app.include_router(luna.router)
app.include_router(code_studio.router)
app.include_router(continuous_factory.router)
app.include_router(mission_control.router)
app.include_router(master_control.router)


@app.get("/", tags=["Root"])
def raiz():
    """Endpoint raiz — informações básicas da API."""
    return {
        "nome": "Synerium Factory API",
        "versao": "0.3.0",
        "descricao": "Centro de Comando da fábrica de SaaS",
        "docs": "/docs",
        "endpoints": [
            "GET  /api/status",
            "GET  /api/squads",
            "GET  /api/aprovacoes",
            "POST /api/aprovacoes",
            "POST /api/aprovacoes/{id}/acao",
            "GET  /api/rag/status",
            "POST /api/rag/consultar",
            "POST /api/standup",
            "GET  /api/usuarios",
            "GET  /api/usuarios/aprovadores",
            "GET  /api/usuarios/{id}",
            "POST /auth/login",
            "POST /auth/refresh",
            "POST /auth/registrar",
            "POST /api/convites",
            "GET  /api/convites/{token}",
        ],
    }
