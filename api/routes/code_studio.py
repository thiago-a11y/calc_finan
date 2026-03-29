"""
Code Studio — Editor de codigo integrado ao Synerium Factory (multi-projeto).

Endpoints:
- GET /api/code-studio/tree — arvore de arquivos do projeto
- GET /api/code-studio/file — ler conteudo de um arquivo
- POST /api/code-studio/file — salvar arquivo (com backup e audit log)
- POST /api/code-studio/analyze — analise de codigo via Smart Router
- POST /api/code-studio/apply-action — aplicar acao IA + VCS auto-commit

Seguranca:
- Path traversal bloqueado via Path.resolve() + is_relative_to()
- Escrita restrita a papeis: CEO, operations_lead, dev, diretor_tecnico
- Binarios bloqueados para leitura
- Audit log LGPD em todas as escritas
- Multi-projeto: cada projeto tem seu caminho base isolado
"""

import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import UsuarioDB, AuditLogDB, ProjetoDB, ProjetoVCSDB

logger = logging.getLogger("synerium.code_studio")

router = APIRouter(prefix="/api/code-studio", tags=["Code Studio"])

# ============================================================
# Configuracao de seguranca
# ============================================================

# Base padrao (Synerium Factory) — fallback quando nenhum projeto e selecionado
if os.path.exists("/opt/synerium-factory"):
    DEFAULT_BASE = Path("/opt/synerium-factory")
else:
    DEFAULT_BASE = Path(__file__).parent.parent.parent.resolve()

# Diretorio base para projetos clonados automaticamente do VCS
PROJETOS_BASE = Path(os.getenv("PROJETOS_BASE", "/opt/projetos"))


# Diretorios ignorados na arvore
IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".claude", ".next", ".cache", "dist",
}

# Extensoes bloqueadas para leitura (binarios)
BLOCKED_EXTENSIONS = {
    ".pyc", ".pyo", ".db", ".sqlite", ".sqlite3",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac",
    # Documentos binarios (Office, PDF) — travam o editor de texto
    ".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
    ".odt", ".ods", ".odp", ".rtf",
    # Imagens e outros
    ".bmp", ".tiff", ".tif", ".psd", ".ai", ".eps",
    ".bin", ".dat", ".lock",
}

# Mapeamento extensao → linguagem CodeMirror
LANG_MAP = {
    ".py": "python", ".pyx": "python", ".pyi": "python",
    ".tsx": "typescript", ".ts": "typescript",
    ".jsx": "javascript", ".js": "javascript", ".mjs": "javascript",
    ".json": "json", ".jsonl": "json",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "css",
    ".md": "markdown", ".mdx": "markdown",
    ".sql": "sql",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".txt": "text", ".log": "text", ".env": "text",
    ".ini": "text", ".cfg": "text", ".conf": "text",
    ".rs": "rust", ".go": "go", ".rb": "ruby",
    ".php": "php", ".java": "java", ".c": "cpp", ".cpp": "cpp", ".h": "cpp",
    ".dockerfile": "text", ".gitignore": "text",
}

# Papeis que podem escrever arquivos
PAPEIS_ESCRITA = {"ceo", "operations_lead", "dev", "desenvolvedor", "diretor_tecnico"}


# ============================================================
# Helpers
# ============================================================

def _slug_projeto(nome: str) -> str:
    """Gera slug seguro a partir do nome do projeto (ex: 'SyneriumX' → 'syneriumx')."""
    slug = re.sub(r'[^a-zA-Z0-9_-]', '', nome.replace(' ', '-')).lower().strip('-')
    return slug or 'projeto'


