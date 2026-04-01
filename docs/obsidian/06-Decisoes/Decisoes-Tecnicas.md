# Decisões Técnicas — Synerium Factory

> Por que escolhemos X e não Y.

---

## Por que Python 3.13 (não Node/TypeScript)?

CrewAI, LangGraph e LangChain têm ecossistema mais maduro em Python. A maioria dos frameworks de agentes IA é Python-first.

## Por que CrewAI (não AutoGen, não custom)?

CrewAI oferece Hierarchical Teams nativo, que encaixa perfeitamente na hierarquia da Objetiva (PM → Líderes → Squads). Processo hierárquico já implementado.

## Por que LangGraph junto com CrewAI?

LangGraph para orquestração de fluxos complexos (standup, aprovações, pipelines). CrewAI para gestão de agentes e crews. Complementares.

## Por que LangSmith (não custom tracing)?

Observabilidade completa out-of-the-box: tracing, custos, latência, aprovações. Essencial para controlar gastos de IA com 45 squads ativos.

## Por que pydantic-settings com `extra="ignore"`?

pydantic-settings lê automaticamente o .env, mas rejeita variáveis extras por padrão. O `extra="ignore"` permite ter variáveis no .env que não mapeiam diretamente para campos do settings.

## Por que vault Obsidian (não Notion, não Wiki)?

- Thiago já usa Obsidian para o SyneriumX
- Arquivos Markdown locais = fácil de versionar com git
- Fácil de ingestar no RAG (são só arquivos .md)
- Sem dependência de serviço externo
- Funciona offline

## Por que multi-tenant desde o início?

O Factory será licenciado para outras empresas. Adicionar multi-tenant depois é 10x mais difícil. Seguindo o padrão do SyneriumX (company_id em tudo).

## Por que Smart Router Sonnet/Opus (não Opus em tudo)?

Opus custa 5x mais que Sonnet ($0.015 vs $0.003 input, $0.075 vs $0.015 output). Para tarefas simples (chat, busca, execução), Sonnet é suficiente. Economia estimada: ~80%.

Regras do router:
1. Override manual sempre tem prioridade
2. Prompt > 15k tokens → Opus
3. >= 2 palavras-chave complexas (arquitetura, refatorar, migração, etc.) → Opus
4. Agente alto nível (peso >= 0.6) + 1 palavra complexa → Opus
5. Default → Sonnet

Bug corrigido: agentes caíam no default do CrewAI (gpt-4.1-mini da OpenAI!) porque ninguém passava `llm=` explícito. Agora todos recebem LLM do Smart Router.

## Por que SSE streaming na Luna (não WebSocket)?

SSE (Server-Sent Events) é unidirecional servidor→cliente, perfeito para streaming de tokens de LLM. Mais simples que WebSocket (que é bidirecional), funciona nativamente com HTTP/2, não precisa de biblioteca extra no frontend (usa EventSource nativo), e é compatível com o FastAPI StreamingResponse sem dependências adicionais.

## Por que cadeia de fallback Opus→Sonnet→Groq→Fireworks→Together na Luna?

Luna é a assistente principal dos usuários — precisa estar sempre disponível. A cadeia garante alta disponibilidade: se Opus falhar (rate limit, timeout), cai para Sonnet; se a Anthropic inteira cair, usa Groq (Llama, mais rápido); depois Fireworks e Together como últimos recursos. Usuário nunca fica sem resposta.

## Por que perfil "consultora_estrategica" com peso 0.4 no Smart Router?

Peso 0.4 é intermediário — não força Opus em tudo (seria caro), mas sobe para Opus quando a pergunta é complexa (arquitetura, estratégia). Conversas simples do dia-a-dia usam Sonnet, economizando ~80%. O perfil de consultora reflete o papel da Luna: ajudar em decisões, não só executar tarefas.

## Por que supervisão de chats com audit log na Luna?

Exigência LGPD + governança corporativa. O CEO/Diretor precisa poder supervisionar o que os agentes estão orientando os funcionários, mas cada acesso é registrado em audit log (quem viu, quando, qual conversa). Transparência: o funcionário sabe que o proprietário pode ver. Segue o padrão do SyneriumX (tudo auditável).

## Por que Web Speech API para voz na Luna (não Whisper API)?

Web Speech API roda no navegador, sem custo de API, sem latência de rede para transcrição. Funciona bem para português brasileiro nos navegadores modernos (Chrome, Edge). Whisper seria mais preciso mas adicionaria custo e latência. Se a precisão for insuficiente no futuro, migrar para Whisper é trivial (só mudar o frontend).

