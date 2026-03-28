# RAG — Base de Conhecimento com IA

## Visão Geral
O sistema RAG (Retrieval-Augmented Generation) permite que os agentes e usuários consultem toda a documentação dos projetos da Objetiva usando busca semântica + resposta inteligente do Claude.

## Fluxo de Consulta

```
Pergunta → Busca Semântica (ChromaDB) → Chunks Relevantes → Claude Gera Resposta → Resposta em Português
```

## Componentes

| Componente | Arquivo | Função |
|---|---|---|
| Config | `rag/config.py` | Configurações (vaults, chunk size, modelo) |
| Loader | `rag/loader.py` | Carrega .md dos vaults Obsidian |
| Splitter | `rag/splitter.py` | Divide em chunks inteligentes (2 estágios) |
| Embeddings | `rag/embeddings.py` | Vetoriza com OpenAI text-embedding-3-small |
| Store | `rag/store.py` | ChromaDB com isolamento multi-tenant |
| Query | `rag/query.py` | Interface de busca formatada |
| Assistant | `rag/assistant.py` | Síntese de respostas com Claude |
| Tool | `tools/rag_tool.py` | Ferramenta CrewAI para agentes |

## Vaults Configurados

| Vault | Caminho | Conteúdo |
|---|---|---|
| syneriumx | `~/Documents/SyneriumX-notes` | Documentação do CRM SyneriumX |
| factory | `~/Documents/SyneriumFactory-notes` | Documentação do Synerium Factory |

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/rag/status` | Configuração dos vaults |
| GET | `/api/rag/stats` | Estatísticas (total chunks, por vault) |
| POST | `/api/rag/consultar` | Consulta com resposta IA + chunks |
| POST | `/api/rag/indexar` | Reindexar vaults (todos ou específico) |

## Estratégia de Chunking (2 estágios)
1. **MarkdownHeaderTextSplitter** — divide por headers (#, ##, ###) preservando hierarquia
2. **RecursiveCharacterTextSplitter** — subdivide chunks grandes (1000 chars, 200 overlap)

## Multi-Tenant
- Cada tenant tem coleções separadas: `tenant_{company_id}_{vault}`
- Isolamento total entre empresas
- Pronto para licenciamento futuro

## Dashboard
A página `/rag` no dashboard oferece:
- Cards de estatísticas (total chunks, vaults, modelo, chunk size)
- Botão "Reindexar" (todos ou por vault)
- Campo de consulta com filtro por vault
- Resposta da IA formatada
- Fontes consultadas (colapsável com detalhes dos chunks)

## Custos Estimados
- Indexação (~35 arquivos): ~$0.002 (OpenAI embeddings)
- Consulta: ~$0.003 por pergunta (Claude claude-sonnet-4-20250514)
- Reindexação: mesmo custo da indexação inicial

## Configuração (.env)
```
RAG_VAULT_SYNERIUMX=/caminho/para/SyneriumX-notes
RAG_VAULT_FACTORY=/caminho/para/SyneriumFactory-notes
RAG_PERSIST_DIR=data/chromadb
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```
