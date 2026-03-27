#!/usr/bin/env python3
"""
Bootstrap AWS — Script de inicialização pós-deploy.

Roda uma única vez (idempotente) para configurar tudo:
1. Criar tabelas do banco
2. Seed de usuários com permissões
3. Corrigir paths de vaults Obsidian para o servidor
4. Indexar vaults no RAG/ChromaDB
5. Verificar conexões externas (SES, LiveKit)
6. Criar projeto SyneriumX se não existir

Uso:
    cd /opt/synerium-factory
    source .venv/bin/activate
    python -m scripts.bootstrap_aws
"""

import os
import sys
import logging

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BOOTSTRAP] %(message)s",
)
log = logging.getLogger("bootstrap")


def step(num, title):
    """Imprime header de etapa."""
    print(f"\n{'='*60}")
    print(f"  [{num}/7] {title}")
    print(f"{'='*60}\n")


def step1_banco():
    """Criar tabelas do banco."""
    step(1, "BANCO DE DADOS")

    from database.models import Base
    from database.session import engine

    Base.metadata.create_all(bind=engine)
    log.info("Tabelas criadas/verificadas com sucesso.")


def step2_usuarios():
    """Seed de usuários com permissões corretas."""
    step(2, "USUÁRIOS E PERMISSÕES")

    from database.session import SessionLocal
    from database.models import UsuarioDB
    from api.security import hash_senha

    db = SessionLocal()

    usuarios_seed = [
        {
            "email": "thiago@objetivasolucao.com.br",
            "nome": "Thiago",
            "cargo": "CEO",
            "papeis": ["ceo"],
            "pode_aprovar": True,
        },
        {
            "email": "jonatas@objetivasolucao.com.br",
            "nome": "Jonatas",
            "cargo": "Diretor Técnico e Operations Lead",
            "papeis": ["diretor_tecnico", "operations_lead"],
            "pode_aprovar": True,
        },
        {
            "email": "rhammon@objetivasolucao.com.br",
            "nome": "Rhammon Eller",
            "cargo": "Desenvolvedor",
            "papeis": ["desenvolvedor"],
            "pode_aprovar": False,
        },
        {
            "email": "marcos.judsson@objetivasolucao.com.br",
            "nome": "Marcos Judsson",
            "cargo": "Líder Técnico",
            "papeis": ["lider", "desenvolvedor"],
            "pode_aprovar": False,
        },
    ]

    senha_padrao = hash_senha("SyneriumFactory@2026")

    for u_data in usuarios_seed:
        existente = db.query(UsuarioDB).filter_by(email=u_data["email"]).first()
        if existente:
            # Atualizar papéis e cargo se necessário
            existente.papeis = u_data["papeis"]
            existente.cargo = u_data["cargo"]
            existente.pode_aprovar = u_data["pode_aprovar"]
            log.info(f"  Atualizado: {u_data['nome']} ({u_data['email']})")
        else:
            novo = UsuarioDB(
                email=u_data["email"],
                nome=u_data["nome"],
                cargo=u_data["cargo"],
                papeis=u_data["papeis"],
                pode_aprovar=u_data["pode_aprovar"],
                password_hash=senha_padrao,
                company_id=1,
            )
            db.add(novo)
            log.info(f"  Criado: {u_data['nome']} ({u_data['email']})")

    db.commit()
    total = db.query(UsuarioDB).count()
    log.info(f"Total de usuários: {total}")
    db.close()


def step3_vaults():
    """Corrigir paths dos vaults e copiar se necessário."""
    step(3, "VAULTS OBSIDIAN")

    vault_dir = "/opt/synerium-factory/data/vaults"
    os.makedirs(vault_dir, exist_ok=True)

    vault_sx = os.path.join(vault_dir, "SyneriumX-notes")
    vault_sf = os.path.join(vault_dir, "SyneriumFactory-notes")

    # Verificar se vaults existem
    if os.path.isdir(vault_sx):
        n = len([f for f in os.listdir(vault_sx) if f.endswith('.md')])
        log.info(f"SyneriumX-notes: {n} arquivos .md")
    else:
        os.makedirs(vault_sx, exist_ok=True)
        log.warning(f"SyneriumX-notes VAZIO — copie com:")
        log.warning(f"  rsync -avz ~/Documents/SyneriumX-notes/ ubuntu@3.223.92.171:{vault_sx}/")

    if os.path.isdir(vault_sf):
        n = len([f for f in os.listdir(vault_sf) if f.endswith('.md')])
        log.info(f"SyneriumFactory-notes: {n} arquivos .md")
    else:
        os.makedirs(vault_sf, exist_ok=True)
        log.warning(f"SyneriumFactory-notes VAZIO — copie com:")
        log.warning(f"  rsync -avz ~/Documents/SyneriumFactory-notes/ ubuntu@3.223.92.171:{vault_sf}/")

    # Atualizar .env com paths corretos
    env_path = "/opt/synerium-factory/.env"
    with open(env_path, "r") as f:
        env_content = f.read()

    # Substituir paths do Mac por paths do servidor
    env_content = env_content.replace(
        "/Users/thiagoxavier/Documents/SyneriumX-notes",
        vault_sx,
    )
    env_content = env_content.replace(
        "/Users/thiagoxavier/Documents/SyneriumFactory-notes",
        vault_sf,
    )

    with open(env_path, "w") as f:
        f.write(env_content)

    log.info("Paths do .env atualizados para o servidor.")


