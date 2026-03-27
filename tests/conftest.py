"""
Fixtures compartilhadas para todos os testes do Synerium Factory.

Inclui: banco de dados de teste, cliente HTTP, usuários mock.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Forçar ambiente de teste ANTES de importar qualquer módulo
os.environ["SYNERIUM_ENV"] = "test"
os.environ["SYNERIUM_LOG_LEVEL"] = "WARNING"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-apenas-para-testes"

from database.models import Base, UsuarioDB
from api.security import hash_senha, criar_access_token


# =====================================================================
# Banco de dados de teste (SQLite em memória)
# =====================================================================

@pytest.fixture(scope="session")
def engine():
    """Cria engine SQLite em memória para testes."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db(engine):
    """Cria sessão de banco limpa para cada teste."""
    Session = sessionmaker(bind=engine)
    session = Session()

    # Limpar tabelas antes de cada teste
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session
    session.close()


# =====================================================================
# Usuários de teste
# =====================================================================

@pytest.fixture
def usuario_ceo(db):
    """Cria o usuário CEO (Thiago) no banco de teste."""
    usuario = UsuarioDB(
        email="thiago@teste.com",
        password_hash=hash_senha("SenhaForte@123"),
        nome="Thiago (Teste)",
        cargo="CEO",
        papeis=["ceo"],
        company_id="test-company",
        pode_aprovar=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_membro(db):
    """Cria um usuário membro comum no banco de teste."""
    usuario = UsuarioDB(
        email="membro@teste.com",
        password_hash=hash_senha("SenhaForte@123"),
        nome="Membro (Teste)",
        cargo="Desenvolvedor",
        papeis=["membro"],
        company_id="test-company",
        pode_aprovar=False,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def token_ceo(usuario_ceo):
    """Gera um token JWT válido para o CEO."""
    return criar_access_token(
        user_id=usuario_ceo.id,
        email=usuario_ceo.email,
        nome=usuario_ceo.nome,
        papeis=usuario_ceo.papeis or [],
        company_id=usuario_ceo.company_id or "",
    )


@pytest.fixture
def token_membro(usuario_membro):
    """Gera um token JWT válido para membro."""
    return criar_access_token(
        user_id=usuario_membro.id,
        email=usuario_membro.email,
        nome=usuario_membro.nome,
        papeis=usuario_membro.papeis or [],
        company_id=usuario_membro.company_id or "",
    )


# =====================================================================
# Cliente HTTP para testes de API
# =====================================================================

@pytest.fixture
def app():
    """Cria instância da app FastAPI para testes."""
    from api.main import app
    return app


@pytest.fixture
def client(app):
    """Cliente HTTP síncrono para testes de API."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
