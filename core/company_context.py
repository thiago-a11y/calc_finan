"""
Company Context Total — Construtor de contexto rico para o agente IA do Code Studio.

Monta contexto em 3 niveis:
- minimal: apenas nome + stack do projeto (comportamento atual)
- standard: detalhes profundos do projeto (membros, regras, VCS, fase)
- full: standard + visao empresa + lista projetos + RAG semantico

O contexto e injetado no system prompt do LLM para que o agente
tenha conhecimento completo da empresa e dos projetos.
"""

import logging
import threading

from sqlalchemy.orm import Session

from database.models import ProjetoDB, ProjetoVCSDB

logger = logging.getLogger("synerium.company_context")

# Niveis validos de contexto
NIVEIS_VALIDOS = {"minimal", "standard", "full"}

# ============================================================
# Cache thread-safe com TTLCache (cachetools)
# ============================================================

try:
    from cachetools import TTLCache
except ImportError:
    # Fallback minimo se cachetools nao estiver instalado
    TTLCache = None

_cache_lock = threading.Lock()
_cache_projetos: "TTLCache | dict" = TTLCache(maxsize=8, ttl=300) if TTLCache else {}


# Resumo estatico da empresa (derivado de CONTEXTO-SYNERIUM-FACTORY.md)
# Otimizado: sem redundancias, compacto, maximo de informacao por char
_CONTEXTO_EMPRESA = """## Empresa: Objetiva Solucao Empresarial (Ipatinga/MG)
- CEO: Thiago Xavier | Diretor Tecnico: Jonatas (aprovacao final)
- 45 funcionarios, cada um com squad de agentes IA
- Objetivo: eficiencia 10x, zero contratacao operacional
- Produtos: SyneriumX (CRM, PHP+React+MySQL), DiamondOne (SAP B1), FinancialOne (credito/captacao), Softwares industriais, Synerium Factory (fabrica de SaaS com agentes IA)

## Padroes Obrigatorios
- Codigo em portugues brasileiro (comentarios, variaveis)
- Multi-tenant (company_id em todas tabelas)
- LGPD: audit log em operacoes criticas
- Approval Gates: deploy, gastos IA, arquitetura → aprovacao humana
- Stack: Python 3.13 + FastAPI | React 18 + TypeScript + Tailwind | SQLite + SQLAlchemy"""


