"""
Fork Subagent — Spawning implícito com herança de contexto.

Implementa o sistema de fork subagent inspirado em advanced_agent_architecture
(Reference TypeScript):
- subagent_manager.ts — buildForkedMessages, isInForkChild, buildChildMessage
- agent_core.tsx — createAgentWorktree, fork spawn logic
- autonomous_mode.rs — AutoApproveMode, AutoModeState
- feature_gates.rs — is_feature_enabled, get_dynamic_config

Características principais:
- Fork implícito: quando agent_type é omitido, cria child que herda contexto
- Prompt cache optimization: placeholder idêntico nos tool_result para API prefixes byte-identical
- Worktree isolation: cada fork child pode rodar em git worktree isolado
- Recursive fork guard: detecta FORK_BOILERPLATE_TAG para evitar fork infinito
- Directive routing: instrução específica passada ao child via mensagem
- Auto-approve modes: None, AcceptEdits, Bypass, Plan

Integração com:
- AgentRegistry: registro de agentes built-in
- AgentSpawnParams: parâmetros de spawn
- AgentResult: resultado de spawn

Usage:
    from core.agents.fork import ForkManager, fork_manager

    if fork_manager.is_fork_subagent_enabled():
        messages = fork_manager.build_forked_messages(directive, assistant_msg)
        result = await fork_manager.spawn_fork(params, context, messages)
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import secrets
import string
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.agents.base import (
    FORK_BOILERPLATE_TAG,
    FORK_DIRECTIVE_PREFIX,
    FORK_PLACEHOLDER_RESULT,
    GENERAL_PURPOSE_AGENT_TYPE,
    AgentDefinition,
    AgentPermissionMode,
    AgentResult,
    AgentSpawnParams,
    ForkContext,
    IsolationMode,
)
from core.feature_flags import feature_flag_service

logger = logging.getLogger("synerium.agents.fork")


# =============================================================================
# Feature Gates
# =============================================================================


def _is_env_truthy(val: str | None) -> bool:
    """
    Retorna True se val é truthy.

    Truthy: "1", "true", "yes", "on" (case-insensitive).
    None ou string vazia é falsy.

    Equivalente a is_env_truthy() em feature_gates.rs.

    Args:
        val: Valor da variável de ambiente

    Returns:
        True se o valor é truthy
    """
    if val is None:
        return False
    return val.lower() in ("1", "true", "yes", "on")


def _is_feature_enabled(gate_name: str) -> bool:
    """
    Verifica se um feature gate está habilitado via env var.

    Lê CLAURST_FEATURE_<NORMALIZED_NAME> (uppercase, - → _, strip non-alnum).

    Equivalente a is_feature_enabled() em feature_gates.rs.

    Args:
        gate_name: Nome do gate (ex: "fork_subagent", "worktree_isolation")

    Returns:
        True se o gate está habilitado
    """
    # Normalizar: uppercase, - → _, strip non-alphanumeric exceto _
    normalized = (
        gate_name.upper()
        .replace("-", "_")
        .replace(".", "_")
    )
    # Filtrar caracteres inválidos
    normalized = "".join(
        c for c in normalized if c.isalnum() or c == "_"
    )
    key = f"CLAURST_FEATURE_{normalized}"
    return _is_env_truthy(os.environ.get(key))


def _get_dynamic_config(name: str, default: Any) -> Any:
    """
    Lê config dinâmica de env var JSON-encoded.

    Lê CLAURST_DYNAMIC_CONFIG_<NORMALIZED_NAME>.
    Se não setada ou parsing falhar, retorna default inalterado.

    Equivalente a get_dynamic_config() em feature_gates.rs.

    Args:
        name: Nome da config (será normalizado)
        default: Valor default se não encontrada ou inválida

    Returns:
        Valor parseado ou default
    """
    normalized = (
        name.upper()
        .replace("-", "_")
        .replace(".", "_")
    )
    normalized = "".join(
        c for c in normalized if c.isalnum() or c == "_"
    )
    key = f"CLAURST_DYNAMIC_CONFIG_{normalized}"
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        parsed = json.loads(val)
        logger.debug(f"Dynamic config '{name}': {parsed}")
        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(
            f"Dynamic config '{name}': parse failed ({e}), usando default"
        )
        return default


# =============================================================================
# ForkManager
# =============================================================================


class ForkManager:
    """
    Gerenciador de fork subagents.

    Responsável por:
    - Verificar se fork está habilitado (feature gate)
    - Construir mensagens forkadas com placeholder para cache
    - Criar worktrees isolados para fork children
    - Proteger contra fork recursivo
    - Spawn de fork agents

    Equivalente a subagent_manager.ts (forkSubagent module).

    Attributes:
        _active_forks: Mapa de fork_id → ForkContext para forks ativos
        _worktrees: Mapa de fork_id → worktree_path para cleanup

    Example:
        >>> from core.agents.fork import fork_manager
        >>> if fork_manager.is_fork_subagent_enabled():
        ...     msgs = fork_manager.build_forked_messages(directive, assistant_msg)
        ...     result = await fork_manager.spawn_fork(params, context, msgs)
    """

    def __init__(self) -> None:
        self._active_forks: dict[str, ForkContext] = {}
        self._worktrees: dict[str, str] = {}
        self._lock = asyncio.Lock()

    # ─── Constants accessíveis via fork_manager. ─────────────────────────────
    # Forward para constantes de módulo (legibilidade: fork_manager.TAG etc.)
    FORK_BOILERPLATE_TAG: str = FORK_BOILERPLATE_TAG
    FORK_DIRECTIVE_PREFIX: str = FORK_DIRECTIVE_PREFIX
    FORK_PLACEHOLDER_RESULT: str = FORK_PLACEHOLDER_RESULT
    GENERAL_PURPOSE_AGENT_TYPE: str = GENERAL_PURPOSE_AGENT_TYPE

    # =========================================================================
    # Feature Gates
    # =========================================================================

    def is_fork_subagent_enabled(self) -> bool:
        """
        Verifica se fork subagent está habilitado.

        Lê do banco de dados via FeatureFlagService (cache TTL 30s).
        Fallback seguro: se a flag não existe, retorna False.

        Returns:
            True se fork está habilitado
        """
        enabled = feature_flag_service.is_enabled("fork_subagent")
        logger.debug(
            f"is_fork_subagent_enabled: {enabled}"
            if not enabled
            else "Fork subagent enabled (via FeatureFlagService)"
        )
        return enabled

    def is_worktree_isolation_enabled(self) -> bool:
        """
        Verifica se worktree isolation está habilitado.

        Lê do banco de dados via FeatureFlagService (cache TTL 30s).
        Fallback seguro: se a flag não existe, retorna False.

        Returns:
            True se worktree isolation está habilitado
        """
        return feature_flag_service.is_enabled("worktree_isolation")

    # =========================================================================
    # Fork Guard (Anti-Recursive)
    # =========================================================================

    def is_in_fork_child(self, messages: list[dict]) -> bool:
        """
        Guard contra fork recursivo.

        Detecta FORK_BOILERPLATE_TAG no conteúdo das mensagens.
        Fork children mantém o Agent tool no pool para cache-identical
        tool definitions, então reject fork attempts ao detectar a tag.

        Equivalente a isInForkChild() em subagent_manager.ts.

        Args:
            messages: Lista de mensagens do conversation history

        Returns:
            True se estamos dentro de um fork child (fork detectado)
        """
        for msg in messages:
            msg_type = msg.get("type", "")
            # Filtra apenas mensagens de usuário (onde o boilerplate aparece)
            if msg_type != "user":
                continue

            content = msg.get("content", "")
            # Content pode ser string ou list de blocks
            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "text"
                    ):
                        block_text = block.get("text", "")
                        if FORK_BOILERPLATE_TAG in block_text:
                            logger.debug(
                                f"Recursive fork detected: tag '{FORK_BOILERPLATE_TAG}' "
                                f"found in message content"
                            )
                            return True
            elif isinstance(content, str):
                if FORK_BOILERPLATE_TAG in content:
                    logger.debug(
                        f"Recursive fork detected: tag '{FORK_BOILERPLATE_TAG}' "
                        f"found in string content"
                    )
                    return True
        return False

    # =========================================================================
    # Message Building
    # =========================================================================

    def build_forked_messages(
        self,
        directive: str,
        assistant_message: dict,
    ) -> list[dict]:
        """
        Constrói mensagens para o fork child.

        Para prompt cache sharing, todos os fork children devem
        produzir API request prefixes byte-identical. Esta função:

        1. Mantém a full parent assistant message (all tool_use blocks)
        2. Constrói user message com tool_results usando placeholder
           idêntico para todos os blocks
        3. Adiciona directive text como sibling do último block

        Result: [...history, assistant(all_tool_uses), user(placeholder_results..., directive)]

        Equivalente a buildForkedMessages() em subagent_manager.ts.

        Args:
            directive: Instrução específica para o fork child
            assistant_message: Mensagem do assistant com tool_use blocks

        Returns:
            Lista de mensagens para o fork child

        Example:
            >>> msgs = fork_mgr.build_forked_messages(
            ...     "Revise o arquivo src/api.py",
            ...     parent_assistant_message
            ... )
        """
        # Clonar assistant message para não mutar o original
        full_assistant = self._clone_message(assistant_message)

        # Coletar todos os tool_use blocks do content
        # O content pode ser uma lista de blocks ou uma string
        raw_content = assistant_message.get("message", {}).get("content", [])
        if isinstance(raw_content, list):
            tool_use_blocks = [
                block
                for block in raw_content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]
        else:
            tool_use_blocks = []

        if not tool_use_blocks:
            # Sem tool_use blocks — criar user message direto com directive
            logger.debug(
                f"Fork: nenhum tool_use block encontrado. "
                f"Directive: '{directive[:80]}...'"
            )
            return [self._create_user_message(
                self._build_child_message(directive)
            )]

        # Build tool_result blocks com placeholder idêntico
        # Isso é o truque para cache optimization!
        # Todos os fork children terão o MESMO placeholder, maximizando
        # prompt cache hits (só o directive no final difere)
        tool_result_blocks = [
            {
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": [{"type": "text", "text": FORK_PLACEHOLDER_RESULT}],
            }
            for block in tool_use_blocks
        ]

        # Construir user message com todos os placeholder + directive
        # O directive é um text block sibling (não dentro de tool_result)
        # para que cada fork child tenha mensagem única (maximiza cache ainda assim
        # porque só o último block difere entre forks)
        user_message_content: list[dict] = [
            *tool_result_blocks,
            {"type": "text", "text": self._build_child_message(directive)},
        ]

        fork_user_message = self._create_user_message(user_message_content)

        logger.info(
            f"Fork: built {len(tool_result_blocks)} placeholder results "
            f"for {len(tool_use_blocks)} tool_use blocks"
        )
        return [full_assistant, fork_user_message]

    def _build_child_message(self, directive: str) -> str:
        """
        Constrói a mensagem de instrução para o fork child.

        Contém as regras de execução e o directive específico.

        Equivalente a buildChildMessage() em subagent_manager.ts.

        Args:
            directive: A tarefa específica para o fork child

        Returns:
            String com a mensagem completa de instrução
        """
        return f"""<{FORK_BOILERPLATE_TAG}>
