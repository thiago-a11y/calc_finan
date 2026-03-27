# PRD — Toggle de Tema no Header

## Metadados

| Campo | Valor |
|-------|-------|
| **Projeto** | Synerium Factory — Dashboard |
| **Versão** | 1.0 |
| **Status** | Aprovado |
| **Autor** | Marco (PM) |
| **Proprietário** | Thiago (CEO) |
| **Data de criação** | 2026-03-25 |
| **Etapas concluídas** | [1,2,3,4,5,6,7,8,9,10,11,12] |

## Etapa 1 — Inicialização
- **Feature:** Toggle Light/Dark Mode no Header do dashboard
- **Problema:** Toggle atual fica escondido na sidebar, difícil de encontrar
- **Público:** Todos os usuários do Synerium Factory
- **Produto afetado:** Dashboard React

## Etapa 2 — Descoberta
- **Dor #1:** Usuários não encontram o toggle na sidebar
- **Dor #2:** Padrão de mercado é toggle no header (GitHub, Vercel, Stripe)
- **Dor #3:** Troca de tema deveria ser 1 clique, não navegar até a sidebar

## Etapa 3 — Visão
- **Visão:** Toggle elegante e discreto no canto superior direito do header
- **Diferencial:** Animação suave sol↔lua com transição de cores

## Etapa 4 — Resumo Executivo
Toggle de tema (Light/Dark Mode) posicionado no Header do dashboard, ao lado do avatar do usuário. Ícone animado de sol/lua com transição suave. Mantém preferência no localStorage.

## Etapa 5 — Métricas de Sucesso
| Métrica | Meta | Como medir |
|---------|------|------------|
| Discoverability | 100% dos usuários encontram em < 3s | Teste manual |
| Persistência | Tema salvo entre sessões | localStorage |
| Performance | Troca < 100ms | DevTools |

## Etapa 6 — Jornada de Usuário
1. Usuário vê ícone 🌙/☀️ no header (canto direito)
2. Clica no ícone
3. Tema muda instantaneamente com transição suave
4. Preferência salva automaticamente
5. Ao relogar, tema preferido é restaurado

## Etapa 7 — Regras de Negócio
- Dark Mode é o padrão (default)
- Preferência salva em localStorage como `sf-theme`
- Tema aplicado via classe `dark`/`light` no `<html>`

## Etapa 8 — Inovação
- Animação de rotação no ícone ao trocar (180° suave)
- Transição global de cores com `transition: background-color 0.3s`

## Etapa 9 — Tipo de Projeto
- [x] Melhoria/refatoração (análise leve)

## Etapa 10 — Escopo
### No escopo
- Toggle no Header com ícone animado
- Persistência no localStorage
- Funcionamento em todas as páginas

### Fora do escopo
- Toggle na sidebar (remover)
- Tema por usuário no banco (futuro)
- Tema automático por horário (futuro)

## Etapa 11 — Requisitos
| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-001 | Toggle visível no header, lado direito | Must |
| RF-002 | Ícone animado sol/lua | Must |
| RF-003 | Persistência localStorage | Must |
| RF-004 | Remover toggle duplicado da sidebar | Should |
| RNF-001 | Transição < 100ms | Must |
| RNF-002 | Acessível via teclado | Should |

## Etapa 12 — Aprovação
| Aprovador | Status | Data |
|-----------|--------|------|
| CEO (Thiago) | ✅ Aprovado | 2026-03-25 |

---

> PRD gerado pelo workflow BMAD — Fase 2 concluída.
