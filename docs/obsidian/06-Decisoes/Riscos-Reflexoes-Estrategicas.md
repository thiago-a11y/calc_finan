# Riscos & Reflexões Estratégicas — Synerium Factory

> Diário de discussões estratégicas com análise de riscos, prós/contras e "advocacia do diabo".
> Objetivo: registrar debates reais para alimentar pré-decisões e evitar erros caros.
> Atualizado em: 2026-03-26

---

## Como usar este documento

Este não é um log de decisões tomadas (isso fica em `Decisoes-Tecnicas.md`). Aqui registramos **o processo de pensar antes de decidir** — incluindo:

- A pergunta original
- Os argumentos a favor e contra
- Os riscos que ninguém mencionou mas existem
- A recomendação final e o porquê
- O que poderia dar errado mesmo com a decisão "certa"

### Regras para pré-decisões:
1. **Nunca apenas concordar** — sempre apresentar o contra-argumento mais forte
2. **Quantificar quando possível** — "é caro" não serve, "custa R$X/mês vs R$Y/mês" serve
3. **Separar urgente de importante** — o que precisa ser feito agora vs o que pode esperar
4. **Pensar em 3 horizontes** — impacto imediato, em 3 meses, em 1 ano
5. **Identificar o ponto sem retorno** — até onde dá pra voltar atrás sem dor

---

## #001 — Deploy AWS Lightsail vs cPanel (2026-03-26)

### Contexto
O Synerium Factory precisa sair do Mac local para um servidor acessível pela empresa.

### Opções
1. **AWS Lightsail** — VPS Ubuntu com Python + Nginx ($12/mês)
2. **cPanel** — Mesmo hosting do SyneriumX (compartilhado, PHP only)
3. **Railway/Render** — PaaS com deploy automático ($5-20/mês)

### Decisão: AWS Lightsail
- Controle total do servidor
- Python nativo (cPanel não suporta bem)
- Mesmo provedor da AWS SES (menos latência)
- 90 dias grátis no plano $12

### Riscos identificados
- Servidor single point of failure (sem redundância)
- Precisa de manutenção manual (updates, SSL renewal)
- Se disco encher, sistema para

### Mitigação
- Snapshots automáticos diários às 3h
- Certbot com auto-renewal para SSL
- Monitoramento de disco via script

---

## #002 — Agentes alucinando vs usando ferramentas (2026-03-25)

### Contexto
Os agentes diziam que enviaram emails, criaram arquivos, etc. — mas não usavam as ferramentas reais.

### Problema raiz
O backstory dos agentes não era rígido o suficiente. LLMs são otimistas por natureza.

### Decisão
Criar REGRAS_ANTI_ALUCINACAO rígidas injetadas em TODOS os agentes:
- "NUNCA invente informação — USE uma ferramenta"
- "NUNCA finja que fez algo"
- "NUNCA invente emails ou domínios"

### Resultado
Melhoria significativa — agentes passaram a ler código antes de opinar e usar propor_edicao em vez de inventar.

### Risco remanescente
Agentes podem ignorar regras em contextos longos. Necessário reforço contínuo.

---

## #003 — Tracking de consumo: Logs vs Banco vs APIs reais (2026-03-26)

### Contexto
O dashboard de consumo mostrava 0 para tudo após reiniciar o servidor.

### Opções
1. **Logs locais** — lê synerium.log (reseta a cada reinício)
2. **APIs dos providers** — consulta Anthropic, OpenAI, etc. diretamente
3. **Banco SQLite** — registra cada chamada permanentemente

### Decisão: Banco SQLite (tracker interno)
- A maioria dos providers (Groq, Together, Fireworks, Tavily, etc.) NÃO tem API de usage
- Anthropic exige Admin key (conta Individual não tem)
- SQLite nunca reseta, funciona para TODOS os 14 providers

### Risco
- Se o tracker falhar, a chamada não é registrada
- Dados retroativos não existem (só a partir da implementação)

---

## #004 — SQLite Schema Migrations: create_all() não basta (2026-03-27)

### Contexto
Após deploy da Luna v0.16.2 (com anexos de arquivos), a produção retornou 500 error ("Erro ao carregar mensagens"). A coluna `anexos` existia no modelo SQLAlchemy mas não na tabela `luna_mensagens` do banco de produção.

### Problema raiz
`SQLAlchemy.create_all()` **só cria tabelas novas** — nunca adiciona colunas a tabelas já existentes. Como `luna_mensagens` já existia (criada na v0.16.0), o campo `anexos` (adicionado na v0.16.2) nunca foi criado no banco.

### Opções para o futuro
1. **Alembic** — ferramenta oficial de migrations do SQLAlchemy, versionamento completo do schema
2. **ALTER TABLE manual no bootstrap** — script Python que detecta colunas faltantes e executa ALTER TABLE
3. **Continuar com create_all()** — funciona só para tabelas novas, exige intervenção manual para colunas novas

### Recomendação: Opção 2 (curto prazo) + Opção 1 (médio prazo)
- **Curto prazo**: implementar detecção de colunas faltantes no `bootstrap.py` com `ALTER TABLE` automático. Simples, sem dependência nova.
- **Médio prazo**: adotar Alembic quando o número de migrations crescer (>10 alterações de schema).

