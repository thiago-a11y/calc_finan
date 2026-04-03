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

# System prompt da Luna — composto via core.prompts (v0.59.0)
from core.prompts.composers import compose_luna_prompt as _compose_luna
SYSTEM_PROMPT = _compose_luna()

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


def _criar_provider_minimax(max_tokens: int = MAX_TOKENS_RESPOSTA):
    """Cria instância Minimax via API OpenAI-compatible (endpoint global)."""
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    group_id = os.environ.get("MINIMAX_GROUP_ID", "")
    if not api_key or len(api_key) < 5:
        raise ValueError("MINIMAX_API_KEY não configurada")
    return ChatOpenAI(
        model="MiniMax-Text-01",
        api_key=api_key,
        base_url="https://api.minimaxi.chat/v1",
        max_tokens=max_tokens,
        temperature=TEMPERATURA,
        streaming=True,
        model_kwargs={"extra_body": {"group_id": group_id}},
    )


def _obter_cadeia_fallback(forcar: str | None = None) -> list[tuple]:
    """
    Retorna lista ordenada de (provider_id, modelo_nome, factory_fn) para fallback.

    v0.52.1 — Smart Router Dinamico reordena a cadeia:
    - forcar="minimax" → Minimax primeiro (SIMPLES)
    - forcar="groq"    → Groq primeiro (MEDIO)
    - forcar="sonnet"  → Anthropic Sonnet primeiro (COMPLEXO)
    - forcar="opus"    → Anthropic Opus primeiro
    - forcar=None      → Minimax → Groq → ... (default, mais barato)
    """
    # Construir todos os providers disponiveis
    todos = {}

    # Minimax
    todos["minimax"] = (
        "minimax",
        "MiniMax-Text-01",
        lambda: _criar_provider_minimax(),
    )

    # Groq, Fireworks, Together
    for provider in PROVIDERS:
        if provider.id in (ProviderID.ANTHROPIC_OPUS, ProviderID.ANTHROPIC_SONNET, ProviderID.ANTHROPIC):
            continue
        if not provider.ativo or not provider.base_url:
            continue
        p_id = provider.id.value
        p_modelo = provider.modelo
        p_key_env = provider.api_key_env
        p_url = provider.base_url
        todos[p_id] = (
            p_id,
            p_modelo,
            lambda key=p_key_env, url=p_url, mod=p_modelo: _criar_provider_openai_compat(mod, key, url),
        )

    # Anthropic
    todos["anthropic_opus"] = (
        "anthropic_opus",
        MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"],
        lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.OPUS]["modelo"]),
    )
    todos["anthropic_sonnet"] = (
        "anthropic_sonnet",
        MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"],
        lambda: _criar_provider_anthropic(MODELOS_CLAUDE[ModeloClaudeTier.SONNET]["modelo"]),
    )

    # Definir ordem baseada no Smart Router
    if forcar == "opus":
        ordem = ["anthropic_opus", "anthropic_sonnet", "groq", "minimax"]
    elif forcar == "sonnet":
        ordem = ["anthropic_sonnet", "groq", "minimax"]
    elif forcar == "groq":
        ordem = ["groq", "minimax", "anthropic_sonnet"]
    elif forcar == "minimax":
        ordem = ["minimax", "groq", "anthropic_sonnet"]
    else:
        # Default: mais barato primeiro
        ordem = ["minimax", "groq", "anthropic_sonnet"]

    # Montar cadeia na ordem definida + providers restantes
    cadeia = []
    adicionados = set()
    for pid in ordem:
        if pid in todos and pid not in adicionados:
            cadeia.append(todos[pid])
            adicionados.add(pid)
    # Adicionar restantes (Fireworks, Together, etc.)
    for pid, entry in todos.items():
        if pid not in adicionados:
            cadeia.append(entry)
            adicionados.add(pid)

    # 6. OpenAI GPT-4o — última linha
    cadeia.append((
        "openai_gpt4o",
        "gpt-4o",
        lambda: _criar_provider_openai_compat("gpt-4o", "OPENAI_API_KEY", "https://api.openai.com/v1"),
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
        Formata o conteúdo da mensagem incluindo o CONTEÚDO REAL dos anexos.
        Extrai texto de XLSX, DOCX, PDF, CSV, TXT, etc. para que o LLM
        possa analisar os dados reais do arquivo.
        """
        if not anexos:
            return conteudo

        from core.luna_file_reader import extrair_conteudo_arquivo

        partes = [conteudo]

        for a in anexos:
            nome = a.get("nome_original", a.get("nome", "arquivo"))
            url = a.get("url", "")
            tipo = a.get("tipo", "documento")

            # v0.58.1: Se imagem falhou na conversao base64, informar ao LLM
            erro_visao = a.get("_erro_visao")
            if erro_visao:
                partes.append(f"\n\n{erro_visao}")
                continue

            # Extrair conteúdo REAL do arquivo
            conteudo_arquivo = extrair_conteudo_arquivo(url, nome, tipo)

            if conteudo_arquivo:
                partes.append(f"\n\n📎 Conteúdo do arquivo '{nome}':")
                partes.append("=" * 60)
                partes.append(conteudo_arquivo)
                partes.append("=" * 60)
            else:
                # Fallback: pelo menos informar que o arquivo foi anexado
                tamanho = a.get("tamanho", 0)
                tamanho_str = f"{tamanho / 1024:.0f}KB" if tamanho > 0 else ""
                partes.append(f"\n\n📎 Arquivo anexado: {nome} ({tipo}) {tamanho_str}")
                partes.append("[⚠️ Não foi possível extrair o conteúdo deste arquivo]")

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

        # Adicionar nova mensagem do usuario (com anexos se houver)
        # Para imagens: enviar como conteudo multimodal (base64) para visao do LLM
        imagens_base64 = []
        anexos_texto = []
        if anexos:
            for a in anexos:
                tipo = a.get("tipo", "documento")
                url = a.get("url", "")
                nome = a.get("nome_original", "imagem")
                if tipo == "imagem" and url:
                    b64 = self._imagem_para_base64(url)
                    if b64:
                        imagens_base64.append(b64)
                        logger.info(f"[Luna] Imagem '{nome}' anexada ao contexto multimodal")
                        continue
                    else:
                        # v0.58.1: Nao dropar silenciosamente — avisar que tinha imagem
                        logger.warning(f"[Luna] Falha ao converter imagem '{nome}' — sera mencionada como texto")
                        anexos_texto.append({
                            **a,
                            "_erro_visao": f"[IMAGEM ANEXADA: {nome} — o usuario enviou esta imagem mas houve erro ao processar. Pergunte ao usuario para descrever o que ele ve na imagem.]",
                        })
                        continue
                anexos_texto.append(a)

        if imagens_base64:
            # Mensagem multimodal: texto + imagens em base64
            conteudo_texto = self._formatar_conteudo_com_anexos(nova_mensagem, anexos_texto if anexos_texto else None)
            content_parts: list[dict] = [{"type": "text", "text": conteudo_texto}]
            for img_data in imagens_base64:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": img_data},
                })
            mensagens.append(HumanMessage(content=content_parts))
        else:
            conteudo_final = self._formatar_conteudo_com_anexos(nova_mensagem, anexos)
            mensagens.append(HumanMessage(content=conteudo_final))

        return mensagens

    def _imagem_para_base64(self, url_relativa: str) -> str | None:
        """
        Converte imagem de uploads para base64 data URI.

        Args:
            url_relativa: URL relativa do upload (ex: /uploads/chat/abc.png)

        Returns:
            Data URI string (data:image/png;base64,...) ou None se falhar.

        v0.58.1: Corrigido para usar caminho absoluto (igual luna_file_reader.py).
        Antes usava Path("data") relativo ao CWD — falhava silenciosamente.
        """
        import base64
        import os
        from pathlib import Path

        try:
            # Resolver path absoluto do upload (v0.58.1: usa __file__ como ancora)
            if url_relativa.startswith("/uploads/"):
                nome_arquivo = url_relativa.split("/")[-1]
                # Caminho absoluto baseado na localizacao deste arquivo
                upload_dir = Path(__file__).parent.parent / "data" / "uploads" / "chat"
                if os.path.exists("/opt/synerium-factory"):
                    upload_dir = Path("/opt/synerium-factory/data/uploads/chat")
                caminho = upload_dir / nome_arquivo
                if not caminho.is_file():
                    logger.warning(f"[Luna] Imagem nao encontrada: {caminho} (url: {url_relativa})")
                    return None
            else:
                caminho = Path(url_relativa)
                if not caminho.is_file():
                    logger.warning(f"[Luna] Imagem path invalido: {url_relativa}")
                    return None

            # Verificar tamanho (max 10MB para base64)
            tamanho = caminho.stat().st_size
            if tamanho > 10_485_760:
                logger.warning(f"[Luna] Imagem muito grande para visao: {tamanho} bytes")
                return None

            # Detectar mime type
            ext = caminho.suffix.lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".gif": "image/gif", ".webp": "image/webp"}
            mime = mime_map.get(ext, "image/png")

            # Converter para base64
            dados = caminho.read_bytes()
            b64 = base64.b64encode(dados).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64}"

            logger.info(f"[Luna] Imagem convertida para visao: {caminho.name} ({tamanho // 1024}KB)")
            return data_uri

        except Exception as e:
            logger.warning(f"[Luna] Erro ao converter imagem: {e}")
            return None

    def _decidir_modelo(self, mensagem: str, modelo_preferido: str = "auto", anexos: list | None = None) -> str | None:
        """
        Usa o Smart Router Dinamico para classificar a mensagem.
        Retorna "opus", "sonnet", "groq", "minimax" ou None (auto).

        v0.52.0: Tambem armazena a classificacao completa para uso no streaming.
        v0.52.1: Retorna provider recomendado pelo Smart Router (não apenas Anthropic).
        v0.58.0: Detecta imagens nos anexos e forca provider com vision.
        """
        if modelo_preferido in ("opus", "sonnet"):
            return modelo_preferido

        # v0.58.0: Detectar se tem imagem nos anexos
        tem_imagem = any(
            a.get("tipo") == "imagem" for a in (anexos or [])
        )

        # v0.52.0: Usar classificador dinamico
        from core.classificador_mensagem import classificar_mensagem
        self._ultima_classificacao = classificar_mensagem(
            mensagem=mensagem,
            tem_tools=False,
            tem_imagem=tem_imagem,
            precisa_streaming=True,
        )

        provider = self._ultima_classificacao.provider
        motivo = self._ultima_classificacao.motivo
        complexidade = self._ultima_classificacao.complexidade.value

        logger.info(f"[Luna] Smart Router → {provider} ({motivo}, complexidade={complexidade})")

        # Mapear para o formato que _obter_cadeia_fallback entende
        if provider in ("anthropic_opus",):
            return "opus"
        elif provider in ("anthropic_sonnet",):
            return "sonnet"
        elif provider in ("groq",):
            return "groq"
        elif provider in ("minimax",):
            return "minimax"
        return None  # Cadeia de fallback default

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

        # Decidir modelo (v0.58.0: passa anexos para detectar imagens → vision)
        forcar = self._decidir_modelo(conteudo, conversa.modelo_preferido, anexos=anexos_json)

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
            conversa.modelo_preferido if conversa else "auto",
            anexos=ultima_user.anexos,  # v0.58.0: detectar imagens na regeneracao
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
