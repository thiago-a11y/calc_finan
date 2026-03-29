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
| 4 | Luna PDF erro 400 ao gerar arquivo | Tags HTML do navegador (`<div>`, `<span>`, etc.) passavam direto ao ReportLab, que não aceita HTML | Nova função `_sanitizar_para_pdf()` em `core/luna_file_generator.py` + sanitização geral em `gerar_arquivo()` | 2026-03-29 |
| 5 | VCS 404 ao salvar configuração | Rotas VCS registradas como `/api/{id}/vcs` em vez de `/api/projetos/{id}/vcs` — prefixo incorreto | Corrigido prefixo das rotas no registro dos endpoints VCS | 2026-03-29 |
| 6 | VCS 500 Internal Server Error ao operar | Endpoint usava `usuario_id` e `detalhes` que não existem em AuditLogDB | Corrigido para `user_id` e `descricao` (campos reais do modelo) | 2026-03-29 |
| 7 | JWT 1h causava logouts aleatórios | Token expirava em 1h; durante trabalho normal o usuário era deslogado sem aviso | Access token aumentado para 8h + auto-refresh transparente via refresh token | 2026-03-29 |
| 8 | Code Studio travava ao abrir binários | Clicar em arquivos `.pptx` (atas de reunião) ou outros binários congelava o editor inteiro | Bloqueio de 19 extensões binárias com mensagem de aviso; editor não tenta abrir | 2026-03-29 |
| 9 | Coluna `regras_aprovacao` faltando no SQLite (AWS) | `create_all()` do SQLAlchemy não adiciona colunas em tabelas existentes — mesmo problema do bug #3 | `ALTER TABLE projetos ADD COLUMN regras_aprovacao JSON` manual no servidor AWS | 2026-03-29 |

| 10 | Code Studio não abria arquivos do SyneriumX no servidor AWS | Campo `caminho` no banco apontava para `/Users/thiagoxavier/propostasap` (caminho do Mac local), que não existe no servidor AWS Linux | Auto-clone VCS: quando o diretório não existe, o Code Studio clona automaticamente o repositório para `/opt/projetos/{slug}/` e atualiza o campo `caminho` no banco | 2026-03-29 |

### Lições Aprendidas

- **Bug #3 e #9**: `create_all()` do SQLAlchemy só cria tabelas novas, nunca altera esquema de tabelas existentes. Para próximos deploys com novos campos, incluir migration manual no bootstrap ou adotar Alembic. Problema reincidente — priorizar solução definitiva.
- **Bug #4**: Dados vindos do frontend sempre devem ser sanitizados antes de passar a bibliotecas de renderização (ReportLab, WeasyPrint, etc.). Nunca confiar que o conteúdo está limpo.
- **Bug #5 e #6**: Ao adicionar novos routers no FastAPI, sempre verificar o prefixo completo e os nomes dos campos do modelo de destino.
- **Bug #7**: Tokens de curta duração (1h) são bons para segurança, mas péssimos para UX em aplicações de trabalho. Auto-refresh transparente resolve sem comprometer segurança.
- **Bug #8**: Editores de código devem ter whitelist de extensões editáveis ou blacklist de extensões binárias. Nunca tentar renderizar binários como texto.
- **Bug #10**: Caminhos absolutos de desenvolvimento local (Mac) não devem ser persistidos no banco de produção. O auto-clone VCS resolve isso de forma elegante: se o diretório não existe, clona do repositório remoto e atualiza o caminho automaticamente.

---

> Última atualização: 2026-03-29
