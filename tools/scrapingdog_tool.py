"""
Ferramenta ScrapingDog — Busca Google SERP via API.

Retorna resultados de busca do Google (títulos, links, snippets)
de forma rápida e confiável. Útil para:
- Pesquisa de concorrência
- Monitoramento de SEO
- Busca de soluções técnicas
- Análise de mercado
"""

import os
import logging
import requests
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger("synerium.tools.scrapingdog")


class ScrapingDogInput(BaseModel):
    """Entrada para busca no Google via ScrapingDog."""
    query: str = Field(description="Termo de busca no Google. Ex: 'crewai best practices 2026'")
    num_results: int = Field(default=5, description="Número de resultados (1-10)")


class ScrapingDogSearchTool(BaseTool):
    """
    Busca no Google via ScrapingDog API.

    Retorna resultados orgânicos do Google com título, link e snippet.
    Velocidade média: ~1.25s por request.
    """

    name: str = "scrapingdog_google_search"
    description: str = (
        "Busca no Google via ScrapingDog. Retorna resultados reais do Google "
        "(títulos, links, snippets). Use para pesquisar concorrência, "
        "soluções técnicas, documentação e análise de mercado."
    )
    args_schema: type = ScrapingDogInput

    def _run(self, query: str, num_results: int = 5) -> str:
        """Executa a busca no Google via ScrapingDog."""
        api_key = os.getenv("SCRAPINGDOG_API_KEY", "")
        if not api_key:
            return "Erro: SCRAPINGDOG_API_KEY não configurada no .env"

        try:
            response = requests.get(
                "https://api.scrapingdog.com/google",
                params={
                    "api_key": api_key,
                    "query": query,
                    "results": min(num_results, 10),
                    "country": "br",
                    "language": "pt-br",
                },
                timeout=15,
            )

            if response.status_code != 200:
                return f"Erro ScrapingDog: status {response.status_code}"

            data = response.json()
            resultados = data.get("organic_results", data.get("organic_data", []))

            if not resultados:
                return f"Nenhum resultado encontrado para: {query}"

            # Formatar resultados
            output = f"Resultados do Google para: '{query}'\n\n"
            for i, r in enumerate(resultados[:num_results], 1):
                titulo = r.get("title", "Sem título")
                link = r.get("link", r.get("url", ""))
                snippet = r.get("snippet", r.get("description", ""))
                output += f"{i}. {titulo}\n   {link}\n   {snippet}\n\n"

            return output

        except requests.Timeout:
            return "Erro: timeout na busca (>15s)"
        except Exception as e:
            logger.error(f"[SCRAPINGDOG] Erro: {e}")
            return f"Erro na busca: {str(e)}"
