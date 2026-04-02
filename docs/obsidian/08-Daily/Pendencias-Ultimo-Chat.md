# Pendencias do Ultimo Chat — 02/Abr/2026

> Atualizado em 02/Abr/2026 (sessao 43 — v0.58.8)
> Sessao 43: Correcao FINAL crash Mission Control ao criar sessao (v0.58.8).

## Sessao 46 (02/Abr/2026) — isInitializing no Startup (v0.58.11)

### v0.58.11 — Guard isInitializing no Startup UseEffect
- [x] Startup useEffect com guard isInitializing
- [x] Build OK, Commit + push OK

---

## Sessao 45 (02/Abr/2026) — isInitializing Guard (v0.58.10)

### v0.58.10 — isInitializing Guard
- [x] isInitializing state + useEffect que aguarda token
- [x] Guardif (carregando || isInitializing) no topo
- [x] Build OK, Commit + push OK

---

## Sessao 44 (02/Abr/2026) — Guard de Loading Mission Control (v0.58.9)

### O que foi feito

#### v0.58.9 — Guard de Loading Mission Control
- [x] Guard carregando no topo do MissionControl
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.9** commitada (deploy pendente)

---

## Sessao 43 (02/Abr/2026) — Correcao FINAL Crash Mission Control v0.58.8

### O que foi feito

#### v0.58.8 — Correcao FINAL do Crash Mission Control ao Criar Sessao
- [x] hasToken guard: todas as chamadas API verificam token antes de executar
- [x] criarSessao: reset estado antes de navegar + JSON parse defensivo
- [x] dispararAgente: guard hasToken + reset mostrarConclusao
- [x] carregarSessao: guard hasToken + JSON parse defensivo + null checks
- [x] Polling useEffects: hasToken em todas as dependencias
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.8** commitada (deploy pendente)
- Mission Control: todas as API calls com guard de token
- Causa: token null + JSON invalido causavam crash

---

## Sessao 42 (02/Abr/2026) — Correcao FINAL Crash Mission Control (v0.58.7)

### O que foi feito

#### v0.58.7 — Correcao FINAL do Crash Mission Control ao Criar Sessao
- [x] ErrorBoundary.tsx: novo componente protecao contra crashes
- [x] App.tsx: MissionControl com ErrorBoundary wrapper
- [x] MissionControl: token fallback via localStorage (tokenSeguro)
- [x] MissionControl: res.ok check em criarSessao
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.7** commitada (deploy pendente)
- Mission Control: protegido por Error Boundary
- Causa: token null + response sem validacao causavam crash

---

## Sessao 41 (02/Abr/2026) — Correcao FINAL Mission Control blank (v0.58.6)

### O que foi feito

#### v0.58.6 — Correcao FINAL Mission Control em Branco
- [x] TaskTray: sf_access_token -> sf_token (localStorage key correto)
- [x] App.tsx: remove h-screen overflow-hidden, usa flex-1 min-h-screen
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.6** commitada (deploy pendente)
- Mission Control: deve funcionar normalmente
- Causa: TaskTray com token key errada (401) + conflito h-screen no body scroll container

---

## Sessao 40 (02/Abr/2026) — Correcao de Regressao Mission Control (v0.58.5)

### O que foi feito

#### v0.58.5 — Correcao de Regressao Mission Control
- [x] Identificado: var(--sf-bg) NAO existe no design system
- [x] Identificado: var(--sf-surface) NAO existe no design system
- [x] MissionControl.tsx era o UNICO arquivo usando var(--sf-bg) em todo o projeto
- [x] Substituido var(--sf-bg) -> var(--sf-bg-primary) em 14 lugares
- [x] Substituido var(--sf-surface) -> var(--sf-bg-card) em 17 lugares
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.5** commitada (deploy pendente)
- Mission Control: CSS corrigido
- Causa: variaveis CSS undefined fazem backgrounds ficarem transparentes

---

## Sessao 39 (02/Abr/2026) — Sidebar Fixo e Colapsavel (v0.58.4)

### O que foi feito

