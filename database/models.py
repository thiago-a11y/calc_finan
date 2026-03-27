"""
Modelos SQLAlchemy do Synerium Factory.

Tabelas:
- usuarios: Cadastro de usuários com autenticação
- convites: Convites por email para novos usuários
- audit_log: Log de auditoria de todas as ações
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime, JSON
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base para todos os modelos."""
    pass


class UsuarioDB(Base):
    """
    Tabela de usuários — autenticação, perfil e permissões.

    Segue o padrão do SyneriumX adaptado para Python:
    - bcrypt para senhas
    - JWT para sessão
    - company_id para multi-tenant
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Autenticação
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Perfil básico
    nome = Column(String(255), nullable=False)
    cargo = Column(String(100), default="")
    telefone = Column(String(20), default="")
    bio = Column(Text, default="")
    avatar_url = Column(String(500), default="")

    # Papéis e permissões (armazenados como JSON)
    papeis = Column(JSON, default=list)  # ["ceo", "operations_lead", ...]
    areas_aprovacao = Column(JSON, default=list)  # ["deploy_producao", ...]
    pode_aprovar = Column(Boolean, default=False)

    # Permissões granulares por módulo (JSON)
    # Formato: {"dashboard": {"view": true, "create": false, ...}, "squads": {...}, ...}
    # Se null/vazio, herda do papel (role). Overrides são explícitos.
    permissoes_granulares = Column(JSON, nullable=True, default=None)

    # Redes sociais
    social_linkedin = Column(String(500), default="")
    social_instagram = Column(String(500), default="")
    social_whatsapp = Column(String(20), default="")

    # Preferências
    pref_tema = Column(String(20), default="light")
    pref_idioma = Column(String(10), default="pt-BR")

    # Notificações
    notif_email = Column(Boolean, default=True)
    notif_whatsapp = Column(Boolean, default=True)
    notif_aprovacoes = Column(Boolean, default=True)

    # Multi-tenant
    company_id = Column(Integer, default=1)

    # Status
    ativo = Column(Boolean, default=True)
    tentativas_login = Column(Integer, default=0)
    bloqueado_ate = Column(DateTime, nullable=True)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario {self.id}: {self.nome} ({self.email})>"


class ConviteDB(Base):
    """
    Tabela de convites por email.

    Fluxo: admin cria convite → email enviado via SES → usuário
    clica no link → preenche senha → conta criada.
    """
    __tablename__ = "convites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    nome = Column(String(255), default="")
    cargo = Column(String(100), default="")
    papeis = Column(JSON, default=list)
    token = Column(String(255), unique=True, nullable=False, index=True)
    convidado_por_id = Column(Integer, nullable=False)
    usado = Column(Boolean, default=False)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<Convite {self.id}: {self.email} ({'usado' if self.usado else 'pendente'})>"


class AuditLogDB(Base):
    """
    Log de auditoria — registra todas as ações importantes.

    Seguindo padrão LGPD do SyneriumX.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    email = Column(String(255), default="")
    acao = Column(String(100), nullable=False)  # LOGIN, LOGOUT, APROVACAO, etc.
    descricao = Column(Text, default="")
    ip = Column(String(50), default="")
    user_agent = Column(String(500), default="")
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.acao} por user_id={self.user_id}>"


class TarefaDB(Base):
    """
    Tabela de tarefas e reuniões executadas pelos agentes.

    Persiste o histórico de todas as interações com os agentes,
    incluindo tarefas individuais e reuniões multi-agente com rodadas.
    """
    __tablename__ = "tarefas"

    id = Column(String(8), primary_key=True)  # UUID curto
    squad_nome = Column(String(255), nullable=False)
    agente_nome = Column(String(255), nullable=False)
    agente_indice = Column(Integer, default=0)
    descricao = Column(Text, nullable=False)
    resultado = Column(Text, nullable=True)
    status = Column(String(20), default="pendente")  # pendente, executando, concluida, erro, aguardando_feedback
    erro = Column(Text, nullable=True)
    tipo = Column(String(20), default="tarefa")  # tarefa ou reuniao
    participantes = Column(JSON, nullable=True)  # Lista de nomes (reunião)
    # Rodadas: lista de {rodada, agente, resposta, timestamp}
    rodadas = Column(JSON, nullable=True)
    rodada_atual = Column(Integer, default=1)
    agente_atual = Column(String(255), nullable=True)  # Qual agente está falando agora
    agentes_indices = Column(JSON, nullable=True)  # Índices dos agentes participantes
    usuario_id = Column(Integer, nullable=False)
    usuario_nome = Column(String(255), nullable=False)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    concluido_em = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Tarefa {self.id}: {self.tipo} [{self.status}] {self.agente_nome}>"


