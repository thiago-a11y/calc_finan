"""
Agent Registry — Catálogo centralizado de tipos de agentes.

Permite:
- Registrar e descobrir tipos de agentes
- Filtrar por capabilities, permissions, MCP requirements
- Builder para spawn com parâmetros

Uso:
    from core.agents import AgentRegistry

    registry = AgentRegistry.get_instance()
    agent = registry.get("tech_lead")
    all_agents = registry.list_active()

Equivalente a loadAgentsDir.ts (TypeScript).
"""

import logging
from core.agents.base import (
    AgentDefinition,
    AgentPermissionMode,
    AgentSpawnParams,
    AgentResult,
    IsolationMode,
)

logger = logging.getLogger("synerium.agents")


class AgentRegistry:
    """
    Registry centralizado de definições de agentes.

    SINGLETON — acesso via AgentRegistry.get_instance()

    Permite registro tardio (late registration) de agentes,
    filtragem por permissions e capabilities, e spawning
    com parâmetros padronizados.

    Equivalente a agentDefinitions em loadAgentsDir.ts.

    Example:
        >>> registry = AgentRegistry.get_instance()
        >>> agents = registry.list_active()
        >>> tech_lead = registry.get("tech_lead")
        >>> if tech_lead:
        ...     print(f"Found: {tech_lead.name}")

    """

    _instance: "AgentRegistry | None" = None

    def __init__(self):
        self._agents: dict[str, AgentDefinition] = {}
        self._lock = False  # Placeholder para threading lock

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """
        Retorna a instância singleton do registry.

        Cria e inicializa no primeiro acesso.
        """
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_built_in_agents()
            logger.info(f"[AGENTS] Registry inicializado com {cls._instance.total} agentes")
        return cls._instance

    # =============================================================================
    # Registration
    # =============================================================================

    def register(self, definition: AgentDefinition) -> None:
        """
        Registra um tipo de agente no catálogo.

        Sobrescreve se já existir um agent_type igual.

        Args:
            definition: Definição completa do agente
        """
        self._agents[definition.agent_type] = definition
        logger.debug(
            f"[AGENTS] Registrado: {definition.agent_type} — {definition.name}"
        )

    def register_builtin(
        self,
        agent_type: str,
        name: str,
        description: str,
        tools: list[str] | None = None,
        max_turns: int = 50,
        model: str | None = None,
        permission_mode: AgentPermissionMode = AgentPermissionMode.ACCEPT_EDITS,
        isolation: IsolationMode = IsolationMode.NONE,
        background: bool = False,
        color: str | None = None,
        required_mcp_servers: list[str] | None = None,
    ) -> AgentDefinition:
        """
        Helper para registrar um agente built-in rapidamente.

        Args:
            agent_type: Identificador único
            name: Nome de exibição
            description: Descrição curta
            tools: Tools disponíveis (None = todas)
            max_turns: Máximo de turnos
            model: Modelo LLM preferido
            permission_mode: Modo de permissão
            isolation: Modo de isolamento
            background: Sempre em background
            color: Cor hex para UI
            required_mcp_servers: Servers MCP requeridos

        Returns:
            A definição criada e registrada
        """
        definition = AgentDefinition(
            agent_type=agent_type,
            name=name,
            description=description,
            tools=tools,
            max_turns=max_turns,
            model=model,
            permission_mode=permission_mode,
            isolation=isolation,
            background=background,
            source="built-in",
            color=color,
            required_mcp_servers=required_mcp_servers or [],
        )
        self.register(definition)
        return definition

    def unregister(self, agent_type: str) -> bool:
        """
        Remove um agente do catálogo.

        Args:
            agent_type: ID do agente a remover

        Returns:
            True se foi removido, False se não existia
        """
        if agent_type in self._agents:
            del self._agents[agent_type]
            logger.debug(f"[AGENTS] Removido: {agent_type}")
            return True
        return False

    # =============================================================================
    # Retrieval
    # =============================================================================

    def get(self, agent_type: str) -> AgentDefinition | None:
        """
        Retorna definição de um agente por tipo.

        Args:
            agent_type: Identificador do agente

        Returns:
            Definição do agente ou None se não existir
        """
        return self._agents.get(agent_type)

    def get_or_raise(self, agent_type: str) -> AgentDefinition:
        """
        Retorna definição de um agente ou levanta KeyError.

        Args:
            agent_type: Identificador do agente

        Returns:
            Definição do agente

        Raises:
            KeyError: Se agente não existir
        """
        agent = self.get(agent_type)
        if agent is None:
            available = ", ".join(self.list_agent_types())
            raise KeyError(
                f"Agente '{agent_type}' não encontrado. "
                f"Disponíveis: {available}"
            )
        return agent

    def list_active(self) -> list[AgentDefinition]:
        """
        Lista todos os agentes ativos (built-in + custom).

        Returns:
            Lista de definições de agentes
        """
        return list(self._agents.values())

    def list_agent_types(self) -> list[str]:
        """
        Lista apenas os tipos (IDs) de agentes registrados.

        Returns:
            Lista de agent_type strings
        """
        return list(self._agents.keys())

    def list_by_source(self, source: str) -> list[AgentDefinition]:
        """
        Lista agentes filtrados por origem.

        Args:
            source: Origem (ex: "built-in", "catalog", "custom")

        Returns:
            Lista de agentes da origem especificada
        """
        return [a for a in self._agents.values() if a.source == source]

    def list_by_permission(
        self, permission_mode: AgentPermissionMode
    ) -> list[AgentDefinition]:
        """
        Lista agentes filtrados por modo de permissão.

        Args:
            permission_mode: Modo de permissão desejado

        Returns:
            Lista de agentes com o modo especificado
        """
        return [
            a
            for a in self._agents.values()
            if a.permission_mode == permission_mode
        ]

    def list_by_mcp_requirement(
        self, mcp_server: str
    ) -> list[AgentDefinition]:
        """
        Lista agentes que requerem um server MCP específico.

        Args:
            mcp_server: Nome do server MCP

        Returns:
            Lista de agentes que requerem o server
        """
        return [
            a
            for a in self._agents.values()
            if mcp_server in a.required_mcp_servers
        ]

    def list_background_agents(self) -> list[AgentDefinition]:
        """
        Lista agentes que sempre executam em background.

        Returns:
            Lista de agentes background
        """
        return [a for a in self._agents.values() if a.background]

    # =============================================================================
    # Filtering
    # =============================================================================

    def filter_by_tools(self, available_tools: list[str]) -> list[AgentDefinition]:
        """
        Filtra agentes que podem usar as tools disponíveis.

        Um agente é retornado se:
        - Não requer nenhuma tool específica, OU
        - Requer apenas tools que estão na lista disponível

        Args:
            available_tools: Lista de nomes de tools disponíveis

        Returns:
            Lista de agentes que podem ser instanciados
        """
        result = []
        for agent in self._agents.values():
            if agent.tools is None:
                # Agente sem requirements específicos
                result.append(agent)
            elif all(t in available_tools for t in agent.tools):
                # Todas as tools requeridas estão disponíveis
                result.append(agent)
        return result

    def filter_denied(
        self,
        denied_types: set[str],
    ) -> list[AgentDefinition]:
        """
        Remove agentes que estão na lista de negados.

        Args:
            denied_types: Set de agent_types negados

        Returns:
            Lista de agentes não negados
        """
        return [a for a in self._agents.values() if a.agent_type not in denied_types]

    def filter_by_mcp_servers(
        self,
        available_servers: list[str],
    ) -> list[AgentDefinition]:
        """
        Filtra agentes cujos MCP servers estão disponíveis.

        Args:
            available_servers: Lista de servers MCP conectados

        Returns:
            Lista de agentes com MCP requirements satisfeitos
        """
        result = []
        for agent in self._agents.values():
            if not agent.required_mcp_servers:
                result.append(agent)
            elif all(s in available_servers for s in agent.required_mcp_servers):
                result.append(agent)
        return result

    # =============================================================================
    # Properties
    # =============================================================================

    @property
    def total(self) -> int:
        """Total de agentes registrados."""
        return len(self._agents)

    @property
    def builtin_count(self) -> int:
        """Total de agentes built-in."""
        return len(self.list_by_source("built-in"))

    @property
    def custom_count(self) -> int:
        """Total de agentes custom (não built-in)."""
        return len(self.list_by_source("custom"))

    # =============================================================================
    # Built-in Agents Registration
    # =============================================================================

    def _register_built_in_agents(self) -> None:
        """
        Registra todos os agentes built-in do Synerium Factory.

        Called automatically on get_instance() first call.

        Agentes:
        - general_purpose: Fork child (propósito geral)
        - tech_lead: Arquiteto e líder técnico
        - backend_dev: Desenvolvedor backend PHP/Python
        - frontend_dev: Desenvolvedor frontend React/TS
        - qa_engineer: Engenheiro de QA e testes
        """
        # ── General Purpose (Fork Child) ───────────────────────────────────────
        self.register_builtin(
            agent_type="general_purpose",
            name="General Purpose",
            description="Fork worker — executa tarefa diretamente herdando contexto do parent",
            tools=None,  # Herda todas do parent
            max_turns=200,
            model=None,  # Herda do parent
            permission_mode=AgentPermissionMode.BUBBLE,
            isolation=IsolationMode.NONE,
            background=True,
            color="#6366f1",
        )

        # ── Tech Lead ──────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="tech_lead",
            name="Tech Lead / Arquiteto de Software",
            description="Planejamento técnico, arquitetura de sistemas, code review",
            tools=["Bash", "Read", "Write", "Edit", "Grep"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#8b5cf6",
        )

        # ── Backend Dev ─────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="backend_dev",
            name="Desenvolvedor Backend PHP/Python",
            description="APIs REST, migrations, banco de dados, integração",
            tools=["Bash", "Read", "Write", "Edit", "Grep"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.WORKTREE,
            background=False,
            color="#3b82f6",
        )

        # ── Frontend Dev ─────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="frontend_dev",
            name="Desenvolvedor Frontend React/TypeScript",
            description="Componentes React, TypeScript, CSS, performance",
            tools=["Bash", "Read", "Write", "Edit", "Grep"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.WORKTREE,
            background=False,
            color="#06b6d4",
        )

        # ── QA Engineer ─────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="qa_engineer",
            name="Engenheiro de QA e Segurança",
            description="Testes automatizados, validação, QA gates",
            tools=["Bash", "Read"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#10b981",
        )

        # ── PM Agent ────────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="pm_agent",
            name="Product Manager",
            description="Gestão de produto, priorização, roadmap, métricas",
            tools=["Bash", "Read", "Write"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.PLAN,
            isolation=IsolationMode.NONE,
            background=False,
            color="#f59e0b",
        )

        # ── DevOps Engineer ────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="devops",
            name="Engenheiro DevOps e Infraestrutura",
            description="CI/CD, Docker, Kubernetes, AWS, monitoramento",
            tools=["Bash", "Read", "Write", "Edit"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.WORKTREE,
            background=False,
            color="#ef4444",
        )

        # ── Security Engineer ───────────────────────────────────────────────────
        self.register_builtin(
            agent_type="security",
            name="Especialista em Segurança",
            description="Análise de vulnerabilidades, pentest, compliance LGPD",
            tools=["Bash", "Read", "Write", "Grep"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.PLAN,
            isolation=IsolationMode.NONE,
            background=False,
            color="#dc2626",
        )

        # ── Integration Specialist ─────────────────────────────────────────────
        self.register_builtin(
            agent_type="integration",
            name="Especialista em Integrações e APIs Externas",
            description="Integração com serviços externos, webhooks, APIs",
            tools=["Bash", "Read", "Write", "Edit", "Grep"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#9333ea",
        )

        # ── Test Master ─────────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="test_master",
            name="Test Master",
            description="Gestão de testes automatizados, validação pré-deploy",
            tools=["Bash", "Read", "Write"],
            max_turns=50,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#22c55e",
        )

        # ── GitHub Master ───────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="github_master",
            name="GitHub Master",
            description="Gestão de repositórios, branches, PRs e Code Review",
            tools=["Bash", "Read", "Write"],
            max_turns=30,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#24292e",
        )

        # ── GitBucket Master ────────────────────────────────────────────────────
        self.register_builtin(
            agent_type="gitbucket_master",
            name="GitBucket Master",
            description="Gestão de repositórios on-premise via GitBucket",
            tools=["Bash", "Read", "Write"],
            max_turns=30,
            model="sonnet",
            permission_mode=AgentPermissionMode.ACCEPT_EDITS,
            isolation=IsolationMode.NONE,
            background=False,
            color="#5c94fc",
        )

        logger.info(
            f"[AGENTS] {self.builtin_count} agentes built-in registrados: "
            f"{', '.join(self.list_agent_types())}"
        )
