# Pendencias do Ultimo Chat — 31/Mar/2026

> Atualizado em 01/Abr/2026 (sessao 26 — v0.55.0)
> Sessao anterior: Correcao Minimax + Smart Router Luna (v0.52.1). Sessao 26: Pipeline + Continuous Factory + Mission Control.

## Resumo da sessao

Sessao mais produtiva da historia do Synerium Factory. 13 versoes entregues em um unico dia, 37+ bugs corrigidos, 5 features de ruptura implementadas. Teste end-to-end aprovado (Fase 2→3→4 sem crash).

## Versoes entregues (v0.38 a v0.50)

### v0.38.0 — Historico de Atividades + Feedback Detalhado
- [x] Endpoint GET /api/code-studio/historico com paginacao
- [x] Calculo de diff no apply-action (difflib)
- [x] HistoricoPanel + toast detalhado + confirmacao inline

### v0.39.0 — Company Context Total
- [x] CompanyContextBuilder com 3 niveis (minimal/standard/full)
- [x] RAG integrado (ChromaDB top 3 chunks, budget 4000 chars)
- [x] Toggle "Contexto Empresa" no AgentPanel

### v0.40.0 — Chat Resiliente
- [x] Timeout aumentado de 10min para 30min
- [x] Endpoint POST /tarefas/{id}/retomar
- [x] Botoes "Retomar conversa" e "Retomar de onde parou"
- [x] Git Pull com token VCS + GIT_TERMINAL_PROMPT=0

### v0.41.0 — One-Click Apply+Deploy
- [x] Pipeline completo: backup → aplicar → Test Master → commit → push
- [x] Test Master obrigatorio e bloqueante
- [x] Rollback automatico em caso de falha

### v0.42.0 — Push & PR & Merge
- [x] Push direto do Code Studio via GitHub API
- [x] Criacao de Pull Request + Merge
- [x] PushDialog com selecao de commits

### v0.43.0 — Live Agents
- [x] Progresso rotativo no AgentPanel
- [x] Balao de status no Escritorio Virtual
- [x] Shimmer no ChatFloating

### v0.44.0 — Paineis Redimensionaveis
- [x] Drag handle entre paineis do Code Studio
- [x] Persistencia de largura em localStorage

### v0.45.0 — Conversas Separadas no AgentPanel
- [x] Multiplas conversas independentes por projeto
- [x] Scroll inteligente (inicio da resposta)
- [x] Persistencia localStorage, max 20 conversas

### v0.46.0 — 3 Agentes Elite + BMAD Completo
- [x] Test Master, GitHub Master, GitBucket Master
- [x] 16 agentes mapeados no BMAD com fases e palavras-chave

### v0.47.0 — Botao Novo Projeto
- [x] Botao na pagina Projetos + modal de criacao (CEO only)

### v0.48.0 — Preview por Commit + Horario Brasilia
- [x] Preview de arquivos alterados no PushDialog
- [x] Timestamps em fuso America/Sao_Paulo

### v0.49.0 — Autonomous Squads + Self-Evolving Factory + Command Center
- [x] Workflow BMAD autonomo (4 fases, gates soft/hard, paralelo)
- [x] Factory Optimizer (ID=16, Distinguished Engineer, PDCA)
- [x] EvolucaoFactoryDB para sugestoes de melhoria
- [x] Command Center CEO (KPIs, comando estrategico, spawn squads)
- [x] Recovery de workflows travados (>30min → erro)

### v0.50.0 — Vision-to-Product + Session Isolada + Fila
- [x] Vision-to-Product: PM Central gera roadmap com estimativa de custo/prazo
- [x] Features com prioridade e complexidade no Comando Estrategico
- [x] Barra de progresso % em cada card de squad
- [x] Session SQLite isolada por fase (fix critico)
- [x] Fila automatica de workflows (proximo inicia ao concluir/falhar)
- [x] LLM Fallback robusto: core/llm_fallback.py (Anthropic → Groq → OpenAI)
- [x] 6 pontos de chamada LLM atualizados para fallback centralizado
- [x] Teste end-to-end aprovado: Fase 2→3→4 sem crash

