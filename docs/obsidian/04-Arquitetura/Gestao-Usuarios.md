# Gestão de Usuários e Permissões

## Visão Geral
O Synerium Factory implementa um sistema completo de gestão de usuários com controle de acesso baseado em papéis (RBAC) e áreas de aprovação.

## Papéis Disponíveis

| ID | Nome | Descrição |
|---|---|---|
| `ceo` | CEO | Chief Executive Officer — poder total |
| `diretor_tecnico` | Diretor Técnico | Responsável pela área técnica |
| `operations_lead` | Operations Lead | Poder de override e aprovação final |
| `pm_central` | PM Central | Project Manager — orquestrador dos squads |
| `lider` | Líder de Squad | Lidera um squad específico |
| `desenvolvedor` | Desenvolvedor | Desenvolvimento de software |
| `marketing` | Marketing | Marketing e growth |
| `financeiro` | Financeiro | Controle financeiro e custos |
| `suporte` | Suporte | Suporte ao cliente |
| `membro` | Membro | Membro da equipe |

## Áreas de Aprovação

| ID | Nome | Descrição |
|---|---|---|
| `deploy_producao` | Deploy Produção | Aprovar deploys em produção |
| `gasto_ia` | Gasto IA | Aprovar gastos de IA acima de R$50 |
| `mudanca_arquitetura` | Mudança Arquitetura | Aprovar mudanças estruturais |
| `campanha_marketing` | Campanha Marketing | Aprovar campanhas |
| `outreach_massa` | Outreach em Massa | Aprovar envios em massa |

## Permissões de Admin
Apenas usuários com papéis `ceo`, `diretor_tecnico` ou `operations_lead` podem:
- Criar novos usuários
- Editar qualquer usuário
- Alterar permissões
- Desativar usuários

## Endpoints da API

| Método | Rota | Descrição | Requer Admin |
|---|---|---|---|
| GET | `/api/usuarios` | Listar todos | Não |
| GET | `/api/usuarios/papeis-disponiveis` | Papéis do sistema | Não |
| GET | `/api/usuarios/areas-aprovacao-disponiveis` | Áreas do sistema | Não |
| POST | `/api/usuarios` | Criar usuário | Sim |
| PUT | `/api/usuarios/{id}` | Editar usuário | Sim |
| PUT | `/api/usuarios/{id}/permissoes` | Alterar permissões | Sim |
| DELETE | `/api/usuarios/{id}` | Desativar (soft delete) | Sim |

## Dashboard — Página Configurações

Acessível em `/configuracoes` com 3 abas:

### Aba Usuários
- Criar novo usuário com email, senha, cargo e papéis
- Editar nome, email e cargo de qualquer usuário
- Desativar usuário (soft delete)

### Aba Permissões
- Visualizar papéis e áreas de cada usuário
- Editar papéis (toggle em chips)
- Ativar/desativar poder de aprovação
- Selecionar áreas de aprovação específicas

### Aba Sistema
- Informações da versão, ambiente, stack técnica
- Configurações de autenticação
- Integrações ativas
- Limites configurados

## Exclusão Permanente de Usuários (v0.16.5)

### Funcionalidade
- Proprietários (CEO, Operations Lead) podem excluir permanentemente um usuário
- Endpoint: `DELETE /api/usuarios/{id}/permanente`
- Remove o registro do banco de dados (hard delete)
- Libera o email para ser usado em novo convite

### Motivação
O soft delete (desativação) mantém o registro no banco, impedindo reconvite para o mesmo email. Em casos como convite enviado para email errado ou funcionário que precisa ser recadastrado, o hard delete é necessário.

### Restrições
- Apenas papéis `ceo`, `operations_lead` e `diretor_tecnico` podem executar
- Não é possível excluir a própria conta
- Audit log LGPD registra a exclusão permanente (quem excluiu, quando, qual usuário)

## Segurança
- Toda ação admin é registrada no audit log (LGPD)
- Não é possível desativar ou excluir a própria conta
- Senha mínima: 8 caracteres com bcrypt cost 12
- Verificação de email duplicado na criação/edição
