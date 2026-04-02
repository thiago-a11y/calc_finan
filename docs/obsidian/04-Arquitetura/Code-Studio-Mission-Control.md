# Code Studio 2.0 — Mission Control

> Versão: v0.58.0 | Data: 01/Abr/2026

## Visão Geral

O Mission Control é o Code Studio 2.0 — um ambiente de desenvolvimento imersivo com painel triplo simultâneo (Editor + Terminal + Artifacts/Navegador). Agentes IA trabalham em tempo real, gerando entregáveis tangíveis que o CEO pode revisar e comentar inline.

## Persistência de Sessões (v0.57.0)

### Fluxo do usuário
1. Acessa `/mission-control` → vê **lista de sessões recentes** (titulo, status, metricas, tempo relativo)
2. Clica "Retomar" → navega para `/mission-control/{sessionId}` → carrega estado completo
3. Ou clica "Nova Sessão" → cria sessão e navega automaticamente para ela
4. Enquanto trabalha, **auto-save a cada 10s** persiste: conteúdo do editor, arquivo ativo, histórico do terminal
5. Fecha aba/navega para outra página → ao voltar, tudo restaurado exatamente

### Endpoints de persistência
- `GET /api/mission-control/sessoes` — Últimas 20 sessões do usuário
- `PATCH /api/mission-control/sessao/{id}/save` — Auto-save (chamado a cada 10s pelo frontend)

### O que é persistido
- **Editor**: conteúdo completo (`painel_editor.conteudo`), arquivo ativo (`arquivo_ativo`)
- **Terminal**: últimos 50 comandos com output, sucesso/falha, timestamp
- **Artifacts**: todos os artifacts gerados por agentes (ArtifactDB)
- **Comentários inline**: `ArtifactDB.comentarios_inline` (JSON)
- **Agentes**: estado de cada agente (executando/concluído/erro)

## Arquitetura

```
Dashboard (/mission-control)
  ├─ Painel 1: Editor (código, preview)
  ├─ Painel 2: Terminal (comandos sandboxed)
  └─ Painel 3: Artifacts (planos, checklists, código)
       ├─ Gerados por agentes em background
       ├─ Comentários inline (estilo Google Docs)
       └─ Status: gerado → revisado → aprovado
```

## Componentes

### Backend (api/routes/mission_control.py)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/mission-control/sessoes` | GET | Lista sessões ativas |
| `/api/mission-control/sessao` | POST | Cria nova sessão |
| `/api/mission-control/sessao/{id}` | GET | Detalhes com artifacts |
| `/api/mission-control/sessao/{id}/comando` | POST | Executa no terminal |
| `/api/mission-control/sessao/{id}/agente` | POST | Dispara agente |
| `/api/mission-control/artifacts/{sessao_id}` | GET | Lista artifacts |
| `/api/mission-control/artifacts/{id}/comentar` | POST | Comentário inline |
| `/api/mission-control/artifacts/{id}/status` | POST | Atualizar status |

### Frontend (dashboard/src/pages/MissionControl.tsx)

- Painel triplo com ResizableHandle (redimensionável)
- Terminal com histórico e input inline
- Barra de instrução de agente no topo
- Agentes vivos com animação pulse no header
- Artifacts expansíveis com comentários

### Visible Live Execution (v0.57.5)

O Mission Control oferece experiência visual completa de execução ao vivo:

**Frontend — Efeitos visuais:**
- **Typewriter**: caracteres aparecem gradualmente no editor (8 chars/frame a 60fps), não mais linhas inteiras
- **Barra de progresso com shimmer**: gradiente animado via CSS keyframes + texto descritivo da fase + porcentagem
- **Icone do agente pulsante**: animacao CSS pulse em todos os paineis durante execucao
- **Badge "Em execucao"** nas mensagens do Team Chat
- **Cursor piscante no terminal**: efeito de digitacao real via CSS keyframe `blink`
- **Indicador de atividade** em todos os paineis simultaneamente

**Backend — Streaming otimizado:**
- Chunks de 2 linhas com delay de 200ms (era 4 linhas / 350ms)
- Progresso granular dentro de cada fase (nao apenas nas transicoes)
- Editor recebe conteudo desde a Fase 1 (scaffold -> plan -> code)
- Comandos reais no terminal: `npm run build`, `pytest`, `eslint`, `tsc --noEmit`
- Todas as fases geram entradas de terminal

**Polling:**
- Sessao: a cada 2s (era 5s)
- Chat: a cada 2s (incremental via `?desde=timestamp`)
- Auto-save: a cada 10s (pula quando agente executando via `agentExecutandoRef`)

### Models

- **ArtifactDB** — tipo, titulo, conteudo, dados (JSON), comentarios_inline (JSON array)
- **MissionControlSessaoDB** — estado dos 3 painéis, agentes ativos, métricas

## Tipos de Artifacts

| Tipo | Descrição | Ícone |
|------|-----------|-------|
| plano | Plano de implementação gerado por LLM | FileText |
| checklist | Lista de tarefas com items verificáveis | CheckSquare |
| codigo | Trecho de código gerado | Code2 |
| terminal | Output significativo de comando | Terminal |
| screenshot | Captura de tela do navegador | Eye |
| markdown | Documentação ou notas | FileText |