def _clonar_projeto_vcs(projeto: ProjetoDB, db: Session) -> Path | None:
    """
    Tenta clonar o repositorio do projeto via VCS (GitHub/GitBucket).

    Se o projeto tem VCS configurado, clona para PROJETOS_BASE/{slug}/.
    Atualiza o campo 'caminho' no banco com o novo diretorio.
    Retorna o Path do diretorio clonado ou None se falhar.
    """
    from core.vcs_service import descriptografar_token

    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=projeto.id, ativo=True).first()
    if not vcs:
        return None

    try:
        token = descriptografar_token(vcs.api_token_encrypted)
    except Exception as e:
        logger.error(f"[CodeStudio] Erro ao descriptografar token VCS do projeto {projeto.nome}: {e}")
        return None

    # Construir URL autenticada para clone
    repo_url = vcs.repo_url.rstrip("/")
    owner_repo = None

    if "github.com" in repo_url:
        url_limpa = repo_url.rstrip("/").rstrip(".git")
        partes = url_limpa.split("github.com/")
        if len(partes) == 2:
            owner_repo = partes[1]
        clone_url = f"https://x-access-token:{token}@github.com/{owner_repo}.git" if owner_repo else None
    elif "/git/" in repo_url:
        url_limpa = repo_url.rstrip("/").rstrip(".git")
        partes = url_limpa.split("/git/")
        if len(partes) == 2:
            owner_repo = partes[1]
        base_host = repo_url.split("/git/")[0].replace("https://", "").replace("http://", "")
        clone_url = f"https://token:{token}@{base_host}/git/{owner_repo}.git" if owner_repo else None
    else:
        logger.warning(f"[CodeStudio] URL VCS nao reconhecida: {repo_url}")
        return None

    if not clone_url:
        return None

    # Diretorio destino
    slug = _slug_projeto(projeto.nome)
    destino = PROJETOS_BASE / slug

    # Se ja existe e e um repo git, apenas fazer pull
    if destino.is_dir() and (destino / ".git").is_dir():
        logger.info(f"[CodeStudio] Projeto {projeto.nome} ja clonado em {destino}, fazendo git pull...")
        try:
            subprocess.run(
                ["git", "pull", "origin", vcs.branch_padrao or "main"],
                cwd=str(destino),
                capture_output=True,
                timeout=60,
            )
        except Exception as e:
            logger.warning(f"[CodeStudio] Erro no git pull: {e}")
        # Atualizar caminho no banco
        projeto.caminho = str(destino)
        db.commit()
        return destino

    # Criar diretorio base se nao existir
    PROJETOS_BASE.mkdir(parents=True, exist_ok=True)

    # Clonar repositorio
    logger.info(f"[CodeStudio] Clonando {projeto.nome} de {repo_url} para {destino}...")
    branch = vcs.branch_padrao or "main"

    try:
        result = subprocess.run(
            ["git", "clone", "--branch", branch, "--single-branch", clone_url, str(destino)],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            # Tentar sem --branch (repo pode ter branch diferente)
            logger.warning(f"[CodeStudio] Clone com --branch {branch} falhou, tentando sem: {stderr[:200]}")
            result = subprocess.run(
                ["git", "clone", clone_url, str(destino)],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                logger.error(f"[CodeStudio] Falha no clone: {stderr[:300]}")
                return None

        # Atualizar caminho no banco
        projeto.caminho = str(destino)
        db.commit()

        logger.info(f"[CodeStudio] Projeto {projeto.nome} clonado com sucesso em {destino}")
        return destino

    except subprocess.TimeoutExpired:
        logger.error(f"[CodeStudio] Timeout ao clonar {projeto.nome}")
        # Limpar diretorio parcial
        if destino.exists():
            shutil.rmtree(destino, ignore_errors=True)
        return None
    except Exception as e:
        logger.error(f"[CodeStudio] Erro ao clonar {projeto.nome}: {e}")
        if destino.exists():
            shutil.rmtree(destino, ignore_errors=True)
        return None


def _obter_base_projeto(project_id: int, db: Session, usuario: UsuarioDB) -> tuple[Path, int | None, ProjetoDB | None]:
    """
    Resolve a base do projeto pelo ID.

    Retorna (base_path, projeto_id_real, projeto_obj).
    Se project_id=0 ou None: retorna DEFAULT_BASE (Synerium Factory).

    Se o diretorio nao existe mas o projeto tem VCS configurado,
    tenta clonar automaticamente do repositorio.
    """
    if not project_id:
        return DEFAULT_BASE, None, None

    projeto = db.query(ProjetoDB).filter_by(id=project_id, ativo=True).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")

    # Verificar que o usuario tem acesso (mesma company)
    if projeto.company_id != usuario.company_id:
        raise HTTPException(status_code=403, detail="Sem acesso a este projeto.")

    caminho = projeto.caminho
    if not caminho or not caminho.strip():
        # Sem caminho — tentar auto-clone via VCS
        base_clonada = _clonar_projeto_vcs(projeto, db)
        if base_clonada:
            return base_clonada, projeto.id, projeto
        raise HTTPException(
            status_code=400,
            detail=f"Projeto '{projeto.nome}' nao tem caminho configurado e nao possui VCS para clone automatico. Configure em Projetos.",
        )

    base = Path(caminho.strip()).resolve()
    if not base.is_dir():
        # Diretorio nao existe — tentar auto-clone via VCS
        base_clonada = _clonar_projeto_vcs(projeto, db)
        if base_clonada:
            return base_clonada, projeto.id, projeto
        raise HTTPException(
            status_code=400,
            detail=f"Diretorio do projeto nao encontrado: {caminho}. Configure VCS para clone automatico.",
        )

    return base, projeto.id, projeto


def _validar_caminho(caminho_relativo: str, base: Path = None) -> Path:
    """Valida e resolve caminho, bloqueando traversal."""
    if base is None:
        base = DEFAULT_BASE

    caminho_relativo = caminho_relativo.strip().lstrip("/")
    if not caminho_relativo:
        raise HTTPException(status_code=400, detail="Caminho nao informado.")

    caminho = (base / caminho_relativo).resolve()

    if not caminho.is_relative_to(base):
        logger.warning(f"Path traversal bloqueado: {caminho_relativo}")
        raise HTTPException(status_code=403, detail="Acesso negado: caminho fora do projeto.")

    return caminho


def _verificar_escrita(usuario: UsuarioDB):
    """Verifica se o usuario tem permissao de escrita."""
    papeis = set(usuario.papeis or [])
    if not papeis.intersection(PAPEIS_ESCRITA):
        raise HTTPException(status_code=403, detail="Sem permissao para editar arquivos.")


def _detectar_linguagem(extensao: str) -> str:
    """Retorna a linguagem do CodeMirror baseada na extensao."""
    return LANG_MAP.get(extensao.lower(), "text")


def _listar_diretorio(caminho: Path, base: Path, profundidade: int = 0, max_prof: int = 4) -> list:
    """Lista recursivamente os arquivos/pastas de um diretorio."""
    if profundidade > max_prof:
        return []

    resultado = []

    try:
        itens = sorted(caminho.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return []

    for item in itens:
        nome = item.name

        # Ignorar diretorios bloqueados
        if item.is_dir() and nome in IGNORED_DIRS:
            continue

        # Ignorar arquivos ocultos (exceto .env)
        if nome.startswith(".") and nome != ".env":
            continue

        caminho_rel = str(item.relative_to(base))

        if item.is_dir():
            filhos = _listar_diretorio(item, base, profundidade + 1, max_prof)
            resultado.append({
                "nome": nome,
                "caminho": caminho_rel,
                "tipo": "pasta",
                "filhos": filhos,
            })
        else:
            ext = item.suffix.lower()
            tamanho = item.stat().st_size if item.exists() else 0
            resultado.append({
                "nome": nome,
                "caminho": caminho_rel,
                "tipo": "arquivo",
                "extensao": ext,
                "tamanho": tamanho,
                "linguagem": _detectar_linguagem(ext),
            })

    return resultado


# ============================================================
# Schemas
# ============================================================

class SalvarArquivoRequest(BaseModel):
    caminho: str
    conteudo: str
    project_id: int = 0


class AnalisarCodigoRequest(BaseModel):
    caminho: str
    conteudo: str
    instrucao: str
    modelo: str = "auto"
    project_id: int = 0


class AplicarAcaoRequest(BaseModel):
    """Aplica codigo gerado pelo agente no arquivo original ou cria novo arquivo."""
    caminho_destino: str
    conteudo_novo: str
    tipo_acao: str = "substituir"  # substituir | criar
    project_id: int = 0


# ============================================================
# Endpoints
# ============================================================

@router.get("/tree")
async def listar_arvore(
    path: str = Query("", description="Subdiretorio relativo"),
    project_id: int = Query(0, description="ID do projeto (0 = Synerium Factory)"),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna a arvore de arquivos do projeto."""
    base, proj_id, projeto = _obter_base_projeto(project_id, db, usuario)

    if path:
        dir_base = _validar_caminho(path, base)
        if not dir_base.is_dir():
            raise HTTPException(status_code=404, detail="Diretorio nao encontrado.")
    else:
        dir_base = base

    arvore = _listar_diretorio(dir_base, base)
    return {
        "arvore": arvore,
        "base": str(base),
        "project_id": proj_id or 0,
        "projeto_nome": projeto.nome if projeto else "Synerium Factory",
    }


@router.get("/file")
async def ler_arquivo(
    path: str = Query(..., description="Caminho relativo do arquivo"),
    project_id: int = Query(0, description="ID do projeto"),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Le o conteudo de um arquivo do projeto."""
    base, proj_id, _ = _obter_base_projeto(project_id, db, usuario)
    caminho = _validar_caminho(path, base)

    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")

    ext = caminho.suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Tipo de arquivo nao suportado: {ext}")

    tamanho = caminho.stat().st_size
    if tamanho > 1_048_576:  # 1MB
        raise HTTPException(status_code=413, detail="Arquivo muito grande (maximo 1MB).")

    try:
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")

    # Verificar permissao de escrita
    papeis = set(usuario.papeis or [])
    editavel = bool(papeis.intersection(PAPEIS_ESCRITA))

    return {
        "caminho": path,
        "conteudo": conteudo,
        "linguagem": _detectar_linguagem(ext),
        "tamanho": tamanho,
        "editavel": editavel,
    }


@router.post("/file")
async def salvar_arquivo(
    dados: SalvarArquivoRequest,
    request: Request,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Salva o conteudo de um arquivo (com backup e audit log)."""
    _verificar_escrita(usuario)

    base, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
    caminho = _validar_caminho(dados.caminho, base)

    # Verificar extensao
    ext = caminho.suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Nao e permitido editar arquivos {ext}.")

    # Criar backup se o arquivo ja existe
    if caminho.is_file():
        backup_dir = base / "data" / "backups" / "code-studio"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_backup = f"{timestamp}_{caminho.name}"
        shutil.copy2(caminho, backup_dir / nome_backup)
        logger.info(f"Backup criado: {nome_backup}")

    # Salvar arquivo
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(dados.conteudo, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")

    # Audit log
    try:
        proj_label = projeto.nome if projeto else "Synerium Factory"
        audit = AuditLogDB(
            user_id=usuario.id,
            email=usuario.email,
            acao="CODE_STUDIO_WRITE",
            descricao=f"[{proj_label}] Arquivo editado: {dados.caminho}",
            ip=request.client.host if request.client else "",
        )
        db.add(audit)
        db.commit()
    except Exception:
        pass

    logger.info(f"Arquivo salvo por {usuario.email}: {dados.caminho} (projeto: {proj_id or 'SF'})")

    return {"sucesso": True, "caminho": dados.caminho, "tamanho": len(dados.conteudo)}


@router.post("/analyze")
async def analisar_codigo(
    dados: AnalisarCodigoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Analisa codigo usando o Smart Router Global + LLM."""
    # Obter contexto do projeto
    _, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
    proj_contexto = ""
    if projeto:
        proj_contexto = f"\nProjeto: {projeto.nome} | Stack: {projeto.stack}\n"

    try:
        prompt = f"""Analise o seguinte codigo do arquivo `{dados.caminho}`:
{proj_contexto}
```
{dados.conteudo[:8000]}
```

Instrucao do usuario: {dados.instrucao}

Responda em portugues brasileiro. Seja direto e objetivo."""

        # Tentar usar Smart Router para decidir o modelo
        provider_nome = "sonnet"
        modelo_nome = "claude-sonnet-4-20250514"
        motivo = "padrao"

        try:
            from core.smart_router_global import SmartRouterGlobal
            router_global = SmartRouterGlobal()
            roteamento = router_global.rotear(
                prompt=prompt,
                agente_nome="Code Studio",
                forcar=dados.modelo if dados.modelo != "auto" else None,
            )
            provider_nome = roteamento.nome_provider
            modelo_nome = roteamento.modelo
            motivo = roteamento.motivo
        except Exception:
            pass  # Fallback para Sonnet

        # System prompt do agente
        system = f"""Voce e o agente de codigo do Synerium Factory — Code Studio.
{f"Voce esta trabalhando no projeto: {projeto.nome} ({projeto.stack})" if projeto else ""}

Regras obrigatorias:
- Responda SEMPRE em portugues brasileiro
- Use Markdown estruturado (titulos, listas, blocos de codigo)
- Quando mostrar codigo, SEMPRE use blocos ```linguagem com a linguagem correta
- Estruture suas respostas assim:
  1. **Analise** — o que o codigo faz (breve)
  2. **Resposta** — responda a instrucao com codigo se necessario
  3. **Motivo** — por que essa e a melhor abordagem
- Seja direto, profissional e completo
- Quando sugerir codigo, mostre o codigo COMPLETO (nao parcial)"""

        from langchain_core.messages import HumanMessage, SystemMessage
        mensagens = [SystemMessage(content=system), HumanMessage(content=prompt)]

        # Cadeia de fallback: tentar multiplos providers
        erros = []
        providers_tentativa = [
            ("anthropic", modelo_nome if "claude" in modelo_nome else "claude-sonnet-4-20250514"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ]

        for prov, modelo in providers_tentativa:
            try:
                from langchain_anthropic import ChatAnthropic
                llm = ChatAnthropic(model=modelo, max_tokens=4000, temperature=0.3)
                resposta = await llm.ainvoke(mensagens)
                return {
                    "resposta": resposta.content,
                    "provider": provider_nome,
                    "modelo": modelo,
                    "motivo": motivo,
                }
            except Exception as e:
                erros.append(f"{prov}/{modelo}: {str(e)[:100]}")
                continue

        # Se todos falharam
        logger.error(f"Todos os providers falharam: {erros}")
        raise HTTPException(status_code=500, detail="Todos os providers falharam. Tente novamente em alguns minutos.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na analise: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na analise: {str(e)}")


@router.post("/apply-action")
async def aplicar_acao(
    dados: AplicarAcaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aplica uma acao do agente IA — substituir conteudo ou criar novo arquivo."""
    try:
        _verificar_escrita(usuario)
        base, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
        caminho = _validar_caminho(dados.caminho_destino, base)

        # Backup antes de qualquer alteracao
        backup_dir = base / "data" / "backups" / "code-studio"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if dados.tipo_acao == "criar":
            caminho.parent.mkdir(parents=True, exist_ok=True)
            if caminho.exists():
                shutil.copy2(str(caminho), str(backup_dir / f"{caminho.name}.{ts}.bak"))
        else:
            if not caminho.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {dados.caminho_destino}")
            shutil.copy2(str(caminho), str(backup_dir / f"{caminho.name}.{ts}.bak"))

        # Escrever
        caminho.write_text(dados.conteudo_novo, encoding="utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CodeStudio] Erro ao aplicar acao: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar: {str(e)}")

    # Audit log
    try:
        proj_label = projeto.nome if projeto else "Synerium Factory"
        db.add(AuditLogDB(
            user_id=usuario.id,
            email=usuario.email,
            acao=f"code_studio_apply_{dados.tipo_acao}",
            descricao=f"[{proj_label}] Acao IA em {dados.caminho_destino} ({len(dados.conteudo_novo)} chars)",
            ip="api",
        ))
        db.commit()
    except Exception:
        pass

    logger.info(f"[CodeStudio] {usuario.email} aplicou '{dados.tipo_acao}' em {dados.caminho_destino} (projeto: {proj_id or 'SF'})")

    # Tentar commit + push se projeto tiver VCS configurado
    vcs_resultado = None
    try:
        from database.models import ProjetoVCSDB
        from core.vcs_service import descriptografar_token, VCSService

        # Buscar VCS do projeto especifico (nao mais .first() generico)
        filtro_vcs = {"ativo": True}
        if proj_id:
            filtro_vcs["projeto_id"] = proj_id

        vcs = db.query(ProjetoVCSDB).filter_by(**filtro_vcs).first()
        if vcs:
            token = descriptografar_token(vcs.api_token_encrypted)
            service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao)

            # Mensagem de commit baseada no tipo de acao
            nomes_acao = {"substituir": "refactor", "criar": "feat"}
            prefixo = nomes_acao.get(dados.tipo_acao, "chore")
            nome_arquivo = dados.caminho_destino.split("/")[-1]
            msg_commit = (
                f"{prefixo}(code-studio): {dados.tipo_acao} em {nome_arquivo}\n\n"
                f"Aplicado via Synerium Factory Code Studio por {usuario.nome}"
            )

            resultado = service.commit_e_push(
                caminho_projeto=str(base),
                arquivos=[dados.caminho_destino],
                mensagem_commit=msg_commit,
                autor_nome=usuario.nome,
                autor_email=usuario.email,
            )
            vcs_resultado = {
                "sucesso": resultado.sucesso,
                "mensagem": resultado.mensagem,
                "commit_hash": resultado.commit_hash,
                "branch": resultado.branch,
            }
            logger.info(f"[CodeStudio/VCS] Commit: {resultado.commit_hash} - {resultado.mensagem}")
    except Exception as e:
        logger.warning(f"[CodeStudio/VCS] Git nao executado: {str(e)[:200]}")

    return {
        "ok": True,
        "caminho": dados.caminho_destino,
        "tipo": dados.tipo_acao,
        "tamanho": len(dados.conteudo_novo),
        "vcs": vcs_resultado,
    }


# ============================================================
# Git Pull — atualizar repositorio do projeto
# ============================================================

@router.post("/git-pull")
async def git_pull(
    project_id: int = Query(0),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Faz git pull no repositorio do projeto para atualizar arquivos locais."""
    base, proj_id, projeto = _obter_base_projeto(project_id, db, usuario)

    git_dir = base / ".git"
    if not git_dir.is_dir():
        raise HTTPException(status_code=400, detail="Diretorio nao e um repositorio git.")

    try:
        # Descobrir branch atual
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(base),
            capture_output=True,
            timeout=10,
        )
        branch = branch_result.stdout.decode().strip() if branch_result.returncode == 0 else "main"

        # Git pull
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=str(base),
            capture_output=True,
            timeout=60,
        )

        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()

        if result.returncode != 0:
            logger.warning(f"[CodeStudio] git pull falhou em {base}: {stderr[:300]}")
            return {"sucesso": False, "mensagem": stderr[:300], "branch": branch}

        logger.info(f"[CodeStudio] git pull OK em {base} ({branch}): {stdout[:200]}")
        return {"sucesso": True, "mensagem": stdout[:300], "branch": branch}

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout no git pull (60s).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no git pull: {str(e)[:200]}")
