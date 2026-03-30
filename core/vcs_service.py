"""
VCS Service — Serviço de Version Control para GitHub e GitBucket.

Abstrai operações de git (commit, push, teste de conexão) para
integração com o Code Studio e outros componentes do Synerium Factory.

Segurança:
- Tokens criptografados em repouso com Fernet
- Token nunca logado em texto claro
- Audit log em toda operação de commit/push
"""

import base64
import hashlib
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger("synerium.vcs")


# ============================================================
# Criptografia de tokens
# ============================================================

def _obter_chave_fernet() -> bytes:
    """Deriva chave Fernet do JWT_SECRET_KEY do ambiente."""
    # Garantir que .env esta carregado (systemd pode nao carregar automaticamente)
    from dotenv import load_dotenv
    load_dotenv()
    secret = os.getenv("JWT_SECRET_KEY", "synerium-factory-default-key-2026")
    # Fernet requer chave de 32 bytes base64-encoded
    chave_raw = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(chave_raw)


def criptografar_token(token: str) -> str:
    """Criptografa um token API com Fernet."""
    f = Fernet(_obter_chave_fernet())
    return f.encrypt(token.encode()).decode()


def descriptografar_token(token_enc: str) -> str:
    """Descriptografa um token API com Fernet."""
    f = Fernet(_obter_chave_fernet())
    return f.decrypt(token_enc.encode()).decode()


# ============================================================
# Data classes
# ============================================================

@dataclass
class ResultadoConexao:
    """Resultado de um teste de conexão com o repositório."""
    sucesso: bool
    mensagem: str
    repo_nome: str = ""
    branch_padrao: str = "main"


@dataclass
class ResultadoCommit:
    """Resultado de um commit + push."""
    sucesso: bool
    mensagem: str
    commit_hash: str = ""
    branch: str = ""


# ============================================================
# VCS Service
# ============================================================

