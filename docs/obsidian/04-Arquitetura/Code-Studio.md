# Code Studio — Editor de Código Integrado

> Adicionado na v0.34.0 (2026-03-28) | Última atualização: v0.48.0 (2026-03-30)

---

## Visão Geral

O Code Studio é um editor de código completo integrado ao dashboard do Synerium Factory. Permite editar arquivos do projeto diretamente pelo navegador, com syntax highlighting, agente IA para assistência, Company Context Total, One-Click Apply+Deploy, Push/PR/Merge via GitHub API, sistema de conversas separadas, painéis redimensionáveis e audit log LGPD.

---

## Layout — 3 Painéis Redimensionáveis

```
┌──────────────┬────────────────────────────┬──────────────┐
│              │        Abas de Arquivos     │              │
│   Árvore de  ├────────────────────────────┤   Painel do  │
│   Arquivos   │                            │   Agente IA  │
│   (sidebar)  │     Editor CodeMirror 6    │  (assistente │
│              │     (syntax highlighting)  │   de código)  │
│              │                            │  OU Histórico │
└──────────────┴────────────────────────────┴──────────────┘
         ↕ drag resize          ↕ drag resize
```

- **Painel esquerdo:** Árvore de arquivos do projeto com navegação hierárquica e ícones por tipo
- **Painel central:** Editor CodeMirror 6 com abas para múltiplos arquivos, indicador de modificação (dot), syntax highlighting
- **Painel direito:** AgentPanel (assistente IA) OU HistoricoPanel (toggle mutuamente exclusivo)
- **Painéis redimensionáveis** (v0.44.0): Drag handle entre painéis para ajustar largura, com persistência em localStorage

---

## Company Context Total (v0.39.0)

Sistema de 3 níveis de contexto injetado no system prompt do agente IA:

| Nível | Conteúdo | Uso |
|-------|----------|-----|
| `minimal` | Nome da empresa + projeto atual | Respostas rápidas e simples |
| `standard` | Detalhes profundos do projeto (membros, regras, VCS, fase, líder técnico) | Maioria das tarefas |
| `full` | Empresa + todos projetos + busca RAG semântica (top 3 chunks ChromaDB) | Decisões estratégicas e cross-projeto |

- **Toggle** "Contexto Empresa" no AgentPanel com switch ON/OFF (ligado por padrão)
- **Badge visual** "Contexto Total" nas respostas quando contexto ativo
- **Cache inteligente**: 5 minutos para lista de projetos, empresa estático (cacheable forever)
- **Budget de tokens**: limitado a 4000 chars para não exceder context window
- **Módulo**: `core/company_context.py` com `CompanyContextBuilder`

---

## One-Click Apply+Deploy (v0.41.0)

Pipeline de 5 etapas acionado por um único clique após o agente IA sugerir alteração:

```
1. Backup → 2. Aplicar alteração → 3. Test Master (bloqueante) → 4. Commit → 5. Push
```

- **Test Master obrigatório** — Nem o CEO pode bypassar; se os testes falharem, pipeline para
- **Backup automático** — Arquivo original salvo antes de aplicar alteração
- **Rollback em caso de falha** — Se qualquer etapa falhar, o backup é restaurado
- **Feedback em tempo real** — Progresso visual de cada etapa no frontend

---

## Push & PR & Merge (v0.42.0)

Operações Git completas direto do Code Studio, sem sair do dashboard:

- **PushDialog** — Modal com lista de commits pendentes (`git log origin/main..HEAD`)
- **Seleção de commits** — Checkboxes para escolher quais commits enviar
- **Preview de arquivos por commit** (v0.48.0) — Lista arquivos alterados por commit com diff
- **Horário Brasília** (v0.48.0) — Timestamps em UTC-3 (America/Sao_Paulo)
- **Push** — Envia commits selecionados para o remote
- **Pull Request** — Cria PR no GitHub/GitBucket
- **Merge** — Merge de PR via GitHub API
- **Auto-pull após merge** — Sincroniza repositório local automaticamente
- **Fetch com token VCS** — Sincroniza `origin/main` antes de listar commits

---

## Sistema de Conversas (v0.45.0)

O AgentPanel suporta múltiplas conversas independentes:

- **Novo Chat** — Botão para iniciar conversa limpa sem perder histórico
- **Histórico de conversas** — Lista lateral com título e preview
- **Scroll inteligente** — Posiciona viewport no início da resposta (não no final)
- **Persistência em localStorage** — Conversas salvas por projeto, sobrevivem a reload
- **Indicador de conversa ativa** — Destaque visual na conversa selecionada

