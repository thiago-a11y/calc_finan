# Smart Router Global — Arquitetura

> Roteador inteligente multi-provider e multi-ferramenta do Synerium Factory.

---

## Visao Geral

O Smart Router Global (`core/smart_router_global.py`) e o ponto unico de decisao para rotear qualquer solicitacao ao provider de LLM ou ferramenta externa mais adequada.

**Importacao:**
```python
from core.smart_router_global import router_global
```

---

## Fluxo de Decisao

```
Prompt do usuario
       |
       v
[1] Override manual?  ──sim──> Usar provider/ferramenta forcada
       |
      nao
       |
       v
[2] Detectar intencao (regex, 13 categorias)
       |
       v
[3] Mapear intencao → provider + ferramenta
       |
       v
[4] Verificar disponibilidade do provider
       |
       v
[5] Fallback se indisponivel
       |
       v
[6] Retornar decisao (provider + ferramenta + config)
```

**Tempo medio de decisao:** 0.12ms (regex puro, sem ML)

---

## Providers de LLM (7)

| Provider | Modelo | Custo relativo | Uso principal |
|----------|--------|---------------|--------------|
| Anthropic | Claude Opus | Alto | Arquitetura, decisoes complexas, refatoracao |
| Anthropic | Claude Sonnet | Medio | Chat, execucao, tarefas do dia-a-dia |
| OpenAI | GPT-4o | Medio | Visao, analise multimodal, fallback |
| Google | Gemini | Medio | Contexto longo, analise de documentos |
| Groq | Llama | Baixo | Resposta ultra-rapida, fallback primario |
| Fireworks | Mixtral/Llama | Baixo | Fallback secundario |
| Together | Llama/Mistral | Baixo | Fallback terciario, ultima linha |

---

## Ferramentas Externas (8)

| Ferramenta | Categoria | Descricao |
|-----------|-----------|-----------|
| **Exa** | Busca semantica | Pesquisa web com entendimento profundo de contexto |
| **Tavily** | Busca web | Pesquisa rapida e resultados estruturados |
| **Firecrawl** | Scraping | Extracao de dados e conteudo de paginas web |
| **Scrapingdog** | Scraping | Scraping com proxy rotativo e anti-bloqueio |
| **Composio** | Integracoes | Conexao com 100+ apps (Slack, GitHub, Jira, etc.) |
| **E2B** | Sandbox | Execucao segura de codigo em ambiente isolado |
| **LiveKit** | Voz/Video | Comunicacao em tempo real (chamadas, reunioes) |
| **SES** | Email | Envio de emails transacionais via Amazon SES |

---

## 13 Categorias de Intencao

O router detecta a intencao do prompt via regex e mapeia para o provider/ferramenta ideal:

| # | Categoria | Exemplo de prompt | Provider padrao | Ferramenta |
|---|----------|-------------------|----------------|------------|
| 1 | Arquitetura/Decisao | "refatore a arquitetura do modulo X" | Opus | — |
| 2 | Codigo complexo | "implemente o sistema de permissoes" | Opus | — |
| 3 | Chat simples | "oi, tudo bem?" | Sonnet | — |
| 4 | Busca web | "pesquise sobre tendencias de IA 2026" | Sonnet | Exa/Tavily |
| 5 | Scraping | "extraia dados dessa pagina" | Sonnet | Firecrawl/Scrapingdog |
| 6 | Execucao de codigo | "rode esse script Python" | Sonnet | E2B |
| 7 | Integracao | "mande mensagem no Slack" | Sonnet | Composio |
| 8 | Email | "envie email para o cliente" | Sonnet | SES |
| 9 | Voz/Video | "inicie chamada de voz" | Sonnet | LiveKit |
| 10 | Analise de documento | "analise esse PDF de 200 paginas" | Gemini | — |
| 11 | Visao/Imagem | "descreva essa imagem" | GPT-4o | — |
| 12 | Resposta rapida | "qual a capital da Franca?" | Groq | — |
| 13 | Default | (nenhuma categoria detectada) | Sonnet | — |

---

## Cadeia de Fallback

Se o provider escolhido estiver indisponivel (rate limit, timeout, erro), o router segue a cadeia:

```
Opus/Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
```

Cada provider tem health check. Se falhar, pula para o proximo. O usuario nunca fica sem resposta.

### Fallback com Vision (v0.58.0+)

Quando imagens sao detectadas na mensagem, a cadeia de fallback e filtrada automaticamente para incluir apenas providers com suporte a vision:

```
GPT-4o-mini → GPT-4o → Claude Sonnet → Claude Opus → Gemini 2.5 Flash
(Minimax, Groq, Fireworks e Together sao excluidos)
```

Deteccao dupla independente:
1. **Classificador** (`classificador_mensagem.py`): parametro `tem_imagem=True` filtra a cadeia
2. **Fallback** (`llm_fallback.py`): helper `_mensagens_tem_imagem()` detecta `image_url` em HumanMessage

### Vision para Squad Agents — Pre-processamento (v0.58.1)

Agentes de squad (CrewAI) nao suportam vision nativamente. A solucao e um pipeline de pre-processamento:

```
Imagem enviada pelo usuario
       |
       v
[1] _analisar_imagens_com_vision() em api/routes/tarefas.py
       |
       v
[2] GPT-4o-mini vision analisa a imagem
       |
       v
[3] Descricao textual rica gerada
       |
       v
[4] Descricao injetada no task.description do CrewAI
       |
       v
[5] Agente CrewAI processa como texto normal
```

O frontend (`ChatFloating.tsx`) envia URLs reais dos anexos. O backend filtra imagens, pre-processa com vision, e injeta a descricao antes de criar a task CrewAI.

---

## Override Manual

O usuario pode forcar um provider ou ferramenta usando prefixo no prompt:

```
@opus Refatore a arquitetura do modulo de pagamentos
@groq Qual a capital da Franca?
@exa Pesquise sobre tendencias de IA em 2026
@e2b Rode esse script Python de analise
```

O override sempre tem prioridade sobre a deteccao automatica.

---

## Endpoints da API

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/api/router/decidir` | Recebe prompt, retorna decisao de roteamento |
| GET | `/api/router/providers` | Lista providers disponiveis e status |
| GET | `/api/router/ferramentas` | Lista ferramentas externas e status |
| GET | `/api/router/categorias` | Lista as 13 categorias de intencao |

---

## Coexistencia com SmartRouter Antigo

| Componente | Arquivo | Escopo |
|-----------|---------|--------|
| SmartRouter (antigo) | `llm_router.py` | Opus/Sonnet para agentes CrewAI |
| Router Global (novo) | `core/smart_router_global.py` | Todos os providers + ferramentas externas |

Ambos coexistem. O SmartRouter antigo continua roteando dentro do CrewAI. O Router Global e usado para decisoes de escopo mais amplo (Luna, API, ferramentas externas).

---

> Ultima atualizacao: 2026-04-01 (v0.58.1)