## Por que hard delete de usuários (não apenas soft delete)?

Soft delete (desativação) preserva o registro no banco, o que impede reconvite para o mesmo email. Em cenários reais — convite enviado para email errado, funcionário que precisa ser recadastrado — o email ficava "preso". O hard delete (`DELETE /api/usuarios/{id}/permanente`) remove o registro definitivamente, liberando o email para novo convite. Apenas proprietários (CEO, Operations Lead) podem executar essa ação, e tudo é registrado em audit log LGPD.

## Por que desinstalar o Syncthing?

O Syncthing foi instalado inicialmente para sincronizar arquivos entre o Mac e o servidor AWS. Porém, o script de deploy (`scripts/deploy_producao.sh`) já usa rsync via SSH para transferir arquivos. Manter dois mecanismos de sincronização era redundante, consumia espaço no Mac e gerava conflitos potenciais. Removido sem impacto — deploy continua 100% funcional via rsync.

## Por que UPLOAD_DIR precisa ser relativo ao projeto (não hardcoded)?

O path de uploads (`data/uploads/`) foi inicialmente configurado como `~/synerium` no desenvolvimento local. No servidor AWS, o projeto fica em `/opt/synerium-factory`, então o path não existia e downloads retornavam 404. A solução foi usar path relativo ao diretório do projeto (`Path(__file__).parent / ...` ou variável de ambiente), garantindo funcionamento tanto local quanto em produção.

## Por que config centralizada de agentes em `src/config/agents.ts`?

Antes, os dados dos agentes (nome, cargo, avatar, cor) estavam espalhados em vários componentes. Centralizar em um único arquivo `agents.ts` resolve duplicação, facilita manutenção e garante consistência visual. Qualquer componente importa `getAgentConfig("kenji")` e recebe tudo pronto — avatar, cor, cargo, especialidade. Adicionar um novo agente é alterar um único arquivo.

## Por que avatares em JPG local (não gerados por IA em tempo real)?

Avatares gerados por IA (DALL-E, Midjourney) a cada renderização seriam caros, lentos e inconsistentes (rosto diferente a cada chamada). Avatares estáticos em JPG são instantâneos, gratuitos, consistentes e funcionam offline. Ficam em `public/avatars/` e são servidos pelo Vite/nginx sem custo de API.

## Por que migrar o vault Obsidian para dentro do repo Git?

O vault Obsidian ficava em `/Users/thiagoxavier/Documents/SyneriumFactory-notes/`, separado do código. Isso causava problemas: não era versionado junto com o projeto, não ia para o servidor no deploy, e dificultava a referência em CI/CD. Migrar para `docs/obsidian/` dentro do repo garante que documentação e código andam juntos, com histórico Git unificado.

## Por que `token_hex` ao invés de `token_urlsafe` para convites?

`token_urlsafe` gera tokens com caracteres visualmente ambíguos (l/I/1, 0/O), causando problemas quando o usuário precisa copiar manualmente o token de um email. `token_hex` usa apenas hexadecimais (0-9, a-f), eliminando ambiguidade visual sem perder segurança.

---

## Por que Router Global separado do SmartRouter antigo?

O SmartRouter antigo (`llm_router.py`) foi projetado para decidir entre Opus e Sonnet dentro do CrewAI. Funciona bem para esse escopo e continua ativo. O Router Global (`smart_router_global.py`) é uma camada acima: roteia para **qualquer** provider (7 LLMs) e **qualquer** ferramenta externa (8 integrações). Separar os dois evita regressão no roteamento CrewAI existente e permite evolução independente.

### Coexistência
- `llm_router.py` — Roteamento Opus/Sonnet para agentes CrewAI (escopo interno)
- `smart_router_global.py` — Roteamento global multi-provider + multi-ferramenta (escopo externo)

### Por que regex e não ML para detecção de intenção?

O router precisa decidir em tempo real (< 1ms). Um modelo de ML adicionaria latência, dependência de inferência e complexidade de treinamento. Regex com 13 categorias de intenção resolve o problema com tempo médio de 0.12ms, zero dependência externa e manutenção trivial (adicionar/editar padrões). Se no futuro a acurácia for insuficiente, migrar para um classificador leve (fasttext, regex + embeddings) é possível sem mudar a interface.

