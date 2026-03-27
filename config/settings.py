"""
Configurações centrais do Synerium Factory.

Nota: Usamos dotenv_values para carregar o .env manualmente,
pois variáveis vazias no ambiente do sistema podem sobrescrever
os valores do arquivo .env quando usando pydantic-settings.
"""

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

# Carregar valores do .env e injetar no ambiente
# para que pydantic-settings os reconheça corretamente
import os

_env_valores = dotenv_values(".env")
for _chave, _valor in _env_valores.items():
    if _valor and (not os.environ.get(_chave)):
        os.environ[_chave] = _valor


class SyneriumSettings(BaseSettings):
    """Configurações carregadas do .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "synerium-factory"

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI (opcional)
    openai_api_key: str = ""

    # Projeto
    synerium_env: str = "development"
    synerium_log_level: str = "INFO"

    # Limites
    limite_gasto_ia_sem_aprovacao: float = 50.00

    # Notificações
    webhook_whatsapp: str = ""
    webhook_telegram: str = ""
    email_operations_lead: str = ""

    # LangSmith tracing
    langsmith_tracing: bool = True

    # JWT (Autenticação)
    jwt_secret_key: str = "synerium-dev-secret-trocar-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 30

    # Amazon SES (Email)
    aws_region: str = "us-east-1"
    aws_ses_sender: str = ""

    # RAG (Base de Conhecimento)
    rag_vault_syneriumx: str = ""
    rag_vault_factory: str = ""
    rag_persist_dir: str = "data/chromadb"

    @property
    def ambiente(self) -> str:
        return self.synerium_env

    @property
    def log_level(self) -> str:
        return self.synerium_log_level

    @property
    def limite_gasto_ia(self) -> float:
        return self.limite_gasto_ia_sem_aprovacao


settings = SyneriumSettings()