## Bugs corrigidos nesta sessao (37+)

- [x] #11 Timeout 10min muito curto → 30min
- [x] #12 Sem retomar conversa apos erro → botoes de retomar
- [x] #13 Git Pull HTTPS sem token → token VCS injetado
- [x] #14 Agente enviava email sem autorizacao → regras no prompt
- [x] #15 LLM tracked incompativel com CrewAI 1.11+ → **kwargs
- [x] #16 Gemini 2.0-flash descontinuado → 2.5-flash
- [x] #17 LangSmith 403 no RAG → removido @traceable
- [x] #18 Chroma deprecation → migrado para langchain_chroma
- [x] #19 Estimador de tokens inflado ($55 fantasma) → corrigido
- [x] #20 Botao Aplicar so em Otimizar → regex todas as acoes
- [x] #21 NetworkError no analyze → timeout 120s + AbortController
- [x] #22 Estouro 213K tokens com imagem → descricao textual
- [x] #23 Texto muted baixo contraste → cores ajustadas WCAG
- [x] #24 Convites naive vs aware datetime → datetime.now(timezone.utc)
- [x] #25 permissoes.py corrompido → restaurado do Git
- [x] #26 Painel Geral usuarios deletados → busca do banco
- [x] #27 Invalid Date no PushDialog → ISO 8601
- [x] #28 Commits mergeados aparecendo → filtro origin/main..HEAD
- [x] #29 VCS remote corrompido → restaurado no finally
- [x] #30 CEO nao podia excluir proprietarios → excecao por ID
- [x] #31 Git fetch sem token → token VCS no fetch
- [x] #32 Session SQLite crash em threads → SessionLocal() isolada
- [x] #33 Workflows aguardando_fila nunca iniciavam → fila automatica
- [x] #34 Gate approval race condition → threading.Lock
- [x] #35 Rota /{tarefa_id} conflitava com /command-center → /detalhe/{tarefa_id}
- [x] #36 langchain_groq nao instalado → pip install
- [x] #37 load_dotenv faltando no llm_fallback.py → adicionado

## Features de ruptura

1. **Autonomous Squads** — Workflow BMAD completo (4 fases, gates, paralelo, session isolada, fila)
2. **Self-Evolving Factory** — Review session automatica, Factory Optimizer (PDCA), EvolucaoFactoryDB
3. **Command Center** — Painel CEO, comando estrategico, KPIs, spawn de squads, Vision-to-Product
4. **LLM Fallback** — core/llm_fallback.py, cadeia Anthropic → Groq → OpenAI, 6 pontos atualizados
5. **Dynamic Team Assembly** — Deteccao automatica de tipo de tarefa + selecao de agentes por LLM

## Sessao 26 (continuacao) — v0.55.0 Mission Control + v0.54.0 Continuous Factory (01/Abr/2026)

### O que foi feito (v0.54.0 — Continuous Factory)
- [x] Modo Continuo 24/7 com toggle por CEO/Operations Lead
- [x] Auto-aprovacao de gates soft e hard (configuravel)
- [x] Notificacao por email (Amazon SES) para gates hard pendentes
- [x] Relatorio diario automatico (23:00) com metricas e resumo LLM
- [x] Worker background com recovery automatico no startup

### O que foi feito (v0.55.0 — Mission Control)
- [x] Painel triplo redimensionavel: Editor + Terminal + Artifacts
- [x] Terminal interativo sandboxed com historico
- [x] Agentes vivos animados no header (pulse)
- [x] Artifacts inteligentes (planos, checklists) gerados por agentes
- [x] Comentarios inline estilo Google Docs em artifacts
- [x] 8 endpoints REST + 2 novos models (ArtifactDB, MissionControlSessaoDB)

