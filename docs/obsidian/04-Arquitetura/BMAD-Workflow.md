# BMAD Workflow — Processo Estruturado de Desenvolvimento

> Baseado no BMAD Method (Breakthrough Method of Agile AI-Driven Development).
> Adaptado para o Synerium Factory e a Objetiva Solução.

## Fluxo Principal (4 Fases)

```
IDEIA
  ↓
[Fase 1] ANÁLISE (opcional)
  Marco pesquisa mercado, Kenji verifica viabilidade
  Gate: Product Brief aprovado
  ↓
[Fase 2] PLANEJAMENTO (obrigatório)
  Marco cria PRD (12 etapas), Carlos faz UX
  Gate: PRD aprovado por CEO/Operations Lead
  ↓
[Fase 3] SOLUÇÃO (obrigatório)
  Kenji cria arquitetura, Marco quebra em stories BDD
  Gate: IMPLEMENTATION READINESS CHECK (PASS/FAIL)
  ↓
[Fase 4] IMPLEMENTAÇÃO (obrigatório)
  TDD por story → code review → QA → deploy
  Gate: Approval Gate (deploy em produção)
  ↓
✅ ENTREGUE E DOCUMENTADO
```

## Quick Flow (Atalho)

Para bug fixes e melhorias pequenas (< 1 dia):
```
Ideia → mini-spec → implementa com TDD → review → deploy
```

## Mapeamento de Agentes

| BMAD | Synerium Factory | Fase |
|------|------------------|------|
| Mary (Analyst) | Marco (PM) | 1 |
| Paige (Tech Writer) | Sofia (Secretária) | 1 |
| John (PM) | Marco (PM) | 2 |
| Sally (UX) | Carlos (Frontend) | 2 |
| Winston (Architect) | Kenji (Tech Lead) | 3 |
| Bob (Scrum Master) | Sofia (Secretária) | 4 |
| Amelia (Dev) | Amara + Carlos | 4 |
| Quinn (QA) | Fatima (QA) | 4 |

## Gates de Aprovação

| Gate | Fase | Quem aprova | Resultado |
|------|------|-------------|-----------|
| Product Brief | 1→2 | CEO ou Operations Lead | Aprovado/Rejeitado |
| PRD Completo | 2→3 | CEO ou Operations Lead | Aprovado/Rejeitado |
| Implementation Readiness | 3→4 | CEO + Tech Lead | PASS / CONCERNS / FAIL |
| Deploy Produção | 4→done | Operations Lead | Aprovado/Rejeitado |

## Arquivos

| Arquivo | Função |
|---------|--------|
| `workflows/main-workflow.yaml` | Definição completa das 4 fases |
| `templates/PRD.md` | Template PRD (12 etapas) |
| `templates/story.md` | Template Story (BDD + Dev Notes) |
| `state/sprint-status.yaml` | Kanban central |
| `gates/approval_gates.py` | Implementation Readiness Check |

---

Criado em: 2026-03-25
