# Arquitetura Multi-Tenant

> O Synerium Factory será licenciado para outras empresas.
> Multi-tenant desde o início, seguindo o padrão do SyneriumX.

---

## Modelo

- Cada empresa = 1 tenant (identificado por `company_id`)
- Isolamento total de dados entre tenants
- Configuração independente por tenant (agentes, squads, limites, branding)
- Billing separado por tenant

## Padrão de Isolamento (inspirado no SyneriumX)

```
Toda query filtra por company_id
Toda criação de registro inclui company_id
Audit log registra tenant + usuário + ação
Logs separados por tenant
```

## Estrutura por Tenant

```
Tenant (Empresa)
├── Configurações (limites de gasto, branding, integrações)
├── Usuários (funcionários da empresa)
├── Squads (um por funcionário)
│   └── Agentes (configurados por squad)
├── Produtos (projetos/softwares que o tenant gerencia)
├── Approval Gates (regras próprias)
└── Relatórios (standups, métricas, custos)
```

## Fase de Implementação

- **Agora:** Funciona como single-tenant (Objetiva)
- **Fase 4:** Adicionar company_id em todas as entidades
- **Fase 5:** Onboarding self-service, billing, API pública

---

> Última atualização: 2026-03-23
