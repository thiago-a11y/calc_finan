# LLM Fallback — Arquitetura

> Sistema centralizado de fallback de LLM para garantir disponibilidade total.
> Criado em v0.49.0, consolidado em v0.50.0. Minimax como principal em v0.51.0.

---

## Visao Geral

O sistema anterior dependia de cada modulo implementar seu proprio fallback, gerando duplicacao e inconsistencia. O `core/llm_fallback.py` centraliza a cadeia de fallback em um unico ponto: qualquer modulo chama `obter_llm_fallback()` e recebe o provider disponivel. O sistema NUNCA para por falta de creditos.

## Arquivo

**Localizacao:** `core/llm_fallback.py`

## Cadeia de Fallback

```
Minimax (MiniMax-Text-01) → Groq (Llama) → Anthropic (Claude) → OpenAI (GPT-4o)
```

1. **Minimax** (provider principal) — MiniMax-Text-01
   - Mais barato: $0.0004/1K input, $0.0016/1K output
   - Integrado via MiniMaxChat (langchain_community)
   - Se falhar (rate limit, creditos, timeout): cai para Groq

2. **Groq** (fallback 1) — Llama via Groq Cloud
   - Ultra-rapido, bom custo-beneficio
   - Se falhar: cai para Anthropic
   - Requer `langchain-groq` instalado

3. **Anthropic** (fallback 2) — Claude Sonnet/Opus
   - Alta qualidade para tarefas complexas
   - Se falhar: cai para OpenAI

4. **OpenAI** (fallback 3) — GPT-4o
   - Ultima linha de defesa
   - Se falhar: levanta excecao (todos indisponiveis)

## Funcao Principal

```python
def obter_llm_fallback() -> BaseChatModel:
    """
    Tenta Anthropic → Groq → OpenAI.
    Retorna o primeiro provider disponivel.
    Levanta RuntimeError se nenhum funcionar.
    """
```

## Deteccao de Erros

O sistema detecta automaticamente:
- **Rate limit** (429) — Troca para proximo provider
- **Creditos insuficientes** — Troca para proximo provider
- **Timeout** — Troca para proximo provider
- **Quota excedida** — Troca para proximo provider
- **Erro de autenticacao** (401/403) — Troca para proximo provider

## 6 Pontos de Chamada Atualizados

Os seguintes modulos foram atualizados para usar `obter_llm_fallback()`:

1. **agents/pm_central.py** — PM Central (Alex) usa fallback para processar visoes e gerar roadmaps
2. **flows/autonomous_squads.py** — Workflows autonomos usam fallback em cada fase BMAD
3. **core/company_context.py** — Company Context usa fallback para enriquecer contexto
4. **api/routes/tarefas.py** — Tarefas e reunioes usam fallback para chamadas de agentes
5. **api/routes/code_studio.py** — Code Studio usa fallback para analise e acao de codigo
6. **flows/review_session.py** — Review sessions do Factory Optimizer usam fallback

## Dependencias

- `langchain-community` — Provider Minimax (MiniMaxChat)
- `langchain-anthropic` — Provider Anthropic
- `langchain-groq` — Provider Groq (instalado em v0.50.0)
- `langchain-openai` — Provider OpenAI
- `python-dotenv` — Carregamento de chaves do .env (load_dotenv obrigatorio)

## Bugs Relacionados

- **Bug #36**: `langchain_groq` nao estava instalado no servidor → `pip install langchain-groq`
- **Bug #37**: `load_dotenv()` faltando no llm_fallback.py → chaves nao carregavam do .env

## Diferenca do Luna Engine

A Luna (assistente IA) tem sua propria cadeia de fallback mais extensa:
```
Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
```

O `llm_fallback.py` e mais enxuto (3 providers) porque e usado em operacoes automatizadas onde velocidade importa mais que variedade. A Luna precisa de mais opcoes porque e a interface principal do usuario e precisa estar SEMPRE disponivel.

---

> Ultima atualizacao: 2026-03-31
