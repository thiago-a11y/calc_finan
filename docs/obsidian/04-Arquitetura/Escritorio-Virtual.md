# Escritório Virtual — Visualização Isométrica

> **Status:** ✅ Implementado (v0.11.0)
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

## Agentes e Emojis

| # | Agente | Emoji | Cor |
|---|--------|-------|-----|
| 1 | Tech Lead / Arquiteto | 🏗️ | Verde (#10b981) |
| 2 | Backend Developer | ⚙️ | Azul (#3b82f6) |
| 3 | Frontend Developer | 🎨 | Roxo (#8b5cf6) |
| 4 | Especialista IA | 🧠 | Amarelo (#f59e0b) |
| 5 | Integrações | 🔗 | Rosa (#ec4899) |
| 6 | DevOps & Infra | 🚀 | Indigo (#6366f1) |
| 7 | QA & Segurança | 🛡️ | Vermelho (#ef4444) |
| 8 | Product Manager | 📊 | Teal (#14b8a6) |

## Histórico de Versões
- **v0.11.0** — Primeira versão com CSS isométrico 3D (rotateX/rotateZ). Ficou distorcido e ilegível.
- **v0.11.1** — Refatorado para grid responsivo com cards animados. Muito mais limpo e funcional.

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
