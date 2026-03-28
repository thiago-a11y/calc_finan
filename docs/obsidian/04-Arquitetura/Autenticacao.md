# Arquitetura — Autenticação e Usuários

> Sistema de autenticação JWT + bcrypt com perfil de usuário, seguindo o padrão do SyneriumX.

---

## Stack de Autenticação

| Componente | Tecnologia | Detalhes |
|---|---|---|
| **Tokens** | JWT (HS256) | python-jose |
| **Senhas** | bcrypt (cost 12) | bcrypt direto |
| **Banco** | SQLite | SQLAlchemy 2.0 |
| **Email** | Amazon SES | boto3 (para convites) |

## Fluxo de Login

```
1. Usuário acessa http://localhost:5173
2. Dashboard redireciona para /login (se não autenticado)
3. Usuário digita email + senha
4. Frontend chama POST /auth/login
5. Backend verifica senha (bcrypt) → gera JWT (1h) + refresh token (30d)
6. Frontend salva tokens no localStorage
7. Todas as requisições incluem Authorization: Bearer <token>
8. Token expira em 1h → frontend chama POST /auth/refresh automaticamente
```

## Tabelas do Banco (data/synerium.db)

### usuarios
| Campo | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID auto-incremento |
| email | VARCHAR UNIQUE | Email de login |
| password_hash | VARCHAR | Hash bcrypt |
| nome | VARCHAR | Nome do usuário |
| cargo | VARCHAR | Cargo/título |
| papeis | JSON | Lista de papéis (ceo, operations_lead, etc.) |
| areas_aprovacao | JSON | Áreas que pode aprovar |
| pode_aprovar | BOOL | Pode aprovar solicitações |
| telefone, bio, avatar_url | VARCHAR/TEXT | Perfil |
| social_linkedin, social_instagram, social_whatsapp | VARCHAR | Redes sociais |
| pref_tema, pref_idioma | VARCHAR | Preferências |
| notif_email, notif_whatsapp, notif_aprovacoes | BOOL | Notificações |
| company_id | INT | Multi-tenant |
| ativo | BOOL | Conta ativa |
| tentativas_login | INT | Bloqueio após 10 tentativas |
| bloqueado_ate | DATETIME | Bloqueio por 30 minutos |

### convites
| Campo | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID |
| email | VARCHAR | Email do convidado |
| token | VARCHAR UNIQUE | Token seguro (URL-safe) |
| convidado_por_id | INT | Quem convidou |
| usado | BOOL | Se já foi usado |
| expira_em | DATETIME | Expira em 7 dias |

### audit_log
| Campo | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID |
| user_id | INT | Quem fez |
| acao | VARCHAR | LOGIN, LOGOUT, APROVACAO, etc. |
| descricao | TEXT | Detalhes |
| ip | VARCHAR | IP do request |

## Endpoints de Auth

| Método | Rota | Proteção | Descrição |
|---|---|---|---|
| POST | `/auth/login` | Público | Login com email/senha |
| POST | `/auth/refresh` | Público | Renovar access token |
| POST | `/auth/registrar` | Público | Completar registro via convite |
| POST | `/auth/trocar-senha` | Autenticado | Alterar senha |
| POST | `/api/convites` | Admin/CEO | Criar e enviar convite |
| GET | `/api/convites/{token}` | Público | Validar token |
| PUT | `/api/usuarios/perfil` | Autenticado | Editar perfil próprio |

## Segurança

- **Bloqueio**: Após 10 tentativas erradas, conta bloqueada por 30 minutos
- **JWT**: Access token 1h, refresh token 30d
- **bcrypt**: Cost 12 (mesmo padrão do SyneriumX)
- **Audit log**: Todo login registrado com IP e timestamp
- **LGPD**: Dados sensíveis nunca expostos (password_hash, tokens)

## Usuários Seed (Iniciais)

| Usuário | Email | Cargo | Papéis | Senha Inicial |
|---|---|---|---|---|
| Thiago | thiago@objetivasolucao.com.br | CEO | ceo | SyneriumFactory@2026 |
| Jonatas | jonatas@objetivasolucao.com.br | Diretor Técnico e Operations Lead | diretor_tecnico, operations_lead | SyneriumFactory@2026 |

## Arquivos Relacionados

```
api/security.py           # JWT + bcrypt
api/routes/auth.py        # Login, refresh, registro
api/routes/convites.py    # Convites por email
api/dependencias.py       # obter_usuario_atual() (JWT middleware)
database/models.py        # UsuarioDB, ConviteDB, AuditLogDB
database/session.py       # SQLite + SQLAlchemy
database/seed.py          # Seed Thiago + Jonatas
dashboard/src/contexts/AuthContext.tsx   # Contexto React
dashboard/src/pages/Login.tsx            # Tela de login
dashboard/src/pages/Perfil.tsx           # Tela de perfil
```

---

> Última atualização: 2026-03-23
