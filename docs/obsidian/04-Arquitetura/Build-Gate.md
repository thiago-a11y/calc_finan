# Build Gate — Validação de Build Antes de Push

> Sistema de validação obrigatória de build antes de qualquer push ao repositório remoto.
> Implementado em v0.52.2 para prevenir código quebrado em produção.

---

## Visão Geral

O Build Gate é um mecanismo de segurança no `core/vcs_service.py` que executa o build do projeto **antes** de fazer `git push`. Se o build falhar, o commit é revertido e o push é bloqueado.

## Motivação

Na sessão 25 (31/Mar/2026), o agente do Synerium Factory substituiu o `EditProposalModal.tsx` do SyneriumX por uma descrição textual (Bug #43). O PR #195 foi auto-merged sem validação de build, quebrando a produção. O PR #196 corrigiu, mas o problema de fundo era a ausência de validação pré-push.

## Arquivo

**Localização:** `core/vcs_service.py` — função `validar_build()`

## Fluxo

```
Agente gera código → VCS faz commit → BUILD GATE executa build
  ├─ Build PASSOU ✅ → push acontece normalmente
  └─ Build FALHOU ❌ → commit revertido (git reset HEAD~1) → push BLOQUEADO ⛔
```

## Detecção de Tipo de Projeto

| Tipo | Detecção | Comando | Timeout |
|------|----------|---------|---------|
| **Node.js** | `package.json` com script `build` | `npm run build` | 3 min |
| **Node.js (lint)** | `package.json` com script `lint` (sem build) | `npm run lint` | 3 min |
| **Python** | `pyproject.toml` ou `setup.py` | `python3 -m py_compile` | 10s/arquivo |
| **Outro** | Sem arquivo de build | Skip (permite push) | — |

## Pontos de Integração

### 1. `VCSService.commit_e_push()` (auto-commit do Code Studio)
- Executa após o commit e antes do push
- Se falhar: `git reset HEAD~1` (desfaz commit, mantém mudanças staged)

### 2. `VCSService.push_branch()` (push manual de branches)
- Executa antes do `git push -u origin {branch}`
- Se falhar: retorna erro sem fazer push

### 3. `tools/deploy_pipeline_v2.py` (Stage 4 — Build)
- Agora é estritamente bloqueante (antes era warning-only para PHP)
- Se falhar: pipeline para e deploy não acontece

## Data Class

```python
@dataclass
class ResultadoBuild:
    sucesso: bool      # True = build passou
    mensagem: str      # Descrição do resultado
    comando: str = ""  # Comando executado (npm run build, py_compile, skip)
    saida: str = ""    # Saída do comando (últimos 1000 chars)
```

## Logs

```
[BUILD GATE] Executando npm run build...
[BUILD GATE] npm run build — PASSOU ✅
[BUILD GATE] npm run build — FALHOU ❌
[BUILD GATE] Python syntax check — PASSOU ✅ (3 arquivos)
[BUILD GATE] Nenhum arquivo de build detectado — skip
[VCS] BUILD GATE BLOQUEOU push do commit abc1234: Build falhou (npm run build)
```

## Bugs Relacionados

- **Bug #43**: Factory destruiu `EditProposalModal.tsx` (PR #195) — Build Gate teria bloqueado o push

---

> Última atualização: 2026-03-31 (v0.52.2)
