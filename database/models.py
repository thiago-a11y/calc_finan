"""
Modelos SQLAlchemy do Synerium Factory.

Tabelas:
- usuarios: Cadastro de usuários com autenticação
- convites: Convites por email para novos usuários
- audit_log: Log de auditoria de todas as ações
- agentes_catalogo: Prateleira de templates de agentes reutilizáveis
- agentes_atribuidos: Vínculo catálogo → usuário
- solicitacoes_agente: Pedidos de novos agentes por usuários
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

    # Regras de aprovação customizáveis por projeto
    # Formato: {"pequena": "lider_tecnico", "grande": "proprietario", "critica": "ambos"}
    # Valores possíveis: "lider_tecnico", "proprietario", "ambos", "nenhum" (auto-aprovação)
    regras_aprovacao = Column(JSON, default=lambda: {
        "pequena": {"aprovador": "lider_tecnico", "descricao": "Bug fix, UI tweak"},
        "grande": {"aprovador": "proprietario", "descricao": "Feature, arquitetura"},
        "critica": {"aprovador": "ambos", "descricao": "Deploy, banco, segurança"},
    })

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


class ProjetoVCSDB(Base):
    """
    Configuração de Version Control (GitHub/GitBucket) por projeto.
    Token criptografado com Fernet para segurança em repouso.
    """
    __tablename__ = "projeto_vcs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    projeto_id = Column(Integer, nullable=False, index=True)
    vcs_tipo = Column(String(20), nullable=False, default="github")  # github | gitbucket
    repo_url = Column(String(500), nullable=False)
    api_token_encrypted = Column(Text, nullable=False)  # Fernet-encrypted
    branch_padrao = Column(String(100), default="main")
    ativo = Column(Boolean, default=True)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProjetoVCS {self.id}: {self.vcs_tipo} → {self.repo_url}>"


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


class AgenteCatalogoDB(Base):
    """
    Prateleira de agentes — templates reutilizáveis.

    Admin cria templates aqui e depois atribui aos usuários.
    Cada agente tem papel, objetivo, história e perfil do SmartRouter.
    """
    __tablename__ = "agentes_catalogo"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identidade do agente
    nome_exibicao = Column(String(255), nullable=False)  # "Tech Lead / Arquiteto de Software"
    papel = Column(String(255), nullable=False)  # Role do CrewAI
    objetivo = Column(Text, nullable=False)  # Goal do CrewAI
    historia = Column(Text, nullable=False)  # Backstory do CrewAI

    # Configuração técnica
    perfil_agente = Column(String(50), nullable=False)  # tech_lead, backend_dev, etc.
    categoria = Column(String(50), default="geral")  # desenvolvimento, gestao, seguranca, ia, operacional
    icone = Column(String(50), default="Bot")  # Nome do ícone lucide-react
    regras_extras = Column(Text, default="")  # Regras anti-alucinação injetadas no backstory
    allow_delegation = Column(Boolean, default=False)

    # Metadata
    ativo = Column(Boolean, default=True)
    company_id = Column(Integer, default=1)
    criado_por_id = Column(Integer, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AgenteCatalogo {self.id}: {self.nome_exibicao} ({self.perfil_agente})>"


class AgenteAtribuidoDB(Base):
    """
    Vínculo catálogo → usuário.

    Admin atribui agentes do catálogo aos usuários.
    Cada atribuição pode ter customizações (objetivo/história override).
    """
    __tablename__ = "agentes_atribuidos"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Vínculo
    agente_catalogo_id = Column(Integer, nullable=False, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    atribuido_por_id = Column(Integer, nullable=False)

    # Customização
    ordem = Column(Integer, default=0)  # Posição no squad do usuário
    objetivo_custom = Column(Text, nullable=True)  # Override do objetivo
    historia_custom = Column(Text, nullable=True)  # Override da história

    # Status
    ativo = Column(Boolean, default=True)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AgenteAtribuido {self.id}: catalogo={self.agente_catalogo_id} → usuario={self.usuario_id}>"


class LunaConversaDB(Base):
    """
    Tabela de conversas da Luna — assistente inteligente.

    Cada usuário pode ter múltiplas conversas persistentes.
    Proprietários (CEO/Operations Lead) podem visualizar conversas de outros.
    """
    __tablename__ = "luna_conversas"

    id = Column(String(12), primary_key=True)  # nanoid curto
    usuario_id = Column(Integer, nullable=False, index=True)
    usuario_nome = Column(String(255), default="")
    titulo = Column(String(500), default="Nova conversa")
    modelo_preferido = Column(String(50), default="auto")  # auto, sonnet, opus

    # Soft delete — quando usuário exclui, conversa vai para lixeira do proprietário
    excluida_pelo_usuario = Column(Boolean, default=False)
    excluida_em = Column(DateTime, nullable=True)  # Quando o usuário excluiu
    excluida_permanente = Column(Boolean, default=False)  # Só proprietário pode excluir de vez

    # Multi-tenant
    company_id = Column(Integer, default=1)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LunaConversa {self.id}: '{self.titulo}' (user={self.usuario_id})>"


class LunaMensagemDB(Base):
    """
    Tabela de mensagens da Luna — histórico completo de cada conversa.

    Persistência infinita: todas as mensagens são salvas para contexto futuro.
    Inclui métricas de uso (tokens, custo, modelo) para tracking.
    """
    __tablename__ = "luna_mensagens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversa_id = Column(String(12), nullable=False, index=True)
    papel = Column(String(20), nullable=False)  # "user" ou "assistant"
    conteudo = Column(Text, nullable=False)

    # Anexos (JSON: lista de {nome_original, url, tipo, tamanho})
    anexos = Column(JSON, nullable=True)

    # Métricas de uso (preenchidas na resposta da IA)
    modelo_usado = Column(String(100), default="")  # ex: "claude-sonnet-4", "llama-3.3-70b"
    provider_usado = Column(String(50), default="")  # ex: "anthropic", "groq", "fireworks"
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    custo_usd = Column(Float, default=0.0)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LunaMensagem {self.id}: {self.papel} em conversa={self.conversa_id}>"


class LunaComentarioDB(Base):
    """
    Comentários/anotações em artefatos da Luna.
    Permite que usuários comentem em PDFs, planilhas, código etc.
    Proprietários veem comentários de todos os funcionários.
    """
    __tablename__ = "luna_comentarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversa_id = Column(String(12), nullable=False, index=True)
    artefato_id = Column(String(100), nullable=False, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    usuario_nome = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LunaComentario {self.id}: {self.usuario_nome} em {self.artefato_id}>"


class ArtifactDB(Base):
    """
    Artifacts gerados por agentes no Mission Control (v0.55.0).

    Entregaveis tangiveis: planos de tarefas, screenshots, checklists,
    trechos de codigo, diagramas, logs de terminal, etc.
    Suportam comentarios inline estilo Google Docs.
    """
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(String(20), nullable=False, unique=True, index=True)

    # Contexto
    sessao_id = Column(String(20), nullable=False, index=True)  # Sessao Mission Control
    workflow_id = Column(String(20), nullable=True)             # Workflow autonomo associado
    agente_nome = Column(String(255), default="")               # Agente que gerou

    # Conteudo
    tipo = Column(String(50), nullable=False)  # plano, screenshot, checklist, codigo, terminal, navegacao, markdown
    titulo = Column(String(500), nullable=False)
    conteudo = Column(Text, nullable=True)          # Texto/markdown/codigo
    dados = Column(JSON, default=dict)              # Metadados estruturados (checklist items, etc)
    arquivo_path = Column(String(500), nullable=True)  # Caminho do arquivo (screenshots, etc)

    # Status
    status = Column(String(50), default="gerado")  # gerado, revisado, aprovado, rejeitado
    revisado_por = Column(String(100), nullable=True)

    # Comentarios inline (JSON array de {linha, texto, autor, data})
    comentarios_inline = Column(JSON, default=list)

    # Metadata
    usuario_id = Column(Integer, nullable=True)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Artifact {self.artifact_id}: {self.tipo} — {self.titulo[:50]}>"


class TeamChatDB(Base):
    """
    Mensagens do Team Chat no Mission Control (v0.57.1).

    Registro de TODA conversa entre agentes e entre agente-usuario.
    Visivel em tempo real no painel Team Chat.
    """
    __tablename__ = "team_chat"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao_id = Column(String(20), nullable=False, index=True)
    agente_nome = Column(String(255), nullable=False)  # "Tech Lead", "Backend Dev", "QA", "Sistema"
    tipo = Column(String(50), default="mensagem")  # mensagem, planejamento, decisao, alerta, sistema
    conteudo = Column(Text, nullable=False)
    fase = Column(String(50), default="")  # planejamento, implementacao, testes, review
    metadata = Column(JSON, default=dict)  # dados extras (ex: arquivo mencionado, comando)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TeamChat {self.agente_nome}: {self.conteudo[:50]}>"


class MissionControlSessaoDB(Base):
    """
    Sessao do Mission Control (v0.55.0).

    Cada sessao representa uma instancia do dev trabalhando com agentes
    no painel triplo (editor + terminal + navegador).
    """
    __tablename__ = "mission_control_sessoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao_id = Column(String(20), nullable=False, unique=True, index=True)

    # Estado
    titulo = Column(String(500), default="Nova Sessão")
    status = Column(String(50), default="ativa")  # ativa, pausada, concluida
    projeto_id = Column(Integer, nullable=True)    # ProjetoDB associado

    # Paineis ativos
    painel_editor = Column(JSON, default=dict)     # {arquivo_aberto, cursor_pos, etc}
    painel_terminal = Column(JSON, default=dict)   # {ultimo_comando, historico}
    painel_navegador = Column(JSON, default=dict)  # {url_atual, screenshots}

    # Agentes ativos na sessao
    agentes_ativos = Column(JSON, default=list)    # [{nome, status, tarefa_atual}]

    # Metricas
    total_artifacts = Column(Integer, default=0)
    total_comandos = Column(Integer, default=0)
    total_arquivos_editados = Column(Integer, default=0)

    # Metadata
    usuario_id = Column(Integer, nullable=False)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MissionControl {self.sessao_id}: {self.titulo} [{self.status}]>"


class SolicitacaoAgenteDB(Base):
    """
    Solicitações de agentes por usuários.

    Fluxo:
    1. Usuário pede um agente (do catálogo ou novo)
    2. Admin (CEO/Jonatas) aprova ou rejeita
    3. Se aprovado, agente é atribuído automaticamente
    """
    __tablename__ = "solicitacoes_agente"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Quem solicitou
    usuario_id = Column(Integer, nullable=False)
    usuario_nome = Column(String(255), nullable=False)

    # O que pediu
    agente_catalogo_id = Column(Integer, nullable=True)  # Se pediu um específico do catálogo
    descricao = Column(Text, nullable=False)  # Justificativa
    perfil_sugerido = Column(String(50), default="")

    # Decisão
    status = Column(String(20), default="pendente")  # pendente, aprovado, rejeitado
    aprovado_por_id = Column(Integer, nullable=True)
    aprovado_por_nome = Column(String(255), default="")
    comentario = Column(Text, default="")  # Resposta do admin

    # Multi-tenant
    company_id = Column(Integer, default=1)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SolicitacaoAgente {self.id}: user={self.usuario_nome} [{self.status}]>"


class WorkflowAutonomoDB(Base):
    """
    Workflow Autonomo — Execucao completa do ciclo BMAD.

    O usuario da uma tarefa de alto nivel e o sistema executa
    as 4 fases BMAD autonomamente, parando apenas nos gates.
    """
    __tablename__ = "workflows_autonomos"

    id = Column(String(20), primary_key=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, default="")

    # Progresso
    fase_atual = Column(Integer, default=1)  # 1=Analise, 2=Planejamento, 3=Solucao, 4=Implementacao
    status = Column(String(50), default="em_execucao")
    # Status: montando_time, em_execucao, aguardando_gate, concluido, erro, cancelado

    # Agentes e execucao
    agentes_ids = Column(JSON, default=list)  # IDs do catalogo selecionados
    outputs = Column(JSON, default=dict)      # {"fase_1": "output...", "fase_2": "output..."}
    gates = Column(JSON, default=dict)        # {"fase_1": {"status": "pass", "por": "auto"}}
    tarefa_atual_id = Column(String(20))      # ID da TarefaDB (reuniao) em execucao

    # Projeto alvo
    projeto_id = Column(Integer, default=0)
    squad_nome = Column(String(100), default="")

    # Usuario
    usuario_id = Column(Integer, nullable=False)
    usuario_nome = Column(String(100), default="")
    company_id = Column(Integer, default=1)

    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Workflow {self.id}: {self.titulo} [Fase {self.fase_atual} - {self.status}]>"


class EvolucaoFactoryDB(Base):
    """
    Registro de auto-evolucoes da fabrica.

    Cada registro representa uma review session pos-workflow
    com sugestoes de melhoria e status de aplicacao.
    """
    __tablename__ = "evolucoes_factory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(20), nullable=True)
    workflow_titulo = Column(String(255), nullable=True)

    # Metricas da execucao
    tempo_total_seg = Column(Integer, default=0)
    custo_total_usd = Column(Float, default=0.0)
    total_fases = Column(Integer, default=4)
    total_agentes = Column(Integer, default=0)
    erros_encontrados = Column(Integer, default=0)

    # Review
    analise = Column(Text, nullable=True)
    sugestoes = Column(JSON, default=list)
    metricas = Column(JSON, default=dict)

    # Status: pendente, analisando, aguardando_aprovacao, aplicado, rejeitado
    status = Column(String(50), default="pendente")
    aplicado_por = Column(String(100), nullable=True)
    aplicado_em = Column(DateTime, nullable=True)

    # Metadata
    usuario_id = Column(Integer, nullable=True)
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Evolucao {self.id}: workflow={self.workflow_id} [{self.status}]>"


class ContinuousFactoryDB(Base):
    """
    Configuracao do Modo Continuo 24/7 (v0.54.0).

    Quando ativado, a fabrica continua executando workflows autonomamente
    mesmo quando o CEO esta offline. Gates soft sao auto-aprovados,
    gates hard geram notificacao por email.

    Singleton por company_id (1 config por empresa).
    """
    __tablename__ = "continuous_factory"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Estado do modo continuo
    ativo = Column(Boolean, default=False)
    ativado_por = Column(String(100), nullable=True)
    ativado_em = Column(DateTime, nullable=True)
    desativado_em = Column(DateTime, nullable=True)

    # Configuracao de gates
    auto_aprovar_soft = Column(Boolean, default=True)   # Gates soft: auto-approve
    auto_aprovar_hard = Column(Boolean, default=False)  # Gates hard: requer humano (default)
    notificar_email = Column(Boolean, default=True)     # Enviar email quando gate hard pendente
    email_notificacao = Column(String(255), default="")  # Email para notificacoes

    # Relatorio diario
    relatorio_diario_ativo = Column(Boolean, default=True)
    horario_relatorio = Column(String(5), default="23:00")  # HH:MM
    ultimo_relatorio_em = Column(DateTime, nullable=True)

    # Fila de trabalho
    max_workflows_paralelos = Column(Integer, default=2)
    intervalo_entre_workflows_seg = Column(Integer, default=60)  # Pausa entre workflows

    # Metricas acumuladas (resetadas diariamente no relatorio)
    workflows_hoje = Column(Integer, default=0)
    custo_hoje_usd = Column(Float, default=0.0)
    fases_completadas_hoje = Column(Integer, default=0)
    erros_hoje = Column(Integer, default=0)

    # Metadata
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ContinuousFactory ativo={self.ativo} company={self.company_id}>"


class RelatorioDiarioDB(Base):
    """
    Relatorio diario gerado automaticamente pelo Modo Continuo (v0.54.0).

    Contem resumo do que foi construido, custos, evolucoes e proximos passos.
    Gerado as 23:00 (configuravel) e enviado por email ao CEO.
    """
    __tablename__ = "relatorios_diarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(String(10), nullable=False)  # YYYY-MM-DD

    # Metricas do dia
    workflows_executados = Column(Integer, default=0)
    workflows_concluidos = Column(Integer, default=0)
    workflows_erro = Column(Integer, default=0)
    fases_completadas = Column(Integer, default=0)
    gates_aprovados = Column(Integer, default=0)
    gates_pendentes = Column(Integer, default=0)

    # Custos
    custo_total_usd = Column(Float, default=0.0)
    tokens_input_total = Column(Integer, default=0)
    tokens_output_total = Column(Integer, default=0)
    provider_mais_usado = Column(String(50), default="")

    # Evolucoes
    evolucoes_geradas = Column(Integer, default=0)
    sugestoes_total = Column(Integer, default=0)

    # Conteudo
    resumo = Column(Text, nullable=True)            # Resumo gerado por LLM
    detalhes = Column(JSON, default=dict)            # JSON com detalhes completos
    proximos_passos = Column(JSON, default=list)     # Lista de proximos passos

    # Status
    enviado_por_email = Column(Boolean, default=False)
    email_destino = Column(String(255), default="")

    # Metadata
    company_id = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Relatorio {self.data}: {self.workflows_concluidos} workflows, ${self.custo_total_usd:.2f}>"
