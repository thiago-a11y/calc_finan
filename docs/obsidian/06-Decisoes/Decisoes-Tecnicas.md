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

> Última atualização: 2026-03-28
