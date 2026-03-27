"""
Sessão e engine do banco de dados SQLite.

Usa SQLAlchemy 2.0 com SQLite local.
O arquivo .db fica em data/synerium.db (mesmo diretório do ChromaDB).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///data/synerium.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite requer isso para FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency do FastAPI para obter uma sessão do banco.

    Uso nas rotas:
        @router.get("/usuarios")
        def listar(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
