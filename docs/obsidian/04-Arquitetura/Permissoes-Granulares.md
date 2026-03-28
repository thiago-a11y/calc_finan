# Permissões Granulares — Sistema de Controle de Acesso

> Cada usuário tem permissões calculadas a partir dos papéis (base) + overrides individuais.

## Módulos (13)

| Módulo | ID | Ações |
|--------|-----|-------|
| 📊 Painel Geral | `dashboard` | view, create, edit, delete, export |
| 👥 Gestão de Squads | `squads` | view, create, edit, delete, export |
| 🤖 Agentes e Chat | `agents` | view, create, edit, delete, export |
| ✅ Aprovações | `approvals` | view, create, edit, delete, export |
| 🎤 Reuniões | `reunioes` | view, create, edit, delete, export |
| 📚 Base de Conhecimento | `rag` | view, create, edit, delete, export |
| 🏢 Escritório Virtual | `escritorio_virtual` | view, create, edit, delete, export |
| ⚙️ Configurações | `configuracoes` | view, create, edit, delete, export |
| 📋 Gestão de Tarefas | `tarefas` | view, create, edit, delete, export |
| 🔧 Skills e Ferramentas | `skills` | view, create, edit, delete, export |
| 📄 Relatórios e Standup | `relatorios` | view, create, edit, delete, export |
| 📁 Projetos | `projetos` | view, create, edit, delete, export |
| 🔒 Administração | `admin` | view, create, edit, delete, export |

## Lógica de Cálculo

```
1. Juntar permissões base de TODOS os papéis do usuário (OR)
2. Aplicar overrides granulares (se existirem — override tem prioridade)
3. Resultado = permissões efetivas
```

## Permissões Base por Papel

| Papel | Admin | Squads | Agents | Aprovações | Config | Tarefas |
|-------|-------|--------|--------|------------|--------|---------|
| CEO | Tudo | Tudo | Tudo | Tudo | Tudo | Tudo |
| Diretor Técnico | Tudo | Tudo | Tudo | Tudo | Tudo | Tudo |
| Operations Lead | Tudo | Tudo | Tudo | Tudo | Tudo | Tudo |
| PM Central | Nada | Tudo | Tudo | Ver+Editar | Ver | Tudo |
| Líder | Nada | Ver+Editar | Tudo | Ver+Editar | Ver | Tudo |
| Desenvolvedor | Nada | Ver | Tudo | Ver | Nada | Ver+Criar |
| Marketing | Nada | Ver | Tudo | Ver+Criar | Nada | Ver+Criar |
| Membro | Nada | Ver | Ver+Criar | Ver | Nada | Ver+Criar |

## Overrides

- Armazenados como JSON no campo `permissoes_granulares` do usuário
- Formato: `{"modulo_id": {"view": true, "create": false, ...}}`
- Se null/vazio: herda 100% do papel
- Override tem prioridade sobre papel

## Endpoints API

- `GET /api/usuarios/modulos-disponiveis` — Lista módulos, ações e permissões por papel
- `PUT /api/usuarios/{id}/permissoes` — Salvar `permissoes_granulares` (JSON)
- Login retorna `permissoes_efetivas` no objeto do usuário

## Frontend

```typescript
const { temPermissao } = useAuth()

// Verificar permissão
if (temPermissao('squads', 'edit')) { /* pode editar */ }
if (temPermissao('admin', 'view')) { /* pode ver admin */ }
```

## Cores na Interface

- 🟢 Verde = permitido pelo papel (base)
- 🔵 Azul = override permitindo (adicionado manualmente)
- 🔴 Vermelho = override negando (removido manualmente)
- ⚪ Cinza = negado pelo papel (base)
- ↩ = remover override (voltar ao padrão)

## Arquivo: `config/permissoes.py`

Contém: MODULOS, ACOES, PERMISSOES_POR_PAPEL, calcular_permissoes_efetivas()

---

Criado em: 2026-03-24
