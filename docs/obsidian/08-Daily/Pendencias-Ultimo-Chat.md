# Pendências do Último Chat — 28/Mar/2026

> Atualizado em 28/Mar/2026 (sessão 8)

## Concluído nesta sessão

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