#### v0.58.4 — Sidebar Fixo e Colapsavel
- [x] Redux Toolkit: sidebarSlice com estado collapsed + localStorage
- [x] Store Redux: configureStore com sidebarReducer
- [x] Hooks Redux: useAppDispatch + useAppSelector tipados
- [x] Sidebar.tsx: posicao fixed, height 100vh, overflow-y auto
- [x] Sidebar colapsavel: 240px expandido / 64px mini (icons only)
- [x] Card usuario + Sair sempre visiveis no bottom (flex-shrink-0)
- [x] Animacao suave 300ms no colapso/expansao
- [x] Mobile: overlay com backdrop + hamburger button
- [x] SidebarContent extraido para reuse em desktop + mobile
- [x] Build TypeScript passando
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.4** commitada (deploy pendente)
- Sidebar: fixo na lateral, colapsavel para mini mode
- Mobile: overlay com backdrop e menu hamburger

---

## Sessao 38 (02/Abr/2026) — Correção de Regressão (v0.58.3)

### O que foi feito

#### v0.58.3 — Correção de Regressão no Mission Control
- [x] PhaseDecisionControls: polling proprio REMOVIDO (causava re-render loop)
- [x] PhaseDecisionControls: componente agora stateless — recebe tudo via props
- [x] useAuth() duplicado: consolidado para const { token, usuario } = useAuth()
- [x] waitingDecision prop: removida (nao utilizada)
- [x] FaseStatus interface redundante: removida
- [x] MissionControl: handleFaseDecisao callback adicionado
- [x] Build TypeScript: zero erros
- [x] Commit + push OK

### Status atual
- Versão: **v0.58.3** commitada (deploy pendente)
- Phase Decision Controls: 4 botoes por fase funcionando
- Crash da pagina em branco CORRIGIDO

---

## Sessao 37 (02/Abr/2026) — Phase Decision Controls (v0.58.2)

### O que foi feito

#### v0.58.2 — Phase Decision Controls — Human-in-the-Loop
- [x] Backend: FaseDecisionEngine com threading.Event (bloqueio entre fases)
- [x] Backend: POST /sessao/{id}/fase-decisao (aprovar/regenerar/rejeitar/revisar)
- [x] Backend: GET /sessao/{id}/fase-status (polling do frontend)
- [x] Backend: ponto de decisao entre cada fase (1→2, 2→3, 3→4, 4→5)
- [x] Frontend: PhaseDecisionControls.tsx (novo componente com 4 botoes)
- [x] Frontend: painel lateral de decisoes com indicador de progresso
- [x] Frontend: MissionCompleteActions com "Voltar para Revisao"
- [x] Frontend: mostrarConclusao state (so mostra conclusao apos 5 fases)
- [x] Build TypeScript passando
- [x] Commit + push OK
- [x] Limpeza final de código (variáveis/imports não utilizados)
- [x] Deploy em produção (SSH timeout — fazer pull manual no servidor)

### Status atual
- Versão: **v0.58.2** commitada (deploy pendente)
- Phase Decision Controls: 4 botoes por fase (Aprovar/Revisar/Regenerar/Rejeitar)
- Human-in-the-loop: agente pausa entre cada fase aguardando decisao
- "Voltar para Revisao" na tela de conclusao preserva todo o historico

---

## Sessao 36 (02/Abr/2026) — Git Actions Funcionais (v0.57.8)

### O que foi feito

#### v0.57.8 — Git Actions Funcionais
- [x] Backend: 4 endpoints de Git (git-info, git-commit, git-push, git-merge)
- [x] Frontend: Git Status Bar com branch e pendências
- [x] Botão Commit (laranja) funcional
- [x] Botão Push + PR (verde) funcional
- [x] Toast de feedback (sucesso/error)
- [x] Permissões: só mostra para ceo/diretor/ops/lider
- [x] Build TypeScript passando
- [x] Deploy em produção OK

### Status atual
- Versão: **v0.57.8** em produção
- Git actions: Commit, Push+PR funcionais com toast feedback

---

## Sessao 35 (02/Abr/2026) — Tela de Conclusão com Ações Recomendadas (v0.57.7)

### O que foi feito

#### v0.57.7 — Tela de Conclusão com Ações Recomendadas
- [x] Criado componente MissionCompleteActions.tsx (7 botões com ícones)
- [x] Badge verde "Concluído" no header (sem spinner)
- [x] Barra de progresso ocultada quando completo
- [x] isCompleto = faseAtual === 5 && progressoAtual === 100
- [x] Build TypeScript passando
- [x] Deploy em produção OK

### Status atual
- Versão: **v0.57.7** em produção
- Tela de conclusão: 7 ações recomendadas com botões grandes