## Team Chat Multi-Agente (v0.57.1)

### Visão geral
O Painel 3 do Mission Control agora tem duas abas: **Team Chat** e **Artifacts**. O Team Chat exibe em tempo real a conversa entre os agentes enquanto trabalham — o CEO assiste ao vivo ao planejamento, debate e execução.

### Fluxo de 5 Fases com Decision Controls (v0.58.2)
```
Instrução → Planejamento → Discussão → Execução → Review QA → Conclusão
              ↓              ↓           ↓          ↓
           [Decisão]     [Decisão]   [Decisão]  [Decisão]
           Aprovar/       Aprovar/    Aprovar/   Aprovar/
           Regenerar/     Regenerar/  Regenerar/ Regenerar/
           Rejeitar/      Rejeitar/   Rejeitar/  Rejeitar/
           Revisar        Revisar     Revisar    Revisar
```

| Fase | Agente | Output | Artifact | Decisão? |
|------|--------|--------|---------|---------|
| 1. Planejamento | Tech Lead | JSON com etapas e riscos | PLANO | ✅ |
| 2. Discussão | Backend Dev, Frontend Dev, QA | Parecer técnico individual | — | ✅ |
| 3. Execução | Backend Dev | Código gerado | CODIGO | ✅ |
| 4. Review QA | QA Engineer | Checklist de qualidade | CHECKLIST | ✅ |
| 5. Conclusão | Sistema | Missão completa | — | — |

### Phase Decision Engine (v0.58.2)
- `FaseDecisionEngine` em `mission_control.py`: motor com `threading.Event` para bloqueio entre fases
- `POST /sessao/{id}/fase-decisao`: aprovar | regenerar | rejeitar | revisar
- `GET /sessao/{id}/fase-status`: polling do frontend (2s)
- Agente thread bloqueia entre fases via `wait_decision()` e desbloqueia via `resolve()`
- Somente após as 5 fases APROVADAS a tela "Concluído com Sucesso!" é mostrada
- "Voltar para Revisão" preserva todo o histórico (artifacts, código, terminal)

### Model: TeamChatDB
```python
class TeamChatDB(Base):
    sessao_id: str          # FK para MissionControlSessaoDB
    agente_nome: str        # "Tech Lead", "Backend Dev", etc.
    tipo: str               # "sistema" | "mensagem" | "acao"
    conteudo: str           # Texto completo da mensagem
    fase: str               # "planejamento"|"discussao"|"execucao"|"review"|"conclusao"
    dados_extra: JSON       # Metadados extras (NÃO "metadata" — reservado pelo SQLAlchemy)
    company_id: int
    criado_em: datetime
```

### Endpoint de Polling
- `GET /api/mission-control/sessao/{id}/chat?desde=2026-04-01T12:00:00` — retorna apenas mensagens criadas após o timestamp informado. Frontend chama a cada 2s para atualização incremental sem duplicação.

### Frontend — Painel 3 (Abas)
- **Team Chat**: badges coloridos por fase, ícones distintos por agente, scroll automático, mensagens de sistema centralizadas
- **Artifacts**: lista clicável, clique abre modal full-size. Modal com botões: "Aplicar no Editor", "Copiar", "Download"
- Auto-switch para aba Team Chat quando agente é disparado

### Artifact Modal
- Nunca fecha sozinho — apenas via botão X ou clique fora do overlay
- Tamanho máximo `max-w-4xl` para legibilidade de código
- "Aplicar no Editor": copia conteúdo diretamente para o `<textarea>` do editor

---

## Roteamento Vision / Multimodal (v0.58.0)

O Smart Router detecta automaticamente quando uma mensagem contém imagem e roteia para providers com suporte a vision. Dois mecanismos independentes garantem roteamento correto:

1. **Classificador** (`core/classificador_mensagem.py`): flag `vision` em cada provider + parâmetro `tem_imagem` filtra a cadeia de fallback
2. **LLM Fallback** (`core/llm_fallback.py`): detecta `image_url` em `HumanMessage.content_parts` e pula providers sem vision

| Complexidade + Imagem | Provider Escolhido |
|------------------------|--------------------|
| SIMPLES/MEDIO + imagem | GPT-4o-mini (vision, mais barato) |
| COMPLEXO + imagem | GPT-4o (vision, máxima qualidade) |
| Sem imagem | Roteamento normal (Minimax/Groq/Sonnet) |

---

## Segurança

- Comandos destrutivos bloqueados (rm -rf, mkfs, shutdown, etc)
- Timeout de 30s por comando
- Sessões isoladas por usuário (usuario_id)
- Multi-tenant (company_id)

## Diferencial vs Antigravity

| Feature | Antigravity | Mission Control |
|---------|-------------|-----------------|
| Painéis simultâneos | 2 (editor + preview) | 3 (editor + terminal + artifacts) |
| Terminal integrado | Não | Sim, sandboxed |
| Artifacts tangíveis | Não | Sim, com checklist e planos |
| Comentários inline | Não | Sim, estilo Google Docs |
| Agentes vivos animados | Não | Sim, com pulse animation |
| Background execution | Limitado | Full async com polling 2s |
