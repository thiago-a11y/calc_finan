# Pendências do Último Chat — 28/Mar/2026

> Atualizado em 28/Mar/2026 (sessão 11)

## Concluído nesta sessão

### v0.34.0 — Code Studio — Editor de Código Integrado
- [x] Editor de código com CodeMirror 6 integrado ao dashboard
- [x] 4 endpoints REST para CRUD de arquivos do projeto
- [x] Árvore de arquivos com navegação hierárquica
- [x] Sistema de abas para múltiplos arquivos abertos
- [x] Agente IA integrado para assistência de código
- [x] Syntax highlighting para Python, TypeScript, JavaScript, JSON, Markdown, CSS, HTML
- [x] Audit log LGPD para todas as operações de leitura/escrita
- [x] Proteção contra path traversal e backup automático

### Sessão anterior (sessão 10)

### v0.33.1 — Gemini 2.0 Flash + GPT-4o como Providers Reais
- [x] Gemini 2.0 Flash adicionado como provider via API OpenAI-compatible
- [x] GPT-4o adicionado como provider alternativo na cadeia de fallback
- [x] Cadeia completa: Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together
- [x] Smart Router Global exposto no dashboard (página LLM Providers)
- [x] Gemini adicionado na tela de Consumo de APIs

### Sessão anterior (sessão 9)

### v0.33.0 — Smart Router Global Multi-Provider + Multi-Ferramenta
- [x] Router Global (`core/smart_router_global.py`) com 7 providers de LLM e 8 ferramentas externas
- [x] 13 categorias de intenção detectadas por regex (tempo médio 0.12ms)
- [x] Override manual via prefixo no prompt (@opus, @groq, @exa, etc.)
- [x] Cadeia de fallback multi-provider (Opus → Sonnet → GPT-4o → Gemini → Groq → Fireworks → Together)
- [x] Coexistência com SmartRouter antigo (llm_router.py continua para CrewAI)
- [x] Endpoints da API: /api/router/decidir, /providers, /ferramentas, /categorias
- [x] Documentação: Changelog, Decisões Técnicas, Arquitetura Smart-Router-Global.md

### Sessão anterior (sessão 8)

### v0.32.0 — Avatares Reais dos Agentes
- [x] 10 avatares oficiais em JPG (Kenji, Amara, Carlos, Yuki, Rafael, Hans, Fatima, Marco, Sofia, Luna)
- [x] Config centralizada `src/config/agents.ts` com dados de todos os agentes
- [x] Componente `AgentAvatar.tsx` reutilizável (sm/md/lg/xl/2xl, fallback iniciais, status, hover)
- [x] `AgentAvatarGroup` para empilhar avatares com sobreposição
- [x] Integrado em: ChatFloating, ReuniaoModal, Escritório Virtual, Catálogo, Luna Chat, Luna Welcome

### Correções e melhorias
- [x] Token de convite agora usa `token_hex` (evita ambiguidade visual l/I/1/0/O)
- [x] Aba "Desativados" em Configurações — reativar ou excluir permanentemente
- [x] Vault Obsidian migrado para dentro do repo Git (`docs/obsidian/`)

### Sessões anteriores (sessão 7)

### v0.16.5 — Exclusão Permanente de Usuários
- [x] Endpoint `DELETE /api/usuarios/{id}/permanente` — hard delete para proprietários
- [x] Libera email para reconvite após exclusão permanente
- [x] Audit log LGPD da exclusão permanente

### v0.16.4 — Fix Download de Arquivos Luna em Produção
- [x] Corrigido UPLOAD_DIR em `api/routes/uploads.py` — path do servidor AWS (`/opt/synerium-factory`)
- [x] Downloads de arquivos gerados pela Luna funcionando em produção

### Syncthing Desinstalado
- [x] Syncthing removido do Mac — redundante com rsync do deploy
- [x] ~93 GB livres no Mac após remoção

### Sessões anteriores (já concluídas)
- [x] v0.31.0 — Escritório Virtual 3D Isométrico Premium
- [x] v0.30.0 — Escritório Virtual Revolucionário
- [x] v0.29.0 — Catálogo de Agentes + Atribuição Dinâmica
- [x] v0.28.0 — Bootstrap AWS

## Status Atual
- Tudo em produção (AWS)
- Avatares reais dos agentes implementados em todas as telas
- Luna funcional com downloads e geração de arquivos

## Pendências / Próximos passos
- [ ] Testar exclusão permanente de usuários em produção
- [ ] Atribuir agentes ao Marcos e Rhammon via dashboard
- [ ] Testar solicitação de agente por um usuário comum
- [ ] Ajustar permissões granulares para a página de Atribuições (só admin vê)
- [ ] Mapear os 45 funcionários da Objetiva e criar squads
- [ ] Corrigir testes de integração (mock do lifespan para CI)
- [ ] Melhorar escritório: interação com sala de reunião (vidro transparente vendo agentes dentro)
- [ ] Adicionar histórico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar sistema de migrations automáticas no bootstrap para novos campos (Alembic ou ALTER TABLE strategy)
