# Sistema de Projetos — Propriedade e Governança

> Cada projeto tem proprietário, líder técnico e membros. Mudanças requerem aprovação baseada na hierarquia.

## Hierarquia
```
Proprietário (nomeado pelo CEO) — palavra final
├── Líder Técnico (nomeado pelo proprietário/CEO) — aprova mudanças menores
└── Membros — solicitam mudanças (precisam de aprovação)
```

## Regras de Aprovação
| Tipo | Exemplos | Quem aprova |
|------|----------|-------------|
| Pequena | Bug fix, UI tweak | Líder Técnico |
| Grande | Nova feature, arquitetura | Proprietário |
| Crítica | Deploy, banco, segurança | Proprietário + Líder |

## Projetos Registrados
| Projeto | Proprietário | Líder | Membros |
|---------|-------------|-------|---------|
| SyneriumX | Thiago | Jonatas | Rhammon |

## Endpoints API
- GET /api/projetos — Lista projetos
- POST /api/projetos — Criar projeto (só CEO)
- PUT /api/projetos/:id/proprietario — Nomear proprietário (só CEO)
- PUT /api/projetos/:id/lider — Nomear líder
- POST /api/projetos/:id/solicitacoes — Criar solicitação
- PUT /api/solicitacoes/:id/aprovar — Aprovar
- PUT /api/solicitacoes/:id/rejeitar — Rejeitar

## Tabelas
- `projetos` — Nome, proprietário, líder, membros, caminho, stack
- `solicitacoes` — Título, descrição, tipo, status, aprovador

---

Criado em: 2026-03-24
