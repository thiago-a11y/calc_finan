# Pendencias do Ultimo Chat — 30/Mar/2026

> Atualizado em 30/Mar/2026 (sessao 21)

## Concluido nesta sessao

### v0.48.0 — Preview de Arquivos por Commit + Horario Brasilia
- [x] Preview de arquivos alterados por commit no PushDialog
- [x] Timestamps em horario Brasilia (UTC-3) no PushDialog
- [x] Selecao visual de commits com checkboxes

### v0.47.0 — Botao Novo Projeto + Modal de Criacao
- [x] Botao "Novo Projeto" na pagina Projetos (visivel so para CEO)
- [x] Modal de criacao com formulario completo (nome, descricao, stack, membros)
- [x] Validacao de permissao (apenas CEO cria projetos)

### v0.46.0 — 3 Agentes Elite + BMAD Mapeamento Completo
- [x] Test Master — agente de testes automatizados, obrigatorio no pipeline
- [x] GitHub Master — agente especializado em operacoes GitHub
- [x] GitBucket Master — agente especializado em operacoes GitBucket on-premise
- [x] BMAD mapeamento completo — 15 agentes com fases, palavras-chave e especialidades
- [x] Catalogo expandido de 12 para 15 templates

### v0.45.0 — Sistema de Conversas Separadas no AgentPanel
- [x] Conversas separadas no AgentPanel (cada uma independente)
- [x] Botao "Novo Chat" para iniciar nova conversa
- [x] Historico de conversas com titulo e preview
- [x] Scroll inteligente (inicio da resposta, nao final)
- [x] Persistencia em localStorage por projeto
- [x] Indicador de conversa ativa

### v0.44.0 — Paineis Redimensionaveis no Code Studio
- [x] Drag handle entre paineis para ajustar largura
- [x] Largura minima garantida no editor central
- [x] Persistencia de tamanho em localStorage
- [x] Cursor visual de resize

### v0.43.0 — Live Agents
- [x] Progresso rotativo no AgentPanel (animacao de processamento)
- [x] Balao de status no Escritorio Virtual (pensando, digitando, ocioso)
- [x] Shimmer no ChatFloating durante carregamento
- [x] Animacoes contextuais por estado do agente

### v0.42.0 — Push & PR & Merge direto do Code Studio
- [x] Push direto do Code Studio com botao dedicado
- [x] Criacao de Pull Request via dashboard
- [x] Merge via GitHub API sem sair do Code Studio
- [x] Selecao de commits com checkboxes
- [x] PushDialog com preview e acoes completas
- [x] Integracao GitHub API com token VCS criptografado

### v0.41.0 — One-Click Apply+Deploy
- [x] Pipeline completo: backup → aplicar → Test Master → commit → push
- [x] Test Master bloqueante (nem CEO pode bypassar)
- [x] Backup automatico antes de aplicar alteracao
- [x] Feedback em tempo real de cada etapa
- [x] Rollback automatico em caso de falha

### v0.40.0 — Chat Resiliente + Timeout + Retomar Conversa
- [x] Timeout de tarefas/reunioes aumentado de 10 para 30 minutos
- [x] Novo endpoint POST /tarefas/{id}/retomar
- [x] Botao "Retomar conversa" no ChatFloating
- [x] Botao "Retomar de onde parou" no ReuniaoModal
- [x] Git Pull no Code Studio com token VCS para autenticacao HTTPS
- [x] GIT_TERMINAL_PROMPT=0 evita travar esperando input

### v0.39.0 — Company Context Total
- [x] CompanyContextBuilder com 3 niveis (minimal/standard/full)
- [x] Toggle "Contexto Empresa" no AgentPanel
- [x] Badge "Contexto Total" nas respostas do assistente
- [x] Cache inteligente (5min projetos, empresa estatico)
- [x] Integracao RAG com ChromaDB + Obsidian vaults
- [x] Budget de tokens limitado a 4000 chars

### v0.38.0 — Historico de Atividades + Feedback Detalhado
- [x] Endpoint GET /api/code-studio/historico com paginacao
- [x] Calculo de diff no apply-action via difflib
- [x] HistoricoPanel com lista cronologica
- [x] Toast detalhado ao aplicar acao IA (diff, commit hash, branch)
- [x] Confirmacao inline antes de aplicar acoes
- [x] Botao Historico na Toolbar