---

## Chamar Time (Multi-Agente)

O AgentPanel permite invocar múltiplos agentes do squad na mesma conversa:

- **Botão "Chamar Time"** — Aciona reunião com agentes especializados
- **15 agentes disponíveis** no catálogo (incluindo 3 Elite: Test Master, GitHub Master, GitBucket Master)
- **ThreadPoolExecutor** para execução paralela de tarefas entre agentes
- **BMAD mapeamento** — Cada agente mapeado para fases e palavras-chave

---

## Live Agents (v0.43.0)

Animações visuais que indicam estado dos agentes:

- **Progresso rotativo** no AgentPanel — Indicador de processamento com rotação
- **Balão de status** no Escritório Virtual — Mostra estado (pensando, digitando, ocioso)
- **Shimmer** no ChatFloating — Efeito shimmer durante carregamento
- **Animações contextuais** — Diferentes visuais por estado do agente

---

## Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/code-studio/arvore` | Lista árvore de arquivos do projeto |
| GET | `/api/code-studio/arquivo` | Lê conteúdo de um arquivo |
| PUT | `/api/code-studio/arquivo` | Salva conteúdo de um arquivo (com backup) |
| POST | `/api/code-studio/arquivo` | Cria novo arquivo |
| GET | `/api/code-studio/historico` | Lista cronológica de atividades com paginação |
| POST | `/api/code-studio/analyze` | Análise IA do arquivo (sugestão, refatoração, documentação) |
| POST | `/api/code-studio/apply-action` | Aplica ação da IA com cálculo de diff |
| POST | `/api/code-studio/git-pull` | Atualiza repositório do remote |
| POST | `/api/code-studio/push` | Push de commits para remote |
| POST | `/api/code-studio/pull-request` | Cria Pull Request |
| POST | `/api/code-studio/merge` | Merge de PR via GitHub API |
| GET | `/api/code-studio/git-log` | Lista commits pendentes |

Todos os endpoints requerem autenticação JWT e registram audit log LGPD.

---

## Componentes Frontend

| Componente | Descrição |
|------------|-----------|
| `CodeStudio.tsx` | Página principal com layout de 3 painéis redimensionáveis |
| `FileTree.tsx` | Árvore de arquivos com expansão/colapso e ícones |
| `EditorTabs.tsx` | Sistema de abas com indicador de modificação |
| `CodeEditor.tsx` | Wrapper do CodeMirror 6 com extensões de linguagem |
| `AgentPanel.tsx` | Painel do agente IA com conversas separadas e Company Context |
| `HistoricoPanel.tsx` | Lista cronológica de atividades com diff e paginação |
| `PushDialog.tsx` | Modal de push/PR/merge com seleção de commits e preview |

---

## Segurança

### Proteção contra Path Traversal
- Sanitização de todos os caminhos recebidos via API
- Rejeição de `..`, caminhos absolutos e symlinks externos
- Restrição ao diretório raiz do projeto

### Backup Automático
- Antes de sobrescrever um arquivo, o conteúdo anterior é salvo como backup
- Rollback automático em caso de falha no pipeline Apply+Deploy

### Audit Log LGPD
- Toda operação de leitura e escrita é registrada no audit log
- Campos: usuário, ação, caminho do arquivo, timestamp, IP, projeto

### VCS Seguro
- Token VCS criptografado com Fernet no banco
- Token injetado temporariamente na URL HTTPS para operações git
- Remote restaurado no bloco `finally` (nunca persiste credenciais)
- `GIT_TERMINAL_PROMPT=0` para evitar input interativo em servidor headless

---

## Dependências (CodeMirror 6)

| Pacote | Uso |
|--------|-----|
| `@codemirror/state` | Estado do editor |
| `@codemirror/view` | Renderização e interação |
| `@codemirror/lang-python` | Syntax highlighting Python |
| `@codemirror/lang-javascript` | Syntax highlighting JS/TS |
| `@codemirror/lang-html` | Syntax highlighting HTML |
| `@codemirror/lang-css` | Syntax highlighting CSS |
| `@codemirror/lang-json` | Syntax highlighting JSON |
| `@codemirror/lang-markdown` | Syntax highlighting Markdown |
| `@codemirror/theme-one-dark` | Tema escuro (compatível com design system) |

---

## Rota no Dashboard

- **URL:** `/code-studio`
- **Sidebar:** Ícone de código (`<Code />` do lucide-react)
- **Permissão:** Usuários autenticados com acesso ao módulo

---

> Última atualização: 2026-03-30
