"""Fix: Atualiza caminho do projeto SyneriumX para o path correto no servidor."""
import sqlite3

DB_PATH = "/opt/synerium-factory/data/synerium.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Atualizar caminho do SyneriumX
cur.execute("""
    UPDATE projetos
    SET caminho = '/opt/projetos/syneriumx'
    WHERE nome = 'SyneriumX' AND ativo = 1
""")
conn.commit()

# Verificar
cur.execute("SELECT id, nome, caminho, repositorio FROM projetos WHERE ativo = 1")
for row in cur.fetchall():
    print(f"ID={row[0]} Nome={row[1]} Caminho={row[2]} Repo={row[3]}")

conn.close()
print("Done!")