# Arquitetura — Integracao VCS (Version Control)

> Adicionado na v0.35.0 (2026-03-29)

---

## Visao Geral

O sistema de Version Control permite vincular repositorios Git (GitHub ou GitBucket) a cada projeto do Synerium Factory. O Code Studio utiliza essa integracao para fazer commit e push automaticamente apos o agente IA aplicar uma acao no codigo.

---

## Fluxo de Commit Automatico

```
1. Usuario abre arquivo no Code Studio
2. Agente IA sugere alteracao (explicar, refatorar, corrigir, documentar, testar)
3. Usuario clica em "Aplicar" na sugestao do agente
4. Code Studio salva o arquivo via endpoint existente
5. Se o projeto tem VCS configurado:
   a. vcs_service.commit(projeto_id, mensagem, arquivos)
   b. vcs_service.push(projeto_id)
6. Feedback visual no Code Studio: "Commit e push realizados com sucesso"
```

---

## Seguranca

### Criptografia de Tokens
- **Algoritmo:** Fernet (AES-128-CBC com HMAC SHA-256)
- **Chave:** Derivada do `JWT_SECRET_KEY` via PBKDF2 ou hash determinisfico
- **Armazenamento:** Token criptografado salvo na coluna `token_criptografado` do `ProjetoVCSDB`
- **Exposicao:** Token NUNCA retornado pela API — endpoint GET retorna apenas `token_configurado: true/false`

### Permissoes
- Apenas **proprietario** e **lider tecnico** do projeto podem configurar VCS
- Operacoes VCS registradas no audit log (LGPD)
- Token descriptografado apenas no momento do uso (commit/push/teste)

---

## Modelo de Dados

### ProjetoVCSDB (tabela: `projeto_vcs`)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | Integer (PK) | ID unico |
| projeto_id | Integer (FK) | Referencia ao projeto |
| provider | String | `github` ou `gitbucket` |
| repo_url | String | URL do repositorio |
| branch | String | Branch padrao (default: `main`) |
| token_criptografado | Text | Token de acesso criptografado com Fernet |
| criado_em | DateTime | Data de criacao |
| atualizado_em | DateTime | Ultima atualizacao |

---

## Endpoints da API

### `POST /api/projetos/{id}/vcs`
Cadastra ou atualiza configuracao VCS do projeto.
- **Body:** `{ provider, repo_url, branch, token }`
- **Resposta:** `{ id, provider, repo_url, branch, token_configurado: true }`
- **Permissao:** Proprietario ou lider tecnico

### `GET /api/projetos/{id}/vcs`
Retorna configuracao VCS (sem token).
- **Resposta:** `{ id, provider, repo_url, branch, token_configurado: true/false }`
- **Permissao:** Qualquer membro do projeto

### `POST /api/projetos/{id}/vcs/testar`
Testa conexao com o repositorio usando o token armazenado.
- **Resposta:** `{ sucesso: true/false, mensagem: "..." }`
- **Permissao:** Proprietario ou lider tecnico

### `DELETE /api/projetos/{id}/vcs`
Remove configuracao VCS do projeto (apaga token criptografado).
- **Permissao:** Proprietario ou lider tecnico

---

## Integracao com Code Studio

O Code Studio (`dashboard/src/pages/CodeStudio.tsx`) verifica se o projeto atual tem VCS configurado. Quando o usuario aplica uma acao do agente IA:

1. Salva o arquivo normalmente (endpoint existente)
2. Chama `POST /api/projetos/{id}/vcs/commit` com a mensagem gerada automaticamente
3. Exibe toast de sucesso/erro no editor

### Secao VCS no Modal de Projeto
- Campo "Provider" (select: GitHub / GitBucket)
- Campo "URL do Repositorio"
- Campo "Branch" (default: main)
- Campo "Token de Acesso" (tipo password, nunca preenchido ao editar)
- Botao "Testar Conexao"

---

## Servico Central

### `core/vcs_service.py`

```python
class VCSService:
    def criptografar_token(self, token: str) -> str
    def descriptografar_token(self, token_criptografado: str) -> str
    def testar_conexao(self, provider: str, repo_url: str, token: str) -> bool
    def commit(self, projeto_id: int, mensagem: str, arquivos: list[str]) -> dict
    def push(self, projeto_id: int) -> dict
```

- Suporte a GitHub (API REST v3) e GitBucket (API compativel)
- Fernet key derivada do `JWT_SECRET_KEY`
- Todas as operacoes com audit log

---

## Providers Suportados

| Provider | API | Autenticacao |
|----------|-----|-------------|
| GitHub | REST API v3 (`api.github.com`) | Personal Access Token (PAT) |
| GitBucket | REST API compativel | Token de acesso |

---

> Ultima atualizacao: 2026-03-29