### Providers escolhidos
| Provider | Modelo | Uso principal |
|----------|--------|--------------|
| Anthropic | Opus | Tarefas complexas, arquitetura, decisões |
| Anthropic | Sonnet | Tarefas do dia-a-dia, chat, execução |
| OpenAI | GPT-4o | Fallback, visão, análise multimodal |
| Google | Gemini | Contexto longo, análise de documentos |
| Groq | Llama | Resposta ultra-rápida, fallback primário |
| Fireworks | Mixtral/Llama | Fallback secundário, custo baixo |
| Together | Llama/Mistral | Fallback terciário, última linha |

### Ferramentas externas integradas
| Ferramenta | Categoria | Uso |
|-----------|-----------|-----|
| Exa | Busca semântica | Pesquisa web com entendimento de contexto |
| Tavily | Busca web | Pesquisa rápida e estruturada |
| Firecrawl | Scraping | Extração de dados de páginas web |
| Scrapingdog | Scraping | Scraping com proxy e anti-bloqueio |
| Composio | Integrações | Conexão com 100+ apps (Slack, GitHub, etc.) |
| E2B | Sandbox | Execução segura de código em sandbox |
| LiveKit | Voz/Vídeo | Comunicação em tempo real |
| SES | Email | Envio de emails transacionais (Amazon SES) |

---

## Por que Gemini via API OpenAI-compatible (não SDK Google)?

O Gemini 2.0 Flash é acessado via `generativelanguage.googleapis.com/v1beta/openai/` usando o formato de API compatível com OpenAI. Isso permite reutilizar o mesmo cliente HTTP/LiteLLM que já funciona para GPT-4o, sem adicionar dependência do SDK Google (`google-generativeai`). Menos dependências = menos superfície de ataque e manutenção mais simples. Se no futuro precisarmos de features exclusivas do SDK (ex: multimodal avançado), a migração é trivial.

### Free tier do Gemini
- 1.5 milhão de tokens/dia sem custo
- Ideal para fallback gratuito após Sonnet e GPT-4o
- Sem necessidade de billing configurado para uso básico

## Por que GPT-4o na cadeia de fallback?

GPT-4o ocupa a posição entre Sonnet e Gemini na cadeia de fallback (Opus → Sonnet → **GPT-4o** → Gemini → Groq → Fireworks → Together). Motivos:
1. Qualidade superior ao Gemini para tarefas de raciocínio e código
2. Já temos a API key da OpenAI configurada (usada para embeddings)
3. Diversifica providers — se a Anthropic inteira cair, GPT-4o assume antes dos open-source
4. Custo moderado ($2.50/1M input, $10/1M output) — mais barato que Opus, mais caro que Groq

---

## Por que JWT de 8h com auto-refresh (não 1h)?

O token de 1h causava logouts aleatórios durante o expediente — o usuário perdia o contexto do trabalho. Aumentar para 8h cobre uma jornada de trabalho completa. O refresh token (30d) continua igual. Além disso, implementamos auto-refresh transparente: quando o frontend recebe 401, tenta renovar o access token via `/auth/refresh` antes de redirecionar ao login. O usuário nunca percebe a renovação. Segurança mantida: o refresh token ainda é de uso único e rotacionado a cada uso.

## Por que bloquear binários no Code Studio (não tentar renderizar)?

Arquivos binários (.docx, .xlsx, .pptx, .pdf, etc.) não são texto — tentar carregá-los no CodeMirror congela o editor (o componente tenta parsear megabytes de dados binários como texto). A solução foi criar uma blacklist de 19 extensões conhecidas que o editor recusa abrir, exibindo uma mensagem de aviso. Alternativa seria detectar binários por magic bytes, mas a blacklist de extensões é mais simples, zero falsos negativos para os formatos comuns de escritório e sem overhead de I/O.

### Extensões bloqueadas
`.docx`, `.xlsx`, `.pptx`, `.pdf`, `.doc`, `.xls`, `.ppt`, `.odt`, `.ods`, `.odp`, `.rtf`, `.bmp`, `.tiff`, `.psd`, `.ai`, `.eps`, `.bin`, `.dat`, `.lock`

## Por que regras de aprovação customizáveis por projeto (campo JSON)?

Cada projeto tem necessidades diferentes de governança. Um projeto interno pode usar auto-aprovação (nenhuma), enquanto um projeto crítico exige aprovação de proprietário + líder técnico. O campo `regras_aprovacao` em `ProjetoDB` armazena um JSON flexível com opções: `lider_tecnico`, `proprietario`, `ambos`, `auto-aprovacao`. Isso evita criar tabelas separadas para regras e permite evolução sem migration (adicionar novas opções é só adicionar ao JSON). O padrão global continua funcionando para projetos sem customização.

