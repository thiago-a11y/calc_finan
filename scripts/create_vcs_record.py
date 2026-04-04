"""Cria registro VCS para SyneriumX com token do GitHub."""
import os
from dotenv import load_dotenv

from core.vcs_service import criptografar_token
from database.models import ProjetoVCSDB
from database.session import SessionLocal

# Carregar .env
load_dotenv('/opt/synerium-factory/.env')

github_token = os.getenv('GITHUB_TOKEN', '')
if not github_token:
    print("GITHUB_TOKEN nao encontrado no .env")
    exit(1)

token_enc = criptografar_token(github_token)

db = SessionLocal()

# Verificar se ja existe
existente = db.query(ProjetoVCSDB).filter_by(projeto_id=1).first()
if existente:
    existente.api_token_encrypted = token_enc
    existente.repo_url = 'https://github.com/objetivasolucao/propostasap'
    existente.vcs_tipo = 'github'
    existente.branch_padrao = 'main'
    existente.ativo = True
    print('VCS atualizado')
else:
    vcs = ProjetoVCSDB(
        projeto_id=1,
        vcs_tipo='github',
        repo_url='https://github.com/objetivasolucao/propostasap',
        api_token_encrypted=token_enc,
        branch_padrao='main',
        ativo=True,
    )
    db.add(vcs)
    print('VCS criado')

db.commit()

# Verificar
vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=1).first()
print(f"VCS: tipo={vcs.vcs_tipo}, repo={vcs.repo_url}, ativo={vcs.ativo}")

db.close()
print("Done!")