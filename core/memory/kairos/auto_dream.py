"""
AutoDream — Processo de consolidação automática de memórias em background.

O AutoDream é o coração do sistema Kairos: periodicamente processa
snapshots brutos de interações e consolida em memórias estruturadas
usando LLM. Funciona como o processo de "sonho" — organiza e destila
informação durante períodos de inatividade.

Fluxo do Dream:
1. Adquirir lock de consolidação (evitar concorrência)
2. Buscar snapshots pendentes (não consolidados)
3. Agrupar por agente/tenant
4. Para cada grupo, enviar ao LLM com prompt de consolidação
5. Parsear resposta e criar/atualizar MemoryEntry no banco
6. Marcar snapshots como consolidados
7. Limpar snapshots expirados
8. Liberar lock

Uso:
    from core.memory.kairos.auto_dream import auto_dream

    # Executar um ciclo de dream manualmente
    resultado = await auto_dream.dream()

    # Iniciar loop automático em background
    auto_dream.iniciar_loop()

    # Parar loop
    auto_dream.parar_loop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from core.memory.kairos.consolidation_lock import consolidation_lock
from core.memory.kairos.consolidation_prompt import prompt_consolidar_snapshots
from core.memory.kairos.memory_snapshot import snapshot_manager
from core.memory.kairos.registry import memory_registry
from core.memory.kairos.types import (
    ConsolidationResult,
    ConsolidationStatus,
    KairosConfig,
    MemoryEntry,
    MemorySnapshotData,
    MemoryType,
)

logger = logging.getLogger("synerium.kairos.dream")


def _gerar_dream_id() -> str:
    """Gera ID único para um ciclo de dream."""
    import secrets
    import string
    alfabeto = string.ascii_lowercase + string.digits
    sufixo = "".join(secrets.choice(alfabeto) for _ in range(8))
    return f"dream_{sufixo}"


class AutoDream:
    """
    Motor de consolidação automática de memórias.

    Processa snapshots brutos → LLM → memórias consolidadas.
    Pode rodar como ciclo único (dream()) ou loop contínuo (iniciar_loop()).

    Atributos:
        _config: configuração do sistema
        _task: referência à task asyncio do loop (se ativo)
        _rodando: flag indicando se o loop está ativo
    """

    def __init__(self, config: KairosConfig | None = None):
        self._config = config or KairosConfig()
        self._task: asyncio.Task | None = None
        self._rodando = False

    # =========================================================================
    # API Principal
    # =========================================================================

    async def dream(self) -> ConsolidationResult:
        """
        Executa um ciclo completo de consolidação (dream).

        Fluxo:
        1. Adquirir lock
        2. Buscar snapshots pendentes
        3. Agrupar por agente
        4. Consolidar cada grupo via LLM
        5. Salvar memórias resultantes
        6. Marcar snapshots como processados
        7. Limpar expirados

        Returns:
            ConsolidationResult com métricas do ciclo
        """
        dream_id = _gerar_dream_id()
        inicio = time.time()

        resultado = ConsolidationResult(
            dream_id=dream_id,
            status=ConsolidationStatus.EM_ANDAMENTO,
            iniciado_em=datetime.now(timezone.utc),
        )

        logger.info(f"[Dream] Iniciando ciclo {dream_id}")

        try:
            # 1. Adquirir lock
            async with consolidation_lock.acquire(dream_id):
                # 2. Buscar snapshots pendentes
                pendentes = snapshot_manager.listar_pendentes(
                    limite=self._config.max_snapshots_por_dream
                )

                if not pendentes:
                    logger.info(f"[Dream] {dream_id}: nenhum snapshot pendente")
                    resultado.status = ConsolidationStatus.CONCLUIDO
                    resultado.concluido_em = datetime.now(timezone.utc)
                    resultado.duracao_ms = (time.time() - inicio) * 1000
                    return resultado

                logger.info(
                    f"[Dream] {dream_id}: {len(pendentes)} snapshots para processar"
                )

                # 3. Agrupar por agente
                grupos = self._agrupar_por_agente(pendentes)

                # 4. Consolidar cada grupo
                for agente_id, snapshots in grupos.items():
                    try:
                        criadas, atualizadas = await self._consolidar_grupo(
                            agente_id, snapshots, dream_id
                        )
                        resultado.memorias_criadas += criadas
                        resultado.memorias_atualizadas += atualizadas
                        resultado.snapshots_processados += len(snapshots)
                    except Exception as e:
                        logger.error(
                            f"[Dream] Erro ao consolidar grupo {agente_id}: {e}"
                        )
                        continue

                # 5. Limpar snapshots expirados
                removidos = snapshot_manager.limpar_expirados(
                    ttl_horas=self._config.ttl_snapshot_horas
                )
                resultado.memorias_removidas = removidos

            # Sucesso
            resultado.status = ConsolidationStatus.CONCLUIDO
            resultado.concluido_em = datetime.now(timezone.utc)
            resultado.duracao_ms = (time.time() - inicio) * 1000

            logger.info(
                f"[Dream] {dream_id} concluído em {resultado.duracao_ms:.0f}ms: "
                f"{resultado.snapshots_processados} snapshots → "
                f"{resultado.memorias_criadas} novas, "
                f"{resultado.memorias_atualizadas} atualizadas"
            )

        except RuntimeError as e:
            # Lock não disponível
            logger.warning(f"[Dream] {dream_id}: lock não disponível ({e})")
            resultado.status = ConsolidationStatus.CANCELADO
            resultado.erro = str(e)
            resultado.concluido_em = datetime.now(timezone.utc)
            resultado.duracao_ms = (time.time() - inicio) * 1000

        except Exception as e:
            logger.error(f"[Dream] {dream_id}: erro inesperado: {e}", exc_info=True)
            resultado.status = ConsolidationStatus.FALHOU
            resultado.erro = str(e)
            resultado.concluido_em = datetime.now(timezone.utc)
            resultado.duracao_ms = (time.time() - inicio) * 1000

        return resultado

    # =========================================================================
    # Loop Automático
    # =========================================================================

    def iniciar_loop(self) -> None:
        """
        Inicia o loop de dream automático em background.

        O loop executa dream() a cada dream_interval_min minutos.
        """
        if self._rodando:
            logger.warning("[Dream] Loop já está rodando")
            return

        if not self._config.habilitar_auto_dream:
            logger.info("[Dream] Auto-dream desabilitado na configuração")
            return

        self._rodando = True
        self._task = asyncio.ensure_future(self._loop())
        logger.info(
            f"[Dream] Loop automático iniciado "
            f"(intervalo: {self._config.dream_interval_min}min)"
        )

    def parar_loop(self) -> None:
        """Para o loop de dream automático."""
        self._rodando = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[Dream] Loop automático parado")

    @property
    def esta_rodando(self) -> bool:
        """Retorna True se o loop automático está ativo."""
        return self._rodando

    async def _loop(self) -> None:
        """Loop interno de dream automático."""
        while self._rodando:
            try:
                await self.dream()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Dream] Erro no loop: {e}")

            # Aguardar intervalo
            try:
                await asyncio.sleep(self._config.dream_interval_min * 60)
            except asyncio.CancelledError:
                break

        logger.info("[Dream] Loop encerrado")

    # =========================================================================
    # Consolidação Interna
    # =========================================================================

    def _agrupar_por_agente(
        self, snapshots: list[MemorySnapshotData]
    ) -> dict[str, list[MemorySnapshotData]]:
        """Agrupa snapshots por agente_id."""
        grupos: dict[str, list[MemorySnapshotData]] = defaultdict(list)
        for snap in snapshots:
            grupos[snap.agente_id].append(snap)
        return dict(grupos)

    async def _consolidar_grupo(
        self,
        agente_id: str,
        snapshots: list[MemorySnapshotData],
        dream_id: str,
    ) -> tuple[int, int]:
        """
        Consolida um grupo de snapshots do mesmo agente via LLM.

        Args:
            agente_id: ID do agente
            snapshots: snapshots para consolidar
            dream_id: ID do ciclo de dream

        Returns:
            (memórias_criadas, memórias_atualizadas)
        """
        # Buscar memórias existentes do agente para contexto
        memorias_existentes = memory_registry.listar(agente_id=agente_id, limite=20)

        # Construir prompt
        prompt = prompt_consolidar_snapshots(snapshots, memorias_existentes)

        # Chamar LLM
        resposta_json = await self._chamar_llm(prompt)
        if not resposta_json:
            logger.warning(
                f"[Dream] LLM não retornou resposta para agente {agente_id}"
            )
            return 0, 0

        # Parsear resposta
        criadas = 0
        atualizadas = 0

        memorias_raw = resposta_json.get("memorias", [])
        for mem_raw in memorias_raw:
            try:
                tipo = MemoryType(mem_raw.get("tipo", "semantica"))
                snapshot_ids = mem_raw.get("snapshot_ids", [])
                atualizar_id = mem_raw.get("atualizar_id")

                if atualizar_id:
                    # Atualizar memória existente
                    ok = memory_registry.atualizar(
                        atualizar_id,
                        conteudo=mem_raw.get("conteudo", ""),
                        tags=mem_raw.get("novas_tags", mem_raw.get("tags", [])),
                    )
                    if ok:
                        atualizadas += 1
                else:
                    # Criar nova memória
                    entry = MemoryEntry(
                        agente_id=agente_id,
                        tenant_id=snapshots[0].tenant_id if snapshots else 1,
                        tipo=tipo,
                        titulo=mem_raw.get("titulo", "Sem título"),
                        conteudo=mem_raw.get("conteudo", ""),
                        tags=mem_raw.get("tags", []),
                        relevancia=mem_raw.get("relevancia", 0.5),
                        fonte_snapshots=snapshot_ids,
                    )
                    memory_registry.salvar(entry)
                    criadas += 1

                # Marcar snapshots como consolidados
                for snap_id in snapshot_ids:
                    snapshot_manager.marcar_consolidado(snap_id)

            except Exception as e:
                logger.warning(f"[Dream] Erro ao processar memória: {e}")
                continue

        # Marcar snapshots ignorados como consolidados também
        ignorados = resposta_json.get("snapshots_ignorados", [])
        for snap_id in ignorados:
            snapshot_manager.marcar_consolidado(snap_id)

        return criadas, atualizadas

    async def _chamar_llm(self, prompt: str) -> dict | None:
        """
        Chama o LLM para consolidação.

        Usa a cadeia de fallback existente da Luna para compatibilidade.

        Args:
            prompt: prompt completo de consolidação

        Returns:
            Dict parseado da resposta JSON, ou None se falhou
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from core.luna_engine import _obter_cadeia_fallback

            # Usar modelo de consolidação configurado
            modelo = self._config.modelo_consolidacao
            cadeia = _obter_cadeia_fallback(modelo)

            mensagens = [
                SystemMessage(content="Você é o sistema Kairos de consolidação de memórias. Responda APENAS com JSON válido."),
                HumanMessage(content=prompt),
            ]

            for provider_id, modelo_nome, factory_fn in cadeia:
                try:
                    llm = factory_fn()
                    resposta = await llm.ainvoke(mensagens)

                    # Extrair texto da resposta
                    texto = resposta.content if hasattr(resposta, "content") else str(resposta)

                    # Limpar e parsear JSON
                    texto = texto.strip()
                    if texto.startswith("```"):
                        texto = texto.split("\n", 1)[-1].rsplit("```", 1)[0]

                    return json.loads(texto)

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"[Dream] LLM {provider_id} retornou JSON inválido: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(f"[Dream] Falha no provider {provider_id}: {e}")
                    continue

            logger.error("[Dream] Todos os providers falharam na consolidação")
            return None

        except Exception as e:
            logger.error(f"[Dream] Erro ao chamar LLM: {e}")
            return None


# Instância singleton
auto_dream = AutoDream()
