# Premissas Estratégicas do Synerium Factory

> Definidas por Thiago (CEO) em 2026-03-23.
> Estas premissas guiam TODAS as decisões do projeto.

---

## 1. Propósito

O Synerium Factory é um **produto da Objetiva Solução** para escalar todos os serviços da empresa. Não é apenas uma ferramenta interna — é uma plataforma que será licenciada futuramente.

## 2. Escopo de Produtos

O Factory gerencia **todos** os produtos da Objetiva:

| Produto | Tipo | Status |
|---|---|---|
| **SyneriumX** | CRM SaaS | Em produção (130 PRs, 61 migrations) |
| **Softwares industriais** | Gestão industrial | Existentes |
| **Financeiro — Crédito** | Controle de crédito | Existente |
| **Financeiro — Captação** | Captação de investimentos | Existente |
| **Financeiro — Endividamento** | Gestão de endividamento | Existente |

## 3. Pessoas e Squads

- **45 funcionários** da Objetiva continuam na empresa
- Cada funcionário terá **seu próprio squad de agentes IA**
- **Zero contratação** de humanos para trabalho operacional
- Objetivo: **multiplicar eficiência por 10x ou mais**
- Orquestração feita por líderes, diretores e Operations Lead

## 4. Multi-Tenant

- Arquitetura multi-tenant **desde o início**
- Cada empresa (tenant) terá seus próprios squads, agentes e configurações
- Futuro: **licenciar o Synerium Factory** para outras empresas escalarem seus times

## 5. Qualidade e Documentação

- **Tudo documentado** em português brasileiro legível
- **Tudo testado** antes de ir para produção
- Código com **comentários claros** para entendimento futuro
- Vault Obsidian como fonte de verdade da documentação

## 6. Hierarquia de Comando

```
CEO (Thiago)
├── Diretores / Líderes — definem estratégia por área
│   └── Operations Lead (irmão do Thiago) — aprovação final
│       └── PM Agent Central (Alex) — orquestra todos os squads
│           ├── Squad Funcionário 1 (agentes próprios)
│           ├── Squad Funcionário 2 (agentes próprios)
│           ├── ...
│           └── Squad Funcionário 45 (agentes próprios)
```

## 7. Approval Gates (Aprovação Obrigatória)

Requerem aprovação do Operations Lead:
- Deploy em produção
- Gasto de IA acima de R$50
- Mudança de arquitetura
- Campanha de marketing
- Outreach em massa

---

> Última atualização: 2026-03-23
