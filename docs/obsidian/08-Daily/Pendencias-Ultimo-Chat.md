# Pendencias do Ultimo Chat — 30/Mar/2026

> Atualizado em 30/Mar/2026 (sessao 22 — v0.50.0)

## Concluido nesta sessao

### v0.50.0 — Vision-to-Product + Correcoes Criticas
- [x] Vision-to-Product: PM Central gera roadmap, estimativa de dias e custo estimado
- [x] Features com prioridade e complexidade no Comando Estrategico
- [x] Barra de progresso % em cada card de squad no Command Center
- [x] Session SQLite isolada por fase no Autonomous Squads (fix critico)
- [x] Fila de workflows automatica (proximo inicia ao concluir/falhar anterior)
- [x] LLM Fallback robusto: core/llm_fallback.py (Anthropic → Groq → OpenAI)
- [x] 6 pontos de chamada LLM atualizados para usar fallback
- [x] langchain-groq instalado no servidor
- [x] Rota conflito corrigida: GET /detalhe/{tarefa_id}
- [x] Botao Novo Projeto na pagina Projetos + modal de criacao (CEO only)
- [x] Sistema de conversas separadas no AgentPanel (localStorage por projeto, max 20)
- [x] Scroll inteligente no AgentPanel (inicio da resposta, nao final)
- [x] Convites corrigidos (naive vs aware datetime em auth.py E convites.py)
- [x] Painel Geral busca usuarios do banco (nao config estatico)
- [x] Jonatas removido do seed (via convites)
- [x] CEO pode excluir qualquer usuario exceto ele mesmo
- [x] permissoes.py corrompido restaurado via SCP
- [x] Pull no Code Studio com token VCS + auto-pull apos merge
- [x] Push dialog: Invalid Date corrigido + commits ja mergeados somem
- [x] Regex extrairBlocoCodigo com 3 fallbacks

### Bugs corrigidos nesta sessao
- [x] Session SQLite crash em threads longas (commit() can't be called) → SessionLocal() isolada por fase
- [x] Workflows aguardando_fila nunca iniciavam → fila automatica implementada
- [x] Gate approval sem verificacao de permissao → threading.Lock + check CEO/OpsLead
- [x] Rota /{tarefa_id} conflitava com /command-center → renomeada para /detalhe/{tarefa_id}
- [x] langchain_groq nao instalado no servidor → pip install langchain-groq
- [x] load_dotenv faltando no llm_fallback.py → adicionado

### Sessoes anteriores (ja concluidas)
- [x] v0.49.0 — Autonomous Squads + Self-Evolving Factory + Command Center
- [x] v0.48.0 — Preview de Arquivos por Commit + Horario Brasilia
- [x] v0.47.0 — Botao Novo Projeto + Modal de Criacao
- [x] v0.46.0 — 3 Agentes Elite + BMAD Mapeamento Completo
- [x] v0.45.0 — Sistema de Conversas Separadas no AgentPanel
- [x] v0.44.0 — Paineis Redimensionaveis no Code Studio
- [x] v0.43.0 — Live Agents
- [x] v0.42.0 — Push & PR & Merge direto do Code Studio
- [x] v0.41.0 — One-Click Apply+Deploy
- [x] v0.40.0 — Chat Resiliente + Timeout + Retomar Conversa
- [x] v0.39.0 — Company Context Total
- [x] v0.38.0 — Historico de Atividades + Feedback Detalhado

## Status Atual
- Tudo em producao (AWS)
- Versao atual: v0.50.0
- 15 agentes no catalogo
- Vision-to-Product operacional no Command Center
- Autonomous Squads com session isolada e fila automatica
- LLM Fallback centralizado (Anthropic → Groq → OpenAI)
- Code Studio completo: Company Context, Apply+Deploy, Push/PR/Merge, conversas separadas
- Live Agents com animacoes de status no Escritorio Virtual
- Chat resiliente com timeout de 30min e botoes de retomar conversa

## Pendencias / Proximos passos
- [ ] Testar integracao VCS com repositorio GitBucket real
- [ ] Testar exclusao permanente de usuarios em producao
- [ ] Atribuir agentes ao Marcos e Rhammon via dashboard
- [ ] Testar solicitacao de agente por um usuario comum
- [ ] Ajustar permissoes granulares para a pagina de Atribuicoes (so admin ve)
- [ ] Mapear os 45 funcionarios da Objetiva e criar squads
- [ ] Corrigir testes de integracao (mock do lifespan para CI)
- [ ] Melhorar escritorio: interacao com sala de reuniao (vidro transparente vendo agentes dentro)
- [ ] Adicionar historico de conversas Luna ao RAG para contexto cruzado
- [ ] Implementar sistema de migrations automaticas no bootstrap (Alembic ou ALTER TABLE strategy)
- [ ] Implementar busca global no Code Studio (Ctrl+Shift+F)
- [ ] Terminal integrado no Code Studio
- [ ] Monitoramento de saude dos agentes (heartbeat)
