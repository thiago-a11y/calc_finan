# Story: [TÍTULO]

## Metadados

| Campo | Valor |
|-------|-------|
| **Key** | `{epic}-{story}-{slug}` |
| **Épico** | [Nome do épico] |
| **Status** | backlog / ready-for-dev / in-progress / review / done |
| **Assignee** | [Agente responsável] |
| **Prioridade** | must / should / could |
| **Estimativa** | [Pequena / Média / Grande] |
| **PRD Refs** | RF-001, RF-002 |
| **Criado em** | [YYYY-MM-DD] |
| **Atualizado em** | [YYYY-MM-DD] |

---

## Objetivo

> [Descrição clara do que esta story entrega. Uma frase.]

---

## Critérios de Aceitação (BDD)

### AC-1: [Nome do critério]
```gherkin
Dado que [contexto/pré-condição]
Quando [ação do usuário/sistema]
Então [resultado esperado]
```

### AC-2: [Nome do critério]
```gherkin
Dado que [contexto/pré-condição]
Quando [ação do usuário/sistema]
Então [resultado esperado]
```

### AC-3: [Nome do critério]
```gherkin
Dado que [contexto/pré-condição]
Quando [ação do usuário/sistema]
Então [resultado esperado]
```

---

## Tasks (Checklist de Implementação)

### Task 1: [Nome]
- [ ] Subtask 1.1
- [ ] Subtask 1.2
- [ ] Testes unitários para task 1

### Task 2: [Nome]
- [ ] Subtask 2.1
- [ ] Subtask 2.2
- [ ] Testes unitários para task 2

### Task 3: [Nome]
- [ ] Subtask 3.1
- [ ] Testes de integração

---

## Dev Notes (Guardrails para o Agente Desenvolvedor)

> **ATENÇÃO:** Estas notas são obrigatórias. O agente desenvolvedor DEVE seguir
> cada uma delas. Não existe "depois eu faço" — cada item é um requisito.

### Padrões Obrigatórios
- [ ] **company_id**: Toda query SQL DEVE filtrar por company_id
- [ ] **Audit Log**: Toda operação de escrita DEVE registrar no audit log (before/after/diff)
- [ ] **LGPD**: Dados pessoais (CPF, email, telefone) DEVEM ser mascarados nos logs
- [ ] **Prepared Statements**: NUNCA concatenar variáveis em queries SQL
- [ ] **Idioma**: Todo código, comentários e mensagens em português brasileiro

### Padrões Técnicos do Projeto
- [ ] PHP 7.4 — NÃO usar syntax PHP 8+ (named arguments, match, etc.)
- [ ] PDO direto — NÃO usar ORM
- [ ] React 18 + TypeScript — componentes funcionais com hooks
- [ ] Tailwind CSS — NÃO usar CSS inline ou styled-components

### Lições de Stories Anteriores
> [Listar aqui bugs, problemas ou decisões de stories anteriores que impactam esta story]
-
-

### Libs/Versões Específicas
> [Listar versões exatas de bibliotecas que devem ser usadas]
-
-

---

## Dev Agent Record

> Preenchido automaticamente pelo agente durante o desenvolvimento.

| Task | Status | Testes | Notas |
|------|--------|--------|-------|
| Task 1 | | | |
| Task 2 | | | |
| Task 3 | | | |

---

## Arquivos Modificados

> Lista de arquivos criados ou modificados por esta story.

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| | Criado / Editado | |
| | Criado / Editado | |

---

## Code Review

| Revisor | Resultado | Data | Notas |
|---------|-----------|------|-------|
| [Agente] | Aprovado / Mudanças necessárias | | |

---

> Template BMAD-Synerium Factory v1.0
> Workflow: Fase 4 — Implementação → create-story