class CompanyContextBuilder:
    """Constroi contexto rico da empresa para o agente IA do Code Studio."""

    def __init__(self, db: Session):
        self.db = db

    def construir(
        self,
        instrucao: str,
        conteudo_arquivo: str,
        projeto: ProjetoDB | None,
        nivel: str = "standard",
        max_chars: int = 6000,
    ) -> str:
        """
        Monta o contexto completo baseado no nivel solicitado.

        Args:
            instrucao: Instrucao do usuario (para busca RAG).
            conteudo_arquivo: Conteudo do arquivo sendo analisado.
            projeto: Projeto atual selecionado no Code Studio.
            nivel: minimal | standard | full.
            max_chars: Budget maximo de caracteres para o contexto.

        Returns:
            Texto formatado para injecao no system prompt.
        """
        if nivel not in NIVEIS_VALIDOS:
            nivel = "standard"

        if nivel == "minimal":
            return ""

        partes: list[str] = []
        partes.append("=== CONTEXTO DA EMPRESA E PROJETO (use para sugestoes assertivas) ===")

        # Standard: contexto profundo do projeto atual
        if projeto:
            ctx_projeto = self._contexto_projeto_atual(projeto)
            if ctx_projeto:
                partes.append(ctx_projeto)

        # Full: empresa + todos projetos + RAG
        if nivel == "full":
            partes.append(_CONTEXTO_EMPRESA)
            partes.append(self._contexto_projetos())

            # RAG semantico — buscar documentos relevantes
            ctx_rag = self._contexto_rag(instrucao, conteudo_arquivo, projeto)
            if ctx_rag:
                partes.append(ctx_rag)

        partes.append("=== FIM DO CONTEXTO ===")

        resultado = "\n\n".join(filter(None, partes))
        return self._truncar(resultado, max_chars)

    def _contexto_projetos(self) -> str:
        """Lista todos os projetos ativos do banco. Cache TTL 5 minutos (thread-safe)."""
        cache_key = "projetos_lista"

        with _cache_lock:
            cached = _cache_projetos.get(cache_key)
            if cached:
                return cached

        try:
            projetos = self.db.query(ProjetoDB).filter_by(ativo=True).all()
            if not projetos:
                return ""

            linhas = ["## Projetos"]
            for p in projetos:
                owner = p.proprietario_nome or "?"
                fase = p.fase_atual or "em andamento"
                linhas.append(f"- {p.nome}: {p.stack or '?'} | {fase} | {owner}")

            resultado = "\n".join(linhas)

            with _cache_lock:
                _cache_projetos[cache_key] = resultado

            return resultado
        except Exception as e:
            logger.warning(f"[CompanyContext] Erro ao listar projetos: {e}")
            return ""

    def _contexto_projeto_atual(self, projeto: ProjetoDB) -> str:
        """Detalhes profundos do projeto selecionado."""
        try:
            linhas = [f"## Projeto Atual: {projeto.nome}"]

            if projeto.descricao:
                linhas.append(f"Descricao: {projeto.descricao[:300]}")
            if projeto.stack:
                linhas.append(f"Stack: {projeto.stack}")
            if projeto.fase_atual:
                linhas.append(f"Fase: {projeto.fase_atual}")
            if projeto.proprietario_nome:
                linhas.append(f"Proprietario: {projeto.proprietario_nome}")
            if projeto.lider_tecnico_nome:
                linhas.append(f"Lider Tecnico: {projeto.lider_tecnico_nome}")

            # Membros
            membros = projeto.membros or []
            if membros:
                nomes = [f"{m.get('nome', '?')} ({m.get('papel', 'membro')})" for m in membros[:10]]
                linhas.append(f"Membros: {', '.join(nomes)}")

            # Regras de aprovacao
            regras = projeto.regras_aprovacao
            if regras:
                regras_resumo = []
                for tipo, regra in regras.items():
                    aprovador = regra.get("aprovador", "?") if isinstance(regra, dict) else str(regra)
                    regras_resumo.append(f"{tipo}→{aprovador}")
                linhas.append(f"Aprovacao: {' | '.join(regras_resumo)}")

            # VCS
            try:
                vcs = self.db.query(ProjetoVCSDB).filter_by(
                    projeto_id=projeto.id, ativo=True
                ).first()
                if vcs:
                    linhas.append(f"Repo: {vcs.repo_url} ({vcs.branch_padrao or 'main'})")
            except Exception:
                pass

            return "\n".join(linhas)
        except Exception as e:
            logger.warning(f"[CompanyContext] Erro contexto projeto: {e}")
            return ""

    def _contexto_rag(
        self, instrucao: str, conteudo_arquivo: str, projeto: ProjetoDB | None
    ) -> str:
        """
        Busca semantica no RAG (ChromaDB) por documentos relevantes.
        Usa singleton para embeddings/store (evita re-instanciacao por request).
        """
        try:
            store, rag_query = _obter_rag_singleton()

            # Construir pergunta combinada (compacta)
            trecho = conteudo_arquivo[:400] if conteudo_arquivo else ""
            pergunta = f"{instrucao}\n\n{trecho}"

            # Filtrar vault por projeto
            vaults = None
            if projeto:
                nome_lower = (projeto.nome or "").lower()
                if "syneriumx" in nome_lower or "propostasap" in nome_lower:
                    vaults = ["syneriumx"]
                elif "factory" in nome_lower or "synerium factory" in nome_lower:
                    vaults = ["factory"]

            resultado = rag_query.consultar(pergunta=pergunta, vaults=vaults, k=3)

            if "Nenhum resultado" in resultado:
                return ""

            return f"## Documentacao Relevante (RAG)\n{resultado}"

        except Exception as e:
            logger.warning(f"[CompanyContext] RAG nao disponivel: {e}")
            return ""

    def _truncar(self, texto: str, max_chars: int) -> str:
        """Trunca o texto para respeitar o budget de tokens."""
        if len(texto) <= max_chars:
            return texto
        truncado = texto[:max_chars]
        ultima_quebra = truncado.rfind("\n")
        if ultima_quebra > max_chars * 0.7:
            truncado = truncado[:ultima_quebra]
        return truncado + "\n[... contexto truncado ...]"


# ============================================================
# Singleton para RAG (evita re-instanciacao de embeddings por request)
# ============================================================

_rag_store = None
_rag_query = None
_rag_lock = threading.Lock()


def _obter_rag_singleton():
    """Retorna singleton de RAGStore + RAGQuery (thread-safe)."""
    global _rag_store, _rag_query

    if _rag_query is not None:
        return _rag_store, _rag_query

    with _rag_lock:
        # Double-check locking
        if _rag_query is not None:
            return _rag_store, _rag_query

        from rag.embeddings import criar_embeddings
        from rag.store import RAGStore
        from rag.query import RAGQuery

        embeddings = criar_embeddings()
        _rag_store = RAGStore("data/chromadb", embeddings)
        _rag_query = RAGQuery(_rag_store, company_id="synerium")

        logger.info("[CompanyContext] RAG singleton inicializado")
        return _rag_store, _rag_query
