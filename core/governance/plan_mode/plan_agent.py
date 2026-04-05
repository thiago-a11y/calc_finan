"""
Plan Agent — Agente especializado em planejamento.

Quando o Plan Mode está ativo, o PlanAgent assume o papel de
assistente de planejamento: analisa contexto, gera planos estruturados,
identifica riscos e sugere ações — tudo sem executar nada.

Integração:
- Luna detecta "modo plano" ou "planejar" e redireciona para o PlanAgent
- Mission Control pode ativar Plan Mode antes de grandes mudanças
- O plano gerado fica salvo na PlanSession para referência futura

Uso:
    from core.governance.plan_mode.plan_agent import plan_agent

    resultado = await plan_agent.gerar_plano(
        diretiva="Planejar a migração do SyneriumX para PostgreSQL",
        contexto={"fase": "3.2"},
    )
"""

from __future__ import annotations

import logging

logger = logging.getLogger("synerium.governance.agent")

# System prompt do agente de planejamento
PLAN_AGENT_PROMPT = """Voce e o Plan Agent do Synerium Factory.

Seu papel: gerar planos estruturados, analisar riscos e propor acoes.
Voce esta em Plan Mode — NUNCA execute acoes, apenas planeje.

REGRAS:
1. Responda APENAS com planos estruturados — nunca execute nada.
2. Use portugues brasileiro.
3. Estruture cada plano com:
   - Objetivo
   - Contexto atual
   - Etapas detalhadas (com responsavel e estimativa)
   - Riscos identificados
   - Criterios de sucesso
   - Dependencias
4. Se algo precisar de execucao, indique como "Acao pendente (requer Normal Mode)".
5. Seja conciso, factual e profissional.
6. Considere o contexto do Synerium Factory:
   - Fabrica de SaaS com agentes IA
   - Stack: Python 3.13, FastAPI, React 18, CrewAI, LangGraph
   - Multi-tenant, LGPD, 45 funcionarios
7. Priorize seguranca e reversibilidade nas sugestoes."""


class PlanAgent:
    """
    Agente de planejamento que opera exclusivamente em Plan Mode.

    Gera planos estruturados usando LLM sem executar ações.
    O plano gerado é salvo na PlanSession para referência.
    """

    def __init__(self):
        self._prompt = PLAN_AGENT_PROMPT

    async def gerar_plano(
        self,
        diretiva: str,
        contexto: dict | None = None,
        modelo: str = "sonnet",
    ) -> dict:
        """
        Gera um plano estruturado a partir de uma diretiva.

        Args:
            diretiva: o que deve ser planejado
            contexto: metadados adicionais
            modelo: modelo LLM para gerar o plano

        Returns:
            Dict com plano gerado e metadados
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from core.luna_engine import _obter_cadeia_fallback

            cadeia = _obter_cadeia_fallback(modelo)

            mensagens = [
                SystemMessage(content=self._prompt),
                HumanMessage(content=diretiva),
            ]

            plano = ""
            provider_usado = ""
            modelo_usado = ""

            for provider_id, modelo_nome, factory_fn in cadeia:
                try:
                    llm = factory_fn()
                    resposta = await llm.ainvoke(mensagens)
                    plano = resposta.content if hasattr(resposta, "content") else str(resposta)
                    provider_usado = provider_id
                    modelo_usado = modelo_nome
                    break
                except Exception as e:
                    logger.warning(f"[PlanAgent] Falha {provider_id}: {e}")
                    continue

            if not plano:
                return {
                    "sucesso": False,
                    "erro": "Todos os providers falharam ao gerar o plano",
                    "plano": "",
                }

            logger.info(
                f"[PlanAgent] Plano gerado ({len(plano)} chars) "
                f"via {provider_usado}"
            )

            return {
                "sucesso": True,
                "plano": plano,
                "modelo": modelo_usado,
                "provider": provider_usado,
                "diretiva": diretiva,
                "contexto": contexto or {},
            }

        except Exception as e:
            logger.error(f"[PlanAgent] Erro ao gerar plano: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "plano": "",
            }


# Instância singleton
plan_agent = PlanAgent()