### Riscos
- **Sem ação**: todo deploy com campo novo vai quebrar produção silenciosamente
- **ALTER TABLE manual**: funciona para SQLite mas tem limitações (não suporta DROP COLUMN em versões antigas, não suporta ALTER COLUMN)
- **Alembic**: overhead de configuração, mais um processo no workflow de deploy

### Mitigação aplicada (27/Mar/2026)
- Fix manual: `ALTER TABLE luna_mensagens ADD COLUMN anexos JSON` no servidor de produção
- Pendência criada no backlog para implementar migrations automáticas

---

## #005 — Polling+DB vs WebSocket para Visible Execution (2026-04-01)

### Contexto
O Mission Control v0.57.2-v0.57.5 precisava mostrar execucao ao vivo: codigo aparecendo gradualmente no editor, barra de progresso animada, terminal com comandos reais. A latencia aceitavel e a arquitetura do backend (agentes em background threads) definiram as opcoes.

### Opcoes
1. **WebSocket** — Tempo real verdadeiro (<100ms). Complexidade: conexao persistente, reconexao, ping/pong, estado compartilhado entre thread do agente e conexao WS
2. **SSE (Server-Sent Events)** — Unidirecional, bom para streaming. Complexidade: queue entre thread do agente e endpoint SSE, gerenciamento de conexoes ativas
3. **Polling + DB** — Agente escreve no banco, frontend le a cada 2s. Zero infra nova

### Decisao: Polling + DB
- O agente ja persiste estado no banco (SQLAlchemy). Adicionar campos JSON (`agentes_ativos`, `painel_editor.fonte`) foi trivial
- Frontend ja fazia polling para o Team Chat (2s). Reaproveitar o mesmo ciclo para sessao foi natural
- Se o usuario recarregar a pagina, o estado completo esta no banco (resiliencia gratis)
- Multiplas abas funcionam sem logica extra (cada uma faz seu polling independente)

### Riscos identificados
- **Latencia de ate 2s** entre agente escrever e frontend exibir (aceitavel para execucao de 2-3 min)
- **Carga no banco** com polling de 2s por usuario ativo. Com 45 usuarios simultaneos = 22.5 queries/s no SQLite
- **Stale data** se o polling falhar silenciosamente (mitigado: frontend exibe timestamp do ultimo update)

### Mitigacao
- Typewriter frontend mascara a latencia do polling (enquanto anima chars, proximo poll ja chegou)
- SQLite suporta facilmente 100+ reads/s em disco SSD (Lightsail)
- Se escalar para 200+ usuarios, migrar polling para SSE com Redis pub/sub como intermediario

### Quando reconsiderar
- Se a latencia de 2s for inaceitavel para algum caso de uso futuro (ex: pair programming ao vivo)
- Se o numero de usuarios simultaneos ultrapassar 100 (carga de polling no SQLite)
- Se implementar comunicacao bidirecional (usuario envia comandos enquanto agente executa)

### Ponto sem retorno
Nenhum — a interface do frontend (`carregarSessao`, `dispararAgente`) abstrai a fonte de dados. Trocar polling por WebSocket exige mudar apenas o transporte, nao a logica de UI. Decisao 100% reversivel.

---

## #006 — Custo aumentado com roteamento de imagens para providers premium (2026-04-01)

### Contexto
A v0.58.0 introduziu roteamento automático de imagens para providers com vision (GPT-4o-mini e GPT-4o). Antes, todas as mensagens simples iam para Minimax ($0.0004/1K). Com imagem, vão para GPT-4o-mini ($0.00015/1K input mas $0.0006/1K output) ou GPT-4o ($0.0025/1K input, $0.01/1K output).

### Risco identificado
Se os 45 funcionários passarem a enviar imagens frequentemente (capturas de tela, fotos de documentos, diagramas), o custo de LLM pode aumentar significativamente. GPT-4o para imagens complexas custa 6x mais que Minimax para texto.

### Quantificação
- **Cenário baixo** (5% das mensagens com imagem): aumento de ~3% no custo mensal total
- **Cenário médio** (20% com imagem): aumento de ~12% no custo mensal
- **Cenário alto** (50% com imagem): aumento de ~30% no custo mensal

### Mitigação implementada
1. GPT-4o-mini (não GPT-4o) como padrão para imagens simples/médias — mais barato com vision
2. GPT-4o reservado apenas para mensagens classificadas como COMPLEXO + imagem
3. Fallback chain mantém providers baratos para mensagens sem imagem (Minimax → Groq)

### Mitigação futura (se custo escalar)
- Implementar cache de descrição de imagem: se a mesma imagem for enviada novamente, usar descrição cacheada em vez de chamar vision novamente
- Comprimir/redimensionar imagens antes de enviar (reduz tokens de input)
- Monitorar % de mensagens com imagem no dashboard de consumo de APIs
- Se Groq ou Fireworks adicionarem suporte a vision, migrar para eles (custo menor)

### Ponto sem retorno
Nenhum — o roteamento é 100% reversível. Se o custo ficar inaceitável, basta desabilitar a flag `vision` ou forçar redimensionamento agressivo de imagens.

---

> Ultima atualizacao: 2026-04-01
