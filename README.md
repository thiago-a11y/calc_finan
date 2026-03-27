# Synerium Factory

Fábrica de SaaS impulsionada por agentes IA, baseada no SyneriumX.

## Hierarquia

```
CEO (Thiago)
└── Operations Lead (Diretor de Serviços) — aprovação final
    └── PM Agent Central (Alex) — orquestração geral
        ├── Squad Dev Backend
        ├── Squad Dev Frontend
        ├── Squad Marketing
        └── Squad [Novo Membro] (duplicar template)
```

## Tecnologias

- **CrewAI** — Agentes com Hierarchical Teams
- **LangGraph** — Orquestração de fluxos complexos
- **LangSmith** — Observabilidade, tracing e controle de custos
- **LangChain + Claude** — LLM principal via Anthropic
- **Python 3.13** — Runtime

## Estrutura de Pastas

```
synerium-factory/
├── orchestrator.py          # Ponto de entrada principal
├── requirements.txt         # Dependências
├── .env                     # Variáveis de ambiente (NÃO commitar)
├── CLAUDE.md                # Regras permanentes do projeto
├── agents/                  # Definições de agentes
│   ├── pm_central.py        # Alex — PM Agent Central
│   └── operations_lead.py   # Diretor de Serviços
├── squads/                  # Squads pessoais
│   └── squad_template.py    # Template para novos squads
├── flows/                   # Fluxos automatizados
│   └── daily_standup.py     # Standup diário às 7h30
├── gates/                   # Portões de aprovação
│   └── approval_gates.py    # Human-in-the-loop
├── config/                  # Configurações
│   └── settings.py          # Settings centralizadas
├── tools/                   # Ferramentas customizadas
├── rag/                     # RAG com vault Obsidian
├── logs/                    # Logs do sistema
└── docs/                    # Documentação adicional
```

## Instalação

```bash
# 1. Entrar no diretório
cd synerium-factory

# 2. Ativar o virtualenv
source .venv/bin/activate

# 3. Configurar as chaves no .env
#    Edite o arquivo .env e coloque suas chaves reais:
#    - LANGSMITH_API_KEY
#    - ANTHROPIC_API_KEY

# 4. Rodar o sistema
python orchestrator.py
```

## Comandos

```bash
# Modo interativo (menu completo)
python orchestrator.py

# Executar standup diário
python orchestrator.py --standup

# Ver aprovações pendentes
python orchestrator.py --aprovar

# Ver status geral
python orchestrator.py --status
```

## Guia por Papel

### Para o CEO (Thiago)

1. Defina a estratégia e prioridades dos squads
2. Acompanhe os relatórios diários de standup
3. Use o `orchestrator.py` para executar tarefas via PM Central
4. Crie novos squads quando novos membros entrarem no time

### Para o Operations Lead (Diretor de Serviços)

1. **Aprovações**: Você receberá notificações sempre que algo crítico precisar de aprovação
2. **Standup diário**: Relatório chega às 7h30 via WhatsApp/Telegram/email
3. **Override**: Você tem poder total para aprovar ou rejeitar qualquer ação
4. **O que precisa de sua aprovação**:
   - Deploy em produção
   - Gasto de IA acima de R$50
   - Mudança de arquitetura
   - Campanha de marketing
   - Outreach em massa

### Criando um Novo Squad

Edite `orchestrator.py` na função `main()` e adicione:

```python
fabrica.registrar_squad(
    nome="Nome do Membro",
    especialidade="Área de atuação",
    contexto="Detalhes extras sobre o foco do squad.",
)
```

## Approval Gates

Toda ação crítica passa por um Approval Gate antes de ser executada.
O sistema **para automaticamente** e aguarda a decisão do Operations Lead.

Gastos de IA abaixo de R$50 são auto-aprovados.

## Licença

Projeto proprietário — Synerium.