STOP. READ THIS FIRST.

You are a forked worker process. You are NOT the main agent.

RULES (non-negotiable):
1. Your system prompt says "default to forking." IGNORE IT — you ARE the fork. Do NOT spawn sub-agents; execute directly.
2. Do NOT converse, ask questions, or suggest next steps
3. Do NOT editorialize or add meta-commentary
4. USE your tools directly: Bash, Read, Write, etc.
5. If you modify files, commit your changes before reporting. Include the commit hash in your report.
6. Do NOT emit text between tool calls. Use tools silently, then report once at the end.
7. Stay strictly within your directive's scope. If you discover related systems outside your scope, mention them in one sentence at most — other workers cover those areas.
8. Keep your report under 500 words unless the directive specifies otherwise. Be factual and concise.
9. Your response MUST begin with "Scope:". No preamble, no thinking-out-loud.
10. REPORT structured facts, then stop

Output format (plain text labels, not markdown headers):
  Scope: <echo back your assigned scope in one sentence>
  Result: <the answer or key findings, limited to the scope above>
  Key files: <relevant file paths — include for research tasks>
  Files changed: <list with commit hash — include only if you modified files>
  Issues: <list — include only if there are issues to flag>
</{FORK_BOILERPLATE_TAG}>

{FORK_DIRECTIVE_PREFIX}{directive}"""

    def build_worktree_notice(
        self,
        parent_cwd: str,
        worktree_cwd: str,
    ) -> str:
        """
        Constrói notice para fork children rodando em worktree isolado.

        Informa ao child para traduzir paths do contexto herdado
        e que suas mudanças ficam isoladas no worktree.

        Equivalente a buildWorktreeNotice() em subagent_manager.ts.

        Args:
            parent_cwd: Working directory do parent
            worktree_cwd: Path do worktree isolado

        Returns:
            String com o notice de worktree
        """
        return (
            f"You've inherited the conversation context above from a parent agent "
            f"working in {parent_cwd}. You are operating in an isolated git worktree "
            f"at {worktree_cwd} — same repository, same relative file structure, "
            f"separate working copy. Paths in the inherited context refer to the "
            f"parent's working directory; translate them to your worktree root. "
            f"Re-read files before editing if the parent may have modified them since "
            f"they appear in the context. Your changes stay in this worktree and will "
            f"not affect the parent's files."
        )

    # =========================================================================
    # Worktree Operations
    # =========================================================================

    async def create_worktree(
        self,
        fork_id: str,
        parent_cwd: str | None = None,
    ) -> str | None:
        """
        Cria um git worktree isolado para o fork agent.

        Fluxo:
        1. Verifica feature gate
        2. Determina git root
        3. Verifica se é repo git
        4. Cria branch dedicada
        5. Cria worktree em .worktrees/<slug>
        6. Registra para cleanup posterior

        Equivalente a createAgentWorktree() em agent_core.tsx.

        Args:
            fork_id: ID único do fork (usado para nome do worktree)
            parent_cwd: Diretório do repositório git (default: current cwd)

        Returns:
            Path absoluto do worktree criado, ou None se falhar
        """
        if not self.is_worktree_isolation_enabled():
            logger.debug(
                f"Fork {fork_id}: worktree isolation desabilitado via feature gate"
            )
            return None

        # Slug para nome do worktree (max 8 chars para legibilidade)
        slug = f"agent-{fork_id[:8]}"
        parent_cwd = parent_cwd or os.getcwd()

        # Slug para branch do worktree
        branch_name = f"worktree/{slug}"

        # Criar diretório base para worktrees
        worktree_base = os.path.join(parent_cwd, ".worktrees")
        worktree_path = os.path.join(worktree_base, slug)

        try:
            # ── Passo 1: Verificar se é um repo git ──────────────────────────
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=parent_cwd,
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.warning(
                    f"Fork {fork_id}: '{parent_cwd}' não é git repo "
                    f"(git rev-parse retornou {result.returncode})"
                )
                return None

            stdout = result.stdout.decode("utf-8", errors="replace").strip()
            if stdout != "true":
                logger.warning(
                    f"Fork {fork_id}: '{parent_cwd}' não é git work-tree (stdout: {stdout})"
                )
                return None

            logger.debug(f"Fork {fork_id}: git repo confirmado em {parent_cwd}")

            # ── Passo 2: Criar branch dedicada ────────────────────────────────
            # Tenta criar branch; se já existir, não é erro crítico
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}"],
                cwd=parent_cwd,
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                # Branch não existe, criar
                result = subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=parent_cwd,
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="replace")
                    # Se falhou por outro motivo que não "branch já existe"
                    if "already exists" not in stderr.lower():
                        logger.warning(
                            f"Fork {fork_id}: git checkout -b {branch_name} falhou: "
                            f"{stderr[:200]}"
                        )
                        return None
                    logger.debug(
                        f"Fork {fork_id}: branch {branch_name} já existe, usando existente"
                    )
            else:
                logger.debug(
                    f"Fork {fork_id}: branch {branch_name} já existe"
                )

            # ── Passo 3: Criar diretório base ────────────────────────────────
            os.makedirs(worktree_base, exist_ok=True)

            # ── Passo 4: Verificar se worktree já existe ────────────────────
            if os.path.exists(worktree_path):
                # Worktree já existe — pode ser de uma execução anterior
                logger.info(
                    f"Fork {fork_id}: worktree já existe em {worktree_path}, "
                    f"reusando (verifique se está limpo)"
                )
                self._worktrees[fork_id] = worktree_path
                return worktree_path

            # ── Passo 5: Criar worktree ──────────────────────────────────────
            result = subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "--force",  # Sobrescreve se existir (reusamos o path check acima)
                    worktree_path,
                    branch_name,
                ],
                cwd=parent_cwd,
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                stdout = result.stdout.decode("utf-8", errors="replace")
                logger.warning(
                    f"Fork {fork_id}: git worktree add falhou (exit {result.returncode}). "
                    f"stderr: {stderr[:200]}, stdout: {stdout[:200]}"
                )
                return None

            # ── Passo 6: Verificar que o worktree foi criado ────────────────
            if not os.path.isdir(worktree_path):
                logger.warning(
                    f"Fork {fork_id}: git worktree add retornou 0 mas "
                    f"{worktree_path} não existe"
                )
                return None

            # ── Sucesso ─────────────────────────────────────────────────────
            logger.info(
                f"Fork {fork_id}: worktree criado em {worktree_path}"
            )
            self._worktrees[fork_id] = worktree_path
            return worktree_path

        except subprocess.TimeoutExpired:
            logger.warning(
                f"Fork {fork_id}: timeout ({30}s) criando worktree"
            )
            return None
        except PermissionError as e:
            logger.warning(
                f"Fork {fork_id}: permission denied criando worktree: {e}"
            )
            return None
        except OSError as e:
            logger.warning(
                f"Fork {fork_id}: OS error criando worktree: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Fork {fork_id}: erro inesperado criando worktree: {e}",
                exc_info=True,
            )
            return None

    async def remove_worktree(self, fork_id: str) -> bool:
        """
        Remove um worktree isolado e limpa a branch associada.

        Executa 'git worktree remove --force' para limpeza completa.

        Args:
            fork_id: ID do fork

        Returns:
            True se removido com sucesso, False caso contrário
        """
        worktree_path = self._worktrees.get(fork_id)
        if not worktree_path:
            logger.debug(f"Fork {fork_id}: worktree path não encontrado no tracking")
            return False

        # Determinar o parent_cwd a partir do worktree path
        # worktree_path = parent_cwd/.worktrees/agent-xxx → parent_cwd = avo
        parent_cwd = os.path.dirname(os.path.dirname(worktree_path))
        branch_name = f"worktree/agent-{fork_id[:8]}"

        try:
            # Remover worktree do git
            result = subprocess.run(
                [
                    "git",
                    "worktree",
                    "remove",
                    "--force",
                    worktree_path,
                ],
                cwd=parent_cwd,
                capture_output=True,
                timeout=15,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                # Não é fatal — o worktree pode já ter sido removido
                logger.warning(
                    f"Fork {fork_id}: git worktree remove falhou "
                    f"(exit {result.returncode}): {stderr[:150]}"
                )
                # Cleanup manual do diretório se existir
                if os.path.exists(worktree_path):
                    try:
                        shutil.rmtree(worktree_path)
                        logger.info(
                            f"Fork {fork_id}: worktree removido manualmente: {worktree_path}"
                        )
                    except OSError as e:
                        logger.warning(
                            f"Fork {fork_id}: cleanup manual também falhou: {e}"
                        )
            else:
                logger.info(
                    f"Fork {fork_id}: worktree removido via git: {worktree_path}"
                )

            # Tentar deletar a branch (best effort — pode já não existir)
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=parent_cwd,
                capture_output=True,
                timeout=5,
            )
            logger.debug(
                f"Fork {fork_id}: branch {branch_name} deletada (ou não existia)"
            )

            # Remover do tracking
            del self._worktrees[fork_id]
            return True

        except subprocess.TimeoutExpired:
            logger.warning(f"Fork {fork_id}: timeout removendo worktree")
            return False
        except Exception as e:
            logger.error(
                f"Fork {fork_id}: erro removendo worktree: {e}",
                exc_info=True,
            )
            # Ainda limpa do tracking mesmo se remoção física falhar
            if fork_id in self._worktrees:
                del self._worktrees[fork_id]
            return False

    # =========================================================================
    # Fork Spawn
    # =========================================================================

    async def spawn_fork(
        self,
        params: AgentSpawnParams,
        context: dict[str, Any],
        parent_messages: list[dict],
        assistant_message: dict,
    ) -> AgentResult:
        """
        Spawn um fork subagent.

        Fluxo:
        1. Verifica recursive guard (is_in_fork_child)
        2. Constrói mensagens forkadas
        3. Se isolation=worktree: cria worktree
        4. Se worktree: adiciona notice
        5. Retorna AgentResult com status fork

        Equivalente ao fork path em agent_core.tsx call().

        Args:
            params: Parâmetros do spawn
            context: Contexto de execução (cwd, parent_agent_id, etc.)
            parent_messages: Mensagens do conversation history
            assistant_message: Última mensagem do assistant (com tool_use blocks)

        Returns:
            AgentResult com status "fork"

        Raises:
            ValueError: Se fork não está habilitado
            ValueError: Se já está em fork child (recursive guard)
        """
        # ── Verificações iniciais ────────────────────────────────────────────
        if not self.is_fork_subagent_enabled():
            logger.error(
                f"Fork spawn bloqueado: feature gate desabilitado. "
                f"Directive: '{params.prompt[:80]}...'"
            )
            raise ValueError("Fork subagent não está habilitado")

        # Guard contra fork recursivo
        if self.is_in_fork_child(parent_messages):
            logger.error(
                f"Fork spawn bloqueado: recursive guard activated. "
                f"Directive: '{params.prompt[:80]}...'"
            )
            raise ValueError(
                "Fork is not available inside a forked worker. "
                "Complete your task directly using your tools."
            )

        # Gerar ID único para o fork
        fork_id = self._generate_id()
        logger.info(
            f"Fork {fork_id}: spawning. Directive: '{params.prompt[:80]}...', "
            f"isolation: {params.isolation.value}"
        )

        # ── Construir mensagens forkadas ─────────────────────────────────────
        fork_messages = self.build_forked_messages(
            params.prompt, assistant_message
        )

        # ── Criar worktree se isolation=worktree ───────────────────────────
        worktree_path: str | None = None
        if params.isolation == IsolationMode.WORKTREE:
            worktree_path = await self.create_worktree(
                fork_id,
                context.get("cwd"),
            )
            if worktree_path:
                # Adicionar worktree notice após as mensagens forkadas
                worktree_notice = self.build_worktree_notice(
                    context.get("cwd", os.getcwd()),
                    worktree_path,
                )
                fork_messages.append(
                    self._create_user_message(worktree_notice)
                )
                logger.info(
                    f"Fork {fork_id}: worktree notice adicionada. "
                    f"worktree={worktree_path}"
                )

        # ── Criar ForkContext para tracking ────────────────────────────────
        fork_ctx = ForkContext(
            fork_id=fork_id,
            parent_agent_id=context.get("parent_agent_id", ""),
            directive=params.prompt,
            worktree_path=worktree_path,
        )
        self._active_forks[fork_id] = fork_ctx

        # ── Retornar resultado ─────────────────────────────────────────────
        result = AgentResult(
            status="fork",
            prompt=params.prompt,
            agent_id=fork_id,
            worktree_path=worktree_path,
            fork_parent_messages=fork_messages,
        )
        logger.info(
            f"Fork {fork_id}: spawn concluído. "
            f"status=fork, worktree={worktree_path}, "
            f"fork_messages={len(fork_messages)}"
        )
        return result

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def get_active_forks(self) -> list[ForkContext]:
        """
        Retorna lista de forks ativos.

        Returns:
            Lista de ForkContext para todos os forks em andamento
        """
        return list(self._active_forks.values())

    def get_fork(self, fork_id: str) -> ForkContext | None:
        """
        Retorna contexto de um fork específico.

        Args:
            fork_id: ID do fork

        Returns:
            ForkContext ou None se não encontrado
        """
        return self._active_forks.get(fork_id)

    async def complete_fork(self, fork_id: str) -> None:
        """
        Marca um fork como completo e limpa todos os recursos associados.

        Executa cleanup de worktree e remove do tracking.

        Args:
            fork_id: ID do fork completado
        """
        async with self._lock:
            worktree_cleanup_ok = True

            # Cleanup worktree se existir
            if fork_id in self._worktrees:
                worktree_cleanup_ok = await self.remove_worktree(fork_id)

            # Remover do tracking
            if fork_id in self._active_forks:
                del self._active_forks[fork_id]

            status = "OK" if worktree_cleanup_ok else "partial"
            logger.info(
                f"Fork {fork_id}: completado e limpo ({status})"
            )

    async def abandon_fork(self, fork_id: str, reason: str) -> None:
        """
        Abandona um fork em andamento por erro ou cancelamento.

        Args:
            fork_id: ID do fork
            reason: Motivo do abandono
        """
        async with self._lock:
            logger.warning(f"Fork {fork_id}: abandonado — {reason}")

            if fork_id in self._worktrees:
                await self.remove_worktree(fork_id)

            if fork_id in self._active_forks:
                del self._active_forks[fork_id]

    # =========================================================================
    # Helpers
    # =========================================================================

    def _generate_id(self, tamanho: int = 12) -> str:
        """
        Gera um ID único para o fork.

        Args:
            tamanho: Comprimento do ID (default: 12)

        Returns:
            String aleatória alfanumérica com tamanho especificado
        """
        alfabeto = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(alfabeto) for _ in range(tamanho))

    def _clone_message(self, message: dict) -> dict:
        """
        Clona uma mensagem para não mutar o original.

        Usa deepcopy para copiar recursivamente toda a estrutura.

        Args:
            message: Mensagem original

        Returns:
            Cópia profunda da mensagem com novo UUID gerado
        """
        cloned: dict = copy.deepcopy(message)
        # Gerar novo UUID para evitar collisions com a mensagem original
        if "uuid" in cloned:
            cloned["uuid"] = self._generate_id()
        if "message" in cloned and isinstance(cloned["message"], dict):
            if "uuid" in cloned["message"]:
                cloned["message"]["uuid"] = self._generate_id()
        return cloned

    def _create_user_message(
        self,
        content: str | list[dict],
    ) -> dict:
        """
        Cria uma mensagem de usuário formatada.

        Args:
            content: Conteúdo — string ou list de content blocks

        Returns:
            Dict de mensagem no formato API-compatible com "role": "user"
            e campos internos (uuid, type, message) para rastreamento.
        """
        if isinstance(content, str):
            content_blocks: list[dict] = [
                {"type": "text", "text": content}
            ]
        else:
            content_blocks = content

        return {
            # API-compatible field
            "role": "user",
            # Internal tracking fields
            "type": "user",
            "uuid": self._generate_id(),
            "message": {
                "content": content_blocks,
            },
        }


# =============================================================================
# Auto-Approve Modes (Plan Mode)
# =============================================================================
# Inspirado em autonomous_mode.rs (Rust).


class AutoApproveMode:
    """
    Modo de auto-aprovação para execução de ferramentas.

    Define como o agente lida com operações que requerem confirmação:
    - NONE: todas as tool calls requerem confirmação do usuário
    - ACCEPT_EDITS: auto-aprova edições em arquivos existentes
    - BYPASS: aprova tudo incluindo bash/shell (perigoso!)
    - PLAN: mostra plano antes de executar ações

    Equivalente a AutoApproveMode em autonomous_mode.rs.
    """

    #: Nenhuma auto-aprovação — todas as tool calls requerem confirmação.
    NONE = "none"

    #: Auto-aprova edições em arquivos existentes (não novos arquivos).
    ACCEPT_EDITS = "acceptEdits"

    #: Bypassa todas as permissões — aprova tudo incluindo bash/shell.
    #: ⚠️ REQUER WARNING ACEITO pelo usuário antes de ativar.
    BYPASS = "bypassPermissions"

    #: Mostra plano antes de executar (plan mode).
    PLAN = "plan"

    @classmethod
    def from_string(cls, value: str) -> "AutoApproveMode":
        """
        Retorna o modo correspondente a uma string.

        Args:
            value: String representando o modo

        Returns:
            AutoApproveMode correspondente

        Raises:
            ValueError: Se a string não corresponde a nenhum modo
        """
        for mode in (cls.NONE, cls.ACCEPT_EDITS, cls.BYPASS, cls.PLAN):
            if mode == value:
                return cls()
        raise ValueError(f"Unknown AutoApproveMode: {value!r}")

    @classmethod
    def all_modes(cls) -> list[str]:
        """Retorna lista de todos os modos disponíveis."""
        return [cls.NONE, cls.ACCEPT_EDITS, cls.BYPASS, cls.PLAN]


class AutoModeState:
    """
    Estado de auto-approve para uma sessão.

    Tracks se o usuário habilitou auto-approve, qual modo está ativo,
    e metadados de ativação (session ID, turn number).

    Equivalente a AutoModeState em autonomous_mode.rs.

    Attributes:
        mode: Modo atual (NONE, ACCEPT_EDITS, BYPASS, PLAN)
        warning_accepted: True se o usuário viu e aceitou o warning de risco
        activated_session: Session ID quando bypass foi ativado
        activated_turn: Turn number quando bypass foi ativado
    """

    def __init__(
        self,
        mode: str = AutoApproveMode.NONE,
        warning_accepted: bool = False,
        activated_session: str | None = None,
        activated_turn: int | None = None,
    ) -> None:
        self.mode = mode
        self.warning_accepted = warning_accepted
        self.activated_session = activated_session
        self.activated_turn = activated_turn

    def auto_approves_bash(self) -> bool:
        """
        True se este modo auto-aprova bash/shell command execution.

        Returns:
            True para BYPASS mode
        """
        return self.mode == AutoApproveMode.BYPASS

    def auto_approves_edits(self) -> bool:
        """
        True se este modo auto-aprova edições em arquivos existentes.

        Returns:
            True para ACCEPT_EDITS e BYPASS
        """
        return self.mode in (AutoApproveMode.ACCEPT_EDITS, AutoApproveMode.BYPASS)

    def is_plan_mode(self) -> bool:
        """
        True se este modo mostra plano antes de executar.

        Returns:
            True para PLAN mode
        """
        return self.mode == AutoApproveMode.PLAN

    def is_bypass(self) -> bool:
        """True se este modo é bypass (aprovação total)."""
        return self.mode == AutoApproveMode.BYPASS

    def is_accept_edits(self) -> bool:
        """True se este modo é acceptEdits."""
        return self.mode == AutoApproveMode.ACCEPT_EDITS

    def label(self) -> str:
        """
        Retorna label curto para display na status line.

        Returns:
            Label descritivo ou string vazia
        """
        return {
            AutoApproveMode.NONE: "",
            AutoApproveMode.ACCEPT_EDITS: "auto-edit",
            AutoApproveMode.BYPASS: "bypass",
            AutoApproveMode.PLAN: "plan-mode",
        }.get(self.mode, "")

    def activate_bypass(
        self,
        session_id: str,
        turn: int,
    ) -> None:
        """
        Ativa bypass mode.

        Requer que warning_accepted seja True (usuário viu o warning).

        Args:
            session_id: ID da sessão
            turn: Número do turno
        """
        if not self.warning_accepted:
            logger.warning(
                f"Bypass activation attempted without accepted warning. "
                f"session={session_id}, turn={turn}"
            )
            return
        self.mode = AutoApproveMode.BYPASS
        self.activated_session = session_id
        self.activated_turn = turn
        logger.info(
            f"Bypass mode activated. session={session_id}, turn={turn}"
        )

    def set_mode(self, mode: str) -> None:
        """
        Define o modo de auto-approve.

        Args:
            mode: Novo modo
        """
        old = self.mode
        self.mode = mode
        logger.info(f"AutoApproveMode changed: {old} → {mode}")

    def reset(self) -> None:
        """Reseta para nenhum auto-approve."""
        self.mode = AutoApproveMode.NONE
        self.warning_accepted = False
        self.activated_session = None
        self.activated_turn = None
        logger.info("AutoApproveMode reset to NONE")


# =============================================================================
# Singleton Instance
# =============================================================================

# Instância global do ForkManager — reuse em toda a aplicação.
fork_manager = ForkManager()
