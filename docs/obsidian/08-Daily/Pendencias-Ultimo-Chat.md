# Pendencias do Ultimo Chat — 29/Mar/2026

> Atualizado em 29/Mar/2026 (sessao 14)

## Concluido nesta sessao

### v0.36.0 — Hierarquia Editavel + Regras de Aprovacao por Projeto
- [x] Hierarquia editavel por projeto (proprietario, lider tecnico, membros) via dropdowns inline
- [x] Regras de aprovacao customizaveis por projeto (campo JSON `regras_aprovacao` em ProjetoDB)
- [x] Endpoint `PUT /projetos/{id}/regras` para atualizar regras de aprovacao
- [x] Frontend com dropdowns inline para edicao direta na pagina de projetos

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
- VCS integrado ao Code Studio com commit + push automatico
- Avatares reais dos agentes implementados em todas as telas
- Luna funcional com downloads e geracao de arquivos (PDF corrigido na v0.35.1)
- Projetos com hierarquia editavel e regras de aprovacao customizaveis (v0.36.0)

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
