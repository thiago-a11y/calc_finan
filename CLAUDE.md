# CLAUDE.md — Regras Permanentes do Synerium Factory

## Perfil do Projeto
- Este é o Synerium Factory: uma fábrica de SaaS impulsionada por agentes IA.
- Baseado no SyneriumX (PHP 7.4 + React + multi-tenant + LGPD).
- Objetivo: criar novos produtos 10x mais rápido usando agentes.
- Sempre siga estritamente as melhores práticas de março 2026.

## Regras Obrigatórias (nunca quebre)
- Use português brasileiro em todos os arquivos, comentários e relatórios.
- Sempre respeite hierarquia: PM Agent Central → Operations Lead (irmão do Thiago) tem poder final de aprovação.
- Implemente Approval Gates fortes para deploy, gastos e campanhas.
- Use Hierarchical Teams + CrewAI Flows quando possível.
- Todo código gerado deve seguir os padrões do SyneriumX (migrations, auditLog, company_id, LGPD).
- Sempre peça confirmação humana antes de comandos destrutivos (git push, deploy, etc.).
- Ative Plan Mode, use ferramentas de git, terminal e edição de arquivos.

## Modo de Trabalho
- Sempre pense passo a passo.
- Mostre estrutura de pastas antes de criar arquivos.
- Use LangSmith tracing quando aplicável.
- Mantenha tudo limpo, organizado e documentado.

## REGRA AUTOMÁTICA: Manter a Documentação SEMPRE atualizada
O vault de documentação está em `docs/obsidian/` dentro do repositório (versionado no Git).
ATUALIZE os arquivos relevantes em CADA momento, NÃO apenas no final:

### Durante o chat (a cada decisão/discussão):
- **docs/obsidian/08-Daily/Pendencias-Ultimo-Chat.md** — O que está sendo discutido, o que foi feito, o que falta
- **docs/obsidian/06-Decisoes/Riscos-Reflexoes-Estrategicas.md** — Se houver debate de prós/contras ou risco identificado
- **docs/obsidian/06-Decisoes/Decisoes-Tecnicas.md** — Se uma decisão técnica for tomada (escolha de lib, padrão, provider)

### Ao concluir implementação:
- **docs/obsidian/03-Changelog/Changelog.md** — Nova versão com o que foi criado/atualizado/corrigido
- **docs/obsidian/01-Roadmap/Roadmap.md** — Marcar itens concluídos
- **docs/obsidian/04-Arquitetura/{arquivo}.md** — Criar/atualizar se mudança estrutural
- **docs/obsidian/CONTEXTO-SYNERIUM-FACTORY.md** — Atualizar se houve mudança importante

### Quando encontrar problema:
- **docs/obsidian/07-Bugs/Bugs-Conhecidos.md** — Registrar bug com descrição, como reproduzir e status
- **docs/obsidian/08-Daily/Pendencias-Ultimo-Chat.md** — Adicionar na seção de pendências

### Quando surgir nova tarefa:
- **docs/obsidian/02-Backlog/Backlog.md** — Adicionar item com prioridade

### Quando criar/alterar squad:
- **docs/obsidian/09-Squads/Mapa-Squads.md** — Atualizar mapa
- **docs/obsidian/09-Squads/Squad-{Nome}.md** — Criar/atualizar arquivo do squad

### NÃO espere o usuário pedir. Faça automaticamente.
### Use agente em background para não bloquear o fluxo principal.

## REGRA: Consultar documentação ANTES de responder
- Antes de responder perguntas sobre o projeto, SEMPRE consulte:
  1. Os arquivos em `docs/obsidian/` para contexto atualizado
  2. O `docs/obsidian/CONTEXTO-SYNERIUM-FACTORY.md` para visão geral
  3. Os arquivos relevantes no código-fonte
- NUNCA responda de memória sem verificar — use as ferramentas.
- Se o usuário perguntar algo que está na documentação, cite a fonte.

Este arquivo é lido automaticamente em todas as sessões. Respeite-o sempre.
