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
import time

from sqlalchemy.orm import Session

from database.models import ProjetoDB, ProjetoVCSDB

logger = logging.getLogger("synerium.company_context")

# Niveis validos de contexto
NIVEIS_VALIDOS = {"minimal", "standard", "full"}

# Cache em nivel de modulo (compartilhado entre requests)
_cache_empresa: str = ""
_cache_projetos: str = ""
_cache_projetos_ts: float = 0
_CACHE_TTL = 300  # 5 minutos

# Resumo estatico da empresa (derivado de CONTEXTO-SYNERIUM-FACTORY.md)
_CONTEXTO_EMPRESA_FIXO = """## Empresa: Objetiva Solucao Empresarial
- Localizacao: Ipatinga, MG
- CEO: Thiago Xavier (thiago@objetivasolucao.com.br)
- Diretor Tecnico / Operations Lead: Jonatas (jonatas@objetivasolucao.com.br) — aprovacao final em tudo critico
- 45 funcionarios, cada um com squad de agentes IA
- Objetivo: eficiencia multiplicada por 10x, zero contratacao operacional

## Produtos
- SyneriumX: CRM completo (PHP 7.4 + React 18 + MySQL)
- DiamondOne: Add-on industrial para SAP B1
- FinancialOne: Modulo financeiro (credito, captacao, endividamento)
- Softwares industriais: producao, qualidade, custeio, manutencao
- Synerium Factory: Fabrica de SaaS impulsionada por agentes IA

## Padroes Obrigatorios
- Todo codigo em portugues brasileiro (comentarios, variaveis descritivas)
- Multi-tenant desde o inicio (company_id em todas tabelas)
- LGPD: audit log em todas operacoes criticas
- Approval Gates: deploy, gastos IA, mudancas de arquitetura precisam de aprovacao humana
- Stack padrao: Python 3.13 + FastAPI (backend) | React 18 + TypeScript + Tailwind (frontend) | SQLite + SQLAlchemy (banco)"""


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
        max_chars: int = 4000,
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
        partes.append("=== CONTEXTO DA EMPRESA E PROJETO (use para dar sugestoes assertivas) ===")

        # Standard: contexto profundo do projeto atual
        if projeto:
            ctx_projeto = self._contexto_projeto_atual(projeto)
            if ctx_projeto:
                partes.append(ctx_projeto)

        # Full: empresa + todos projetos + RAG
        if nivel == "full":
            partes.append(self._contexto_empresa())
            partes.append(self._contexto_projetos())

            # RAG semantico — buscar documentos relevantes
            ctx_rag = self._contexto_rag(instrucao, conteudo_arquivo, projeto)
            if ctx_rag:
                partes.append(ctx_rag)

        partes.append("=== FIM DO CONTEXTO ===")

        resultado = "\n\n".join(filter(None, partes))
        return self._truncar(resultado, max_chars)

    def _contexto_empresa(self) -> str:
        """Retorna resumo estatico da empresa (cache em modulo)."""
        global _cache_empresa
        if not _cache_empresa:
            _cache_empresa = _CONTEXTO_EMPRESA_FIXO
        return _cache_empresa

    def _contexto_projetos(self) -> str:
        """Lista todos os projetos ativos do banco. Cache por 5 minutos."""
        global _cache_projetos, _cache_projetos_ts

        agora = time.time()
        if _cache_projetos and (agora - _cache_projetos_ts) < _CACHE_TTL:
            return _cache_projetos

        try:
            projetos = self.db.query(ProjetoDB).filter_by(ativo=True).all()
            if not projetos:
                return ""

            linhas = ["## Projetos da Empresa"]
            for p in projetos:
                owner = p.proprietario_nome or "nao definido"
                fase = p.fase_atual or "em andamento"
                linhas.append(f"- {p.nome}: {p.stack or 'stack nao definida'} | Fase: {fase} | Proprietario: {owner}")

            _cache_projetos = "\n".join(linhas)
            _cache_projetos_ts = agora
            return _cache_projetos
        except Exception as e:
            logger.warning(f"[CompanyContext] Erro ao listar projetos: {e}")
            return ""

    def _contexto_projeto_atual(self, projeto: ProjetoDB) -> str:
        """Detalhes profundos do projeto selecionado."""
        try:
            linhas = [f"## Projeto Atual: {projeto.nome}"]

            if projeto.descricao:
                linhas.append(f"Descricao: {projeto.descricao[:200]}")
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
                linhas.append("Regras de aprovacao:")
                for tipo, regra in regras.items():
                    aprovador = regra.get("aprovador", "?") if isinstance(regra, dict) else str(regra)
                    desc = regra.get("descricao", "") if isinstance(regra, dict) else ""
                    linhas.append(f"  - {tipo}: {aprovador} ({desc})")

            # VCS
            try:
                vcs = self.db.query(ProjetoVCSDB).filter_by(
                    projeto_id=projeto.id, ativo=True
                ).first()
                if vcs:
                    linhas.append(f"Repositorio: {vcs.repo_url} (branch: {vcs.branch_padrao or 'main'})")
            except Exception:
                pass

            return "\n".join(linhas)
        except Exception as e:
            logger.warning(f"[CompanyContext] Erro ao montar contexto do projeto: {e}")
            return ""

    def _contexto_rag(
        self, instrucao: str, conteudo_arquivo: str, projeto: ProjetoDB | None
    ) -> str:
        """
        Busca semantica no RAG (ChromaDB) por documentos relevantes.

        Usa a instrucao do usuario + trecho do arquivo para encontrar
        documentacao, decisoes tecnicas e padroes relacionados.
        """
        try:
            from rag.embeddings import criar_embeddings
            from rag.store import RAGStore
            from rag.query import RAGQuery

            # Inicializar RAG (reutiliza ChromaDB existente em data/chromadb)
            embeddings = criar_embeddings()
            store = RAGStore("data/chromadb", embeddings)
            rag_query = RAGQuery(store, company_id="synerium")

            # Construir pergunta combinada
            trecho = conteudo_arquivo[:500] if conteudo_arquivo else ""
            pergunta = f"{instrucao}\n\nTrecho do codigo:\n{trecho}"

            # Filtrar vault por projeto
            vaults = None  # todos
            if projeto:
                nome_lower = (projeto.nome or "").lower()
                if "syneriumx" in nome_lower or "propostasap" in nome_lower:
                    vaults = ["syneriumx"]
                elif "factory" in nome_lower or "synerium factory" in nome_lower:
                    vaults = ["factory"]

            # Buscar top 3 chunks mais relevantes
            resultado = rag_query.consultar(
                pergunta=pergunta,
                vaults=vaults,
                k=3,
            )

            # Verificar se retornou algo util
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
        # Truncar preservando linhas completas
        truncado = texto[:max_chars]
        ultima_quebra = truncado.rfind("\n")
        if ultima_quebra > max_chars * 0.7:
            truncado = truncado[:ultima_quebra]
        return truncado + "\n[... contexto truncado por limite de tokens ...]"
