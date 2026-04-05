"""
Consolidation Prompt — Prompts para o processo de dream (consolidação).

O AutoDream usa estes prompts para instruir o LLM a:
1. Analisar snapshots brutos
2. Extrair informação relevante
3. Categorizar por tipo de memória
4. Gerar memórias consolidadas
5. Detectar duplicatas e mesclar

Uso:
    from core.memory.kairos.consolidation_prompt import (
        prompt_consolidar_snapshots,
        prompt_mesclar_memorias,
    )
"""

from __future__ import annotations

from core.memory.kairos.types import MemorySnapshotData, MemoryEntry


def prompt_consolidar_snapshots(
    snapshots: list[MemorySnapshotData],
    memorias_existentes: list[MemoryEntry] | None = None,
) -> str:
    """
    Gera o prompt para consolidar uma lista de snapshots em memórias.

    O LLM deve retornar JSON com as memórias extraídas.

    Args:
        snapshots: lista de snapshots brutos para processar
        memorias_existentes: memórias já consolidadas (para evitar duplicatas)

    Returns:
        Prompt completo para o LLM
    """
    # Formatar snapshots para o contexto
    snapshots_texto = ""
    for i, snap in enumerate(snapshots, 1):
        snapshots_texto += (
            f"\n--- Snapshot {i} (id={snap.id}, agente={snap.agente_id}, "
            f"source={snap.source.value}) ---\n"
            f"{snap.conteudo}\n"
        )

    # Formatar memórias existentes (se houver)
    memorias_texto = ""
    if memorias_existentes:
        memorias_texto = "\n\n## Memórias já existentes (para referência — evite duplicatas):\n"
        for mem in memorias_existentes[:20]:  # Limitar contexto
            memorias_texto += f"- [{mem.tipo.value}] {mem.titulo}: {mem.conteudo[:100]}...\n"

    return f"""Você é o sistema de memória Kairos do Synerium Factory.

Sua tarefa é consolidar snapshots brutos em memórias estruturadas.

## Regras:
1. Extraia APENAS informação factual e útil — ignore conversa casual.
2. Categorize cada memória como:
   - "episodica": evento específico (decisão tomada, bug encontrado, reunião)
   - "semantica": conhecimento geral (padrão, regra, conceito aprendido)
   - "procedural": como fazer algo (workflow, processo, passo-a-passo)
   - "estrategica": decisão de alto nível (roadmap, prioridade, meta)
3. Se um snapshot não contém informação útil, ignore-o.
4. Se a informação já existe nas memórias existentes, não crie duplicata.
5. Se a informação atualiza uma memória existente, indique o ID para atualizar.
6. Atribua relevância de 0.0 a 1.0 (decisões estratégicas = alta, detalhes técnicos menores = baixa).
7. Gere tags relevantes para busca futura.
8. Use português brasileiro.

## Snapshots para processar:
{snapshots_texto}
{memorias_texto}

## Formato de resposta (JSON):
Responda APENAS com JSON válido, sem markdown, sem explicação:
{{
  "memorias": [
    {{
      "titulo": "Título curto da memória",
      "conteudo": "Conteúdo consolidado e claro",
      "tipo": "episodica|semantica|procedural|estrategica",
      "tags": ["tag1", "tag2"],
      "relevancia": 0.8,
      "snapshot_ids": ["snap_abc123"],
      "atualizar_id": null
    }}
  ],
  "snapshots_ignorados": ["snap_xyz789"],
  "resumo": "Resumo curto do que foi consolidado"
}}"""


def prompt_mesclar_memorias(
    memorias: list[MemoryEntry],
) -> str:
    """
    Gera o prompt para mesclar memórias duplicadas ou sobrepostas.

    Usado periodicamente para manter a base de memórias limpa.

    Args:
        memorias: lista de memórias candidatas a mesclagem

    Returns:
        Prompt para o LLM
    """
    memorias_texto = ""
    for i, mem in enumerate(memorias, 1):
        memorias_texto += (
            f"\n--- Memória {i} (id={mem.id}, tipo={mem.tipo.value}, "
            f"relevância={mem.relevancia}) ---\n"
            f"Título: {mem.titulo}\n"
            f"Conteúdo: {mem.conteudo}\n"
            f"Tags: {', '.join(mem.tags)}\n"
        )

    return f"""Você é o sistema de memória Kairos do Synerium Factory.

Analise as memórias abaixo e identifique quais podem ser mescladas.

## Regras:
1. Mescle memórias que tratam do MESMO assunto ou decisão.
2. Ao mesclar, mantenha a informação mais recente e completa.
3. Combine tags de todas as memórias mescladas.
4. Use a maior relevância entre as memórias mescladas.
5. Não mescle memórias de tipos diferentes (episódica + semântica).

## Memórias:
{memorias_texto}

## Formato de resposta (JSON):
Responda APENAS com JSON válido:
{{
  "mesclar": [
    {{
      "manter_id": "id da memória principal (a que fica)",
      "remover_ids": ["ids das memórias absorvidas"],
      "novo_conteudo": "Conteúdo mesclado e consolidado",
      "novo_titulo": "Título atualizado se necessário",
      "novas_tags": ["tags combinadas"]
    }}
  ],
  "sem_alteracao": ["ids de memórias que ficam como estão"]
}}"""
