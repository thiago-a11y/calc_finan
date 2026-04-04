"""Fix: Adiciona coluna regras_aprovacao à tabela projetos."""
import sqlite3
import json

DB_PATH = "/opt/synerium-factory/data/synerium.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check if column exists
cur.execute("PRAGMA table_info(projetos)")
columns = [col[1] for col in cur.fetchall()]

if "regras_aprovacao" not in columns:
    default_value = json.dumps({
        "pequena": {"aprovador": "lider_tecnico", "descricao": "Bug fix, UI tweak"},
        "grande": {"aprovador": "proprietario", "descricao": "Feature, arquitetura"},
        "critica": {"aprovador": "ambos", "descricao": "Deploy, banco, seguranca"},
    })

    cur.execute(f'ALTER TABLE projetos ADD COLUMN regras_aprovacao JSON DEFAULT \'{default_value}\'')
    conn.commit()
    print(f"Coluna regras_aprovacao adicionada à tabela projetos")
else:
    print("Coluna regras_aprovacao já existe")

conn.close()