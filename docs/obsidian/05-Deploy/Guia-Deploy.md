# Guia de Deploy — Synerium Factory

> Como rodar e fazer deploy do sistema.

---

## Rodando Localmente

```bash
# 1. Entrar no diretório
cd ~/synerium-factory

# 2. Ativar virtualenv
source .venv/bin/activate

# 3. Verificar .env (chaves de API devem estar preenchidas)
cat .env

# 4. Rodar o sistema
python orchestrator.py           # Menu interativo
python orchestrator.py --status  # Ver status
python orchestrator.py --standup # Executar standup
python orchestrator.py --aprovar # Aprovar pendências
```

## Variáveis de Ambiente Necessárias

| Variável | Obrigatória | Descrição |
|---|---|---|
| `LANGSMITH_API_KEY` | Sim | Chave do LangSmith para tracing |
| `ANTHROPIC_API_KEY` | Sim | Chave da Anthropic (Claude) |
| `OPENAI_API_KEY` | Não | Fallback OpenAI (opcional) |
| `SYNERIUM_ENV` | Não | Ambiente (default: development) |
| `LIMITE_GASTO_IA_SEM_APROVACAO` | Não | Limite em R$ (default: 50) |

## Deploy em Produção

> Ainda não configurado. Será definido na Fase 5.
> Candidatos: AWS (EC2/ECS), Docker, ou serviço gerenciado.

---

> Última atualização: 2026-03-23
