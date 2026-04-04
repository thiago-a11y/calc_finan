#!/usr/bin/env python3
"""
Migração: Feature Flags para Master Control.

Cria as tabelas feature_flags e feature_flag_history se não existirem,
e faz seed das 6 flags iniciais.

Uso:
    python scripts/migrate_feature_flags.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from sqlalchemy import inspect

#_FLAGS_INICIAIS = [
#    {
#        "nome": "fork_subagent",
#        "descricao": "Fork implícito com herança de contexto",
#        "requer_restart": False,
#    },
#    {
#        "nome": "worktree_isolation",
#        "descricao": "Git worktree para isolamento de agentes",
#        "requer_restart": False,
#    },
#    {
#        "nome": "autonomous_mode",
#        "descricao": "Modo autônomo sem approval gates",
#        "requer_restart": False,
#    },
#    {
#        "nome": "brief_mode",
#        "descricao": "Forçar output via Brief tool",
#        "requer_restart": False,
#    },
#    {
#        "nome": "continuous_factory",
#        "descricao": "Modo contínuo 24/7",
#        "requer_restart": True,
#    },
#    {
#        "nome": "visible_execution",
#        "descricao": "Streaming ao vivo no Mission Control",
#        "requer_restart": False,
#    },
#]


def main():
    from database.session import SessionLocal, engine
    from database.models import Base, FeatureFlagDB

    print("[Migration] Inicializando banco de dados...")

    # Garantir que todas as tabelas existam
    Base.metadata.create_all(bind=engine)
    print("[Migration] Tabelas criadas/verificadas.")

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        tabelas = inspector.get_table_names()

        # Criar feature_flags se não existir
        if "feature_flags" not in tabelas:
            print("[Migration] Tabela 'feature_flags' não existe — será criada.")
            FeatureFlagDB.__table__.create(engine, checkfirst=False)
            print("[Migration] Tabela 'feature_flags' criada.")
        else:
            print("[Migration] Tabela 'feature_flags' já existe.")

        # Criar feature_flag_history se não existir
        if "feature_flag_history" not in tabelas:
            from database.models import FeatureFlagHistoryDB
            print("[Migration] Tabela 'feature_flag_history' não existe — será criada.")
            FeatureFlagHistoryDB.__table__.create(engine, checkfirst=False)
            print("[Migration] Tabela 'feature_flag_history' criada.")
        else:
            print("[Migration] Tabela 'feature_flag_history' já existe.")

        # Seed das flags iniciais (se não existirem)
        FLAGS_INICIAIS = [
            {
                "nome": "fork_subagent",
                "descricao": "Fork implícito com herança de contexto",
                "requer_restart": False,
            },
            {
                "nome": "worktree_isolation",
                "descricao": "Git worktree para isolamento de agentes",
                "requer_restart": False,
            },
            {
                "nome": "autonomous_mode",
                "descricao": "Modo autônomo sem approval gates",
                "requer_restart": False,
            },
            {
                "nome": "brief_mode",
                "descricao": "Forçar output via Brief tool",
                "requer_restart": False,
            },
            {
                "nome": "continuous_factory",
                "descricao": "Modo contínuo 24/7",
                "requer_restart": True,
            },
            {
                "nome": "visible_execution",
                "descricao": "Streaming ao vivo no Mission Control",
                "requer_restart": False,
            },
        ]

        flags_existentes = {f.nome for f in db.query(FeatureFlagDB).all()}

        for flag_data in FLAGS_INICIAIS:
            if flag_data["nome"] not in flags_existentes:
                flag = FeatureFlagDB(
                    nome=flag_data["nome"],
                    descricao=flag_data["descricao"],
                    requer_restart=flag_data["requer_restart"],
                    habilitado=False,
                    atualizado_por="system",
                    atualizado_em=datetime.now(timezone.utc),
                )
                db.add(flag)
                print(f"[Migration] Seed: flag '{flag_data['nome']}' adicionada.")
            else:
                print(f"[Migration] Flag '{flag_data['nome']}' já existe — pulando.")

        db.commit()
        print("[Migration] Migração concluída com sucesso!")

        # Mostrar estado final
        flags = db.query(FeatureFlagDB).all()
        print(f"\n[Migration] Feature Flags ({len(flags)} total):")
        for f in flags:
            status = "ON " if f.habilitado else "OFF"
            restart = " [RESTART]" if f.requer_restart else ""
            print(f"  [{status}] {f.nome}{restart} — {f.descricao}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
