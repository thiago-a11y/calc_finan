# Pendencias do Ultimo Chat — 29/Mar/2026

> Atualizado em 29/Mar/2026 (sessao 19)

## Concluido nesta sessao

### v0.39.0 — Company Context Total
- [x] Novo modulo core/company_context.py com CompanyContextBuilder (3 niveis: minimal/standard/full)
- [x] Nivel standard: detalhes profundos do projeto (membros, regras, VCS, fase, lider tecnico)
- [x] Nivel full: empresa + todos projetos + busca RAG semantica (top 3 chunks do ChromaDB)
- [x] Toggle "Contexto Empresa" no AgentPanel com switch ON/OFF (ligado por padrao)
- [x] Badge visual "Contexto Total" nas respostas do assistente quando contexto ativo
- [x] Cache inteligente: 5 minutos para lista de projetos, empresa estatico
- [x] Integracao RAG: ChromaDB + Obsidian vaults, filtrando vault por projeto automaticamente
- [x] Budget de tokens limitado a 4000 chars para nao exceder context window

### v0.38.0 — Historico de Atividades + Feedback Detalhado no Code Studio
- [x] Novo endpoint GET /api/code-studio/historico com paginacao e filtro por projeto
- [x] Calculo de diff no apply-action via difflib (linhas adicionadas/removidas)
- [x] Novo componente HistoricoPanel — lista cronologica com icones, tempo relativo, paginacao
- [x] Toast detalhado ao aplicar acao IA: mostra diff (+N/-N linhas), commit hash e branch VCS
- [x] Confirmacao inline antes de aplicar acoes (Confirmar/Cancelar)
- [x] Botao Historico na Toolbar (toggle mutuamente exclusivo com AgentPanel)
- [x] Clique em arquivo no historico abre diretamente no editor
- [x] Deployado e ativo na AWS

### v0.37.1 — Auto-Clone VCS no Code Studio
- [x] Auto-clone VCS: quando projeto tem VCS configurado mas sem diretorio local, clona para `/opt/projetos/{slug}/`
- [x] Campo `caminho` atualizado automaticamente no banco apos clone
- [x] Git pull inteligente se diretorio ja existe com `.git`
- [x] Endpoint `POST /api/code-studio/git-pull` para atualizar repositorio do remote
- [x] Botao "Pull" no header do Code Studio (visivel com VCS configurado)
- [x] Botao de refresh para recarregar arvore de arquivos
- [x] Mensagem de loading inteligente ("Clonando repositorio...")
- [x] Fix: caminho local do Mac (`/Users/thiagoxavier/propostasap`) nao funcionava no servidor AWS — resolvido via auto-clone

### v0.37.0 — Code Studio Multi-Projeto
- [x] Code Studio agora e project-aware (multi-projeto)
- [x] Seletor de projeto no header com nome, stack e icone VCS
- [x] Backend `_obter_base_projeto()` resolve caminho base por ID
- [x] Todos os endpoints aceitam `project_id`
- [x] VCS auto-commit usa config especifica do projeto
- [x] Agente IA recebe contexto do projeto no system prompt
- [x] Audit log inclui nome do projeto
- [x] Frontend persiste ultimo projeto em localStorage
- [x] Troca de projeto limpa abas e recarrega arvore

### v0.36.3 — JWT Auto-Refresh + Bloqueio de Binarios no Code Studio
- [x] JWT access token aumentado de 1h para 8h (jornada de trabalho completa)
- [x] Auto-refresh transparente: ao receber 401, tenta refresh token antes de redirecionar ao login
- [x] Bloqueio de 19 extensoes de arquivos binarios no Code Studio (.docx, .xlsx, .pptx, .pdf, etc.)
- [x] Corrigido travamento do editor ao abrir arquivos de ata (PPTX)

