# Arquitetura — Company Context Total

> Módulo que injeta conhecimento completo da empresa e projetos no system prompt do agente IA.

---

## Visão Geral

O `CompanyContextBuilder` (`core/company_context.py`) constrói um bloco de contexto estruturado que é injetado no system prompt antes de cada interação com o LLM. Permite que o agente IA tenha conhecimento profundo sobre a empresa, projetos, hierarquia e documentação — sem precisar perguntar ao usuário.

## Fluxo de Dados

```
AgentPanel (frontend)
  │
  │ toggle "Contexto Empresa" ON
  │ envia context_level no request
  ▼
API /api/code-studio/assistente
  │
  ▼
CompanyContextBuilder.build(project_id, level)
  │
  ├── minimal: nome empresa + projeto atual
  │
  ├── standard: + membros, regras, VCS, fase, líder técnico
  │     └── query ProjetoDB + UsuarioDB
  │
  └── full: + todos projetos + RAG semântica
        ├── query ProjetoDB (todos)
        └── ChromaDB.query(prompt, vault=projeto)
              └── top 3 chunks (Obsidian)
  │
  ▼
System Prompt = contexto_empresa + contexto_projeto + rag_chunks + prompt_usuario
  │
  ▼
LLM (Opus/Sonnet via Smart Router)
  │
  ▼
Resposta com badge "Contexto Total" (se contexto ativo)
```

## Níveis de Contexto

### minimal
- Nome da empresa
- Nome e stack do projeto atual
- Uso: respostas rápidas, perguntas genéricas de código

### standard (padrão)
- Tudo do minimal +
- Membros do projeto com papéis (proprietário, líder técnico, membros)
- Regras de aprovação configuradas
- Configuração VCS (provider, repositório, branch)
- Fase atual do projeto
- Líder técnico identificado
- Uso: maioria das interações no Code Studio

### full
- Tudo do standard +
- Dados da empresa (domínio, produtos, hierarquia executiva)
- Lista de todos os projetos ativos com resumo
- Busca RAG semântica no ChromaDB (top 3 chunks mais relevantes ao prompt)
- Filtragem automática de vault por projeto
- Uso: decisões estratégicas, perguntas cross-projeto, análise de arquitetura

## Integração com RAG

O nível `full` utiliza o ChromaDB já indexado pelo sistema RAG existente (`rag/`). A busca semântica é feita com o prompt do usuário como query, filtrando pela collection do vault Obsidian associado ao projeto. Retorna os 3 chunks mais relevantes, cada um truncado para respeitar o budget total de tokens.

### Fluxo RAG
1. Recebe o prompt do usuário
2. Identifica o vault Obsidian do projeto (metadata no ChromaDB)
3. Executa similarity search com filtro de vault
4. Retorna top 3 chunks ordenados por relevância
5. Concatena respeitando o budget de 4000 chars

## Gestão de Tokens

O contexto total é limitado a **4000 caracteres** para não exceder o context window do LLM. A distribuição aproximada:

| Componente | Budget |
|-----------|--------|
| Empresa (estático) | ~500 chars |
| Projeto atual | ~800 chars |
| Membros e regras | ~700 chars |
| Outros projetos (full) | ~500 chars |
| RAG chunks (full) | ~1500 chars |
| **Total máximo** | **~4000 chars** |

Se o contexto exceder o budget, os chunks RAG são truncados primeiro, depois os projetos secundários.

## Cache

| Dado | TTL | Motivo |
|------|-----|--------|
| Empresa | Infinito (estático) | Raramente muda |
| Lista de projetos | 5 minutos | Projetos podem ser criados/alterados |
| Detalhes do projeto | Por request | Membros e regras podem mudar a qualquer momento |
| Chunks RAG | Por request | Depende do prompt do usuário |

## Frontend

- **Toggle** "Contexto Empresa" no AgentPanel — switch ON/OFF
- Ligado por padrão para máxima utilidade
- Estado persistido em localStorage
- **Badge** "Contexto Total" exibido nas respostas do assistente quando contexto estava ativo

## Arquivos Relacionados

- `core/company_context.py` — CompanyContextBuilder
- `rag/` — Sistema RAG com ChromaDB
- `dashboard/src/components/AgentPanel.tsx` — Toggle no frontend
- `api/routes/code_studio.py` — Endpoint que recebe context_level

---

> Última atualização: 2026-03-29