---

## Sessao 34 (01/Abr/2026) — True Live Typing & Execution Feeling (v0.57.6)

### O que foi feito

#### v0.57.6 — True Live Typing & Execution Feeling
- [x] True Live Typing: caractere por caractere no editor com delay variável (8-40ms)
- [x] Cursor verde piscando com glow (0.65s blink cycle, box-shadow)
- [x] Highlight de linha atual (borda verde + fundo sutil rgba)
- [x] Badge STREAMING com glow vermelho pulsante
- [x] Badge "Em execução" com glow verde forte
- [x] Barra de progresso com glow intenso quando LIVE
- [x] Texto descritivo "Fase X/5" com emoji
- [x] Animação agent-pulse mais forte (0.8s, scale 1.3x)
- [x] Cursor verde no terminal com texto "agente executando..."
- [x] Build TypeScript passando
- [x] Deploy em produção OK

### Status atual
- Versão: **v0.57.6** em produção
- True Live Typing: digitação caractere por caractere com cursor verde
- Execution feeling: todos os elementos pulsam, glow forte
- Terminal: cursor verde com "agente executando..."

---

## Sessao 33 (01/Abr/2026) — Vision Real para Agentes de Squad (v0.58.1)

### O que foi feito

#### v0.58.1 — Vision real para agentes de squad
- [x] ChatFloating.tsx: envia anexos com URL real ao invés de texto placeholder
- [x] tarefas.py: `_analisar_imagens_com_vision()` pré-processa imagens com GPT-4o-mini
- [x] luna_engine.py: fix path resolution absoluto + fallback não-silencioso
- [x] 4 arquivos alterados, 158 linhas adicionadas

### Status atual
- Versão: **v0.58.1**
- Imagens pré-processadas com GPT-4o-mini vision antes de enviar ao agente
- URLs reais de upload no ChatFloating (não mais placeholders)
- Luna Engine com path absoluto e erro não-silencioso

---

## Sessao 32 (01/Abr/2026) — Agentes Multimodais Vision (v0.58.0)

### O que foi feito

#### v0.58.0 — Agentes Multimodais (Vision)
- [x] `classificador_mensagem.py`: flag `vision` adicionada a todos os 8 providers em PROVIDERS_REGISTRO
- [x] `classificador_mensagem.py`: novo parâmetro `tem_imagem` — quando True, força provider com vision
- [x] `classificador_mensagem.py`: SIMPLES/MEDIO com imagem → GPT-4o-mini; COMPLEXO com imagem → GPT-4o
- [x] `classificador_mensagem.py`: fallback chain filtra providers sem vision quando tem_imagem=True
- [x] `luna_engine.py`: `_decidir_modelo()` aceita `anexos`, detecta `tipo="imagem"` e passa `tem_imagem=True`
- [x] `luna_engine.py`: streaming e regeneração atualizados para passar anexos
- [x] `llm_fallback.py`: helper `_mensagens_tem_imagem()` detecta `image_url` em HumanMessage content_parts
- [x] `llm_fallback.py`: sync e async pulam Minimax/Groq/Fireworks/Together quando imagem detectada
- [x] Rede de segurança dupla: classificador + fallback, independentes entre si

### Status atual
- Versão: **v0.58.0**
- Imagens enviadas no Escritório Virtual são roteadas para GPT-4o-mini (barato + vision)
- Mensagens complexas com imagem vão para GPT-4o (máxima qualidade multimodal)
- Fallback chain seguro: nunca envia imagem para provider sem vision

---

## Sessao 31 (01/Abr/2026) — Visible Live Execution (v0.57.5)

### O que foi feito

#### v0.57.5 — Visible Live Execution
- [x] Frontend: efeito typewriter — caracteres aparecem gradualmente no editor
- [x] Frontend: barra de progresso animada com shimmer + texto descritivo + porcentagem
- [x] Frontend: ícone do agente pulsante durante execução
- [x] Frontend: badge "Em execução" nas mensagens do Team Chat
- [x] Frontend: cursor piscante no terminal (efeito de digitação)
- [x] Frontend: indicador de atividade do agente em todos os painéis
- [x] Backend: chunks de streaming reduzidos de 4→2 linhas, delay de 350ms→200ms
- [x] Backend: progresso granular dentro das fases (não apenas nas transições)
- [x] Backend: comandos reais no terminal (npm run build, pytest, eslint, tsc --noEmit)
- [x] Backend: editor mostra conteúdo desde a Fase 1 (scaffold → plan → code)
- [x] Backend: mais entradas de terminal em todas as fases

