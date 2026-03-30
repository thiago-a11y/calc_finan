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

## Registro Completo de Agentes (15 agentes)

| ID | Agente | Perfil | Fases | Convocado quando |
|----|--------|--------|-------|------------------|
| 1 | Tech Lead / Arquiteto | tech_lead | 1,3,4 | arquitetura, refatorar, decisao tecnica |
| 2 | Backend PHP/Python | backend_dev | 4 | API, banco, migration, PHP, Python |
| 3 | Frontend React/TS | frontend_dev | 2,4 | UI, UX, React, CSS, componente |
| 4 | Especialista IA | especialista_ia | 3,4 | LLM, RAG, prompt, agente, embeddings |
| 5 | Integracoes/APIs | integracao | 4 | webhook, OAuth, API externa, SES |
| 6 | DevOps/Infra | devops | 4 | deploy, nginx, Docker, CI/CD |
| 7 | QA e Seguranca | qa_seguranca | 3,4 | vulnerabilidade, LGPD, XSS, pentest |
| 8 | Product Manager | product_manager | 1,2 | negocio, roadmap, feature, PRD |
| 9 | Secretaria Executiva | secretaria_executiva | 1-4 | ata, email, relatorio, sprint |
| 10 | Revisor de Codigo Sr | diretor | 4 | code review, anti-pattern, qualidade |
| 11 | Arquiteto Infra | arquiteto | 3 | AWS, cloud, escala, rede |
| 12 | Analista LGPD | qa_seguranca | 3,4 | compliance, privacidade, auditoria |
| **13** | **Test Master** | qa_seguranca | **4** | **OBRIGATORIO: testes, deploy, pipeline** |
| **14** | **GitHub Master** | devops | 3,4 | PR, merge, GitHub, Actions |
| **15** | **GitBucket Master** | devops | 3,4 | GitBucket, on-premise, webhook |

### Pipeline One-Click Apply+Deploy
```
Backup → Aplicar → 🛡️ Test Master (BLOQUEANTE) → Commit → Push/PR
                         ↓ falhou?
                    REVERT automatico
```

O Test Master é o UNICO agente que pode bloquear o pipeline. Nem o CEO pode bypassar.

## Gates de Aprovação

| Gate | Fase | Quem aprova | Resultado |
|------|------|-------------|-----------|
| Product Brief | 1→2 | CEO ou Operations Lead | Aprovado/Rejeitado |
| PRD Completo | 2→3 | CEO ou Operations Lead | Aprovado/Rejeitado |
| Implementation Readiness | 3→4 | CEO + Tech Lead | PASS / CONCERNS / FAIL |
| Test Master | 4 (pre-deploy) | Automatico | APROVADO / BLOQUEADO |
| Deploy Produção | 4→done | Operations Lead | Aprovado/Rejeitado |

## Arquivos

| Arquivo | Função |
|---------|--------|
| `workflows/main-workflow.yaml` | Definição completa das 4 fases + agentes elite + pipeline |
| `templates/PRD.md` | Template PRD (12 etapas) |
| `templates/story.md` | Template Story (BDD + Dev Notes) |
| `state/sprint-status.yaml` | Kanban central |
| `gates/approval_gates.py` | Implementation Readiness Check |
| `scripts/seed_agentes_elite.py` | Seed dos 3 agentes elite no banco |

---

Criado em: 2026-03-25
Atualizado em: 2026-03-30 (agentes elite + pipeline)
