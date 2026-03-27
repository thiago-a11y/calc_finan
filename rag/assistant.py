"""
RAG Assistant — Síntese de respostas com Claude.

Recebe chunks recuperados da busca semântica e usa o Claude
para gerar uma resposta inteligente em português brasileiro.

Integra com LangSmith para tracing de cada consulta.
"""

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from config.settings import settings
from rag.store import RAGStore

logger = logging.getLogger("synerium.rag.assistant")

# Prompt do sistema para o assistente RAG
SYSTEM_PROMPT = """Você é o assistente de conhecimento do Synerium Factory — uma fábrica de SaaS da Objetiva Solução impulsionada por agentes IA.

Sua função é responder perguntas usando EXCLUSIVAMENTE o contexto fornecido abaixo. Siga estas regras:

1. Responda SEMPRE em português brasileiro
2. Seja direto, claro e objetivo
3. Se o contexto não contiver informação suficiente para responder, diga claramente: "Não encontrei informação suficiente na base de conhecimento para responder esta pergunta."
4. Cite a fonte quando possível (vault e arquivo)
5. Formate a resposta de forma legível com parágrafos e listas quando apropriado
6. Não invente informações — use apenas o que está no contexto"""


class RAGAssistant:
    """
    Assistente que combina busca semântica com síntese via Claude.

    Fluxo:
        1. Recebe a pergunta do usuário
        2. Busca chunks relevantes no ChromaDB
        3. Monta prompt com contexto
        4. Claude gera resposta em português
    """

    def __init__(self, store: RAGStore, company_id: str):
        """
        Inicializa o assistente RAG.

        Args:
            store: Instância do RAGStore (ChromaDB).
            company_id: Identificador do tenant.
        """
        self.store = store
        self.company_id = company_id
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=settings.anthropic_api_key,
            max_tokens=2048,
            temperature=0.1,
        )
        logger.info("[RAG ASSISTANT] Inicializado com Claude claude-sonnet-4-20250514.")

    @traceable(name="rag_assistant_consultar")
    def consultar(
        self,
        pergunta: str,
        vaults: list[str] | None = None,
        k: int = 5,
    ) -> dict:
        """
        Consulta a base de conhecimento e retorna resposta sintetizada.

        Args:
            pergunta: Texto da pergunta.
            vaults: Lista de vaults para filtrar. None = todos.
            k: Quantidade máxima de chunks a recuperar.

        Returns:
            Dict com:
                - resposta_ia: Resposta sintetizada pelo Claude
                - chunks: Lista de chunks recuperados (para debug)
                - total_chunks: Quantidade de chunks encontrados
        """
        logger.info(f"[RAG ASSISTANT] Pergunta: '{pergunta[:80]}...'")

        # 1. Buscar chunks relevantes
        documentos = self.store.consultar(
            company_id=self.company_id,
            pergunta=pergunta,
            vaults=vaults,
            k=k,
        )

        if not documentos:
            logger.info("[RAG ASSISTANT] Nenhum chunk encontrado.")
            return {
                "resposta_ia": (
                    "Não encontrei resultados na base de conhecimento para esta pergunta. "
                    "Verifique se os vaults foram indexados."
                ),
                "chunks": [],
                "total_chunks": 0,
            }

        # 2. Montar contexto formatado
        contexto = self._formatar_contexto(documentos)

        # 3. Gerar resposta com Claude
        resposta = self._gerar_resposta(pergunta, contexto)

        # 4. Extrair chunks para retorno
        chunks = self._extrair_chunks(documentos)

        logger.info(f"[RAG ASSISTANT] Resposta gerada com {len(documentos)} chunk(s).")

        return {
            "resposta_ia": resposta,
            "chunks": chunks,
            "total_chunks": len(documentos),
        }

    @traceable(name="rag_assistant_gerar_resposta")
    def _gerar_resposta(self, pergunta: str, contexto: str) -> str:
        """Gera resposta sintetizada usando Claude com o contexto recuperado."""
        mensagens = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"## Contexto da Base de Conhecimento\n\n"
                f"{contexto}\n\n"
                f"---\n\n"
                f"## Pergunta\n\n"
                f"{pergunta}"
            )),
        ]

        try:
            resposta = self.llm.invoke(mensagens)
            return resposta.content
        except Exception as e:
            logger.error(f"[RAG ASSISTANT] Erro ao gerar resposta: {e}")
            return (
                f"Erro ao gerar resposta com IA: {str(e)}. "
                "Os chunks foram recuperados com sucesso — veja abaixo."
            )

    def _formatar_contexto(self, documentos: list[Document]) -> str:
        """Formata documentos em texto estruturado para o prompt."""
        partes: list[str] = []

        for i, doc in enumerate(documentos, 1):
            meta = doc.metadata
            vault = meta.get("vault", "desconhecido")
            arquivo = meta.get("source_path", meta.get("file_name", "?"))
            header_1 = meta.get("header_1", "")
            header_2 = meta.get("header_2", "")
            header_3 = meta.get("header_3", "")

            secoes = [s for s in [header_1, header_2, header_3] if s]
            secao_str = " > ".join(secoes) if secoes else "Documento completo"

            partes.append(
                f"### Trecho {i} (Vault: {vault} | Arquivo: {arquivo} | Seção: {secao_str})\n"
                f"{doc.page_content}\n"
            )

        return "\n".join(partes)

    def _extrair_chunks(self, documentos: list[Document]) -> list[dict]:
        """Extrai dados dos chunks para retorno na API."""
        chunks = []
        for doc in documentos:
            meta = doc.metadata
            chunks.append({
                "vault": meta.get("vault", ""),
                "arquivo": meta.get("source_path", meta.get("file_name", "")),
                "secao": " > ".join(
                    s for s in [
                        meta.get("header_1", ""),
                        meta.get("header_2", ""),
                        meta.get("header_3", ""),
                    ] if s
                ) or "Documento completo",
                "conteudo": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
            })
        return chunks