### v0.36.2 — Fix Campos AuditLogDB no VCS
- [x] Corrigido erro 500 no endpoint VCS — campos `usuario_id` e `detalhes` nao existiam no AuditLogDB
- [x] Corrigido para `user_id` e `descricao`

### v0.36.1 — Fix Rotas VCS
- [x] Corrigido 404 ao salvar configuracao VCS — rotas registradas com prefixo errado
- [x] Prefixo corrigido de `/api/{id}/vcs` para `/api/projetos/{id}/vcs`

### v0.36.0 — Hierarquia Editavel + Regras de Aprovacao por Projeto
- [x] Hierarquia editavel por projeto (proprietario, lider tecnico, membros) via dropdowns inline
- [x] Regras de aprovacao customizaveis por projeto (campo JSON `regras_aprovacao` em ProjetoDB)
- [x] Endpoint `PUT /projetos/{id}/regras` para atualizar regras de aprovacao
- [x] Frontend com dropdowns inline para edicao direta na pagina de projetos
- [x] ALTER TABLE manual no SQLite AWS para adicionar coluna `regras_aprovacao`

### v0.35.1 — Fix Geracao de PDF (Luna)
- [x] Corrigido erro 400 ao gerar PDF — tags HTML do navegador passavam direto ao ReportLab
- [x] Nova funcao `_sanitizar_para_pdf()` para remover/converter tags HTML
- [x] Sanitizacao geral aplicada em `gerar_arquivo()` para prevenir erros similares

### Sessao anterior (sessao 13)

### v0.35.0 — Version Control (VCS) — Integracao GitHub/GitBucket por Projeto
- [x] `core/vcs_service.py` — Servico de VCS com criptografia Fernet para tokens
- [x] `ProjetoVCSDB` — Modelo SQLAlchemy para configuracao VCS por projeto
- [x] 4 endpoints VCS: cadastrar, buscar (sem token), testar conexao, remover
- [x] Code Studio: commit + push automatico apos aplicar acao do agente IA
- [x] Secao VCS no modal de projeto (dashboard)
- [x] Seguranca: token nunca exposto na API, Fernet/AES-128-CBC, audit log LGPD

### Sessao anterior (sessao 12)

### v0.34.1 — Correcoes e Melhorias do Code Studio
- [x] Fix: token de autenticacao renomeado de `token` para `sf_token`
- [x] Fix: tratamento de erro na arvore de arquivos (catch de excecoes)
- [x] Fix: integracao Smart Router corrigida (modelo_forcado removido)
- [x] Feat: menu de contexto (clique direito) no Escritorio Virtual → Code Studio
- [x] Feat: 5a acao no AgentPanel: "Testar" (gera testes unitarios)
- [x] Feat: contexto do arquivo (nome, linguagem, caminho) enviado ao LLM

### Sessao anterior (sessao 11)

### v0.34.0 — Code Studio — Editor de Codigo Integrado
- [x] Editor de codigo com CodeMirror 6 integrado ao dashboard
- [x] 4 endpoints REST para CRUD de arquivos do projeto
- [x] Arvore de arquivos com navegacao hierarquica
- [x] Sistema de abas para multiplos arquivos abertos
- [x] Agente IA integrado para assistencia de codigo
- [x] Syntax highlighting para Python, TypeScript, JavaScript, JSON, Markdown, CSS, HTML
- [x] Audit log LGPD para todas as operacoes de leitura/escrita

### Sessao anterior (sessao 10)

### v0.33.1 — Gemini 2.0 Flash + GPT-4o como Providers Reais
- [x] Gemini 2.0 Flash adicionado como provider via API OpenAI-compatible
- [x] GPT-4o adicionado como provider alternativo na cadeia de fallback
- [x] Cadeia completa: Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
- [x] Smart Router Global exposto no dashboard (pagina LLM Providers)
- [x] Gemini adicionado na tela de Consumo de APIs

### Sessao anterior (sessao 9)

