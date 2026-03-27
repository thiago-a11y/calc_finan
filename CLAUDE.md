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

## REGRA AUTOMÁTICA: Manter o Obsidian SEMPRE atualizado
O vault `SyneriumFactory-notes` é a fonte de verdade do projeto.
ATUALIZE os arquivos relevantes em CADA momento, NÃO apenas no final:

### Durante o chat (a cada decisão/discussão):
- **08-Daily/Pendencias-Ultimo-Chat.md** — O que está sendo discutido, o que foi feito, o que falta
- **06-Decisoes/Riscos-Reflexoes-Estrategicas.md** — Se houver debate de prós/contras ou risco identificado
- **06-Decisoes/Decisoes-Tecnicas.md** — Se uma decisão técnica for tomada (escolha de lib, padrão, provider)

### Ao concluir implementação:
- **03-Changelog/Changelog.md** — Nova versão com o que foi criado/atualizado/corrigido
- **01-Roadmap/Roadmap.md** — Marcar itens concluídos
- **04-Arquitetura/{arquivo}.md** — Criar/atualizar se mudança estrutural
- **CONTEXTO-SYNERIUM-FACTORY.md** — Atualizar se houve mudança importante

### Quando encontrar problema:
- **07-Bugs/Bugs-Conhecidos.md** — Registrar bug com descrição, como reproduzir e status
- **08-Daily/Pendencias-Ultimo-Chat.md** — Adicionar na seção de pendências

### Quando surgir nova tarefa:
- **02-Backlog/Backlog.md** — Adicionar item com prioridade

### Quando criar/alterar squad:
- **09-Squads/Mapa-Squads.md** — Atualizar mapa
- **09-Squads/Squad-{Nome}.md** — Criar/atualizar arquivo do squad

### NÃO espere o usuário pedir. Faça automaticamente.
### Use agente em background para não bloquear o fluxo principal.

## REGRA: Consultar Obsidian ANTES de responder
- Antes de responder perguntas sobre o projeto, SEMPRE consulte:
  1. O vault Obsidian (RAG) para contexto atualizado
  2. O CONTEXTO-SYNERIUM-FACTORY.md para visão geral
  3. Os arquivos relevantes no código-fonte
- NUNCA responda de memória sem verificar — use as ferramentas.
- Se o usuário perguntar algo que está no Obsidian, cite a fonte.

Este arquivo é lido automaticamente em todas as sessões. Respeite-o sempre.