---

## Por que histórico usa AuditLogDB existente (não nova tabela)?

O endpoint `GET /api/code-studio/historico` reutiliza a tabela `AuditLogDB` já existente, filtrando com `LIKE 'code_studio%'` na coluna de ação. Criar uma tabela separada seria redundante — os dados já estão lá por causa do audit log LGPD. Vantagem: zero migration, dados retroativos disponíveis desde a v0.34.0, e o histórico herda automaticamente todas as entradas futuras do Code Studio.

## Por que diff calculado com difflib no backend (não no frontend)?

O cálculo de diff (linhas adicionadas/removidas) é feito no backend com `difflib` do Python, limitado a 5000 linhas por performance. Fazer no frontend seria possível, mas exigiria enviar o conteúdo anterior e novo para o navegador (duplicando tráfego). No backend, comparamos antes e depois do apply-action in-memory e retornamos apenas os números (+N/-N). Limite de 5000 linhas previne timeout em arquivos muito grandes.

## Por que painéis mutuamente exclusivos (AgentPanel OU HistoricoPanel)?

O Code Studio tem espaço horizontal limitado: editor + painel lateral. Abrir AgentPanel e HistoricoPanel simultaneamente comprimiria o editor a ponto de ficar inutilizável em telas menores. A solução foi torná-los mutuamente exclusivos via toggle na toolbar — clicar em "Histórico" fecha o "Agente" e vice-versa. O editor sempre mantém largura mínima confortável.

---

## Por que Company Context usa 3 níveis (minimal/standard/full)?

Nem toda interação precisa do mesmo volume de contexto. O nível `minimal` envia apenas nome da empresa e projeto atual — ideal para respostas rápidas e simples. O `standard` adiciona detalhes profundos do projeto (membros, regras de aprovação, VCS, fase, líder técnico) — suficiente para a maioria das tarefas. O `full` inclui empresa + todos os projetos + busca RAG semântica (top 3 chunks do ChromaDB) — para decisões estratégicas e perguntas cross-projeto. Essa hierarquia balanceia latência vs profundidade: 90% das interações usam standard, economizando tokens e tempo.

## Por que RAG integrado via ChromaDB existente (sem nova indexação)?

O sistema RAG já indexa os vaults Obsidian no ChromaDB (implementado na v0.33.0+). O CompanyContextBuilder reutiliza essa base vetorial, filtrando por vault/projeto automaticamente. Criar uma indexação separada seria redundante e consumiria mais armazenamento. A busca semântica retorna os top 3 chunks mais relevantes, limitados ao budget de 4000 chars para não estourar o context window do LLM.

## Por que contexto da empresa é estático (cacheable forever)?

Dados da empresa (nome, CNPJ, domínio, produtos, hierarquia) mudam muito raramente — talvez uma vez por ano. Cachear esses dados indefinidamente elimina queries desnecessárias ao banco. Já a lista de projetos usa cache de 5 minutos, pois projetos podem ser criados/alterados com mais frequência. Essa separação de estratégias de cache garante dados frescos onde importa sem desperdiçar recursos.

## Por que toggle no frontend para desativar contexto empresa?

Alguns usuários preferem respostas mais rápidas e diretas, sem o overhead de contexto completo no system prompt. O toggle "Contexto Empresa" no AgentPanel permite desativar o envio de contexto empresarial, reduzindo tokens no prompt e acelerando a resposta. Ligado por padrão para máxima utilidade, mas desativável com um clique para quem quer velocidade.

---

## Por que timeout de 30 minutos para tarefas e reuniões (não 10min)?

O timeout original de 10 minutos era insuficiente para consultas complexas envolvendo múltiplos agentes, análise RAG e reuniões com vários participantes. Tarefas de arquitetura, revisão de código e reuniões de planejamento frequentemente levam 15-25 minutos. Aumentar para 30 minutos cobre 99% dos cenários sem risco de processos órfãos, pois o endpoint `/tarefas/{id}/retomar` permite recuperação manual caso algo trave.

## Por que token VCS injetado na URL HTTPS (não GIT_ASKPASS ou credential helper)?

Três alternativas foram avaliadas para autenticação git no servidor:
1. **GIT_ASKPASS** — exige script externo no filesystem, complicação desnecessária
2. **git credential helper** — persiste credenciais no disco, risco de segurança em servidor compartilhado
3. **Token na URL HTTPS** — `https://token@github.com/repo.git`, efêmero (só existe na memória do processo), sem persistência, sem script externo

