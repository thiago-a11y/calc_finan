"""
Prompts do workflow BMAD (Autonomous Squads) — 4 fases.

Fonte original: api/routes/tarefas.py:1189-1293 (extraido na Fase 2.1).
Contem templates de cada fase, mapeamento de agentes e gates de aprovacao.
"""

from core.prompts.registry import PromptSection, SectionPriority
from core.prompts.tools import INSTRUCAO_TOOLS


# Nomes das fases BMAD
FASES_BMAD: dict[int, str] = {
    1: "Analise",
    2: "Planejamento",
    3: "Solucao",
    4: "Implementacao",
}

# Templates de prompt por fase (com placeholders {titulo}, {descricao}, {output_anterior})
_PROMPT_FASE_1 = (
    "FASE 1 — ANALISE\n"
    "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
    "Voce deve:\n"
    "1. Analisar o problema/feature solicitado\n"
    "2. Pesquisar viabilidade tecnica (use ler_arquivo_syneriumx e buscar_no_syneriumx para ver o codigo atual)\n"
    "3. Identificar riscos e dependencias\n"
    "4. Produzir um Product Brief com escopo, objetivo e criterios de sucesso\n"
    "Responda de forma estruturada em portugues brasileiro."
    + INSTRUCAO_TOOLS
)

_PROMPT_FASE_2 = (
    "FASE 2 — PLANEJAMENTO\n"
    "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
    "Resultado da Fase 1 (Analise):\n{output_anterior}\n\n"
    "Voce deve:\n"
    "1. Criar um PRD (Product Requirements Document) completo\n"
    "2. Definir requisitos funcionais e nao-funcionais\n"
    "3. Criar epicos e stories com criterios de aceitacao BDD (Given/When/Then)\n"
    "4. Priorizar e estimar complexidade\n"
    "Responda de forma estruturada em portugues brasileiro."
    + INSTRUCAO_TOOLS
)

_PROMPT_FASE_3 = (
    "FASE 3 — SOLUCAO (Arquitetura)\n"
    "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
    "Resultado do Planejamento:\n{output_anterior}\n\n"
    "Voce deve:\n"
    "1. Definir arquitetura tecnica (componentes, patterns, stack)\n"
    "2. Criar ADRs (Architecture Decision Records) para decisoes criticas\n"
    "3. Fazer Implementation Readiness Check\n"
    "4. Listar arquivos que serao criados/modificados (use listar_diretorio_syneriumx para ver a estrutura atual)\n"
    "Responda de forma estruturada em portugues brasileiro."
    + INSTRUCAO_TOOLS
)

_PROMPT_FASE_4 = (
    "FASE 4 — IMPLEMENTACAO\n"
    "Tarefa: {titulo}\nDescricao: {descricao}\n\n"
    "Arquitetura definida:\n{output_anterior}\n\n"
    "Voce deve:\n"
    "1. Use ler_arquivo_syneriumx para ler os arquivos que serao modificados\n"
    "2. Implementar a solucao seguindo a arquitetura definida\n"
    "3. Use propor_edicao_syneriumx para CADA arquivo criado/modificado\n"
    "4. Escrever testes para cada componente\n"
    "5. Fazer code review cruzado dos arquivos propostos\n"
    "6. Validar que todos os criterios de aceitacao passam\n\n"
    "REGRA CRITICA: Todo codigo DEVE ser enviado via propor_edicao_syneriumx.\n"
    "NAO cole codigo no chat. CADA arquivo = uma proposta separada.\n"
    "Formato: caminho_do_arquivo|||conteudo_completo|||descricao_da_mudanca\n"
    "Responda em portugues brasileiro."
    + INSTRUCAO_TOOLS
)

# Dict de prompts por fase (backward compatible com PROMPTS_FASE)
PROMPTS_FASE: dict[int, str] = {
    1: _PROMPT_FASE_1,
    2: _PROMPT_FASE_2,
    3: _PROMPT_FASE_3,
    4: _PROMPT_FASE_4,
}

# Agentes por fase (perfis do catalogo)
AGENTES_POR_FASE: dict[int, list[str]] = {
    1: ["product_manager", "tech_lead"],
    2: ["product_manager", "frontend_dev", "tech_lead"],
    3: ["tech_lead", "backend_dev", "qa_seguranca"],
    4: ["backend_dev", "frontend_dev", "qa_seguranca"],
}

# Gates por fase
GATES_FASE: dict[int, str] = {
    1: "soft",   # Auto-pass (opcional)
    2: "hard",   # CEO/Operations Lead deve aprovar PRD
    3: "hard",   # Implementation Readiness Check
    4: "hard",   # Deploy requer aprovacao
}

# Secoes registraveis (templates como PromptSection)
FASE_1 = PromptSection(
    name="bmad.fase_1",
    content=_PROMPT_FASE_1,
    is_static=True,
    priority=SectionPriority.CONTEXT,
    tags=("bmad", "fase_1"),
)

FASE_2 = PromptSection(
    name="bmad.fase_2",
    content=_PROMPT_FASE_2,
    is_static=True,
    priority=SectionPriority.CONTEXT,
    tags=("bmad", "fase_2"),
)

FASE_3 = PromptSection(
    name="bmad.fase_3",
    content=_PROMPT_FASE_3,
    is_static=True,
    priority=SectionPriority.CONTEXT,
    tags=("bmad", "fase_3"),
)

FASE_4 = PromptSection(
    name="bmad.fase_4",
    content=_PROMPT_FASE_4,
    is_static=True,
    priority=SectionPriority.CONTEXT,
    tags=("bmad", "fase_4"),
)


def registrar(registry) -> None:
    """Registra todas as secoes BMAD no registry."""
    registry.register(FASE_1)
    registry.register(FASE_2)
    registry.register(FASE_3)
    registry.register(FASE_4)
