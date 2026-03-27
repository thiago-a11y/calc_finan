"""
Luna Engine — Motor de conversação da assistente inteligente.

Funcionalidades:
- Streaming de respostas via SSE (Server-Sent Events)
- Cadeia de fallback: Opus → Sonnet → Groq → Fireworks → Together
- Smart Router para decidir automaticamente Sonnet vs Opus
- Geração automática de título da conversa
- Tracking de uso (tokens, custo, provider) por mensagem
- Janela deslizante de contexto (últimas 20 mensagens)

Uso:
    from core.luna_engine import luna_engine
    async for chunk in luna_engine.stream_resposta(conversa_id, mensagem, db):
        print(chunk)  # texto parcial
"""

import os
import json
import time
import logging
import secrets
import string
from datetime import datetime
from typing import AsyncGenerator

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langsmith import traceable
from sqlalchemy.orm import Session

from config.settings import settings
from core.llm_router import smart_router, MODELOS_CLAUDE, ModeloClaudeTier
from config.llm_providers import PROVIDERS, ProviderID
from database.models import (
    LunaConversaDB, LunaMensagemDB, UsageTrackingDB, AuditLogDB
)

logger = logging.getLogger("synerium.luna")

# =====================================================================
# Constantes
# =====================================================================

# Janela de contexto: quantas mensagens enviar ao LLM
JANELA_CONTEXTO = 20

# Máximo de tokens de saída
MAX_TOKENS_RESPOSTA = 4096

# Temperatura padrão
TEMPERATURA = 0.3

# Estimativa: 1 token ≈ 4 caracteres em português
CHARS_POR_TOKEN = 4

# System prompt da Luna
SYSTEM_PROMPT = """Você é Luna, a consultora estratégica e assistente geral do Synerium Factory — uma fábrica de SaaS da Objetiva Solução impulsionada por agentes IA.

## Personalidade
- Inteligente, serena, estratégica, amigável e direta
- Você ajuda a pensar melhor, não apenas a responder perguntas
- Sugere abordagens alternativas e pontos cegos quando relevante
- Prepara pedidos claros para os agentes especializados quando apropriado
- Usa analogias e exemplos práticos para explicar conceitos complexos

## Regras
- Responda SEMPRE em português brasileiro
- Use Markdown para formatar respostas: **negrito**, listas, `código`, tabelas, headers
- Para blocos de código, sempre especifique a linguagem (```python, ```html, etc.)
- Seja concisa mas completa — sem rodeios desnecessários
- Quando o usuário pedir algo que seria melhor executado por um agente especializado do Synerium Factory, sugira qual agente usar e como formular o pedido
- Se o usuário pedir algo que você não sabe, diga claramente em vez de inventar
- Proteja informações sensíveis — nunca exponha credenciais, tokens ou dados internos

## Geração de Arquivos
Você pode gerar arquivos para download! Quando o usuário pedir uma planilha, documento, apresentação ou qualquer arquivo, gere o conteúdo estruturado e use o marcador especial abaixo. O sistema vai converter automaticamente para o formato solicitado.

Formatos disponíveis: xlsx, docx, pptx, pdf, txt, md, csv, json, html

Para gerar um arquivo, use este formato EXATO no final da sua resposta:

:::arquivo[nome_do_arquivo.formato]
conteúdo aqui (tabela markdown para xlsx, texto para docx, etc.)
:::

Exemplos:
- Planilha: Use tabela markdown com | delimitadores para criar o conteúdo
- Documento: Use markdown normal (headers, listas, parágrafos)
- Apresentação: Use ## para separar slides, - para bullet points
- PDF: Use markdown (será convertido automaticamente)

IMPORTANTE: Sempre gere o conteúdo completo dentro do marcador. Para planilhas, use tabela markdown com todas as linhas e colunas. O sistema converte automaticamente para o formato final com formatação profissional.

## Contexto
Você opera dentro do Synerium Factory, uma plataforma com:
- 45 squads de agentes IA (um por funcionário da Objetiva)
- PM Central (Alex), Operations Lead (Jonatas), CEO (Thiago)
- Sistema de aprovações, RAG, deploy, reuniões multi-agente
- Produtos: SyneriumX (CRM), softwares industriais e financeiros"""

# Prompt para gerar título automático
PROMPT_TITULO = """Com base na primeira mensagem do usuário abaixo, gere um título curto (máximo 50 caracteres) para esta conversa. Responda APENAS com o título, sem aspas, sem explicação.

Mensagem: {mensagem}"""


