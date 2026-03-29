# Code Studio — Editor de Código Integrado

> Adicionado na v0.34.0 (2026-03-28)

---

## Visão Geral

O Code Studio é um editor de código completo integrado ao dashboard do Synerium Factory. Permite editar arquivos do projeto diretamente pelo navegador, com syntax highlighting, agente IA para assistência e audit log LGPD.

---

## Layout — 3 Painéis

```
┌──────────────┬────────────────────────────┬──────────────┐
│              │        Abas de Arquivos     │              │
│   Árvore de  ├────────────────────────────┤   Painel do  │
│   Arquivos   │                            │   Agente IA  │
│   (sidebar)  │     Editor CodeMirror 6    │  (assistente │
│              │     (syntax highlighting)  │   de código)  │
│              │                            │              │
└──────────────┴────────────────────────────┴──────────────┘
```

- **Painel esquerdo:** Árvore de arquivos do projeto com navegação hierárquica e ícones por tipo
- **Painel central:** Editor CodeMirror 6 com abas para múltiplos arquivos, indicador de modificação (dot), syntax highlighting
- **Painel direito:** Agente IA integrado para assistência de código (sugestões, refatoração, explicação)

---

## Endpoints REST (4)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/code-studio/arvore` | Lista árvore de arquivos do projeto |
| GET | `/api/code-studio/arquivo` | Lê conteúdo de um arquivo (query param: `caminho`) |
| PUT | `/api/code-studio/arquivo` | Salva conteúdo de um arquivo (com backup) |
| POST | `/api/code-studio/arquivo` | Cria novo arquivo |

Todos os endpoints requerem autenticação JWT e registram audit log LGPD.

---

## Componentes Frontend

| Componente | Descrição |
|------------|-----------|
| `CodeStudio.tsx` | Página principal com layout de 3 painéis |
| `FileTree.tsx` | Árvore de arquivos com expansão/colapso e ícones |
| `EditorTabs.tsx` | Sistema de abas com indicador de modificação |
| `CodeEditor.tsx` | Wrapper do CodeMirror 6 com extensões de linguagem |
| `AIAssistant.tsx` | Painel do agente IA para assistência de código |

---

## Segurança

### Proteção contra Path Traversal
- Sanitização de todos os caminhos recebidos via API
- Rejeição de `..`, caminhos absolutos e symlinks externos
- Restrição ao diretório raiz do projeto

### Backup Automático
- Antes de sobrescrever um arquivo, o conteúdo anterior é salvo como backup
- Permite recuperação em caso de erro

### Audit Log LGPD
- Toda operação de leitura e escrita é registrada no audit log
- Campos: usuário, ação, caminho do arquivo, timestamp, IP

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

> Última atualização: 2026-03-28