def step4_rag():
    """Indexar vaults no ChromaDB."""
    step(4, "INDEXAR RAG / CHROMADB")

    from config.settings import SyneriumSettings
    settings = SyneriumSettings()

    vault_dir = "/opt/synerium-factory/data/vaults"
    vaults = {}
    for nome, var in [("syneriumx", "SyneriumX-notes"), ("factory", "SyneriumFactory-notes")]:
        path = os.path.join(vault_dir, var)
        if os.path.isdir(path) and len(os.listdir(path)) > 0:
            vaults[nome] = path
            log.info(f"Vault {nome}: {path}")
        else:
            log.warning(f"Vault {nome}: VAZIO ou não existe em {path}")

    if not vaults:
        log.warning("Nenhum vault com dados — pulando indexação.")
        log.warning("Copie os vaults e rode o bootstrap novamente.")
        return

    try:
        from rag import RAGConfig, RAGIndexer

        config = RAGConfig(
            vaults=vaults,
            persist_directory="data/chromadb",
        )
        indexer = RAGIndexer(config)
        indexer.indexar_todos(company_id="synerium")

        stats = indexer.store.contar_chunks(company_id="synerium")
        log.info(f"RAG indexado: {stats}")
    except Exception as e:
        log.error(f"Erro na indexação: {e}")


def step5_projeto():
    """Criar projeto SyneriumX se não existir."""
    step(5, "PROJETO SYNERIUMX")

    from database.session import SessionLocal
    from database.models import ProjetoDB

    db = SessionLocal()

    existente = db.query(ProjetoDB).filter_by(nome="SyneriumX").first()
    if existente:
        log.info(f"Projeto SyneriumX já existe (ID: {existente.id})")
    else:
        projeto = ProjetoDB(
            nome="SyneriumX",
            descricao="CRM completo da Objetiva Solução",
            stack="PHP 7.4 + React 18 + MySQL",
            repositorio="https://github.com/SineriumX/syneriumx",
            caminho_local="/opt/synerium-factory",  # No servidor
            proprietario_email="thiago@objetivasolucao.com.br",
            lider_email="jonatas@objetivasolucao.com.br",
            company_id=1,
        )
        db.add(projeto)
        db.commit()
        log.info("Projeto SyneriumX criado.")

    db.close()


def step6_verificar():
    """Verificar conexões externas."""
    step(6, "VERIFICAR CONEXÕES")

    # SES
    try:
        import boto3
        ses = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
        identities = ses.list_identities(IdentityType="Domain")
        log.info(f"AWS SES: OK — domínios: {identities.get('Identities', [])}")
    except Exception as e:
        log.error(f"AWS SES: FALHA — {e}")

    # LiveKit
    lk_url = os.getenv("LIVEKIT_URL", "")
    if lk_url:
        log.info(f"LiveKit: Configurado — {lk_url}")
    else:
        log.warning("LiveKit: NÃO configurado")

    # Anthropic
    ak = os.getenv("ANTHROPIC_API_KEY", "")
    log.info(f"Anthropic: {'OK' if ak else 'FALTA'}")

    # OpenAI (embeddings)
    ok = os.getenv("OPENAI_API_KEY", "")
    log.info(f"OpenAI: {'OK' if ok else 'FALTA'}")


def step7_diretorios():
    """Garantir que todos os diretórios existem."""
    step(7, "DIRETÓRIOS")

    dirs = [
        "data/chromadb",
        "data/uploads/chat",
        "data/propostas_edicao",
        "data/deploys",
        "data/vaults",
        "logs",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        log.info(f"  {d}/")

    log.info("Todos os diretórios verificados.")


def main():
    print("\n" + "=" * 60)
    print("  SYNERIUM FACTORY — Bootstrap AWS")
    print("  Inicialização pós-deploy")
    print("=" * 60)

    step1_banco()
    step2_usuarios()
    step3_vaults()
    step4_rag()
    step5_projeto()
    step6_verificar()
    step7_diretorios()

    print("\n" + "=" * 60)
    print("  BOOTSTRAP CONCLUÍDO!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Copiar vaults Obsidian (se não foram copiados)")
    print("2. Rodar bootstrap novamente para indexar RAG")
    print("3. Reiniciar API: sudo systemctl restart synerium-factory")
    print("4. Acessar: https://synerium-factory.objetivasolucao.com.br")
    print()


if __name__ == "__main__":
    main()
