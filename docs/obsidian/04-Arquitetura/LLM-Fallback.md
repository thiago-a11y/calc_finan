# LLM Fallback — Arquitetura

> Sistema centralizado de fallback de LLM para garantir disponibilidade total.
> Criado em v0.49.0, consolidado em v0.50.0. Minimax como principal em v0.51.0. Smart Router Dinâmico em v0.52.0.

---

## Visao Geral

O sistema anterior dependia de cada modulo implementar seu proprio fallback, gerando duplicacao e inconsistencia. O `core/llm_fallback.py` centraliza a cadeia de fallback em um unico ponto: qualquer modulo chama `obter_llm_fallback()` e recebe o provider disponivel. O sistema NUNCA para por falta de creditos.

## Arquivo

**Localizacao:** `core/llm_fallback.py`

## Cadeia de Fallback (Definitiva — v0.51.0)

```
Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
```

1. **Minimax** (provider principal) — MiniMax-Text-01
   - Mais barato: $0.0004/1K input, $0.0016/1K output
   - **Endpoint global:** `api.minimaxi.chat` (com **i** — NÃO `api.minimax.chat` que é China)
   - **API key:** pay-as-you-go (`sk-api-`) — Token Plan Key (`sk-cp-`) NÃO funciona na API REST
   - **Group ID** obrigatorio: passado como parametro na URL
   - Se falhar: cai para Groq

2. **Groq** (fallback 1) — Llama 3.3 70B via Groq Cloud
   - Ultra-rapido, bom custo-beneficio ($0.00059/1K input)
   - Se falhar: cai para Fireworks
   - Requer `langchain-groq` instalado

3. **Fireworks** (fallback 2) — Llama via API OpenAI-compatible
   - Custo baixo ($0.0009/1K)
   - Endpoint: `api.fireworks.ai/inference/v1`
   - Se falhar: cai para Together

4. **Together** (fallback 3) — Llama via API OpenAI-compatible
   - Custo baixo ($0.00088/1K)
   - Endpoint: `api.together.xyz/v1`
   - Se falhar: cai para Anthropic

5. **Anthropic** (fallback 4) — Claude Sonnet
   - Alta qualidade para tarefas complexas ($0.003/1K)
   - Se falhar: cai para OpenAI

6. **OpenAI** (fallback 5) — GPT-4o
   - Ultima linha de defesa ($0.005/1K)
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
- `langchain-openai` — Provider OpenAI + Fireworks + Together (via OpenAI-compatible API)
- `python-dotenv` — Carregamento de chaves do .env (load_dotenv obrigatorio)

## Bugs Relacionados

- **Bug #36**: `langchain_groq` nao estava instalado no servidor → `pip install langchain-groq`
- **Bug #37**: `load_dotenv()` faltando no llm_fallback.py → chaves nao carregavam do .env
- **Bug #39**: Endpoint China (`api.minimax.chat`) vs Global (`api.minimaxi.chat`) — contas internacionais devem usar host com **i**

## Smart Router Dinâmico por Mensagem (v0.52.0)

A partir da v0.52.0, o sistema classifica CADA MENSAGEM individualmente antes de rotear para o provider correto. O classificador (`core/classificador_mensagem.py`) usa regex para determinar a complexidade e selecionar o LLM mais adequado.

### Matriz de Decisão

| Classificação | Provider | Modelo | Motivo |
|--------------|----------|--------|--------|
| **SIMPLES** | Minimax | MiniMax-Text-01 | Mais barato ($0.0004/1K) — perguntas diretas, saudações |
| **MEDIO** | Groq | Llama 3.3 70B | Rápido e bom custo ($0.00059/1K) — análise, resumo |
| **COMPLEXO** | Anthropic | Claude Sonnet | Qualidade premium ($0.003/1K) — arquitetura, refatoração |
| **TOOLS** | OpenAI | GPT-4o-mini | Suporta function calling + system role ($0.00015/1K) |

### Arquivo do Classificador

**Localizacao:** `core/classificador_mensagem.py`

### Adaptador de Mensagens para Minimax

Minimax não suporta role `system` (erro 2013). O adaptador converte automaticamente mensagens com role `system` para role `user` antes de enviar à API. O conteúdo é preservado integralmente.

### CrewAI — GPT-4o-mini

O CrewAI usa GPT-4o-mini como LLM principal porque é o único provider barato que suporta:
- **Function calling** — Essencial para que agentes usem ferramentas
- **Role system** — Essencial para system prompts do CrewAI

Groq falha com `tool_use_failed` (Bug #40) e Minimax falha com erro 2013 (Bug #41).

### Bugs Relacionados (Smart Router Dinâmico)

- **Bug #40**: Groq falha em function calling (`tool_use_failed`) → roteado para GPT-4o-mini
- **Bug #41**: Minimax não suporta role `system` (erro 2013) → adaptador system → user
- **Bug #42**: Minimax 404 — GroupId como query param na base_url — SDK OpenAI adiciona /chat/completions, causando URL malformada. Fix: usar extra_body para passar group_id

---

## Diferenca do Luna Engine

A Luna (assistente IA) tem sua propria cadeia de fallback mais extensa:
```
Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
```

O `llm_fallback.py` agora tem 6 providers (Minimax, Groq, Fireworks, Together, Anthropic, OpenAI), cobrindo tanto opcoes baratas quanto premium. A Luna tem cadeia propria otimizada para qualidade de resposta ao usuario.

---

> Ultima atualizacao: 2026-03-31 (v0.52.1)
