# Bugs Conhecidos — Synerium Factory

> Issues abertas e workarounds.

---

## Ativos

Nenhum bug ativo no momento. Sistema recém-criado.

## Resolvidos

| # | Descrição | Causa | Solução | Data |
|---|---|---|---|---|
| 1 | ANTHROPIC_API_KEY não carregava do .env | Variável vazia no env do sistema sobrescrevia o .env | Usar dotenv_values como fallback no settings.py | 2026-03-23 |
| 2 | pydantic-settings rejeitava variáveis extras do .env | Faltava `extra="ignore"` no model_config | Adicionar `extra="ignore"` no SettingsConfigDict | 2026-03-23 |
| 3 | Luna 500 error em produção após deploy v0.16.2 ("Erro ao carregar mensagens") | SQLAlchemy `create_all()` não adiciona colunas novas em tabelas já existentes no SQLite — coluna `anexos` ficou faltando na `luna_mensagens` | `ALTER TABLE luna_mensagens ADD COLUMN anexos JSON` manual no servidor de produção | 2026-03-27 |

### Lições Aprendidas

- **Bug #3**: `create_all()` do SQLAlchemy só cria tabelas novas, nunca altera esquema de tabelas existentes. Para próximos deploys com novos campos, incluir migration manual no bootstrap ou adotar Alembic.

---

> Última atualização: 2026-03-27