### Bugs corrigidos nesta sessao
- [x] LLM tracked incompativel com CrewAI 1.11+ (available_tools → **kwargs)
- [x] Gemini 2.0-flash descontinuado → 2.5-flash
- [x] LangSmith 403 no RAG → removido @traceable
- [x] Chroma deprecation → migrado para langchain_chroma
- [x] Tokens inflados no tracker ($55 fantasma → $0.70 real)
- [x] Regex do botao Aplicar (so aparecia em Otimizar)
- [x] NetworkError no fetch do analyze (timeout 120s)
- [x] Estouro de 213K tokens ao enviar imagem
- [x] Contraste texto muted no dark/light mode
- [x] Git pull HTTPS sem token (could not read Username)
- [x] Convites invalidos (naive vs aware datetime em convites.py E auth.py)
- [x] permissoes.py corrompido no servidor (conteudo de IA misturado)
- [x] Painel Geral mostrava usuarios deletados (buscava config estatico)
- [x] Push dialog: Invalid Date + commits ja mergeados aparecendo
- [x] VCS remote corrompido apos commit (restaura no finally)
- [x] CEO nao podia excluir outros proprietarios
- [x] Agente do Escritorio enviava emails sem pedir autorizacao

### Sessoes anteriores (ja concluidas)
- [x] v0.37.1 — Auto-Clone VCS no Code Studio
- [x] v0.37.0 — Code Studio Multi-Projeto
- [x] v0.36.3 — JWT Auto-Refresh + Bloqueio de Binarios
- [x] v0.36.2 — Fix Campos AuditLogDB no VCS
- [x] v0.36.1 — Fix Rotas VCS
- [x] v0.36.0 — Hierarquia Editavel + Regras de Aprovacao
- [x] v0.35.1 — Fix Geracao de PDF (Luna)
- [x] v0.35.0 — VCS Integracao GitHub/GitBucket
- [x] v0.34.1 — Correcoes e Melhorias do Code Studio
- [x] v0.34.0 — Code Studio Editor de Codigo Integrado
- [x] v0.33.1 — Gemini 2.0 Flash + GPT-4o
- [x] v0.33.0 — Smart Router Global
- [x] v0.32.0 — Avatares Reais dos Agentes
- [x] v0.31.0 — Escritorio Virtual 3D Isometrico Premium
- [x] v0.30.0 — Escritorio Virtual Revolucionario
- [x] v0.29.0 — Catalogo de Agentes + Atribuicao Dinamica
- [x] v0.28.0 — Bootstrap AWS

## Status Atual
- Tudo em producao (AWS)
- Versao atual: v0.48.0
- 15 agentes no catalogo (incluindo Test Master, GitHub Master, GitBucket Master)
- Code Studio completo: Company Context, Apply+Deploy, Push/PR/Merge, conversas separadas, paineis redimensionaveis
- Sistema de conversas separadas no AgentPanel com persistencia localStorage
- One-Click Apply+Deploy com Test Master bloqueante no pipeline
- Push, PR e Merge direto do Code Studio via GitHub API
- Live Agents com animacoes de status no Escritorio Virtual
- Chat resiliente com timeout de 30min e botoes de retomar conversa
- Company Context Total: agente IA com conhecimento completo da empresa e projetos
- BMAD mapeamento completo com 15 agentes e fases definidas

## Pendencias / Proximos passos
- [ ] Testar integracao VCS com repositorio GitBucket real
- [ ] Testar exclusao permanente de usuarios em producao
- [ ] Atribuir agentes ao Marcos e Rhammon via dashboard
- [ ] Testar solicitacao de agente por um usuario comum
- [ ] Ajustar permissoes granulares para a pagina de Atribuicoes (so admin ve)
- [ ] Mapear os 45 funcionarios da Objetiva e criar squads
- [ ] Corrigir testes de integracao (mock do lifespan para CI)
- [ ] Melhorar escritorio: interacao com sala de reuniao (vidro transparente vendo agentes dentro)
- [ ] Adicionar historico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar sistema de migrations automaticas no bootstrap (Alembic ou ALTER TABLE strategy)
- [ ] Implementar busca global no Code Studio (Ctrl+Shift+F)
- [ ] Terminal integrado no Code Studio
- [ ] Monitoramento de saude dos agentes (heartbeat)
