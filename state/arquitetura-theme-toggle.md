# Arquitetura — Toggle de Tema no Header

## ADR-001: Posição do Toggle
- **Decisão:** Header, lado direito, antes do avatar
- **Alternativas:** Sidebar (atual), Settings page, Floating button
- **Motivo:** Padrão de mercado. GitHub, Vercel, Stripe usam header.

## ADR-002: Mecanismo de Tema
- **Decisão:** Classe `dark`/`light` no `<html>` + CSS variables
- **Já existe:** ThemeProvider no AuthContext com localStorage
- **Mudança:** Mover toggle da Sidebar para o Header

## ADR-003: Componente
- **Criar:** `ThemeToggle.tsx` — componente isolado e reutilizável
- **Ícones:** Sun e Moon do lucide-react (consistente com design system)
- **Animação:** Framer Motion rotate 180° no toggle

## Arquivos a modificar
1. `dashboard/src/components/ThemeToggle.tsx` — CRIAR componente
2. `dashboard/src/components/Sidebar.tsx` — REMOVER toggle antigo
3. `dashboard/src/App.tsx` — Adicionar ThemeToggle no layout (header area)

## Story BDD

### AC-1: Toggle visível no header
```gherkin
Dado que o usuário está logado
Quando a página carrega
Então o ícone de tema (sol ou lua) aparece no canto superior direito
```

### AC-2: Troca de tema
```gherkin
Dado que o tema atual é dark
Quando o usuário clica no ícone lua
Então o tema muda para light com transição suave
E o ícone muda para sol
```

### AC-3: Persistência
```gherkin
Dado que o usuário escolheu light mode
Quando ele recarrega a página
Então o tema light é restaurado automaticamente
```
