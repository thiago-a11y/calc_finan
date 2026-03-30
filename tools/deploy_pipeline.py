"""
Deploy Pipeline — Build + Git + Deploy automático do SyneriumX.

Fluxo:
1. Aprovação da edição → arquivo é editado
2. npm run build → gera dist/
3. git add + commit → versionamento
4. Cria solicitação de DEPLOY (2ª aprovação)
5. Ao aprovar deploy → git push → GitHub Actions deploya

Segurança:
- Build e commit são automáticos (reversíveis)
- Push só acontece com 2ª aprovação do CEO/Diretor
- Tudo com logging detalhado
"""

import os
import subprocess
import logging
import json
from datetime import datetime

logger = logging.getLogger("synerium.deploy")

from tools.syneriumx_tools import SYNERIUMX_BASE
SYNERIUMX_PATH = SYNERIUMX_BASE  # Resolvido dinamicamente (banco → /opt/projetos/syneriumx → ~/propostasap)
PROPOSTAS_DIR = os.path.expanduser("~/synerium-factory/data/propostas_edicao")
DEPLOYS_DIR = os.path.expanduser("~/synerium-factory/data/deploys")


def executar_build() -> dict:
    """
    Roda npm run build no SyneriumX.
    Retorna dict com sucesso, saida e erro.
    """
    logger.info("[PIPELINE] Iniciando build do SyneriumX...")

    try:
        resultado = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=SYNERIUMX_PATH,
        )

        sucesso = resultado.returncode == 0
        logger.info(f"[PIPELINE] Build {'OK' if sucesso else 'FALHOU'}")

        return {
            "sucesso": sucesso,
            "saida": resultado.stdout[-2000:] if resultado.stdout else "",
            "erro": resultado.stderr[-1000:] if resultado.stderr else "",
        }
    except subprocess.TimeoutExpired:
        logger.error("[PIPELINE] Build timeout (120s)")
        return {"sucesso": False, "saida": "", "erro": "Build demorou mais de 120s"}
    except Exception as e:
        logger.error(f"[PIPELINE] Erro no build: {e}")
        return {"sucesso": False, "saida": "", "erro": str(e)}


def executar_git_commit(descricao: str, arquivo: str) -> dict:
    """
    Faz git add + commit no SyneriumX.
    """
    logger.info(f"[PIPELINE] Git commit: {descricao}")

    try:
        # Git add do arquivo modificado
        subprocess.run(
            ["git", "add", arquivo],
            capture_output=True, text=True, timeout=10,
            cwd=SYNERIUMX_PATH,
        )

        # Git commit
        msg = f"[Synerium Factory] {descricao}\n\nAprovado via dashboard pelo proprietário."
        resultado = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, timeout=15,
            cwd=SYNERIUMX_PATH,
        )

        sucesso = resultado.returncode == 0
        saida = resultado.stdout or resultado.stderr
        logger.info(f"[PIPELINE] Commit {'OK' if sucesso else 'FALHOU'}: {saida[:200]}")

        return {
            "sucesso": sucesso,
            "saida": saida[:500],
            "commit_hash": "",
        }
    except Exception as e:
        logger.error(f"[PIPELINE] Erro no commit: {e}")
        return {"sucesso": False, "saida": str(e), "commit_hash": ""}


def criar_solicitacao_deploy(proposta_id: str, descricao: str, arquivo: str,
                              build_ok: bool, commit_ok: bool) -> dict:
    """
    Cria solicitação de deploy (2ª aprovação) para o CEO aprovar o push.
    """
    os.makedirs(DEPLOYS_DIR, exist_ok=True)

    deploy_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    deploy = {
        "id": deploy_id,
        "proposta_id": proposta_id,
        "projeto": "SyneriumX",
        "descricao": descricao,
        "arquivo": arquivo,
        "build_ok": build_ok,
        "commit_ok": commit_ok,
        "status": "pendente",
        "criado_em": datetime.now().isoformat(),
    }

    deploy_path = os.path.join(DEPLOYS_DIR, f"{deploy_id}.json")
    with open(deploy_path, "w", encoding="utf-8") as f:
        json.dump(deploy, f, ensure_ascii=False, indent=2)

    logger.info(f"[PIPELINE] Solicitação de deploy criada: {deploy_id}")
    return deploy


