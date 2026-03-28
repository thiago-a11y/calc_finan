# Pendências do Último Chat — 27/Mar/2026

> Atualizado em 27/Mar/2026 (sessão 7)

## Concluído nesta sessão

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

### Sessões anteriores (sessão 6)

### v0.16.3 — Luna: Geração de Arquivos para Download
- [x] Motor de geração: `core/luna_file_generator.py` com engines por formato
- [x] 9 formatos: XLSX, DOCX, PPTX, PDF, TXT, MD, CSV, JSON, HTML
- [x] Endpoint `POST /api/luna/gerar-arquivo`
- [x] Marcadores `:::arquivo[nome.ext]` no system prompt
- [x] Componente `LunaFileBlock` com card de download profissional
- [x] Planilhas com formatação (headers emerald, bordas, largura auto)
- [x] Documentos com markdown parseado
- [x] Apresentações com slides por `##`
- [x] PDFs com layout profissional (ReportLab)

### v0.16.2 — Luna: Anexos de Arquivos
- [x] Botão 📎 no input com preview dos arquivos selecionados
- [x] Anexos (imagens, PDFs, documentos, código) incluídos no contexto do LLM
- [x] Exibição clicável nos balões de mensagem
- [x] Suporte a múltiplos arquivos (max 50MB cada)

### v0.16.1 — Luna: Soft Delete + Lixeira
- [x] Soft delete transparente (usuário não percebe — exclusão lógica)
- [x] Lixeira exclusiva para proprietários no painel de supervisão
- [x] Restaurar ou excluir permanentemente conversas da lixeira
- [x] Confirmação dupla para exclusão permanente
- [x] Audit log LGPD em todas as ações de soft delete/restauração/exclusão

### v0.16.0 — Luna: Assistente IA Integrada
- [x] Backend: 2 modelos novos (LunaConversaDB, LunaMensagemDB)
- [x] Backend: luna_engine.py com streaming + fallback chain (Opus→Sonnet→Groq→Fireworks→Together)
- [x] Backend: Rotas API com SSE streaming
- [x] Frontend: 7 componentes (MarkdownRenderer, LunaWelcome, LunaInput, LunaChat, LunaSidebar, LunaPreview, LunaAdminView)
- [x] Frontend: Página Luna.tsx + service luna.ts
- [x] Streaming SSE em tempo real
- [x] Entrada por voz (Web Speech API)
- [x] Markdown rendering com syntax highlighting
- [x] Preview de artefatos
- [x] Gestão de conversas (criar, listar, renomear, excluir)
- [x] Supervisão do CEO (visão de chats dos funcionários com audit LGPD)
- [x] Smart Router perfil consultora_estrategica (peso 0.4)
- [x] Rota /luna + entrada na Sidebar com badge IA

### Deploy Luna v0.16.0 + v0.16.1 + v0.16.2 na AWS
- [x] Deploy em produção AWS (27/Mar/2026)
- [x] Fix produção: coluna `anexos` faltando na `luna_mensagens` — `ALTER TABLE` manual aplicado (27/Mar/2026)

### Sessões anteriores (já concluídas)
- [x] v0.31.0 — Escritório Virtual 3D Isométrico Premium
- [x] v0.30.0 — Escritório Virtual Revolucionário
- [x] v0.29.0 — Catálogo de Agentes + Atribuição Dinâmica
- [x] v0.28.0 — Bootstrap AWS

## Status Atual
- Tudo em produção (AWS)
- 93 GB livres no Mac (Syncthing removido)
- Luna funcional com downloads e geração de arquivos

## Pendências / Próximos passos
- [ ] Testar exclusão permanente de usuários em produção
- [x] ~~Testar Luna em produção (deploy AWS)~~ — Concluído 27/Mar/2026
- [ ] Atribuir agentes ao Marcos e Rhammon via dashboard
- [ ] Testar solicitação de agente por um usuário comum
- [ ] Ajustar permissões granulares para a página de Atribuições (só admin vê)
- [ ] Mapear os 45 funcionários da Objetiva e criar squads
- [ ] Corrigir testes de integração (mock do lifespan para CI)
- [ ] Melhorar escritório: interação com sala de reunião (vidro transparente vendo agentes dentro)
- [ ] Adicionar histórico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar sistema de migrations automáticas no bootstrap para novos campos (Alembic ou ALTER TABLE strategy)
