# Pendencias do Ultimo Chat — 30/Mar/2026

> Atualizado em 30/Mar/2026 (sessao 20)

## Concluido nesta sessao

### v0.40.0 — Chat Resiliente + Timeout + Retomar Conversa
- [x] Timeout de tarefas/reunioes aumentado de 10 para 30 minutos
- [x] Novo endpoint POST /tarefas/{id}/retomar — re-executa tarefa ou reabre reuniao
- [x] Botao "Retomar conversa" no ChatFloating do Escritorio Virtual quando agente da erro
- [x] Botao "Retomar de onde parou" no ReuniaoModal quando reuniao da timeout/erro
- [x] Git Pull no Code Studio agora usa token VCS para autenticacao HTTPS
- [x] GIT_TERMINAL_PROMPT=0 evita travar esperando input do usuario

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

### Bugs corrigidos nesta sessao
- [x] LLM tracked incompativel com CrewAI 1.11+ (available_tools) — Corrigido com **kwargs
- [x] Gemini 2.0-flash descontinuado — Atualizado para Gemini 2.5-flash
- [x] LangSmith 403 no RAG — Removido @traceable do query
- [x] Chroma deprecation warning — Migrado para langchain_chroma
- [x] Estimador de tokens inflado ($55 fantasma) — Corrigido para valores reais
- [x] Botao "Aplicar" so aparecia em Otimizar, nao em Refatorar/Documentar — Regex corrigida
- [x] NetworkError no fetch do analyze — Timeout aumentado para 120s com AbortController
- [x] Estouro de 213K tokens ao enviar imagem no chat — Imagens tratadas como descricao textual
- [x] Texto muted com baixo contraste no dark/light mode — Cores ajustadas
- [x] Git Pull no Code Studio falhava com "could not read Username" em repos HTTPS — Corrigido com injecao de token VCS
- [x] Agente do Escritorio enviava emails sem pedir — Bloqueado com regras obrigatorias no prompt

### Administrativo
- [x] Creditos Anthropic recarregados ($29.90)
- [x] Chave Gemini confirmada como paga (Nivel 1 pos-pagamento)

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
- Chat resiliente com timeout de 30min e botoes de retomar conversa (v0.40.0)
- Company Context Total: agente IA com conhecimento completo da empresa e projetos (v0.39.0)
- Code Studio com historico de atividades, feedback detalhado e confirmacao inline (v0.38.0)
- Code Studio multi-projeto com auto-clone VCS (v0.37.1)
- VCS integrado ao Code Studio com commit + push automatico
- Git Pull autenticado com token VCS via HTTPS
- Avatares reais dos agentes implementados em todas as telas
- Luna funcional com downloads e geracao de arquivos
- JWT com auto-refresh transparente — sessao de 8h

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