def executar_git_push() -> dict:
    """
    Cria branch, push e PR no SyneriumX.
    A branch main está protegida — precisa de Pull Request.

    Fluxo:
    1. Cria branch: sf/proposta-{timestamp}
    2. Push da branch
    3. Cria PR via gh CLI (GitHub CLI)
    """
    logger.info("[PIPELINE] Criando branch e PR...")

    try:
        branch_nome = f"sf/proposta-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 1. Criar branch
        r1 = subprocess.run(
            ["git", "checkout", "-b", branch_nome],
            capture_output=True, text=True, timeout=15,
            cwd=SYNERIUMX_PATH,
        )
        if r1.returncode != 0:
            return {"sucesso": False, "saida": f"Erro criando branch: {r1.stderr}"}

        # 2. Push da branch
        r2 = subprocess.run(
            ["git", "push", "origin", branch_nome],
            capture_output=True, text=True, timeout=60,
            cwd=SYNERIUMX_PATH,
        )
        if r2.returncode != 0:
            # Voltar para main se push falhar
            subprocess.run(["git", "checkout", "main"], capture_output=True, cwd=SYNERIUMX_PATH)
            return {"sucesso": False, "saida": f"Erro no push: {r2.stderr}"}

        # 3. Criar PR via gh CLI
        r3 = subprocess.run(
            ["gh", "pr", "create",
             "--title", f"[Synerium Factory] {branch_nome.replace('sf/proposta-', '')}",
             "--body", "PR criado automaticamente pelo Synerium Factory após aprovação do CEO.",
             "--base", "main",
             "--head", branch_nome],
            capture_output=True, text=True, timeout=30,
            cwd=SYNERIUMX_PATH,
        )

        pr_url = r3.stdout.strip() if r3.returncode == 0 else ""

        # 4. Merge automático do PR (squash merge)
        merge_ok = False
        merge_saida = ""
        if pr_url and r3.returncode == 0:
            logger.info(f"[PIPELINE] Fazendo merge automático do PR...")
            r4 = subprocess.run(
                ["gh", "pr", "merge", branch_nome,
                 "--squash",
                 "--subject", f"[Synerium Factory] {branch_nome.replace('sf/proposta-', '')}",
                 "--body", "Merge automático após dupla aprovação no Synerium Factory.",
                 "--delete-branch"],
                capture_output=True, text=True, timeout=30,
                cwd=SYNERIUMX_PATH,
            )
            merge_ok = r4.returncode == 0
            merge_saida = r4.stdout or r4.stderr
            logger.info(f"[PIPELINE] Merge {'OK' if merge_ok else 'FALHOU'}: {merge_saida[:200]}")

        # 5. Voltar para main e atualizar
        subprocess.run(["git", "checkout", "main"], capture_output=True, cwd=SYNERIUMX_PATH)
        if merge_ok:
            subprocess.run(["git", "pull", "origin", "main"], capture_output=True, timeout=30, cwd=SYNERIUMX_PATH)

        sucesso = r2.returncode == 0 and merge_ok
        saida = (
            f"Branch: {branch_nome}\n"
            f"Push: OK\n"
            f"PR: {pr_url or 'Criação manual necessária'}\n"
            f"Merge: {'OK (squash)' if merge_ok else 'Pendente — faça merge manual no GitHub'}\n"
            f"{'GitHub Actions vai completar o deploy.' if merge_ok else ''}"
        )
        logger.info(f"[PIPELINE] Deploy completo: push=OK, PR={pr_url}, merge={'OK' if merge_ok else 'manual'}")

        return {
            "sucesso": sucesso,
            "saida": saida,
            "branch": branch_nome,
            "pr_url": pr_url,
            "merge_ok": merge_ok,
        }
    except Exception as e:
        # Garantir retorno para main
        subprocess.run(["git", "checkout", "main"], capture_output=True, cwd=SYNERIUMX_PATH)
        logger.error(f"[PIPELINE] Erro no deploy: {e}")
        return {"sucesso": False, "saida": str(e)}


def pipeline_pos_aprovacao(proposta: dict) -> dict:
    """
    Pipeline completo após aprovação de uma edição:
    1. Build
    2. Git commit
    3. Criar solicitação de deploy (2ª aprovação)
    """
    descricao = proposta.get("descricao", "Edição aprovada")
    arquivo = proposta.get("caminho", "")
    proposta_id = proposta.get("id", "")

    resultado = {
        "build": None,
        "commit": None,
        "deploy_solicitacao": None,
    }

    # 1. Build
    build = executar_build()
    resultado["build"] = build

    # 2. Git commit (mesmo se build falhar — para não perder a mudança)
    commit = executar_git_commit(descricao, arquivo)
    resultado["commit"] = commit

    # 3. Criar solicitação de deploy
    deploy = criar_solicitacao_deploy(
        proposta_id=proposta_id,
        descricao=descricao,
        arquivo=arquivo,
        build_ok=build["sucesso"],
        commit_ok=commit["sucesso"],
    )
    resultado["deploy_solicitacao"] = deploy

    logger.info(
        f"[PIPELINE] Pipeline concluído: build={'OK' if build['sucesso'] else 'FALHOU'}, "
        f"commit={'OK' if commit['sucesso'] else 'FALHOU'}, deploy=pendente"
    )

    return resultado
