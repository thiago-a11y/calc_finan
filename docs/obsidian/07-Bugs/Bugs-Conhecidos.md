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

| 11 | Timeout 10min muito curto para reuniões longas — agente expirava antes de concluir consultas complexas | Timeout padrão de 10 minutos insuficiente para tarefas de análise profunda e reuniões com múltiplos agentes | Timeout aumentado para 30 minutos em tarefas e reuniões | 2026-03-30 |
| 12 | Sem opção de retomar conversa após erro/timeout no Escritório Virtual | ChatFloating e ReuniaoModal não tinham mecanismo de recuperação após falha | Botão "Retomar conversa" no ChatFloating e "Retomar de onde parou" no ReuniaoModal + endpoint POST /tarefas/{id}/retomar | 2026-03-30 |
| 13 | Git Pull no Code Studio falhava com "could not read Username" em repos HTTPS | Git tentava abrir prompt interativo para credenciais, travando o processo no servidor | Token VCS injetado na URL HTTPS + GIT_TERMINAL_PROMPT=0 para evitar input interativo | 2026-03-30 |
| 14 | Agente do Escritório Virtual enviava emails sem pedir autorização ao usuário | Prompt do agente não continha restrição explícita sobre envio de emails | Regras obrigatórias injetadas no prompt: não enviar email sem pedir, sugerir Code Studio para código | 2026-03-30 |
| 15 | LLM tracked incompatível com CrewAI 1.11+ (parâmetro available_tools) | CrewAI 1.11 passou a enviar `available_tools` como kwargs, mas o wrapper LLM tracked não aceitava kwargs extras | Corrigido com `**kwargs` no método de chamada do wrapper | 2026-03-30 |
| 16 | Gemini 2.0-flash descontinuado pelo Google | Modelo `gemini-2.0-flash` removido da API do Google, retornando erro 404 | Atualizado para `gemini-2.5-flash` em todas as referências | 2026-03-30 |
| 17 | LangSmith 403 Forbidden no endpoint de query RAG | Decorator `@traceable` no endpoint de query tentava enviar traces sem permissão adequada | Removido `@traceable` do endpoint de query RAG | 2026-03-30 |
| 18 | Chroma deprecation warning (`langchain_community.vectorstores`) | Pacote `langchain_community` marcou Chroma como deprecated, recomendando `langchain_chroma` | Migrado imports de `langchain_community.vectorstores` para `langchain_chroma` | 2026-03-30 |
| 19 | Estimador de tokens inflado — mostrava $55 fantasma | Cálculo de estimativa de custo usava valores incorretos de multiplicação | Corrigido para refletir valores reais de custo por token | 2026-03-30 |
| 20 | Botão "Aplicar" só aparecia na ação Otimizar, não em Refatorar/Documentar | Regex de detecção de ação aplicável capturava apenas "Otimizar" | Regex corrigida para capturar todas as ações (Otimizar, Refatorar, Documentar, Testar) | 2026-03-30 |
| 21 | NetworkError no fetch do endpoint analyze do Code Studio | Timeout padrão do fetch (sem AbortController) expirava antes da resposta do LLM para arquivos grandes | Timeout aumentado para 120s com AbortController explícito | 2026-03-30 |
| 22 | Estouro de 213K tokens ao enviar imagem no chat do agente | Imagem era convertida em base64 e enviada inteira no contexto do LLM, estourando o context window | Imagens passaram a ser tratadas como descrição textual em vez de base64 completo | 2026-03-30 |
| 23 | Texto muted com baixo contraste em dark/light mode | Cor de texto `muted` não atendia padrões de acessibilidade WCAG em ambos os temas | Cores de texto muted ajustadas para contraste adequado em dark e light mode | 2026-03-30 |

### Lições Aprendidas

- **Bug #3 e #9**: `create_all()` do SQLAlchemy só cria tabelas novas, nunca altera esquema de tabelas existentes. Para próximos deploys com novos campos, incluir migration manual no bootstrap ou adotar Alembic. Problema reincidente — priorizar solução definitiva.
- **Bug #4**: Dados vindos do frontend sempre devem ser sanitizados antes de passar a bibliotecas de renderização (ReportLab, WeasyPrint, etc.). Nunca confiar que o conteúdo está limpo.
- **Bug #5 e #6**: Ao adicionar novos routers no FastAPI, sempre verificar o prefixo completo e os nomes dos campos do modelo de destino.
- **Bug #7**: Tokens de curta duração (1h) são bons para segurança, mas péssimos para UX em aplicações de trabalho. Auto-refresh transparente resolve sem comprometer segurança.
- **Bug #8**: Editores de código devem ter whitelist de extensões editáveis ou blacklist de extensões binárias. Nunca tentar renderizar binários como texto.
- **Bug #10**: Caminhos absolutos de desenvolvimento local (Mac) não devem ser persistidos no banco de produção. O auto-clone VCS resolve isso de forma elegante: se o diretório não existe, clona do repositório remoto e atualiza o caminho automaticamente.
- **Bug #11-12**: Timeouts curtos e falta de recuperação são péssimos para UX. Operações de IA são imprevisíveis em duração — timeouts generosos (30min) + botões de retomar garantem que o usuário nunca perca o trabalho.
- **Bug #13**: Git em servidores headless nunca deve esperar input interativo. Injetar credenciais via URL HTTPS + `GIT_TERMINAL_PROMPT=0` é o padrão seguro para automação.
- **Bug #14**: Agentes IA devem ter restrições explícitas no prompt sobre ações irreversíveis (enviar email, deletar dados). Regras implícitas não funcionam — o LLM precisa de instrução clara.
- **Bug #15**: Wrappers de LLM devem sempre aceitar `**kwargs` para compatibilidade futura com frameworks que adicionam novos parâmetros.
- **Bug #16**: Modelos de LLM são descontinuados sem aviso prévio. Manter fallback chain e atualizar rapidamente quando um modelo sai do ar.
- **Bug #19**: Estimadores de custo devem ser validados contra valores reais da API periodicamente para evitar alarmes falsos.
- **Bug #21**: Chamadas a LLMs para arquivos grandes precisam de timeouts generosos (120s+) com AbortController para controle fino.
- **Bug #22**: Nunca enviar imagens em base64 como contexto de LLM — converter para descrição textual ou usar API de vision separada.

---

> Última atualização: 2026-03-30