A opção 3 é a mais simples e segura para automação. O token já está criptografado (Fernet) no banco e é descriptografado apenas no momento do git pull. Combinado com `GIT_TERMINAL_PROMPT=0`, garante que o git nunca trave esperando input em ambiente headless.

## Por que regras obrigatórias injetadas no prompt do agente (não configuração externa)?

Agentes IA podem executar ações inesperadas se o prompt não contiver restrições explícitas. O agente do Escritório Virtual enviava emails automaticamente sem pedir autorização. A solução foi injetar regras obrigatórias diretamente no system prompt:
1. **Nunca enviar email sem autorização explícita do usuário**
2. **Sugerir Code Studio para tarefas de código** (em vez de tentar editar pelo chat)
3. **Confirmar ações irreversíveis antes de executar**

Essas regras ficam no prompt (não em configuração externa) porque o LLM precisa tê-las no contexto de decisão. Regras em banco de dados ou variáveis de ambiente não são visíveis ao modelo durante a geração.

## Por que cache thread-safe com TTLCache + threading.Lock no CompanyContext?

O CompanyContextBuilder é chamado por múltiplas requests simultâneas do FastAPI (que roda em threads via uvicorn). Sem lock, duas threads poderiam atualizar o cache ao mesmo tempo, causando race condition. A solução usa `cachetools.TTLCache` (cache com expiração automática) protegido por `threading.Lock`. O lock é adquirido apenas na leitura/escrita do cache (microsegundos), sem impacto perceptível na latência. TTL de 5 minutos para projetos e sem expiração para dados da empresa.

---

## Por que Test Master obrigatório e bloqueante no pipeline Apply+Deploy?

O pipeline One-Click Apply+Deploy executa 5 etapas sequenciais: backup → aplicar → Test Master → commit → push. O Test Master é a terceira etapa e é **obrigatória e bloqueante** — se os testes falharem, o pipeline para e o backup é restaurado. Nem o CEO pode bypassar essa etapa. Motivos:
1. Código que quebra testes nunca deve chegar ao repositório remoto
2. O backup automático garante rollback sem perda de trabalho
3. A obrigatoriedade elimina a tentação de "pular testes desta vez"
4. Em uma fábrica com 45 squads, um push quebrado pode paralisar múltiplas equipes

---

## Por que conversas separadas no AgentPanel (não uma conversa contínua)?

O AgentPanel do Code Studio inicialmente tinha uma única conversa contínua por sessão. Problemas:
1. Contexto misturado — perguntas sobre arquivos diferentes na mesma thread confundiam o agente
2. Histórico poluído — difícil encontrar uma resposta específica em uma conversa longa
3. Sem separação por tarefa — refatoração, documentação e debugging tudo junto

A solução foi implementar conversas separadas com persistência em localStorage por projeto. Cada conversa tem título editável, preview e pode ser retomada a qualquer momento. O botão "Novo Chat" limpa o contexto para uma nova tarefa. Isso espelha o padrão de ChatGPT/Claude (múltiplas conversas), que os usuários já conhecem.

---

## Por que scroll inteligente vai ao início da resposta (não ao final)?

O comportamento padrão de chat (scroll para o final) não funciona bem para respostas longas de agentes de código. O usuário quer ler a resposta do início — se o scroll vai direto ao final, ele precisa rolar para cima manualmente. O scroll inteligente detecta quando uma nova resposta do agente começa e posiciona o viewport no início dessa resposta, permitindo leitura natural de cima para baixo.

---

## Por que ThreadPoolExecutor para reuniões paralelas (não asyncio)?

Reuniões com múltiplos agentes precisam executar tarefas em paralelo (cada agente processa sua parte). O `ThreadPoolExecutor` foi escolhido em vez de `asyncio` porque:
1. CrewAI é síncrono — usar asyncio exigiria wrappers `run_in_executor` em todo lugar
2. ThreadPoolExecutor integra naturalmente com código síncrono existente
3. O GIL do Python não é problema aqui — a maior parte do tempo é I/O (chamadas a APIs de LLM)
4. Controle fino de workers: `max_workers` limita concorrência para evitar rate limits

---

## Por que 15 agentes mapeados no BMAD com fases e palavras-chave?

O framework BMAD (Business, Marketing, Architecture, Development) organiza o trabalho em fases. Cada agente foi mapeado para uma ou mais fases, com palavras-chave que ativam o roteamento automático. Com 15 agentes (9 originais + 3 do Jonatas + 3 Elite), o mapeamento garante:
1. **Roteamento automático** — o sistema sabe qual agente chamar com base no tipo de tarefa
2. **Cobertura completa** — todas as fases do BMAD têm pelo menos 2 agentes capacitados
3. **Especialização** — Test Master para testes, GitHub Master para VCS, etc.
4. **Escalabilidade** — novos agentes são adicionados ao mapa com palavras-chave, sem mudar código

