"""
Permissões Granulares — Definição de módulos e permissões padrão por papel.

Cada módulo tem 5 ações: view, create, edit, delete, export.
Papéis definem permissões base. Overrides granulares por usuário são possíveis.
"""

# Módulos do Synerium Factory
MODULOS = [
    {"id": "dashboard", "nome": "Painel Geral", "icone": "📊"},
    {"id": "squads", "nome": "Gestão de Squads", "icone": "👥"},
    {"id": "agents", "nome": "Agentes e Chat", "icone": "🤖"},
    {"id": "approvals", "nome": "Aprovações", "icone": "✅"},
    {"id": "reunioes", "nome": "Reuniões e Rodadas", "icone": "🎤"},
    {"id": "rag", "nome": "Base de Conhecimento", "icone": "📚"},
    {"id": "escritorio_virtual", "nome": "Escritório Virtual", "icone": "🏢"},
    {"id": "configuracoes", "nome": "Configurações", "icone": "⚙️"},
    {"id": "tarefas", "nome": "Gestão de Tarefas", "icone": "📋"},
    {"id": "skills", "nome": "Skills e Ferramentas", "icone": "🔧"},
    {"id": "relatorios", "nome": "Relatórios e Standup", "icone": "📄"},
    {"id": "projetos", "nome": "Projetos", "icone": "📁"},
    {"id": "admin", "nome": "Administração", "icone": "🔒"},
]

ACOES = ["view", "create", "edit", "delete", "export"]

# Permissões padrão por papel (role)
# True = permitido, False = negado
_TUDO = {acao: True for acao in ACOES}
_SOMENTE_VER = {"view": True, "create": False, "edit": False, "delete": False, "export": False}
_VER_E_CRIAR = {"view": True, "create": True, "edit": False, "delete": False, "export": False}
_VER_EDITAR = {"view": True, "create": True, "edit": True, "delete": False, "export": True}
_NADA = {acao: False for acao in ACOES}

PERMISSOES_POR_PAPEL: dict[str, dict[str, dict[str, bool]]] = {
    "ceo": {m["id"]: _TUDO.copy() for m in MODULOS},
    "diretor_tecnico": {m["id"]: _TUDO.copy() for m in MODULOS},
    "operations_lead": {m["id"]: _TUDO.copy() for m in MODULOS},
    "pm_central": {
        "dashboard": _TUDO, "squads": _TUDO, "agents": _TUDO,
        "approvals": _VER_EDITAR, "reunioes": _TUDO, "rag": _TUDO,
        "escritorio_virtual": _TUDO, "configuracoes": _SOMENTE_VER,
        "tarefas": _TUDO, "skills": _VER_EDITAR, "relatorios": _TUDO,
        "projetos": _VER_EDITAR, "admin": _NADA,
    },
    "lider": {
        "dashboard": _TUDO, "squads": _VER_EDITAR, "agents": _TUDO,
        "approvals": _VER_EDITAR, "reunioes": _TUDO, "rag": _VER_EDITAR,
        "escritorio_virtual": _TUDO, "configuracoes": _SOMENTE_VER,
        "tarefas": _TUDO, "skills": _SOMENTE_VER, "relatorios": _TUDO,
        "projetos": _VER_EDITAR, "admin": _NADA,
    },
    "desenvolvedor": {
        "dashboard": _SOMENTE_VER, "squads": _SOMENTE_VER, "agents": _TUDO,
        "approvals": _SOMENTE_VER, "reunioes": _VER_E_CRIAR, "rag": _VER_EDITAR,
        "escritorio_virtual": _TUDO, "configuracoes": _NADA,
        "tarefas": _VER_E_CRIAR, "skills": _SOMENTE_VER, "relatorios": _SOMENTE_VER,
        "projetos": _SOMENTE_VER, "admin": _NADA,
    },
    "marketing": {
        "dashboard": _SOMENTE_VER, "squads": _SOMENTE_VER, "agents": _TUDO,
        "approvals": _VER_E_CRIAR, "reunioes": _VER_E_CRIAR, "rag": _SOMENTE_VER,
        "escritorio_virtual": _TUDO, "configuracoes": _NADA,
        "tarefas": _VER_E_CRIAR, "skills": _SOMENTE_VER, "relatorios": _SOMENTE_VER,
        "projetos": _SOMENTE_VER, "admin": _NADA,
    },
    "financeiro": {
        "dashboard": _SOMENTE_VER, "squads": _SOMENTE_VER, "agents": _SOMENTE_VER,
        "approvals": _SOMENTE_VER, "reunioes": _SOMENTE_VER, "rag": _SOMENTE_VER,
        "escritorio_virtual": _SOMENTE_VER, "configuracoes": _NADA,
        "tarefas": _SOMENTE_VER, "skills": _NADA, "relatorios": _TUDO,
        "projetos": _SOMENTE_VER, "admin": _NADA,
    },
    "suporte": {
        "dashboard": _SOMENTE_VER, "squads": _SOMENTE_VER, "agents": _TUDO,
        "approvals": _SOMENTE_VER, "reunioes": _VER_E_CRIAR, "rag": _SOMENTE_VER,
        "escritorio_virtual": _TUDO, "configuracoes": _NADA,
        "tarefas": _VER_E_CRIAR, "skills": _SOMENTE_VER, "relatorios": _SOMENTE_VER,
        "projetos": _SOMENTE_VER, "admin": _NADA,
    },
    "membro": {
        "dashboard": _SOMENTE_VER, "squads": _SOMENTE_VER, "agents": _VER_E_CRIAR,
        "approvals": _SOMENTE_VER, "reunioes": _VER_E_CRIAR, "rag": _SOMENTE_VER,
        "escritorio_virtual": _SOMENTE_VER, "configuracoes": _NADA,
        "tarefas": _VER_E_CRIAR, "skills": _SOMENTE_VER, "relatorios": _SOMENTE_VER,
        "projetos": _SOMENTE_VER, "admin": _NADA,
    },
}


def calcular_permissoes_efetivas(
    papeis: list[str],
    overrides: dict | None = None,
) -> dict[str, dict[str, bool]]:
    """
    Calcula as permissões efetivas de um usuário.

    1. Junta as permissões base de todos os papéis (OR — se qualquer papel permite, permite)
    2. Aplica overrides granulares (se existirem — override tem prioridade)

    Returns:
        Dict com módulo → {view, create, edit, delete, export}
    """
    # Começar com nada
    efetivas: dict[str, dict[str, bool]] = {}
    for modulo in MODULOS:
        efetivas[modulo["id"]] = {acao: False for acao in ACOES}

    # Juntar permissões de todos os papéis (OR)
    for papel in papeis:
        perms_papel = PERMISSOES_POR_PAPEL.get(papel, {})
        for modulo_id, acoes in perms_papel.items():
            if modulo_id in efetivas:
                for acao, permitido in acoes.items():
                    if permitido:
                        efetivas[modulo_id][acao] = True

    # Aplicar overrides (se existirem)
    if overrides:
        for modulo_id, acoes in overrides.items():
            if modulo_id in efetivas and isinstance(acoes, dict):
                for acao, permitido in acoes.items():
                    if acao in ACOES and isinstance(permitido, bool):
                        efetivas[modulo_id][acao] = permitido

    return efetivas