class VCSService:
    """Serviço unificado de Version Control (GitHub + GitBucket)."""

    def __init__(self, vcs_tipo: str, repo_url: str, token: str, branch: str = "main"):
        self.vcs_tipo = vcs_tipo  # "github" ou "gitbucket"
        self.repo_url = repo_url.rstrip("/")
        self.token = token
        self.branch = branch

    # ----------------------------------------------------------
    # Testar conexão
    # ----------------------------------------------------------

    async def testar_conexao(self) -> ResultadoConexao:
        """Testa se o token e o repositório são válidos."""
        try:
            if self.vcs_tipo == "github":
                return await self._testar_github()
            elif self.vcs_tipo == "gitbucket":
                return await self._testar_gitbucket()
            else:
                return ResultadoConexao(False, f"Tipo VCS não suportado: {self.vcs_tipo}")
        except Exception as e:
            logger.error(f"[VCS] Erro ao testar conexão: {str(e)[:200]}")
            return ResultadoConexao(False, f"Erro: {str(e)[:200]}")

    async def _testar_github(self) -> ResultadoConexao:
        """Testa conexão com GitHub via API."""
        # Extrair owner/repo da URL
        owner_repo = self._extrair_owner_repo()
        if not owner_repo:
            return ResultadoConexao(False, "URL inválida. Formato esperado: https://github.com/owner/repo")

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner_repo}",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                },
            )

        if resp.status_code == 200:
            data = resp.json()
            return ResultadoConexao(
                sucesso=True,
                mensagem=f"Conectado ao repositório {data.get('full_name', owner_repo)}",
                repo_nome=data.get("full_name", owner_repo),
                branch_padrao=data.get("default_branch", "main"),
            )
        elif resp.status_code == 401:
            return ResultadoConexao(False, "Token inválido ou expirado")
        elif resp.status_code == 404:
            return ResultadoConexao(False, "Repositório não encontrado. Verifique a URL e as permissões do token.")
        else:
            return ResultadoConexao(False, f"Erro HTTP {resp.status_code}: {resp.text[:200]}")

    async def _testar_gitbucket(self) -> ResultadoConexao:
        """Testa conexão com GitBucket via API."""
        # GitBucket usa API compatível com GitHub
        owner_repo = self._extrair_owner_repo()
        if not owner_repo:
            return ResultadoConexao(False, "URL inválida. Formato: http://host/git/owner/repo")

        # Extrair base URL do GitBucket
        base_url = self.repo_url.split("/git/")[0] if "/git/" in self.repo_url else self.repo_url.rsplit("/", 2)[0]

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{base_url}/api/v3/repos/{owner_repo}",
                headers={"Authorization": f"token {self.token}"},
            )

        if resp.status_code == 200:
            data = resp.json()
            return ResultadoConexao(
                sucesso=True,
                mensagem=f"Conectado ao GitBucket: {data.get('full_name', owner_repo)}",
                repo_nome=data.get("full_name", owner_repo),
                branch_padrao=data.get("default_branch", "main"),
            )
        elif resp.status_code == 401:
            return ResultadoConexao(False, "Token GitBucket inválido")
        elif resp.status_code == 404:
            return ResultadoConexao(False, "Repositório GitBucket não encontrado")
        else:
            return ResultadoConexao(False, f"Erro HTTP {resp.status_code}")

    # ----------------------------------------------------------
    # Commit e Push
    # ----------------------------------------------------------

    def commit_e_push(
        self,
        caminho_projeto: str,
        arquivos: list[str],
        mensagem_commit: str,
        autor_nome: str = "Synerium Factory",
        autor_email: str = "factory@objetivasolucao.com.br",
    ) -> ResultadoCommit:
        """Faz git add, commit e push dos arquivos alterados."""
        cwd = caminho_projeto
        remote_original = None

        try:
            # Verificar se é um repositório git
            result = self._run_git(["rev-parse", "--is-inside-work-tree"], cwd)
            if result.returncode != 0:
                return ResultadoCommit(False, "Diretório não é um repositório git")

            # Salvar remote original ANTES de alterar
            remote_result = self._run_git(["remote", "get-url", "origin"], cwd)
            if remote_result.returncode == 0:
                remote_original = remote_result.stdout.decode().strip()

            # Configurar remote com token (temporário — será restaurado no finally)
            remote_url = self._construir_remote_url()
            if remote_url:
                self._run_git(["remote", "set-url", "origin", remote_url], cwd)

            # Git add
            for arquivo in arquivos:
                self._run_git(["add", arquivo], cwd)

            # Git commit
            result = self._run_git(
                [
                    "-c", f"user.name={autor_nome}",
                    "-c", f"user.email={autor_email}",
                    "commit", "-m", mensagem_commit,
                ],
                cwd,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                if "nothing to commit" in stderr:
                    return ResultadoCommit(True, "Nenhuma alteração para commitar", branch=self.branch)
                return ResultadoCommit(False, f"Erro no commit: {stderr[:200]}")

            # Extrair hash do commit
            hash_result = self._run_git(["rev-parse", "--short", "HEAD"], cwd)
            commit_hash = hash_result.stdout.decode().strip() if hash_result.returncode == 0 else "?"

            # Git push
            push_result = self._run_git(["push", "origin", self.branch], cwd)
            if push_result.returncode != 0:
                stderr = push_result.stderr.decode("utf-8", errors="replace")
                # Tentar com --set-upstream
                push_result = self._run_git(["push", "-u", "origin", self.branch], cwd)
                if push_result.returncode != 0:
                    return ResultadoCommit(
                        False,
                        f"Commit {commit_hash} criado mas push falhou: {stderr[:200]}",
                        commit_hash=commit_hash,
                        branch=self.branch,
                    )

            logger.info(f"[VCS] Commit {commit_hash} + push para {self.branch} OK")
            return ResultadoCommit(
                sucesso=True,
                mensagem=f"Commit {commit_hash} enviado para {self.branch}",
                commit_hash=commit_hash,
                branch=self.branch,
            )

        except Exception as e:
            logger.error(f"[VCS] Erro em commit_e_push: {str(e)[:300]}")
            return ResultadoCommit(False, f"Erro: {str(e)[:200]}")

        finally:
            # SEMPRE restaurar o remote original para nao corromper o repositorio
            if remote_original:
                try:
                    self._run_git(["remote", "set-url", "origin", remote_original], cwd)
                    logger.debug(f"[VCS] Remote restaurado para URL original")
                except Exception:
                    logger.warning(f"[VCS] Falha ao restaurar remote original")

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _extrair_owner_repo(self) -> Optional[str]:
        """Extrai owner/repo da URL do repositório."""
        url = self.repo_url.rstrip("/").rstrip(".git")

        # GitHub: https://github.com/owner/repo
        if "github.com" in url:
            partes = url.split("github.com/")
            if len(partes) == 2:
                return partes[1]

        # GitBucket: http://host/git/owner/repo
        if "/git/" in url:
            partes = url.split("/git/")
            if len(partes) == 2:
                return partes[1]

        # Genérico: últimas duas partes do path
        partes = url.rstrip("/").split("/")
        if len(partes) >= 2:
            return f"{partes[-2]}/{partes[-1]}"

        return None

    def _construir_remote_url(self) -> Optional[str]:
        """Constrói URL do remote com token embutido para push."""
        if self.vcs_tipo == "github":
            owner_repo = self._extrair_owner_repo()
            if owner_repo:
                return f"https://x-access-token:{self.token}@github.com/{owner_repo}.git"

        elif self.vcs_tipo == "gitbucket":
            # GitBucket usa basic auth
            owner_repo = self._extrair_owner_repo()
            base = self.repo_url.split("/git/")[0] if "/git/" in self.repo_url else ""
            if base and owner_repo:
                host = base.replace("https://", "").replace("http://", "")
                return f"https://token:{self.token}@{host}/git/{owner_repo}.git"

        return None

    # ----------------------------------------------------------
    # Push branch + Criar PR
    # ----------------------------------------------------------

    def push_branch(
        self,
        caminho_projeto: str,
        branch_nome: str,
    ) -> ResultadoCommit:
        """Faz push de uma branch para o remote (com token temporario)."""
        cwd = caminho_projeto
        remote_original = None

        try:
            remote_result = self._run_git(["remote", "get-url", "origin"], cwd)
            if remote_result.returncode == 0:
                remote_original = remote_result.stdout.decode().strip()

            remote_url = self._construir_remote_url()
            if remote_url:
                self._run_git(["remote", "set-url", "origin", remote_url], cwd)

            push_result = self._run_git(["push", "-u", "origin", branch_nome], cwd)
            if push_result.returncode != 0:
                stderr = push_result.stderr.decode("utf-8", errors="replace")
                return ResultadoCommit(False, f"Push falhou: {stderr[:200]}", branch=branch_nome)

            logger.info(f"[VCS] Push branch {branch_nome} OK")
            return ResultadoCommit(True, f"Branch {branch_nome} enviada", branch=branch_nome)

        except Exception as e:
            return ResultadoCommit(False, f"Erro: {str(e)[:200]}", branch=branch_nome)
        finally:
            if remote_original:
                try:
                    self._run_git(["remote", "set-url", "origin", remote_original], cwd)
                except Exception:
                    pass

    async def criar_pr(
        self,
        titulo: str,
        descricao: str,
        branch_origem: str,
        branch_destino: str = "main",
    ) -> dict:
        """Cria Pull Request no GitHub ou GitBucket via API."""
        owner_repo = self._extrair_owner_repo()
        if not owner_repo:
            return {"sucesso": False, "mensagem": "Nao foi possivel extrair owner/repo da URL"}

        try:
            if self.vcs_tipo == "github":
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"https://api.github.com/repos/{owner_repo}/pulls",
                        headers={
                            "Authorization": f"Bearer {self.token}",
                            "Accept": "application/vnd.github+json",
                        },
                        json={
                            "title": titulo,
                            "body": descricao,
                            "head": branch_origem,
                            "base": branch_destino,
                        },
                    )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "sucesso": True,
                        "pr_url": data.get("html_url", ""),
                        "pr_number": data.get("number", 0),
                        "mensagem": f"PR #{data.get('number')} criada",
                    }
                else:
                    return {
                        "sucesso": False,
                        "mensagem": f"GitHub API {resp.status_code}: {resp.text[:200]}",
                    }

            elif self.vcs_tipo == "gitbucket":
                base_url = self.repo_url.split("/git/")[0] if "/git/" in self.repo_url else ""
                if not base_url:
                    return {"sucesso": False, "mensagem": "URL GitBucket invalida"}
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{base_url}/api/v3/repos/{owner_repo}/pulls",
                        headers={"Authorization": f"token {self.token}"},
                        json={
                            "title": titulo,
                            "body": descricao,
                            "head": branch_origem,
                            "base": branch_destino,
                        },
                    )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "sucesso": True,
                        "pr_url": data.get("html_url", ""),
                        "pr_number": data.get("number", 0),
                        "mensagem": f"PR #{data.get('number')} criada",
                    }
                else:
                    return {"sucesso": False, "mensagem": f"GitBucket {resp.status_code}"}

            return {"sucesso": False, "mensagem": f"VCS tipo nao suportado: {self.vcs_tipo}"}

        except Exception as e:
            logger.error(f"[VCS] Erro ao criar PR: {e}")
            return {"sucesso": False, "mensagem": str(e)[:200]}

    @staticmethod
    def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
        """Executa comando git via subprocess."""
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            timeout=30,
        )