---

## Por que fetch com token VCS no git log (origin/main desatualizado sem token)?

O PushDialog lista commits pendentes usando `git log origin/main..HEAD`. Porém, o `origin/main` local pode estar desatualizado se o repositório remoto recebeu commits (merge de PR, push de outro dev). Para sincronizar, o Code Studio executa `git fetch origin` antes de listar commits. Em repositórios HTTPS privados, o fetch precisa de autenticação — sem o token VCS, falhava silenciosamente e mostrava commits já mergeados. A solução injeta o token VCS na URL temporariamente para o fetch, restaurando o remote limpo no finally.

---

## Por que auto-pull após merge (sincronizar local automaticamente)?

Após um merge de PR via GitHub API, o repositório local fica desatualizado (o merge aconteceu no remote). Sem auto-pull, o PushDialog continuaria mostrando os commits antigos como "pendentes". O auto-pull automático após merge garante que:
1. O repositório local reflete o estado real do remote
2. O PushDialog mostra apenas commits genuinamente pendentes
3. Não há confusão do usuário com commits duplicados
4. O próximo push/PR parte de um estado limpo

---

## Por que LLM Fallback centralizado em `core/llm_fallback.py`?

O sistema anterior dependia de cada módulo implementar seu próprio fallback. Isso gerava duplicação e inconsistência — um módulo podia parar por falta de créditos enquanto outro continuava. O `llm_fallback.py` centraliza a cadeia Anthropic → Groq → OpenAI em um único ponto: qualquer módulo chama `obter_llm_fallback()` e recebe o provider disponível. Se a Anthropic cair (rate limit, créditos), o Groq assume automaticamente; se o Groq falhar, cai para OpenAI. Nunca mais para por falta de créditos.

## Por que Gate Approval com `threading.Lock`?

O FastAPI roda com uvicorn em múltiplas threads. Sem lock, duas requests simultâneas de aprovação poderiam aprovar o mesmo gate duas vezes (race condition). A solução usa `threading.Lock` no momento da verificação e atualização do status do gate. O lock é adquirido por microsegundos — sem impacto em performance. A verificação confirma que o usuário é CEO ou Operations Lead antes de aprovar.

## Por que recovery automático de workflows travados (>30min → erro)?

Workflows autônomos podem travar por timeout de LLM, erro de rede ou crash do processo. Sem recovery, ficam eternamente com status "executando" no banco. No startup do servidor, uma verificação automática identifica workflows com mais de 30 minutos em execução e os marca como erro, liberando recursos e notificando o CEO. O threshold de 30 minutos foi escolhido porque é o dobro do timeout máximo de qualquer tarefa individual.

## Por que Factory Optimizer como agente Distinguished Engineer?

O Factory Optimizer (ID=16) é um meta-agente que analisa o desempenho da própria fábrica usando ciclo PDCA (Plan-Do-Check-Act). Após cada workflow autônomo concluído, uma review session avalia o resultado e gera sugestões de melhoria. O papel de Distinguished Engineer reflete sua função: não executa tarefas operacionais, mas faz meta-análise e propõe evoluções estruturais.

## Por que `EvolucaoFactoryDB` para registrar sugestões de melhoria?

As sugestões do Factory Optimizer precisam ser rastreáveis e auditáveis. O modelo `EvolucaoFactoryDB` armazena cada sugestão com: origem (workflow que gerou), tipo (performance, qualidade, processo), descrição, status (pendente, aprovada, implementada, rejeitada) e quem aprovou. Isso cria um histórico de evolução da fábrica, permitindo análise de tendências e medição de melhoria contínua.

---

## Por que Session SQLite isolada por fase (não sessão compartilhada)?

O Autonomous Squads executa 4 fases BMAD em threads longas. Inicialmente, uma única session SQLAlchemy era compartilhada entre todas as fases. Quando uma fase demorava, a session expirava com erro `commit() can't be called` porque outra thread já havia finalizado a transação. A solução foi criar `SessionLocal()` nova por operação — cada fase abre e fecha sua própria session independente. Overhead mínimo (criar session é microsegundos), mas elimina 100% dos crashes de concorrência SQLite em threads.

## Por que fila automática de workflows (não execução simultânea)?

