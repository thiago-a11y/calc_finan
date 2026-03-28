# LLM Providers — Sistema Multi-Provider com Fallback

> Fallback inteligente: se o provider principal falhar, o sistema tenta automaticamente o próximo na cadeia.

## Cadeia de Fallback

```
🧠 Claude (Anthropic) → ⚡ Groq Llama → 🔥 Fireworks Llama → 🤝 Together.ai Llama
     Principal            Fallback 1       Fallback 2          Fallback 3
```

## Providers

| # | Provider | Modelo | Custo/1k input | Custo/1k output | Latência |
|---|----------|--------|----------------|-----------------|----------|
| 1 | 🧠 Claude (Anthropic) | claude-sonnet-4-20250514 | $0.003 | $0.015 | ~3s |
| 2 | ⚡ Groq Llama | llama-3.3-70b-versatile | $0.00059 | $0.00079 | ~5s |
| 3 | 🔥 Fireworks Llama | llama-v3p3-70b-instruct | $0.0009 | $0.0009 | ~4s |
| 4 | 🤝 Together.ai Llama | Llama-3.3-70B-Instruct-Turbo | $0.00088 | $0.00088 | ~3s |

## Como Funciona

1. Sistema tenta o **provider padrão** (configurável no dashboard)
2. Se falhar (timeout, erro de API, rate limit) → tenta o **próximo** na cadeia
3. **Logging** de qual modelo foi usado em cada chamada
4. CEO/Diretor pode **trocar o padrão** e **ativar/desativar** providers no dashboard
5. **LiteLLM** como camada de abstração para suportar todos os providers via CrewAI

## Endpoints API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/llm/status` | Status de todos os providers |
| POST | `/api/llm/provider-padrao` | Trocar provider padrão |
| POST | `/api/llm/ativar` | Ativar/desativar provider |
| POST | `/api/llm/testar` | Testar provider com prompt |

## Dashboard

Página visual em `/llm-providers` com:
- Cadeia de fallback visual
- Cards por provider com métricas (chamadas, latência, custo)
- Toggle para ativar/desativar
- Botão de teste em tempo real
- Botão para definir como padrão

## Arquivos

- `config/llm_providers.py` — LLMProviderManager (singleton)
- `api/routes/llm.py` — Endpoints REST
- `dashboard/src/pages/LLMProviders.tsx` — Página visual

## Variáveis de Ambiente

```
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
FIREWORKS_API_KEY=fw_...
TOGETHER_API_KEY=tgp_v1_...
```

---

Criado em: 2026-03-24
