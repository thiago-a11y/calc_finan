# Luna — Assistente Inteligente

## Visão Geral
Luna é a assistente inteligente do Synerium Factory — um ChatGPT/Claude pessoal integrado à plataforma, em ambiente controlado com contexto infinito e supervisão de proprietários.

**Diferença da Sofia:** Sofia é secretária executiva (reuniões, atas, emails). Luna é consultora estratégica (pensar melhor, refinar prompts, reflexões, preparar pedidos para agentes).

## Arquitetura Backend

### Motor (`core/luna_engine.py`)
- Streaming via SSE (Server-Sent Events) usando `ChatAnthropic.astream()`
- Cadeia de fallback: Opus → Sonnet → Groq → Fireworks → Together
- Smart Router: perfil `consultora_estrategica` (peso 0.4, default Sonnet)
- Janela deslizante de contexto (últimas 20 mensagens)
- Geração automática de título após primeira mensagem
- Tracking de uso via UsageTrackingDB (tipo="luna")

### Banco de Dados
| Tabela | Campos principais |
|--------|------------------|
| `luna_conversas` | id (nanoid 12), usuario_id, usuario_nome, titulo, modelo_preferido, company_id, timestamps |
| `luna_mensagens` | id, conversa_id, papel (user/assistant), conteudo, modelo_usado, provider_usado, tokens_input, tokens_output, custo_usd, criado_em |

### API (`api/routes/luna.py`)
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/luna/conversas` | GET | Listar conversas do usuário |
| `/api/luna/conversas` | POST | Criar nova conversa |
| `/api/luna/conversas/{id}` | GET | Buscar conversa com mensagens |
| `/api/luna/conversas/{id}` | PUT | Renomear conversa |
| `/api/luna/conversas/{id}` | DELETE | Excluir conversa |
| `/api/luna/conversas/{id}/mensagens` | POST | Enviar mensagem (SSE streaming) |
| `/api/luna/conversas/{id}/regenerar` | POST | Regenerar última resposta (SSE) |
| `/api/luna/admin/usuarios` | GET | Listar usuários Luna (proprietários) |
| `/api/luna/admin/conversas/{uid}` | GET | Conversas de funcionário (proprietários) |
| `/api/luna/admin/conversas/{uid}/{cid}` | GET | Ver chat completo (somente leitura, LGPD) |

### Supervisão (Proprietários)
- Papéis com acesso: `ceo`, `operations_lead`, `proprietario`, `diretor_tecnico`
- Somente leitura — proprietários NÃO podem editar/excluir chats de outros
- Audit log LGPD: registra quando proprietário visualiza chat (`acao="LUNA_SUPERVISAO"`)

## Arquitetura Frontend

### Componentes (`dashboard/src/components/luna/`)
| Componente | Função |
|------------|--------|
| `MarkdownRenderer.tsx` | Renderização Markdown + syntax highlight (react-markdown + remark-gfm) |
| `LunaWelcome.tsx` | Tela de boas-vindas com sugestões rápidas |
| `LunaInput.tsx` | Textarea auto-expansível + voz (Web Speech API pt-BR) + envio |
| `LunaChat.tsx` | Mensagens com streaming + detecção de artefatos |
| `LunaSidebar.tsx` | Lista de conversas agrupada por data |
| `LunaPreview.tsx` | Painel de preview de artefatos (código, HTML, Markdown) |
| `LunaAdminView.tsx` | Painel de supervisão para proprietários |

### Página Principal (`pages/Luna.tsx`)
- Layout: Sidebar esquerda (conversas) + Chat (centro) + Preview (direita, opcional)
- Rota: `/luna` — entrada na sidebar com badge "IA" em destaque

### Serviço (`services/luna.ts`)
- CRUD de conversas via REST
- Streaming SSE via `fetch` + `ReadableStream` + parser de eventos
- Suporte a cancelamento via `AbortController`

## Funcionalidades
- ✅ Streaming em tempo real (token por token)
- ✅ Reconhecimento de voz (Web Speech API, pt-BR)
- ✅ Markdown com syntax highlighting
- ✅ Preview de artefatos (código, HTML, tabelas)
- ✅ Gestão de conversas (criar, listar, renomear, excluir)
- ✅ Supervisão de proprietários com audit log LGPD
- ✅ Fallback multi-provider (nunca falha)
- ✅ Smart Router (Sonnet para simples, Opus para complexo)
- ✅ Contexto infinito (histórico persistido, janela deslizante)

## Anexos de Arquivos (v0.16.2)

### Funcionalidade
- Usuário pode anexar arquivos (imagens, PDFs, documentos, código) às mensagens
- Botão 📎 no `LunaInput` abre seletor de arquivos com preview antes do envio
- Múltiplos arquivos por mensagem, limite de 50MB cada
- Anexos são incluídos automaticamente no contexto enviado ao LLM
- Nos balões de mensagem (`LunaChat`), anexos aparecem como elementos clicáveis

### Tipos suportados
| Categoria | Extensões |
|-----------|-----------|
| Imagens | PNG, JPG, GIF, WebP, SVG |
| Documentos | PDF, DOC, DOCX, TXT |
| Código | JS, TS, PY, JSON, HTML, CSS, MD |

## Geração de Arquivos para Download (v0.16.3)

### Funcionalidade
- Luna gera arquivos para download direto no chat em 9 formatos
- Marcador `:::arquivo[nome.ext]` no system prompt sinaliza a geração
- Card profissional (`LunaFileBlock`) exibe nome, ícone e botão de download

### Formatos suportados
| Formato | Engine | Detalhes |
|---------|--------|----------|
| XLSX | openpyxl | Headers emerald, bordas, largura automática |
| DOCX | python-docx | Markdown parseado com estilos |
| PPTX | python-pptx | Slides separados por `##` |
| PDF | ReportLab | Layout profissional |
| TXT | nativo | Texto puro |
| MD | nativo | Markdown |
| CSV | nativo | Dados tabulares |
| JSON | nativo | Dados estruturados |
| HTML | nativo | Página web |

### Arquitetura
- **Motor**: `core/luna_file_generator.py` — engines especializadas por formato
- **Endpoint**: `POST /api/luna/gerar-arquivo` — recebe conteúdo + formato, retorna arquivo
- **Frontend**: `LunaFileBlock.tsx` — componente de download com card profissional
- **Detecção**: parser no `LunaChat` identifica marcadores `:::arquivo[...]` e renderiza o bloco

## Fix de Produção — Download de Arquivos (v0.16.4)

### Problema
Downloads de arquivos gerados pela Luna retornavam 404 em produção (AWS). O `UPLOAD_DIR` em `api/routes/uploads.py` apontava para `~/synerium` (path local do Mac), mas no servidor o projeto fica em `/opt/synerium-factory`.

### Solução
Path de uploads ajustado para ser relativo ao projeto, funcionando tanto em desenvolvimento local quanto em produção AWS.

## Versão
- v0.16.0 — Implementação inicial (27/Mar/2026)
- v0.16.1 — Soft Delete + Lixeira (27/Mar/2026)
- v0.16.2 — Anexos de Arquivos (27/Mar/2026)
- v0.16.3 — Geração de Arquivos para Download (27/Mar/2026)
- v0.16.4 — Fix download de arquivos em produção (27/Mar/2026)