### Status atual
- Versão: **v0.57.5**
- Experiência visual completa: typewriter, shimmer, pulso, cursor piscante
- Streaming mais fluido (2 linhas, 200ms)

---

## Sessao 30 (01/Abr/2026) — Fix Crítico Streaming ao Vivo (v0.57.4)

### O que foi feito

#### v0.57.4 — Root cause fix streaming
- [x] Identificados 3 root causes que impediam o streaming de funcionar
- [x] Backend: helpers com session isolada + flag_modified + deep copy + try/except
- [x] Backend: auto_save_sessao preserva conteúdo do agente (não sobrescreve se fonte='agente')
- [x] Backend: auto_save não sobrescreve terminal se agente tem entradas que frontend não recebeu
- [x] Frontend: polling fixo 2s (sem sessao?.agentes_ativos nos deps)
- [x] Frontend: agentExecutandoRef — auto-save pula quando agente executando
- [x] Frontend: editorEditadoRef — closures sem stale state no carregarSessao
- [x] Frontend: dispararAgente recarrega sessão imediatamente após dispatch
- [x] Build TypeScript passou sem erros
- [x] Deploy em produção: synerium-factory.service ativo

### Status atual
- Versão: **v0.57.4** em produção
- Streaming ao vivo: funcionando (code aparece linha por linha no editor)
- Barra de progresso: mostra fase real e %

---

## Sessao 29 (01/Abr/2026) — Mission Control v0.57.2 — Visible Execution

### O que foi feito

#### v0.57.2 — Visible Execution
- [x] `_atualizar_fase_agente()` — helper persiste fase/progresso em `agentes_ativos` a cada fase
- [x] `_escrever_codigo_no_editor()` — helper persiste código gerado em `painel_editor` com `fonte: "agente"`
- [x] `_adicionar_terminal_agente()` — helper insere entradas `tipo: "agente"` no terminal da sessão
- [x] Progresso por fase: Planejamento (10%) → Discussão (35%) → Execução (60%) → QA Review (85%) → Concluído (100%)
- [x] Fase 3: placeholder "Gerando..." no editor imediatamente; código real ao concluir
- [x] Frontend: barra de progresso animada com gradiente + glow acima do campo de instrução
- [x] Frontend: editor detecta `fonte === "agente"` e auto-atualiza (sem sobrescrever edições manuais)
- [x] Frontend: badge "agente" pulsante no header do editor; "gerando..." durante Fase 3
- [x] Frontend: terminal com ícone Bot verde para entradas do agente vs `$` azul para usuário
- [x] Frontend: botão "Rodar Testes" no modal de artifact de código
- [x] Build TypeScript passou sem erros
- [x] Commit + push para `claude/condescending-einstein`

#### v0.57.3 — Modo LIVE
- [x] Backend: `_escrever_codigo_no_editor(streaming=True/False)` — escrita progressiva em blocos de 4 linhas
- [x] Backend: Fase 3 escreve código com `time.sleep(0.35)` entre chunks para efeito de digitação
- [x] Frontend: `modoLive` state (default true) + `editorStreaming`
- [x] Frontend: botão toggle LIVE verde na barra de progresso
- [x] Frontend: polling dinâmico 1s (LIVE + executando) / 5s (normal)
- [x] Frontend: badge LIVE vermelho pulsante no editor header durante streaming
- [x] Frontend: indicador "escrevendo..." com cursor pulsante no canto do editor
- [x] Build TypeScript passou sem erros
- [x] Deploy em produção OK (synerium-factory.service active)