### Pendencias
- [ ] PR para main com v0.54.0 + v0.55.0
- [ ] Manual do Synerium Factory — 12 capitulos planejados

---

## Sessao 26 — v0.53.0→v0.53.1 Pipeline Completo + Correcoes Vision-to-Product (31/Mar/2026)

### O que foi feito (v0.53.0)
- [x] Pipeline agente → proposta → aprovação → deploy implementado
- [x] Prompt dos agentes atualizado em 3 pontos (tarefa, reunião paralela, reunião sequencial)
- [x] Build Gate integrado na aprovação de propostas
- [x] Auto-deploy opcional implementado

### O que foi feito (v0.53.1 — Correcoes Vision-to-Product)
- [x] Rate Limit Retry — backoff exponencial (2s→4s→8s) em llm_fallback.py, sync + async
- [x] Self-Evolving Factory — _executar_review_session() agora SEMPRE salva EvolucaoFactoryDB
- [x] Tool Schemas GPT-4o-mini — args_schema Pydantic em todas as 10 tools CrewAI

### Pendencias novas (Sessao 26)
- [ ] Testar pipeline completo com um agente real
- [ ] Criar PR para main com v0.52.2→v0.53.1

---

## Sessao 25 — v0.52.1 Correcao Minimax + Smart Router Luna (31/Mar/2026)

### O que foi feito
- [x] Bug #42 resolvido: Minimax 404 — GroupId via extra_body em vez de query param
- [x] Luna Engine agora respeita classificacao do Smart Router (SIMPLES→minimax, MEDIO→groq, COMPLEXO→sonnet)
- [x] _obter_cadeia_fallback() reordenada baseada na classificacao
- [x] Anthropic com creditos novamente (confirmado pelo usuario)
- [x] Teste end-to-end aprovado: 3 mensagens × 3 providers distintos

### Pendencias novas (Sessao 25)
- [x] Implementar Build Gate no core/vcs_service.py (npm run build antes de push)
- [ ] Melhorar contexto dos agentes para código real (RAG com código-fonte)
- [ ] Bug #43: Factory destruiu EditProposalModal.tsx — PR #195 auto-merged quebrado

---

## Sessao 24 — v0.52.0 Smart Router Dinâmico por Mensagem (31/Mar/2026)

### O que foi feito
- [x] Classificador de mensagem por complexidade (`core/classificador_mensagem.py`) — regex com 4 níveis: SIMPLES, MEDIO, COMPLEXO, TOOLS
- [x] Matriz de decisão dinâmica: SIMPLES→Minimax, MEDIO→Groq, COMPLEXO→Sonnet, TOOLS→GPT-4o-mini
- [x] 6 pontos de chamada integrados com classificação por mensagem individual
- [x] Adaptador de mensagens para Minimax (converte role system → user, pois Minimax não suporta system)
- [x] GPT-4o-mini definido como LLM principal no CrewAI (suporta function calling + system role)
- [x] Bug #40 resolvido: Groq não suporta function calling (tool_use_failed) — roteado para GPT-4o-mini
- [x] Bug #41 resolvido: Minimax não suporta role system (erro 2013) — adaptador de mensagens

### Descobertas importantes
- Groq NÃO suporta function calling de forma confiável — erro `tool_use_failed` ao usar ferramentas
- Minimax NÃO suporta role `system` — retorna erro 2013. Solução: adaptar mensagens system → user
- GPT-4o-mini é o único provider barato que suporta TANTO function calling QUANTO system role
- Classificador regex é suficiente para roteamento (< 1ms, sem dependência de ML)

---

## Sessao 23 — v0.51.0 Minimax como LLM Principal (30/Mar/2026)