class ProjetoDB(Base):
    """
    Tabela de projetos registrados no Synerium Factory.

    Cada projeto tem:
    - Proprietário (CEO pode nomear): palavra final em tudo
    - Líder Técnico: aprova mudanças técnicas menores
    - Membros: podem solicitar mudanças (precisam de aprovação)

    Regras de aprovação:
    - Mudança pequena (bug fix, UI tweak) → Líder Técnico aprova
    - Mudança grande (nova feature, arquitetura) → Proprietário aprova
    - Mudança crítica (deploy, banco, segurança) → Proprietário + Líder
    """
    __tablename__ = "projetos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, unique=True)
    descricao = Column(Text, default="")
    caminho = Column(String(500), default="")  # ~/propostasap
    repositorio = Column(String(500), default="")  # URL do GitHub
    stack = Column(String(255), default="")  # "PHP 7.4 + React 18 + MySQL"
    icone = Column(String(10), default="📁")

    # Hierarquia
    proprietario_id = Column(Integer, nullable=False)  # Usuário dono (só CEO pode nomear)
    proprietario_nome = Column(String(255), nullable=False)
    lider_tecnico_id = Column(Integer, nullable=True)  # Líder técnico (aprovações menores)
    lider_tecnico_nome = Column(String(255), default="")
    membros = Column(JSON, default=list)  # [{"id": 1, "nome": "Rhammon", "papel": "dev"}]

    # Status
    ativo = Column(Boolean, default=True)
    fase_atual = Column(String(100), default="")  # "Fase 7.3"

    # Multi-tenant
    company_id = Column(Integer, default=1)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Projeto {self.id}: {self.nome} (dono: {self.proprietario_nome})>"


class SolicitacaoDB(Base):
    """
    Tabela de solicitações de mudança em projetos.

    Fluxo:
    1. Membro cria solicitação descrevendo a mudança desejada
    2. Sistema determina nível (pequena/grande/crítica)
    3. Notificação vai para o aprovador correto
    4. Aprovador aprova/rejeita com comentário
    5. Se aprovada → agentes podem executar a mudança
    """
    __tablename__ = "solicitacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    projeto_id = Column(Integer, nullable=False)
    projeto_nome = Column(String(255), nullable=False)

    # Quem solicitou
    solicitante_id = Column(Integer, nullable=False)
    solicitante_nome = Column(String(255), nullable=False)

    # Detalhes da mudança
    titulo = Column(String(500), nullable=False)
    descricao = Column(Text, nullable=False)
    tipo_mudanca = Column(String(20), nullable=False)  # pequena, grande, critica
    categoria = Column(String(50), default="feature")  # feature, bugfix, refactor, deploy, seguranca

    # Aprovação
    status = Column(String(20), default="pendente")  # pendente, aprovada, rejeitada, em_execucao, concluida
    aprovador_necessario = Column(String(50), default="")  # proprietario, lider_tecnico, ambos
    aprovado_por_id = Column(Integer, nullable=True)
    aprovado_por_nome = Column(String(255), default="")
    comentario_aprovador = Column(Text, default="")
    aprovado_em = Column(DateTime, nullable=True)

    # Execução (se aprovada)
    executado_por_agente = Column(String(255), default="")  # Nome do agente que executou
    resultado_execucao = Column(Text, default="")

    # Multi-tenant
    company_id = Column(Integer, default=1)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Solicitacao {self.id}: {self.titulo} [{self.status}] projeto={self.projeto_nome}>"


class UsageTrackingDB(Base):
    """
    Tracking de consumo de APIs — registra CADA chamada em tempo real.

    Nunca reseta. Fonte de verdade para o dashboard de consumo.
    Suporta todos os 14 providers configurados.
    """
    __tablename__ = "usage_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Provider identificação
    provider_id = Column(String(50), nullable=False, index=True)  # anthropic, openai, groq, etc.
    provider_nome = Column(String(100), default="")
    modelo = Column(String(100), default="")  # claude-sonnet-4-20250514, llama-3.3-70b, etc.

    # Métricas de uso
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    requests = Column(Integer, default=1)

    # Custo
    custo_usd = Column(Float, default=0.0)

    # Contexto
    tipo = Column(String(50), default="chat")  # chat, reuniao, rag, embedding, busca, email, videocall
    agente_nome = Column(String(255), default="")
    squad_nome = Column(String(255), default="")
    usuario_id = Column(Integer, nullable=True)
    usuario_nome = Column(String(255), default="")

    # Detalhes extras (JSON livre)
    detalhes = Column(JSON, nullable=True)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)

    # Multi-tenant
    company_id = Column(Integer, default=1)

    def __repr__(self):
        return f"<Usage {self.provider_id}: {self.tokens_total} tokens, ${self.custo_usd:.4f}>"