### v0.33.0 — Smart Router Global Multi-Provider + Multi-Ferramenta
- [x] Router Global (`core/smart_router_global.py`) com 7 providers de LLM e 8 ferramentas externas
- [x] 13 categorias de intencao detectadas por regex (tempo medio 0.12ms)
- [x] Override manual via prefixo no prompt (@opus, @groq, @exa, etc.)
- [x] Cadeia de fallback multi-provider (Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together)
- [x] Coexistencia com SmartRouter antigo (llm_router.py continua para CrewAI)
- [x] Endpoints da API: /api/router/decidir, /providers, /ferramentas, /categorias
- [x] Documentacao: Changelog, Decisoes Tecnicas, Arquitetura Smart-Router-Global.md

### Sessao anterior (sessao 8)

### v0.32.0 — Avatares Reais dos Agentes
- [x] 10 avatares oficiais em JPG (Kenji, Amara, Carlos, Yuki, Rafael, Hans, Fatima, Marco, Sofia, Luna)
- [x] Config centralizada `src/config/agents.ts` com dados de todos os agentes
- [x] Componente `AgentAvatar.tsx` reutilizavel (sm/md/lg/xl/2xl, fallback iniciais, status, hover)
- [x] `AgentAvatarGroup` para empilhar avatares com sobreposicao
- [x] Integrado em: ChatFloating, ReuniaoModal, Escritorio Virtual, Catalogo, Luna Chat, Luna Welcome

### Correcoes e melhorias
- [x] Token de convite agora usa `token_hex` (evita ambiguidade visual l/I/1/0/O)
- [x] Aba "Desativados" em Configuracoes — reativar ou excluir permanentemente
- [x] Vault Obsidian migrado para dentro do repo Git (`docs/obsidian/`)

### Sessoes anteriores (sessao 7)

### v0.16.5 — Exclusao Permanente de Usuarios
- [x] Endpoint `DELETE /api/usuarios/{id}/permanente` — hard delete para proprietarios
- [x] Libera email para reconvite apos exclusao permanente
- [x] Audit log LGPD da exclusao permanente

### v0.16.4 — Fix Download de Arquivos Luna em Producao
- [x] Corrigido UPLOAD_DIR em `api/routes/uploads.py` — path do servidor AWS (`/opt/synerium-factory`)
- [x] Downloads de arquivos gerados pela Luna funcionando em producao

### Syncthing Desinstalado
- [x] Syncthing removido do Mac — redundante com rsync do deploy
- [x] ~93 GB livres no Mac apos remocao

### Sessoes anteriores (ja concluidas)
- [x] v0.31.0 — Escritorio Virtual 3D Isometrico Premium
- [x] v0.30.0 — Escritorio Virtual Revolucionario
- [x] v0.29.0 — Catalogo de Agentes + Atribuicao Dinamica
- [x] v0.28.0 — Bootstrap AWS

## Status Atual
- Tudo em producao (AWS)
- Company Context Total: agente IA com conhecimento completo da empresa e projetos (v0.39.0)
- Code Studio com historico de atividades, feedback detalhado e confirmacao inline (v0.38.0)
- Code Studio multi-projeto com auto-clone VCS: clona repositorio automaticamente se diretorio nao existe (v0.37.1)
- VCS integrado ao Code Studio com commit + push automatico (rotas e audit log corrigidos v0.36.1/v0.36.2)
- Avatares reais dos agentes implementados em todas as telas
- Luna funcional com downloads e geracao de arquivos (PDF corrigido na v0.35.1)
- Projetos com hierarquia editavel e regras de aprovacao customizaveis (v0.36.0)
- JWT com auto-refresh transparente — sessao de 8h sem logouts aleatorios (v0.36.3)
- Code Studio com bloqueio de binarios — nao trava mais ao abrir .pptx/.docx (v0.36.3)

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
- [ ] Implementar sistema de migrations automaticas no bootstrap para novos campos (Alembic ou ALTER TABLE strategy)