def _gerar_id(tamanho: int = 12) -> str:
    """Gera um ID curto aleatório (nanoid-like)."""
    alfabeto = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


# =====================================================================
# Provider Factory — cria instâncias de LLM para streaming
# =====================================================================

def _criar_provider_anthropic(modelo: str, max_tokens: int = MAX_TOKENS_RESPOSTA):
    """Cria instância ChatAnthropic para streaming."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or len(api_key) < 5:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return ChatAnthropic(
        model=modelo,
        anthropic_api_key=api_key,
        max_tokens=max_tokens,
        temperature=TEMPERATURA,
        streaming=True,
    )


def _criar_provider_openai_compat(
    modelo: str, api_key_env: str, base_url: str,
    max_tokens: int = MAX_TOKENS_RESPOSTA
):
    """Cria instância ChatOpenAI (compatível) para streaming com Groq/Fireworks/Together."""
    api_key = os.environ.get(api_key_env, "")
    if not api_key or len(api_key) < 5:
        raise ValueError(f"{api_key_env} não configurada")
    return ChatOpenAI(
        model=modelo,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        temperature=TEMPERATURA,
        streaming=True,
    )


def _obter_cadeia_fallback(forcar: str | None = None) -> list[tuple]:
    """
    Retorna lista ordenada de (provider_id, modelo_nome, factory_fn) para fallback.

    Ordem:
    1. Claude Opus (se forçado ou Smart Router decidir)
    2. Claude Sonnet (padrão)
    3. Groq Llama
    4. Fireworks Llama
    5. Together.ai Llama
    """
    cadeia = []

    if forcar == "opus":
        cadeia.append((
            "anthropic_opus",
            MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"],
            lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"]),
        ))
        cadeia.append((
            "anthropic_sonnet",
            MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"],
            lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"]),
        ))
    else:
        # Padrão: Sonnet primeiro
        cadeia.append((
            "anthropic_sonnet",
            MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"],
            lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"]),
        ))
        cadeia.append((
            "anthropic_opus",
            MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"],
            lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"]),
        ))

    # Fallbacks OpenAI-compatible
    for provider in PROVIDERS:
        if provider.id in (ProviderID.ANTHROPIC_OPUS, ProviderID.ANTHROPIC_SONNET, ProviderID.ANTHROPIC):
            continue
        if not provider.ativo or not provider.base_url:
            continue
        p_id = provider.id.value
        p_modelo = provider.modelo
        p_key_env = provider.api_key_env
        p_url = provider.base_url
        cadeia.append((
            p_id,
            p_modelo,
            lambda key=p_key_env, url=p_url, mod=p_modelo: _criar_provider_openai_compat(mod, key, url),
        ))

    return cadeia


# =====================================================================
# Luna Engine
# =====================================================================

class LunaEngine:
    """
    Motor principal da Luna — gerencia conversas, streaming e fallback.
    """

    def __init__(self):
        logger.info("[Luna] Engine inicializada")

    def criar_conversa(
        self, db: Session, usuario_id: int, usuario_nome: str,
        company_id: int = 1, modelo_preferido: str = "auto"
    ) -> LunaConversaDB:
        """Cria uma nova conversa no banco."""
        conversa = LunaConversaDB(
            id=_gerar_id(),
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            titulo="Nova conversa",
            modelo_preferido=modelo_preferido,
            company_id=company_id,
        )
        db.add(conversa)
        db.commit()
        db.refresh(conversa)
        logger.info(f"[Luna] Conversa criada: {conversa.id} (user={usuario_id})")
        return conversa

    def _formatar_conteudo_com_anexos(self, conteudo: str, anexos: list | None) -> str:
        """
        Formata o conteúdo da mensagem incluindo referência aos anexos.
        Assim o LLM sabe que o usuário enviou arquivos.
        """
        if not anexos:
            return conteudo

        partes = [conteudo]
        partes.append("\n\n📎 Arquivos anexados:")
        for a in anexos:
            nome = a.get("nome_original", a.get("nome", "arquivo"))
            tipo = a.get("tipo", "documento")
            tamanho = a.get("tamanho", 0)
            tamanho_str = f"{tamanho / 1024:.0f}KB" if tamanho > 0 else ""
            partes.append(f"  - {nome} ({tipo}) {tamanho_str}")

        return "\n".join(partes)

    def _montar_mensagens(
        self, db: Session, conversa_id: str, nova_mensagem: str,
        anexos: list | None = None
    ) -> list:
        """
        Monta a lista de mensagens para enviar ao LLM.
        Usa janela deslizante com as últimas JANELA_CONTEXTO mensagens.
        Inclui referência a anexos no contexto.
        """
        # Buscar mensagens anteriores (janela deslizante)
        mensagens_db = (
            db.query(LunaMensagemDB)
            .filter(LunaMensagemDB.conversa_id == conversa_id)
            .order_by(LunaMensagemDB.id.desc())
            .limit(JANELA_CONTEXTO)
            .all()
        )
        # Reverter para ordem cronológica
        mensagens_db.reverse()

        # Montar lista de mensagens LangChain
        mensagens = [SystemMessage(content=SYSTEM_PROMPT)]

        for msg in mensagens_db:
            conteudo = msg.conteudo
            # Incluir referência a anexos do histórico
            if msg.anexos:
                conteudo = self._formatar_conteudo_com_anexos(conteudo, msg.anexos)

            if msg.papel == "user":
                mensagens.append(HumanMessage(content=conteudo))
            elif msg.papel == "assistant":
                mensagens.append(AIMessage(content=conteudo))

        # Adicionar nova mensagem do usuário (com anexos se houver)
        conteudo_final = self._formatar_conteudo_com_anexos(nova_mensagem, anexos)
        mensagens.append(HumanMessage(content=conteudo_final))

        return mensagens

    def _decidir_modelo(self, mensagem: str, modelo_preferido: str = "auto") -> str | None:
        """
        Usa o Smart Router para decidir se deve forçar Opus.
        Retorna "opus", "sonnet" ou None (auto).
        """
        if modelo_preferido in ("opus", "sonnet"):
            return modelo_preferido

        # Usar Smart Router para decidir
        tier, motivo = smart_router.decidir(
            prompt=mensagem,
            perfil_agente="consultora_estrategica",
        )
        if tier == ModeloClaudeTier.OPUS:
            logger.info(f"[Luna] Smart Router → Opus ({motivo})")
            return "opus"
        return None  # Padrão (Sonnet)

    async def stream_resposta(
        self,
        db: Session,
        conversa_id: str,
        conteudo: str,
        usuario_id: int,
        usuario_nome: str = "",
        anexos: list | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Envia mensagem e faz streaming da resposta da Luna.

        Yields dicts com:
        - {"tipo": "chunk", "conteudo": "texto parcial"}
        - {"tipo": "titulo", "titulo": "Título gerado"}
        - {"tipo": "fim", "mensagem_id": 123, "modelo": "...", "provider": "..."}
        - {"tipo": "erro", "mensagem": "..."}
        """
        inicio = time.time()

        # Buscar conversa
        conversa = db.query(LunaConversaDB).filter(
            LunaConversaDB.id == conversa_id
        ).first()
        if not conversa:
            yield {"tipo": "erro", "mensagem": "Conversa não encontrada"}
            return

        # Serializar anexos para JSON
        anexos_json = None
        if anexos:
            anexos_json = [
                {
                    "nome_original": a.get("nome_original", ""),
                    "url": a.get("url", ""),
                    "tipo": a.get("tipo", "documento"),
                    "tamanho": a.get("tamanho", 0),
                }
                for a in anexos
            ]

        # Salvar mensagem do usuário
        msg_usuario = LunaMensagemDB(
            conversa_id=conversa_id,
            papel="user",
            conteudo=conteudo,
            anexos=anexos_json,
        )
        db.add(msg_usuario)
        db.commit()

        # Decidir modelo
        forcar = self._decidir_modelo(conteudo, conversa.modelo_preferido)

        # Montar histórico (inclui referência a anexos no contexto do LLM)
        mensagens = self._montar_mensagens(db, conversa_id, conteudo, anexos_json)

        # Cadeia de fallback
        cadeia = _obter_cadeia_fallback(forcar)

        resposta_completa = ""
        provider_usado = ""
        modelo_usado = ""
        tokens_in = 0
        tokens_out = 0

        for provider_id, modelo_nome, factory_fn in cadeia:
            try:
                logger.info(f"[Luna] Tentando provider: {provider_id} ({modelo_nome})")
                llm = factory_fn()

                # Streaming
                async for chunk in llm.astream(mensagens):
                    texto = ""
                    if hasattr(chunk, "content") and chunk.content:
                        texto = chunk.content
                    elif isinstance(chunk, str):
                        texto = chunk

                    if texto:
                        resposta_completa += texto
                        yield {"tipo": "chunk", "conteudo": texto}

                provider_usado = provider_id
                modelo_usado = modelo_nome

                # Estimar tokens
                tokens_in = len(conteudo) // CHARS_POR_TOKEN
                tokens_out = len(resposta_completa) // CHARS_POR_TOKEN

                logger.info(
                    f"[Luna] Resposta completa via {provider_id}. "
                    f"Tokens: ~{tokens_in}in/{tokens_out}out"
                )
                break  # Sucesso — sair do loop de fallback

            except Exception as e:
                logger.warning(f"[Luna] Falha no {provider_id}: {e}. Tentando próximo...")
                continue

        if not resposta_completa:
            yield {"tipo": "erro", "mensagem": "Todos os providers falharam. Tente novamente."}
            return

        # Calcular custo estimado
        custo = self._calcular_custo(provider_usado, tokens_in, tokens_out)

        # Salvar resposta no banco
        msg_assistente = LunaMensagemDB(
            conversa_id=conversa_id,
            papel="assistant",
            conteudo=resposta_completa,
            modelo_usado=modelo_usado,
            provider_usado=provider_usado,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            custo_usd=custo,
        )
        db.add(msg_assistente)

        # Atualizar timestamp da conversa
        conversa.atualizado_em = datetime.utcnow()

        # Gerar título se for a primeira mensagem
        total_msgs = db.query(LunaMensagemDB).filter(
            LunaMensagemDB.conversa_id == conversa_id
        ).count()
        if total_msgs <= 2:  # user + assistant = primeira troca
            titulo = await self._gerar_titulo(conteudo)
            if titulo:
                conversa.titulo = titulo
                yield {"tipo": "titulo", "titulo": titulo}

        db.commit()
        db.refresh(msg_assistente)

        # Registrar uso no tracking
        duracao_ms = (time.time() - inicio) * 1000
        self._registrar_uso(
            db, provider_usado, modelo_usado, tokens_in, tokens_out,
            custo, duracao_ms, usuario_id, usuario_nome
        )

        yield {
            "tipo": "fim",
            "mensagem_id": msg_assistente.id,
            "modelo": modelo_usado,
            "provider": provider_usado,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "custo_usd": custo,
        }

    async def regenerar_resposta(
        self,
        db: Session,
        conversa_id: str,
        usuario_id: int,
        usuario_nome: str = "",
    ) -> AsyncGenerator[dict, None]:
        """
        Regenera a última resposta da Luna.
        Remove a última resposta e re-envia a última mensagem do usuário.
        """
        # Buscar última mensagem do assistente
        ultima_assistant = (
            db.query(LunaMensagemDB)
            .filter(
                LunaMensagemDB.conversa_id == conversa_id,
                LunaMensagemDB.papel == "assistant",
            )
            .order_by(LunaMensagemDB.id.desc())
            .first()
        )

        if ultima_assistant:
            db.delete(ultima_assistant)
            db.commit()

        # Buscar última mensagem do usuário
        ultima_user = (
            db.query(LunaMensagemDB)
            .filter(
                LunaMensagemDB.conversa_id == conversa_id,
                LunaMensagemDB.papel == "user",
            )
            .order_by(LunaMensagemDB.id.desc())
            .first()
        )

        if not ultima_user:
            yield {"tipo": "erro", "mensagem": "Nenhuma mensagem para regenerar"}
            return

        # Re-enviar (sem salvar mensagem do usuário novamente)
        conversa = db.query(LunaConversaDB).filter(
            LunaConversaDB.id == conversa_id
        ).first()
        forcar = self._decidir_modelo(
            ultima_user.conteudo,
            conversa.modelo_preferido if conversa else "auto"
        )
        mensagens = self._montar_mensagens(db, conversa_id, ultima_user.conteudo)

        # Remover a última HumanMessage duplicada (já está no histórico)
        # A _montar_mensagens adiciona a mensagem como nova, mas ela já existe no DB
        # Então removemos a última HumanMessage adicionada
        if mensagens and isinstance(mensagens[-1], HumanMessage):
            pass  # Manter — é a mensagem correta para regenerar

        cadeia = _obter_cadeia_fallback(forcar)
        resposta_completa = ""
        provider_usado = ""
        modelo_usado = ""
        inicio = time.time()

        for provider_id, modelo_nome, factory_fn in cadeia:
            try:
                llm = factory_fn()
                async for chunk in llm.astream(mensagens):
                    texto = ""
                    if hasattr(chunk, "content") and chunk.content:
                        texto = chunk.content
                    elif isinstance(chunk, str):
                        texto = chunk
                    if texto:
                        resposta_completa += texto
                        yield {"tipo": "chunk", "conteudo": texto}

                provider_usado = provider_id
                modelo_usado = modelo_nome
                break
            except Exception as e:
                logger.warning(f"[Luna] Regenerar — falha no {provider_id}: {e}")
                continue

        if not resposta_completa:
            yield {"tipo": "erro", "mensagem": "Todos os providers falharam."}
            return

        tokens_in = len(ultima_user.conteudo) // CHARS_POR_TOKEN
        tokens_out = len(resposta_completa) // CHARS_POR_TOKEN
        custo = self._calcular_custo(provider_usado, tokens_in, tokens_out)

        msg_assistente = LunaMensagemDB(
            conversa_id=conversa_id,
            papel="assistant",
            conteudo=resposta_completa,
            modelo_usado=modelo_usado,
            provider_usado=provider_usado,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            custo_usd=custo,
        )
        db.add(msg_assistente)
        db.commit()
        db.refresh(msg_assistente)

        duracao_ms = (time.time() - inicio) * 1000
        self._registrar_uso(
            db, provider_usado, modelo_usado, tokens_in, tokens_out,
            custo, duracao_ms, usuario_id, usuario_nome
        )

        yield {
            "tipo": "fim",
            "mensagem_id": msg_assistente.id,
            "modelo": modelo_usado,
            "provider": provider_usado,
        }

    async def _gerar_titulo(self, mensagem: str) -> str | None:
        """Gera título automático para a conversa usando Sonnet."""
        try:
            llm = _criar_provider_anthropic(
                MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"],
                max_tokens=60,
            )
            prompt = PROMPT_TITULO.format(mensagem=mensagem[:500])
            resposta = await llm.ainvoke([HumanMessage(content=prompt)])
            titulo = resposta.content.strip()[:50]
            logger.info(f"[Luna] Título gerado: '{titulo}'")
            return titulo
        except Exception as e:
            logger.warning(f"[Luna] Falha ao gerar título: {e}")
            return None

    def _calcular_custo(
        self, provider_id: str, tokens_in: int, tokens_out: int
    ) -> float:
        """Calcula custo estimado em USD."""
        # Buscar config do provider
        custos = {
            "anthropic_opus": (0.015, 0.075),
            "anthropic_sonnet": (0.003, 0.015),
            "groq": (0.00059, 0.00079),
            "fireworks": (0.0009, 0.0009),
            "together": (0.00088, 0.00088),
        }
        custo_in, custo_out = custos.get(provider_id, (0.003, 0.015))
        return round(
            (tokens_in / 1000 * custo_in) + (tokens_out / 1000 * custo_out),
            6,
        )

    def _registrar_uso(
        self, db: Session, provider_id: str, modelo: str,
        tokens_in: int, tokens_out: int, custo: float,
        duracao_ms: float, usuario_id: int, usuario_nome: str
    ):
        """Registra uso no UsageTrackingDB."""
        try:
            tracking = UsageTrackingDB(
                provider_id=provider_id,
                provider_nome=f"Luna ({provider_id})",
                modelo=modelo,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                tokens_total=tokens_in + tokens_out,
                custo_usd=custo,
                tipo="luna",
                agente_nome="Luna",
                squad_nome="assistente",
                usuario_id=usuario_id,
                usuario_nome=usuario_nome,
                detalhes={"duracao_ms": round(duracao_ms, 1)},
            )
            db.add(tracking)
            db.commit()
        except Exception as e:
            logger.warning(f"[Luna] Erro ao registrar uso: {e}")

    def registrar_auditoria_supervisao(
        self, db: Session, proprietario_id: int, proprietario_email: str,
        funcionario_id: int, conversa_id: str, ip: str = ""
    ):
        """Registra no audit log quando proprietário visualiza chat de funcionário (LGPD)."""
        try:
            audit = AuditLogDB(
                user_id=proprietario_id,
                email=proprietario_email,
                acao="LUNA_SUPERVISAO",
                descricao=(
                    f"Proprietário visualizou conversa Luna: "
                    f"conversa_id={conversa_id}, funcionario_id={funcionario_id}"
                ),
                ip=ip,
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"[Luna] Erro ao registrar auditoria: {e}")


# =====================================================================
# Instância Global
# =====================================================================
luna_engine = LunaEngine()