Workflows autônomos consomem LLM tokens intensivamente (múltiplos agentes por fase). Executar vários simultaneamente estouraria rate limits e custos. A fila garante execução sequencial: ao concluir ou falhar, o sistema verifica se há workflow com status `aguardando_fila` e o inicia automaticamente. O CEO pode enfileirar vários workflows pelo Command Center sem esperar — eles executam em ordem. Se no futuro a capacidade de tokens aumentar, é trivial mudar para execução paralela com semáforo.

## Por que Vision-to-Product via PM Central + LLM (não templates fixos)?

O Vision-to-Product permite ao CEO descrever uma visão de produto em linguagem natural. O PM Central (Alex) processa a visão via LLM e gera: roadmap de features, estimativa de dias por feature, estimativa de custo total, prioridade e complexidade. Usar templates fixos seria limitante — cada produto tem necessidades diferentes. O LLM entende nuances e gera roadmaps contextualizados. As features geradas são então convertidas em workflows autônomos pelo Command Center.

## Por que teste end-to-end Fase 2→3→4 como critério de qualidade?

O fluxo completo de um workflow autônomo (Business → Architecture → Development, pulando Marketing em teste) é o cenário mais complexo do sistema: envolve múltiplas fases, transição de gates, session management, LLM calls e persistência. Se esse fluxo passa sem crash, os cenários mais simples (fase única, cancelamento, retry) funcionam por consequência. O teste validou: session isolada, fila automática, gates, progresso % e persistência de resultado.

---

## Por que Minimax como LLM principal (não Groq ou Anthropic)?

Minimax MiniMax-Text-01 oferece o menor custo por token entre todos os providers: $0.0004/1K input vs $0.00059 (Groq) vs $0.003 (Sonnet). Com 45 squads e workflows autônomos consumindo milhares de chamadas diárias, a diferença de custo é significativa. Qualidade suficiente para tarefas operacionais (análise, planejamento, geração de código).

## Por que endpoint `api.minimaxi.chat` com i (não `api.minimax.chat`)?

A Minimax tem dois hosts: `api.minimax.chat` (China) e `api.minimaxi.chat` (Global/Internacional). Contas registradas na plataforma global (interface em inglês, pagamento em USD) DEVEM usar o host com **i**. O host sem i retorna `invalid api key` (código 2049) para keys globais. Descoberto após investigação: não estava documentado de forma clara na documentação oficial.

## Por que API key pay-as-you-go da Minimax (não Token Plan)?

A Minimax oferece dois tipos de key: `sk-api-` (pay-as-you-go, cobra do Balance) e `sk-cp-` (Token Plan, assinatura mensal para ferramentas internas como OpenCode/OpenClaw). Apenas a key `sk-api-` funciona na API REST. A key `sk-cp-` retorna `invalid api key` na API REST. O Token Plan de $50/mês é uma assinatura separada para outras ferramentas, não para API REST.

## Por que cadeia de 6 providers no fallback (não apenas 3)?

A cadeia definitiva Minimax → Groq → Fireworks → Together → Anthropic → OpenAI garante máxima resiliência:
1. **Minimax** — Mais barato ($0.0004/1K), provider principal
2. **Groq** — Ultra-rápido, segundo mais barato ($0.00059/1K)
3. **Fireworks** — Llama via OpenAI-compatible API, custo baixo ($0.0009/1K)
4. **Together** — Llama via OpenAI-compatible API, outra opção open-source ($0.00088/1K)
5. **Anthropic** — Claude Sonnet, qualidade premium ($0.003/1K), para quando todos os baratos falharem
6. **OpenAI** — GPT-4o, última linha de defesa ($0.005/1K)

Com 6 providers, a probabilidade de todos falharem simultaneamente é praticamente zero. O sistema NUNCA para.

---

## Por que classificador regex e não ML para roteamento dinâmico?

O Smart Router Dinâmico (v0.52.0) classifica cada mensagem individual em 4 níveis de complexidade (SIMPLES, MEDIO, COMPLEXO, TOOLS). A classificação usa regex com padrões de palavras-chave em vez de um modelo de ML. Motivos:
1. **Latência** — Regex executa em < 1ms; ML adicionaria 50-200ms por classificação
2. **Zero dependência** — Sem modelo treinado, sem dataset, sem inferência
3. **Manutenção trivial** — Adicionar/remover padrões é editar uma lista de strings
4. **Determinístico** — Mesmo input sempre gera mesmo output (sem probabilidade)
5. **Suficiente para 4 classes** — SIMPLES/MEDIO/COMPLEXO/TOOLS é granularidade baixa; regex resolve bem