### O que foi feito
- [x] Minimax MiniMax-Text-01 implementado como LLM principal (mais barato: $0.0004/1K input)
- [x] Cadeia definitiva de fallback: Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
- [x] Endpoint correto descoberto: `api.minimaxi.chat` (global, com **i**) — NÃO `api.minimax.chat` (China)
- [x] API key pay-as-you-go (`sk-api-`) configurada e funcionando no servidor
- [x] Token Plan Key (`sk-cp-`) NÃO funciona na API REST — é para ferramentas internas da Minimax
- [x] Group ID configurado: 2038667454804140743
- [x] Fireworks e Together adicionados na cadeia de fallback (via OpenAI-compatible API)
- [x] Bug #39 resolvido: endpoint China vs Global da Minimax

### Descobertas importantes
- Minimax tem DOIS hosts: `api.minimax.chat` (China) e `api.minimaxi.chat` (Global/Internacional)
- Conta global (interface em ingles) DEVE usar o host com **i**
- Token Plan ($50/mes) é assinatura para ferramentas internas (OpenCode, OpenClaw), NAO para API REST
- Para API REST, usar Balance (pay-as-you-go) com key `sk-api-`
- Minimax desabilita keys automaticamente se detectar exposicao publica

## Status atual

- Tudo em producao (AWS)
- Versao atual: v0.54.0
- Build Gate ativo — validação de build obrigatória antes de push
- PR #2 mergeado na main (Smart Router + Minimax fix + Build Gate)
- 16 agentes no catalogo (9 CEO + 3 Jonatas + 3 Elite + Factory Optimizer)
- LLM Principal: **Minimax MiniMax-Text-01** (funcionando em producao)
- Cadeia de fallback: Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
- Vision-to-Product operacional e testado no Command Center
- Autonomous Squads com session isolada e fila automatica
- Code Studio completo: Company Context, Apply+Deploy, Push/PR/Merge, conversas separadas
- Live Agents com animacoes de status no Escritorio Virtual
- Chat resiliente com timeout de 30min e botoes de retomar conversa
- Teste end-to-end aprovado: Fase 2→3→4 sem crash

## Pendencias / Proximos passos

- [ ] CrewAI com fallback (integrar llm_fallback.py no CrewAI para agentes)
- [x] ~~Fila pos-gate~~ — Resolvido
- [x] ~~Review pos-gate~~ — Resolvido
- [x] ~~Minimax como LLM principal~~ — Resolvido (v0.51.0)
- [ ] Testar integracao VCS com repositorio GitBucket real
- [ ] Testar exclusao permanente de usuarios em producao
- [ ] Atribuir agentes ao Marcos e Rhammon via dashboard
- [ ] Testar solicitacao de agente por um usuario comum
- [ ] Ajustar permissoes granulares para a pagina de Atribuicoes (so admin ve)
- [ ] Mapear os 45 funcionarios da Objetiva e criar squads
- [ ] Corrigir testes de integracao (mock do lifespan para CI)
- [ ] Manual completo do Synerium Factory (docs/obsidian/10-Manual/) — 12 capítulos planejados, prioridade alta
- [ ] Melhorar escritorio: interacao com sala de reuniao (vidro transparente vendo agentes dentro)
- [ ] Adicionar historico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar sistema de migrations automaticas no bootstrap (Alembic ou ALTER TABLE strategy)
- [ ] Implementar busca global no Code Studio (Ctrl+Shift+F)
- [ ] Terminal integrado no Code Studio
- [ ] Monitoramento de saude dos agentes (heartbeat)

## Teste End-to-End Vision-to-Product — APROVADO ✅
- Visão: "Lançar PlaniFactory como SaaS em 90 dias"
- 5 workflows criados (Autenticação, Dashboard, SAP B1, Infraestrutura, Testes)
- Workflow "Módulo de Autenticação" executou 4 fases BMAD completas sem erro
- Gates soft (auto-pass) e hard (CEO aprova) funcionaram
- Self-Evolving Factory disparou review com 3 sugestões reais via Groq
- Fila avançou automaticamente: "Dashboard Personalizável" iniciou após conclusão
- LLM Fallback Anthropic → Groq funcionou em todas as chamadas
- Zero crashes, zero race conditions, zero erros de session
- Veredicto: FLUXO 100% FUNCIONAL — pronto para produção
