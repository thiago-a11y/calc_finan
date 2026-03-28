# SyneriumX Tools — Acesso Real ao Repositório

> Ferramentas que permitem aos agentes ler, editar e criar arquivos no projeto SyneriumX real.

## Caminho Base
`~/propostasap` (expandido: /Users/thiagoxavier/propostasap)

## Ferramentas Disponíveis (6)

| Ferramenta | ID | O que faz |
|---|---|---|
| Ler Arquivo | sx_ler_arquivo | Lê conteúdo de qualquer arquivo do projeto |
| Listar Diretório | sx_listar_diretorio | Lista pastas e arquivos |
| Editar Arquivo | sx_escrever_arquivo | Cria ou sobrescreve arquivos |
| Buscar (grep) | sx_buscar | Busca texto recursivamente |
| Git | sx_git | git status/diff/log/branch/add/commit |
| Terminal | sx_terminal | Comandos shell seguros |

## Segurança
- Path restrito: só opera dentro de ~/propostasap
- Comandos destrutivos bloqueados: rm -rf, drop, format, etc.
- Git push/merge/reset requerem aprovação do Operations Lead
- Limite de 100KB por leitura de arquivo
- Timeout de 30s por comando

## Agentes com Acesso
Todos os 9 agentes do Squad CEO têm acesso completo.

Criado em: 2026-03-24