Se no futuro a acurácia for insuficiente, migrar para fasttext ou embeddings é possível sem mudar a interface (`classificar_mensagem()` continua retornando o mesmo enum).

## Por que GPT-4o-mini como LLM principal no CrewAI (não Minimax ou Groq)?

O CrewAI usa function calling (ferramentas/tools) extensivamente para que os agentes executem ações. Nem Minimax nem Groq suportam function calling de forma confiável:
- **Groq** — Retorna `tool_use_failed` ao tentar usar ferramentas (Bug #40)
- **Minimax** — Não suporta role `system` (erro 2013), essencial para o system prompt do CrewAI

GPT-4o-mini ($0.00015/1K input, $0.0006/1K output) é o provider mais barato que suporta TANTO function calling QUANTO system role. Custo aceitável para o volume de chamadas do CrewAI. O roteamento dinâmico direciona automaticamente chamadas com ferramentas para GPT-4o-mini via classificação `TOOLS`.

## Por que adaptador de mensagens para Minimax (system → user)?

Minimax MiniMax-Text-01 retorna erro 2013 quando recebe mensagens com role `system`. A API aceita apenas roles `user` e `assistant`. A solução foi criar um adaptador em `core/classificador_mensagem.py` que converte mensagens com role `system` para role `user` antes de enviar à API da Minimax. O conteúdo da mensagem é preservado integralmente — apenas o campo `role` é alterado. Isso permite usar Minimax para mensagens simples sem modificar o código dos módulos que enviam system prompts.

---

## Build Gate — Validação Obrigatória Antes de Push (v0.52.2)

**Contexto:** O agente do Factory (GPT-4o-mini via CrewAI) destruiu `EditProposalModal.tsx` do SyneriumX substituindo código React por descrição textual. O PR #195 foi auto-merged sem validação, quebrando a produção.

**Decisão:** Implementar Build Gate no `core/vcs_service.py` que executa `npm run build` (Node.js) ou `py_compile` (Python) antes de qualquer push. Se falhar, commit é revertido e push bloqueado.

**Alternativas consideradas:**
1. Confiar no CI do GitHub — Rejeitado: PR pode ser auto-merged antes do CI terminar
2. Pre-commit hook local — Rejeitado: agentes rodam no servidor, não têm hooks locais configurados
3. Build Gate no VCS Service — **Escolhido**: Integrado no ponto correto do fluxo, impossível de bypassar

**Consequências:** Push fica ~30s mais lento (tempo do build), mas código quebrado nunca chega ao GitHub.

---

## Por que polling + DB para "Visible Execution" (não WebSocket/SSE)?

O Mission Control v0.57.2 precisava mostrar execução ao vivo: barra de progresso, código aparecendo no editor e terminal com comandos do agente. Três opções foram avaliadas:

1. **WebSocket** — Bidirecional, tempo real verdadeiro. Rejeitado: complexidade de manter conexão persistente no FastAPI + frontend, necessita infraestrutura de ping/pong, reconexão automática e estado compartilhado entre threads
2. **SSE (Server-Sent Events)** — Unidirecional, bom para streaming. Rejeitado: o agente roda em background thread separada — precisaria de queue entre a thread e o endpoint SSE. Adiciona complexidade sem benefício claro sobre polling
3. **Polling + persistência no banco** — **Escolhido**: O agente escreve progresso/código/terminal diretamente nos campos JSON da sessão (`agentes_ativos`, `painel_editor`, `painel_terminal`). O frontend já faz polling a cada 2s (chat) e 5s (sessão). Latência máxima de 5s é aceitável para o caso de uso.

**Vantagens da abordagem escolhida:**
- Zero infraestrutura nova (sem WebSocket server, sem Redis, sem message queue)
- Persistência gratuita — se o usuário recarregar a página, o estado completo está no banco
- Funciona com múltiplas abas do navegador simultaneamente
- O backend não precisa saber quem está ouvindo (desacoplamento total)

**Trade-off aceito:** Latência de até 5s entre o agente escrever e o frontend exibir. Para uma execução que leva 2-3 minutos, isso é imperceptível.

**Padrão utilizado:** `painel_editor.fonte = "agente"` sinaliza ao frontend que o conteúdo veio do agente (não do usuário). O frontend só sobrescreve o editor se o usuário não editou manualmente (`editorEditadoPeloUsuario`). Isso evita conflitos de escrita.

---

> Última atualização: 2026-04-01
