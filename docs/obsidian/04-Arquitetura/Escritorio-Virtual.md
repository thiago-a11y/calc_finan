# Escritório Virtual — Visualização Isométrica

> **Status:** ✅ Implementado (v0.11.0) · expandido v0.56.0 (16 posições)
> **Rota:** `/escritorio`
> **Arquivo:** `dashboard/src/pages/Escritorio.tsx`

## Visão Geral

O Escritório Virtual é uma representação visual top-down do squad do CEO. Cada agente aparece como um bonequinho com emoji sentado em sua mesa com monitor, e status em tempo real.

**v0.11.1** — Refatorado de isométrico 3D (distorcido) para grid 4x2 responsivo com cards animados.

## Funcionalidades

### Visualização
- Grid responsivo 4x2 (desktop) / 2x4 (mobile) com cards por agente
- Bonequinhos com emoji, corpo e braços animados
- Monitores com tela dinâmica (apagada, código rolando, amarelo em reunião)
- Cores únicas por agente para identificação rápida
- Banner de reunião ativa no topo da página

### Status em Tempo Real
- **🟢 Disponível** — agente livre, pronto para receber tarefas
- **🔵 Trabalhando** — agente executando tarefa (indicador pulsando)
- **🟡 Em reunião** — agente participando de reunião ativa

O status é atualizado via polling (3s) consultando o histórico de tarefas.

### Interação
- **Hover** — card sobe, borda colorida, tooltip "Clique para conversar"
- **Clique** — abre chat messenger flutuante para conversar com o agente
- **"Reunir todos no escritório"** — botão no topo para iniciar reunião

### Reunião Ativa
Quando há uma reunião em andamento, aparece banner amarelo pulsante no topo com link para Relatórios.

### Animações (CSS @keyframes)
- `digitando` — bracinhos sobem/descem simulando digitação
- `flutuando` — bonequinho flutua suavemente (hover e reunião)
- `brilho` — indicadores de status pulsam
- `pulso` — banner de reunião pulsa com box-shadow

## Layout de Mesas — Array DK (v0.56.0)

O escritório usa coordenadas absolutas pixel (x, y). O array `DK` define 16 posições:

```
Fileira 1 (y=160): x=340, 540, 740          → agentes 1, 2, 3
Fileira 2 (y=340): x=340, 540, 740          → agentes 4, 5, 6
Fileira 3 (y=520): x=340, 540, 740          → agentes 7, 8, 9
Fileira 4 (y=160,340,520): x=920            → agentes 10, 11, 12 (ala expandida)
Fileira 5 (y=160,340,520,400): x=1060       → agentes 13, 14, 15, 16 (ala premium)
```

Posições especiais: `CEO_POS` (x=80, y=310), `MEET_CENTER` (x=1180, y=350, sala de reunião).

## Agentes no Escritório (dinâmico — baseado em atribuições do usuário)

Os agentes exibidos são carregados de `GET /api/squads` → `nomes_agentes[]`. Cada nome é mapeado para uma configuração visual via `agCfg(index, nome)`:
- Cor única baseada em hash do índice
- Emoji/ícone baseado no perfil do agente (`buscarAgente(nome)` em `config/agents.ts`)
- Status: livre / trabalhando / reunião (polling 3s em tarefas ativas)

## Histórico de Versões
- **v0.11.0** — Primeira versão com CSS isométrico 3D. Ficou distorcido.
- **v0.11.1** — Refatorado para grid responsivo com cards animados.
- **v0.43.0** — Live Agents: balões de status animados, pulse em tarefas ativas.
- **v0.56.0** — Array DK expandido de 9 → 16 posições. Agentes 10–16 têm mesa dedicada.

## Evolução Futura
- Arrastar agentes para reposicionar mesas
- Animações de caminhada quando agente entra em reunião
- Notificações visuais (balão de fala quando agente termina tarefa)
- Múltiplos andares para diferentes squads (quando 45 funcionários tiverem squads)
- Sons ambientes opcionais
- Personalização de avatar por agente

---

*Criado em: 24/03/2026*
*Última atualização: 24/03/2026*
