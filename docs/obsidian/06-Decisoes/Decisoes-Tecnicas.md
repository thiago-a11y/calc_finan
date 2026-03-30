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

> Última atualização: 2026-03-29