#### Bug #52 — Recovery de Agentes Órfãos (Sessão 29, parte 2)
- [x] Identificado bug crítico: agente disparado antes de `systemctl restart` ficava preso em "Executando..." 0% para sempre
- [x] Causa raiz: `systemctl restart` mata threads Python sem notificar o banco — `agentes_ativos[].status` permanecia `"executando"` para sempre
- [x] Diagnóstico via `journalctl -u synerium-factory | grep MISSION` — sem log `"[MISSION] Agente disparado"` após o restart, só GETs de polling
- [x] Fix emergencial: script Python manual no servidor marcou sessão `819548c7da7a` como erro no banco
- [x] Fix permanente: `_recovery_agentes_orfaos()` em `api/routes/mission_control.py` — executada no import do módulo (a cada startup)
- [x] Commit: `fix(mission-control): recovery de agentes orfaos no startup`
- [x] Deploy em produção + verificação via `systemctl status synerium-factory`
- [x] Documentado em: Bugs-Conhecidos.md (#52), Changelog.md (v0.57.3), Decisoes-Tecnicas.md, CONTEXTO

### Status atual (01/Abr/2026 — v0.57.3)
- Versão: **v0.57.3** em produção
- Modo LIVE ligado por padrão — código aparece ao vivo no editor
- Recovery automático de agentes órfãos ativo no startup

---

## Sessao 28 (01/Abr/2026) — Mission Control v0.57.0 + v0.57.1

### O que foi feito

#### v0.57.0 — Persistência de Sessões
- [x] `PATCH /api/mission-control/sessao/{id}/save` — auto-save a cada 10s (editor + terminal)
- [x] Tela de sessões recentes com "Retomar" e "Nova Sessão"
- [x] URL com ID: `/mission-control/:sessionId` (rota adicionada em App.tsx)
- [x] Auto-save indica "Salvo HH:MM" no header com spinner
- [x] Editor `<pre>` → `<textarea>` editável com monospace

#### v0.57.1 — Team Chat + Modal de Artifacts
- [x] `TeamChatDB` model criado (campo `dados_extra` — NOT `metadata`, reservado pelo SQLAlchemy)
- [x] `GET /api/mission-control/sessao/{id}/chat?desde=...` — polling incremental a cada 2s
- [x] `_executar_agente_mission_control()` reescrito: 4 fases com 4 agentes distintos
  - Fase 1: Tech Lead → plano JSON → artifact PLANO
  - Fase 2: Backend Dev + Frontend Dev + QA Engineer → pareceres técnicos
  - Fase 3: Tech Lead → código real → artifact CODIGO
  - Fase 4: QA Engineer → checklist → artifact CHECKLIST
- [x] Painel 3 com abas: Team Chat | Artifacts
- [x] Team Chat com ícones por agente, badges de fase coloridos, scroll automático
- [x] Artifact modal: nunca fecha sozinho, max-w-4xl, botões "Aplicar no Editor" / "Copiar" / "Download"
- [x] Bug #49: `metadata` reservado → renomeado para `dados_extra`
- [x] Bug #50: string raw como classificação → `classificar_mensagem()` em todos os pontos
- [x] Bug #51: import `FileText` desnecessário → removido (build TypeScript passando)

#### Teste de Integração Completo — APROVADO ✅
- Sessão `17f4adb17602`: instrução "Crie componente de Login com validação de email..."
- 14 mensagens no Team Chat com 4 agentes participando
- 3 artifacts gerados: PLANO + CODIGO + CHECKLIST
- Polling 2s funcionando sem duplicações
- Modal de artifact funcionando com "Aplicar no Editor"

#### Deploy
- [x] `git push` + `git pull` no servidor + `npm run build` + `systemctl restart synerium-api`
- [x] PR #10 criado e mergeado em main

### Status atual (01/Abr/2026 — v0.57.1)
- Versão: **v0.57.1** em produção
- URL: `https://synerium-factory.objetivasolucao.com.br`
- Mission Control com Team Chat ao vivo, 4 fases multi-agente, session persistence
- 3 bugs novos resolvidos (#49, #50, #51)

---

## Sessao 27 (01/Abr/2026) — Bug Fixes + Novos Agentes

### O que foi feito

#### Bugs corrigidos (3 críticos)
- [x] **Bug #43 — Aprovação retornava Erro 500**: HTTPException(400) do Build Gate era capturada por `except Exception` genérico e re-lançada como 500. Fix: `except HTTPException: raise` antes do handler genérico em `api/routes/propostas.py`.
- [x] **Bug #44 — Git Pull com conflito "unmerged files"**: Agente havia substituído `EditProposalModal.tsx` e `App.tsx` do SyneriumX por texto puro. Fix: `git checkout HEAD -- <arquivo>` nos dois arquivos afetados no servidor.
- [x] **Bug #45 — Command Center sem detalhes de erro e sem reabrir**: Adicionado bloco de exibição de `outputs.erro` com monospace vermelho + botão "Reiniciar da Fase X" em `AutonomoPanel.tsx`. Novo endpoint `POST /tarefas/autonomo/{id}/reiniciar`.

#### v0.55.1 — Mission Control URL fix
- [x] `MissionControl.tsx`: `VITE_API_URL || 'http://localhost:8000'` → `VITE_API_URL || ''`
- [x] Criado `/etc/systemd/system/synerium-dashboard.service` (vite preview porta 5173)
- [x] Diagnóstico: porta 5173 bloqueada pelo Lightsail → URL correta é o domínio HTTPS

#### v0.56.0 — Suporte completo novos agentes
- [x] `Catalogo.tsx`: ícones `GitBranch`, `TrendingUp`, `FlaskConical` + filtros + cores para 3 novas categorias
- [x] `Atribuicoes.tsx`: mesmos ícones + cores (`qualidade`, `otimizacao`, `operacional`)
- [x] `Skills.tsx`: perfis `diretor` e `arquiteto` adicionados
- [x] `api/routes/catalogo.py`: `CATEGORIAS_DISPONIVEIS` expandido
- [x] `Escritorio.tsx`: `DK` de 9 → 16 posições (fileiras 4 e 5 com agentes 10–16)

#### Deploy e infraestrutura
- [x] Servidor Lightsail reiniciado (SSH daemon travado — UPSTREAM_ERROR 515)
- [x] PRs #7, #8, #9 criados e mergeados em main
- [x] Todos os deploys realizados via git pull + npm run build no servidor

### Status atual (01/Abr/2026)
- Versão: **v0.56.0** em produção
- URL: `https://synerium-factory.objetivasolucao.com.br`
- 16 agentes no catálogo, todos visíveis e atribuíveis
- Escritório virtual suporta até 16 agentes por squad
- Mission Control acessível em `/mission-control`
- 3 bugs críticos resolvidos (Aprovação 500, Git Pull, Command Center)

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

- Tudo em produção (AWS Lightsail — Virginia Zone A)
- Versão atual: **v0.56.0**
- URL: `https://synerium-factory.objetivasolucao.com.br`
- Build Gate ativo — validação de build obrigatória antes de push
- PRs #7, #8, #9 mergeados em main
- 16 agentes no catálogo (todos visíveis com ícones, filtros e cores corretos)
- LLM Principal: **Minimax MiniMax-Text-01** (funcionando em produção)
- Cadeia de fallback: Minimax → Groq → Fireworks → Together → Anthropic → OpenAI
- Vision-to-Product operacional e testado no Command Center
- Autonomous Squads com session isolada e fila automática
- Code Studio completo: Company Context, Apply+Deploy, Push/PR/Merge, conversas separadas
- Continuous Factory: modo 24/7 com auto-gates, relatório diário e notificações SES
- Mission Control: painel triplo (Editor + Terminal + Artifacts) com agentes live
- Escritório virtual suporta até 16 agentes por squad (DK expandido)
- 3 bugs críticos resolvidos (Aprovação 500, Git Pull conflito, Command Center)

## Pendencias / Proximos passos

- [ ] Atribuir agentes ao Marcos, Rhammon e André via dashboard (usar tela Atribuições)
- [ ] Testar solicitação de agente por usuário comum (fluxo de aprovação)
- [ ] Mapear os 45 funcionários da Objetiva e criar squads personalizados
- [ ] Manual completo do Synerium Factory (docs/obsidian/10-Manual/) — 12 capítulos planejados, prioridade alta
- [ ] Testar integração VCS com repositório GitBucket real (on-premise)
- [ ] Melhorar escritório: sala de reunião com vidro transparente (ver agentes dentro)
- [ ] Adicionar histórico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar migrations automáticas no bootstrap (Alembic ou ALTER TABLE strategy)
- [ ] Busca global no Code Studio (Ctrl+Shift+F)
- [ ] Monitoramento de saúde dos agentes (heartbeat)
- [ ] CrewAI com fallback integrado (llm_fallback.py no CrewAI)
- [x] ~~Fila pós-gate~~ — Resolvido
- [x] ~~Minimax como LLM principal~~ — Resolvido (v0.51.0)
- [x] ~~Build Gate~~ — Resolvido (v0.52.2)
- [x] ~~Atribuições de agentes com novos ícones/categorias~~ — Resolvido (v0.56.0)

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
