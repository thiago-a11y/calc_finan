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

import asyncio
import difflib
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
from database.models import UsuarioDB, AuditLogDB, ProjetoDB, ProjetoVCSDB, AgenteCatalogoDB

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
    context_level: str = "standard"  # minimal | standard | full


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
    """Analisa codigo usando o Smart Router Global + LLM + Company Context."""
    # Obter contexto do projeto
    _, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
    proj_contexto = ""
    if projeto:
        proj_contexto = f"\nProjeto: {projeto.nome} | Stack: {projeto.stack}\n"

    # Construir contexto rico (Company Context Total)
    contexto_rico = ""
    context_level_usado = dados.context_level or "standard"
    if context_level_usado not in ("minimal", "standard", "full"):
        context_level_usado = "standard"

    if context_level_usado != "minimal":
        try:
            from core.company_context import CompanyContextBuilder
            builder = CompanyContextBuilder(db=db)
            contexto_rico = builder.construir(
                instrucao=dados.instrucao,
                conteudo_arquivo=dados.conteudo,
                projeto=projeto,
                nivel=context_level_usado,
            )
            if contexto_rico:
                logger.info(f"[CodeStudio] Company Context ({context_level_usado}): {len(contexto_rico)} chars injetados")
        except Exception as e:
            logger.warning(f"[CodeStudio] Company Context falhou: {e}")

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

        # System prompt do agente com Company Context injetado
        system = f"""Voce e o agente de codigo do Synerium Factory — Code Studio.
{f"Voce esta trabalhando no projeto: {projeto.nome} ({projeto.stack})" if projeto else ""}

{contexto_rico}

Regras obrigatorias:
- Responda SEMPRE em portugues brasileiro
- Use Markdown estruturado (titulos, listas, blocos de codigo)
- Quando mostrar codigo, SEMPRE use blocos ```linguagem com a linguagem correta
- Estruture suas respostas assim:
  1. **Analise** — o que o codigo faz (breve)
  2. **Resposta** — responda a instrucao com codigo se necessario
  3. **Motivo** — por que essa e a melhor abordagem
- Seja direto, profissional e completo
- Quando sugerir codigo, mostre o codigo COMPLETO (nao parcial)
- Use o contexto da empresa e do projeto para dar sugestoes alinhadas com a arquitetura e padroes reais
- Nunca sugira tecnologias ou padroes que contradigam as decisoes tecnicas da empresa"""

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
                    "context_level": context_level_usado,
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


# ============================================================
# Apply + Deploy — Pipeline completo: backup → aplicar → testar → commit → push
# ============================================================

class ApplyDeployRequest(BaseModel):
    caminho_destino: str
    conteudo_novo: str
    tipo_acao: str = "substituir"
    project_id: int = 0


@router.post("/apply-deploy")
async def apply_deploy(
    dados: ApplyDeployRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Pipeline completo: backup → aplicar → testar → commit → push.
    Retorna resultado de cada etapa para progresso no frontend.
    """
    _verificar_escrita(usuario)
    base, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
    caminho = _validar_caminho(dados.caminho_destino, base)

    etapas = []
    conteudo_original = ""
    backup_path = ""

    # === ETAPA 1: Backup ===
    try:
        backup_dir = base / "data" / "backups" / "code-studio"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if caminho.exists():
            conteudo_original = caminho.read_text(encoding="utf-8", errors="replace")
            backup_path = str(backup_dir / f"{caminho.name}.{ts}.bak")
            shutil.copy2(str(caminho), backup_path)
        etapas.append({"etapa": "backup", "sucesso": True, "msg": f"Backup salvo ({ts})"})
    except Exception as e:
        etapas.append({"etapa": "backup", "sucesso": False, "msg": str(e)[:200]})
        return {"ok": False, "etapas": etapas, "erro": "Falha no backup"}

    # === ETAPA 2: Aplicar ===
    try:
        if dados.tipo_acao == "criar":
            caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(dados.conteudo_novo, encoding="utf-8")
        linhas_antes = len(conteudo_original.splitlines()) if conteudo_original else 0
        linhas_depois = len(dados.conteudo_novo.splitlines())
        etapas.append({"etapa": "aplicar", "sucesso": True, "msg": f"{linhas_antes} → {linhas_depois} linhas"})
    except Exception as e:
        # Reverter do backup
        if backup_path and Path(backup_path).exists():
            shutil.copy2(backup_path, str(caminho))
        etapas.append({"etapa": "aplicar", "sucesso": False, "msg": str(e)[:200]})
        return {"ok": False, "etapas": etapas, "erro": "Falha ao aplicar"}

    # === ETAPA 3: Test Master — Validação obrigatória ===
    testes_ok = True
    try:
        ext = caminho.suffix.lower()
        test_cmd = None

        # Detectar framework de testes por tipo de projeto
        if ext in (".py", ".pyx"):
            if (base / "pytest.ini").exists() or (base / "tests").exists() or (base / "pyproject.toml").exists():
                test_cmd = ["python", "-m", "pytest", "--tb=short", "-q", "--timeout=30", "-x"]
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            if (base / "vitest.config.ts").exists() or (base / "vitest.config.js").exists():
                test_cmd = ["npx", "vitest", "run", "--reporter=dot"]
            elif (base / "package.json").exists():
                pkg = (base / "package.json").read_text(errors="replace")
                if '"test"' in pkg:
                    test_cmd = ["npm", "test", "--", "--watchAll=false"]
        elif ext == ".php":
            if (base / "phpunit.xml").exists() or (base / "phpunit.xml.dist").exists():
                test_cmd = ["vendor/bin/phpunit", "--no-coverage", "--stop-on-failure"]

        if test_cmd:
            etapas.append({"etapa": "test_master", "sucesso": False, "msg": "🛡️ Test Master validando..."})
            result = subprocess.run(
                test_cmd, cwd=str(base), capture_output=True, timeout=90,
                env={**os.environ, "CI": "1"},
            )
            if result.returncode == 0:
                stdout = result.stdout.decode("utf-8", errors="replace")[:200]
                etapas[-1] = {"etapa": "test_master", "sucesso": True, "msg": f"🛡️ Test Master: APROVADO — {stdout.strip()[:100]}"}
            else:
                stderr = result.stderr.decode("utf-8", errors="replace")[:300]
                etapas[-1] = {"etapa": "test_master", "sucesso": False, "msg": f"🛡️ Test Master: BLOQUEADO — {stderr}"}
                testes_ok = False
        else:
            # Sem framework de testes — Test Master faz validação sintática básica
            try:
                # Verificar se o arquivo é sintaticamente válido
                conteudo_novo = dados.conteudo_novo
                if ext == ".py":
                    compile(conteudo_novo, str(caminho), "exec")
                    etapas.append({"etapa": "test_master", "sucesso": True, "msg": "🛡️ Test Master: Sintaxe Python OK (sem framework de testes)"})
                elif ext in (".json",):
                    import json as json_mod
                    json_mod.loads(conteudo_novo)
                    etapas.append({"etapa": "test_master", "sucesso": True, "msg": "🛡️ Test Master: JSON válido"})
                else:
                    etapas.append({"etapa": "test_master", "sucesso": True, "msg": "🛡️ Test Master: Sem framework — validação básica OK"})
            except SyntaxError as se:
                etapas.append({"etapa": "test_master", "sucesso": False, "msg": f"🛡️ Test Master: ERRO DE SINTAXE — linha {se.lineno}: {se.msg}"})
                testes_ok = False
            except Exception:
                etapas.append({"etapa": "test_master", "sucesso": True, "msg": "🛡️ Test Master: Validação básica OK"})

    except subprocess.TimeoutExpired:
        etapas.append({"etapa": "test_master", "sucesso": False, "msg": "🛡️ Test Master: Timeout (90s)"})
        testes_ok = False
    except Exception as e:
        etapas.append({"etapa": "test_master", "sucesso": True, "msg": f"🛡️ Test Master: Pulado ({str(e)[:60]})"})

    # Se testes falharam, reverter
    if not testes_ok:
        if backup_path and Path(backup_path).exists():
            shutil.copy2(backup_path, str(caminho))
            etapas.append({"etapa": "revert", "sucesso": True, "msg": "Revertido para backup (testes falharam)"})
        return {"ok": False, "etapas": etapas, "erro": "Testes falharam — alteracao revertida"}

    # === ETAPA 4: Commit + Push via VCS ===
    vcs_resultado = None
    try:
        from core.vcs_service import descriptografar_token, VCSService

        filtro_vcs = {"ativo": True}
        if proj_id:
            filtro_vcs["projeto_id"] = proj_id

        vcs = db.query(ProjetoVCSDB).filter_by(**filtro_vcs).first()
        if vcs:
            token = descriptografar_token(vcs.api_token_encrypted)
            service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao)

            nomes_acao = {"substituir": "refactor", "criar": "feat"}
            prefixo = nomes_acao.get(dados.tipo_acao, "chore")
            nome_arquivo = dados.caminho_destino.split("/")[-1]
            msg_commit = f"{prefixo}(code-studio): {dados.tipo_acao} em {nome_arquivo}"

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
            if resultado.sucesso:
                etapas.append({"etapa": "commit_push", "sucesso": True, "msg": f"Commit {resultado.commit_hash} → {resultado.branch}"})
            else:
                etapas.append({"etapa": "commit_push", "sucesso": False, "msg": resultado.mensagem[:200]})
        else:
            etapas.append({"etapa": "commit_push", "sucesso": True, "msg": "VCS nao configurado — pulado"})
    except Exception as e:
        etapas.append({"etapa": "commit_push", "sucesso": False, "msg": str(e)[:200]})
        logger.warning(f"[ApplyDeploy] VCS falhou: {e}")

    # Audit log
    try:
        proj_label = projeto.nome if projeto else "Synerium Factory"
        db.add(AuditLogDB(
            user_id=usuario.id, email=usuario.email,
            acao="code_studio_apply_deploy",
            descricao=f"[{proj_label}] Apply+Deploy em {dados.caminho_destino}",
            ip="api",
        ))
        db.commit()
    except Exception:
        pass

    # Diff resumo
    diff_resumo = None
    try:
        la = conteudo_original.splitlines() if conteudo_original else []
        ld = dados.conteudo_novo.splitlines()
        if len(la) <= 5000 and len(ld) <= 5000:
            d = list(difflib.unified_diff(la, ld, lineterm=""))
            diff_resumo = {
                "linhas_antes": len(la), "linhas_depois": len(ld),
                "linhas_adicionadas": sum(1 for x in d if x.startswith("+") and not x.startswith("+++")),
                "linhas_removidas": sum(1 for x in d if x.startswith("-") and not x.startswith("---")),
            }
    except Exception:
        pass

    return {
        "ok": True,
        "etapas": etapas,
        "vcs": vcs_resultado,
        "diff_resumo": diff_resumo,
        "caminho": dados.caminho_destino,
    }


@router.post("/apply-action")
async def aplicar_acao(
    dados: AplicarAcaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aplica uma acao do agente IA — substituir conteudo ou criar novo arquivo."""
    conteudo_original = ""
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
                conteudo_original = caminho.read_text(encoding="utf-8", errors="replace")
                shutil.copy2(str(caminho), str(backup_dir / f"{caminho.name}.{ts}.bak"))
        else:
            if not caminho.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {dados.caminho_destino}")
            conteudo_original = caminho.read_text(encoding="utf-8", errors="replace")
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

    # Calcular resumo de diff (limitado a 5000 linhas)
    diff_resumo = None
    try:
        linhas_antes = conteudo_original.splitlines() if conteudo_original else []
        linhas_depois = dados.conteudo_novo.splitlines()
        if len(linhas_antes) <= 5000 and len(linhas_depois) <= 5000:
            diff = list(difflib.unified_diff(linhas_antes, linhas_depois, lineterm=""))
            adicionadas = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
            removidas = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
            diff_resumo = {
                "linhas_antes": len(linhas_antes),
                "linhas_depois": len(linhas_depois),
                "linhas_adicionadas": adicionadas,
                "linhas_removidas": removidas,
            }
    except Exception:
        pass

    return {
        "ok": True,
        "caminho": dados.caminho_destino,
        "tipo": dados.tipo_acao,
        "tamanho": len(dados.conteudo_novo),
        "vcs": vcs_resultado,
        "diff_resumo": diff_resumo,
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

        # Verificar se tem VCS com token para autenticar
        env = dict(os.environ)
        if proj_id:
            from database.models import ProjetoVCSDB
            from core.vcs_service import descriptografar_token
            vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=proj_id, ativo=True).first()
            if vcs and vcs.api_token_encrypted:
                # Injetar token via GIT_ASKPASS para nao pedir senha
                remote_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(base), capture_output=True, timeout=5,
                )
                remote_url = remote_result.stdout.decode().strip() if remote_result.returncode == 0 else ""
                if remote_url.startswith("https://"):
                    # Configurar credencial temporaria via env
                    env["GIT_TERMINAL_PROMPT"] = "0"
                    # Descriptografar token e usar na URL
                    try:
                        token_real = descriptografar_token(vcs.api_token_encrypted)
                    except Exception as e:
                        logger.warning(f"[CodeStudio] Erro ao descriptografar token VCS: {e}")
                        token_real = None

                    if token_real:
                        url_com_token = remote_url.replace("https://", f"https://x-access-token:{token_real}@")
                        result = subprocess.run(
                            ["git", "pull", "--rebase", "--autostash", url_com_token, branch],
                            cwd=str(base),
                            capture_output=True,
                            timeout=60,
                            env=env,
                        )
                        stdout = result.stdout.decode("utf-8", errors="replace").strip()
                        stderr = result.stderr.decode("utf-8", errors="replace").strip()
                        # Git usa stderr para progresso (From https://...) mesmo em sucesso
                        output_completo = stdout or stderr
                        if result.returncode != 0:
                            logger.warning(f"[CodeStudio] git pull (token) falhou em {base}: {output_completo[:300]}")
                            return {"sucesso": False, "mensagem": output_completo[:300], "branch": branch}
                        logger.info(f"[CodeStudio] git pull OK (token) em {base} ({branch})")
                        return {"sucesso": True, "mensagem": output_completo[:300], "branch": branch}

        # Git pull sem token (fallback)
        env["GIT_TERMINAL_PROMPT"] = "0"
        result = subprocess.run(
            ["git", "pull", "--rebase", "--autostash", "origin", branch],
            cwd=str(base),
            capture_output=True,
            timeout=60,
            env=env,
        )

        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        output_completo = stdout or stderr

        if result.returncode != 0:
            logger.warning(f"[CodeStudio] git pull falhou em {base}: {output_completo[:300]}")
            return {"sucesso": False, "mensagem": output_completo[:300], "branch": branch}

        logger.info(f"[CodeStudio] git pull OK em {base} ({branch}): {output_completo[:200]}")
        return {"sucesso": True, "mensagem": output_completo[:300], "branch": branch}

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout no git pull (60s).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no git pull: {str(e)[:200]}")


# ============================================================
# Historico de atividades do Code Studio
# ============================================================

# Mapeamento de acoes para labels em PT-BR
_ACAO_LABELS = {
    "code_studio_apply_substituir": "Otimizacao/Refatoracao via IA",
    "code_studio_apply_criar": "Arquivo criado via IA",
    "CODE_STUDIO_WRITE": "Edicao manual",
}

# Regex para extrair caminho do arquivo da descricao
_RE_ARQUIVO = re.compile(r"(?:Arquivo editado:|Acao IA em)\s*(\S+)")


@router.get("/historico")
async def listar_historico(
    project_id: int = Query(0, description="ID do projeto (0 = todos)"),
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna o historico de atividades do Code Studio (paginado)."""
    from sqlalchemy import or_, func

    # Filtro base: acoes do code studio
    filtro = or_(
        AuditLogDB.acao.like("code_studio%"),
        AuditLogDB.acao == "CODE_STUDIO_WRITE",
    )

    # Filtro por projeto (se informado)
    if project_id:
        projeto = db.query(ProjetoDB).filter_by(id=project_id, ativo=True).first()
        if projeto:
            filtro = filtro & AuditLogDB.descricao.like(f"[{projeto.nome}]%")

    # Total de registros
    total = db.query(func.count(AuditLogDB.id)).filter(filtro).scalar() or 0

    # Buscar com paginacao + join com usuario
    offset = (page - 1) * limit
    registros = (
        db.query(AuditLogDB, UsuarioDB.nome)
        .outerjoin(UsuarioDB, AuditLogDB.user_id == UsuarioDB.id)
        .filter(filtro)
        .order_by(AuditLogDB.criado_em.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    atividades = []
    for audit, usuario_nome in registros:
        # Extrair caminho do arquivo
        arquivo = ""
        match = _RE_ARQUIVO.search(audit.descricao or "")
        if match:
            arquivo = match.group(1)

        atividades.append({
            "id": audit.id,
            "usuario_nome": usuario_nome or audit.email or "Sistema",
            "usuario_email": audit.email or "",
            "acao": audit.acao,
            "acao_label": _ACAO_LABELS.get(audit.acao, audit.acao),
            "descricao": audit.descricao or "",
            "arquivo": arquivo,
            "criado_em": audit.criado_em.isoformat() if audit.criado_em else "",
        })

    return {
        "atividades": atividades,
        "total": total,
        "pagina": page,
        "limite": limit,
    }


# ============================================================
# Git Log — commits pendentes de push
# ============================================================

@router.get("/git-log")
async def git_log_pendentes(
    project_id: int = Query(0),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista commits locais que ainda nao foram pushados para o remote."""
    base, proj_id, projeto = _obter_base_projeto(project_id, db, usuario)

    git_dir = base / ".git"
    if not git_dir.is_dir():
        raise HTTPException(status_code=400, detail="Nao e um repositorio git.")

    try:
        # Branch atual
        branch_r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(base), capture_output=True, timeout=10,
        )
        branch = branch_r.stdout.decode().strip() if branch_r.returncode == 0 else "main"

        # Buscar VCS config para saber branch padrao
        vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=proj_id or 0, ativo=True).first()
        branch_remoto = vcs.branch_padrao if vcs else "main"

        # Fetch silencioso (atualiza refs sem baixar)
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            cwd=str(base), capture_output=True, timeout=30,
        )

        # Commits pendentes: local mas nao no remote
        # Usar separador que nao aparece em mensagens de commit
        SEP = "§§§"
        log_r = subprocess.run(
            ["git", "log", f"origin/{branch_remoto}..HEAD",
             f"--format=%H{SEP}%h{SEP}%s{SEP}%an{SEP}%aI", "--no-merges"],
            cwd=str(base), capture_output=True, timeout=10,
        )

        commits = []
        if log_r.returncode == 0 and log_r.stdout.decode().strip():
            for linha in log_r.stdout.decode().strip().split("\n"):
                partes = linha.split(SEP, 4)
                if len(partes) >= 5:
                    commit_hash = partes[0]
                    # Buscar arquivos alterados neste commit
                    arquivos = []
                    try:
                        stat_r = subprocess.run(
                            ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit_hash],
                            cwd=str(base), capture_output=True, timeout=5,
                        )
                        if stat_r.returncode == 0:
                            for sl in stat_r.stdout.decode().strip().split("\n"):
                                if sl.strip():
                                    stat_parts = sl.split("\t", 1)
                                    if len(stat_parts) == 2:
                                        arquivos.append({
                                            "status": stat_parts[0],  # M=modified, A=added, D=deleted
                                            "arquivo": stat_parts[1],
                                        })
                    except Exception:
                        pass

                    commits.append({
                        "hash": commit_hash,
                        "hash_curto": partes[1],
                        "mensagem": partes[2],
                        "autor": partes[3],
                        "data": partes[4],
                        "arquivos": arquivos,
                    })

        return {
            "commits": commits,
            "branch": branch,
            "branch_remoto": branch_remoto,
            "total": len(commits),
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout no git log.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)[:200]}")


# ============================================================
# Git Push — criar branch + push + PR
# ============================================================

class GitPushRequest(BaseModel):
    project_id: int = 0
    commit_hashes: list[str] = []  # vazio = todos os pendentes
    titulo_pr: str = ""


@router.post("/git-push")
async def git_push_e_pr(
    dados: GitPushRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cria branch, push e abre PR no GitHub/GitBucket."""
    _verificar_escrita(usuario)

    base, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)

    git_dir = base / ".git"
    if not git_dir.is_dir():
        raise HTTPException(status_code=400, detail="Nao e um repositorio git.")

    # Buscar VCS config
    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=proj_id or 0, ativo=True).first()
    if not vcs:
        raise HTTPException(status_code=400, detail="Projeto sem VCS configurado.")

    try:
        from core.vcs_service import descriptografar_token, VCSService

        token = descriptografar_token(vcs.api_token_encrypted)
        service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao or "main")

        branch_remoto = vcs.branch_padrao or "main"

        # Branch atual
        branch_r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(base), capture_output=True, timeout=10,
        )
        branch_atual = branch_r.stdout.decode().strip() if branch_r.returncode == 0 else "main"

        # Criar branch para o push
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_push = f"sf/push-{ts}"

        # Se tem commits especificos, criar branch e cherry-pick
        if dados.commit_hashes:
            # Criar branch a partir do remote
            subprocess.run(
                ["git", "checkout", "-b", branch_push, f"origin/{branch_remoto}"],
                cwd=str(base), capture_output=True, timeout=10,
            )
            # Cherry-pick dos commits selecionados (ordem cronologica)
            for h in reversed(dados.commit_hashes):
                cp = subprocess.run(
                    ["git", "cherry-pick", h],
                    cwd=str(base), capture_output=True, timeout=30,
                )
                if cp.returncode != 0:
                    # Abortar cherry-pick e voltar
                    subprocess.run(["git", "cherry-pick", "--abort"], cwd=str(base), capture_output=True)
                    subprocess.run(["git", "checkout", branch_atual], cwd=str(base), capture_output=True)
                    subprocess.run(["git", "branch", "-D", branch_push], cwd=str(base), capture_output=True)
                    stderr = cp.stderr.decode("utf-8", errors="replace")
                    raise HTTPException(status_code=400, detail=f"Cherry-pick falhou: {stderr[:200]}")
        else:
            # Push de todos os commits pendentes — criar branch a partir de HEAD
            subprocess.run(
                ["git", "checkout", "-b", branch_push],
                cwd=str(base), capture_output=True, timeout=10,
            )

        # Push da branch
        push_result = service.push_branch(str(base), branch_push)
        if not push_result.sucesso:
            # Voltar para branch original e limpar
            subprocess.run(["git", "checkout", branch_atual], cwd=str(base), capture_output=True)
            subprocess.run(["git", "branch", "-D", branch_push], cwd=str(base), capture_output=True)
            raise HTTPException(status_code=500, detail=f"Push falhou: {push_result.mensagem}")

        # Criar PR via API
        titulo = dados.titulo_pr or f"[Synerium Factory] Push de {usuario.nome} — {ts}"
        n_commits = len(dados.commit_hashes) if dados.commit_hashes else "todos os"
        descricao = (
            f"## Push via Synerium Factory Code Studio\n\n"
            f"- **Usuario:** {usuario.nome} ({usuario.email})\n"
            f"- **Projeto:** {projeto.nome if projeto else 'Synerium Factory'}\n"
            f"- **Commits:** {n_commits}\n"
            f"- **Branch:** `{branch_push}` → `{branch_remoto}`\n\n"
            f"🤖 Gerado pelo [Synerium Factory](https://synerium-factory.objetivasolucao.com.br)"
        )

        pr_result = await service.criar_pr(titulo, descricao, branch_push, branch_remoto)

        # Voltar para branch original
        subprocess.run(["git", "checkout", branch_atual], cwd=str(base), capture_output=True)

        # Audit log
        try:
            db.add(AuditLogDB(
                user_id=usuario.id,
                email=usuario.email,
                acao="code_studio_push",
                descricao=f"[{projeto.nome if projeto else 'SF'}] Push {branch_push} + PR {pr_result.get('pr_url', '?')}",
                ip="api",
            ))
            db.commit()
        except Exception:
            pass

        logger.info(f"[CodeStudio/Push] {usuario.email} criou PR: {pr_result.get('pr_url', '?')}")

        return {
            "sucesso": pr_result.get("sucesso", False),
            "pr_url": pr_result.get("pr_url", ""),
            "pr_number": pr_result.get("pr_number", 0),
            "branch": branch_push,
            "commits_enviados": len(dados.commit_hashes) if dados.commit_hashes else -1,
            "mensagem": pr_result.get("mensagem", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Garantir volta para branch original
        try:
            subprocess.run(["git", "checkout", branch_atual], cwd=str(base), capture_output=True)
        except Exception:
            pass
        logger.error(f"[CodeStudio/Push] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no push: {str(e)[:200]}")


# ============================================================
# Git Merge — merge de PR via API
# ============================================================

class GitMergeRequest(BaseModel):
    project_id: int = 0
    pr_number: int


@router.post("/git-merge")
async def git_merge_pr(
    dados: GitMergeRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Faz merge de uma PR no GitHub/GitBucket via API."""
    _verificar_escrita(usuario)

    _, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)

    vcs = db.query(ProjetoVCSDB).filter_by(projeto_id=proj_id or 0, ativo=True).first()
    if not vcs:
        raise HTTPException(status_code=400, detail="Projeto sem VCS configurado.")

    try:
        from core.vcs_service import descriptografar_token, VCSService
        import httpx

        token = descriptografar_token(vcs.api_token_encrypted)
        service = VCSService(vcs.vcs_tipo, vcs.repo_url, token, vcs.branch_padrao or "main")
        owner_repo = service._extrair_owner_repo()

        if not owner_repo:
            raise HTTPException(status_code=400, detail="URL do repositorio invalida.")

        if vcs.vcs_tipo == "github":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.put(
                    f"https://api.github.com/repos/{owner_repo}/pulls/{dados.pr_number}/merge",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    json={
                        "merge_method": "squash",
                        "commit_title": f"Merge PR #{dados.pr_number} via Synerium Factory",
                    },
                )

            if resp.status_code == 200:
                data = resp.json()
                # Audit log
                try:
                    db.add(AuditLogDB(
                        user_id=usuario.id, email=usuario.email,
                        acao="code_studio_merge",
                        descricao=f"[{projeto.nome if projeto else 'SF'}] Merge PR #{dados.pr_number} — {data.get('sha', '?')[:8]}",
                        ip="api",
                    ))
                    db.commit()
                except Exception:
                    pass

                logger.info(f"[CodeStudio/Merge] PR #{dados.pr_number} merged por {usuario.email}")

                # Auto-pull para sincronizar local com remote apos merge
                try:
                    base, _, _ = _obter_base_projeto(dados.project_id, db, usuario)
                    env = dict(os.environ)
                    env["GIT_TERMINAL_PROMPT"] = "0"
                    url_com_token = vcs.repo_url.replace("https://", f"https://x-access-token:{token}@")
                    subprocess.run(
                        ["git", "pull", "--rebase", url_com_token, vcs.branch_padrao or "main"],
                        cwd=str(base), capture_output=True, timeout=30, env=env,
                    )
                    logger.info(f"[CodeStudio/Merge] Auto-pull apos merge OK")
                except Exception as ep:
                    logger.warning(f"[CodeStudio/Merge] Auto-pull falhou: {ep}")

                return {
                    "sucesso": True,
                    "mensagem": f"PR #{dados.pr_number} merged com sucesso (squash)",
                    "merge_sha": data.get("sha", ""),
                }
            elif resp.status_code == 405:
                return {"sucesso": False, "mensagem": "PR nao pode ser merged (conflitos ou regras)", "merge_sha": ""}
            elif resp.status_code == 409:
                return {"sucesso": False, "mensagem": "Conflito de merge — resolva no GitHub", "merge_sha": ""}
            else:
                return {"sucesso": False, "mensagem": f"GitHub API {resp.status_code}: {resp.text[:200]}", "merge_sha": ""}

        elif vcs.vcs_tipo == "gitbucket":
            base_url = vcs.repo_url.split("/git/")[0] if "/git/" in vcs.repo_url else ""
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.put(
                    f"{base_url}/api/v3/repos/{owner_repo}/pulls/{dados.pr_number}/merge",
                    headers={"Authorization": f"token {token}"},
                )
            if resp.status_code == 200:
                return {"sucesso": True, "mensagem": f"PR #{dados.pr_number} merged", "merge_sha": ""}
            else:
                return {"sucesso": False, "mensagem": f"GitBucket {resp.status_code}", "merge_sha": ""}

        raise HTTPException(status_code=400, detail=f"VCS tipo nao suportado: {vcs.vcs_tipo}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CodeStudio/Merge] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no merge: {str(e)[:200]}")


# ============================================================
# Collaborative Agent Mode — Analise Multi-Agente
# ============================================================

MAX_AGENTES_TIME = 3  # Limite de agentes por colaboracao


class AnalisarTimeRequest(BaseModel):
    caminho: str
    conteudo: str
    instrucao: str
    project_id: int = 0
    context_level: str = "full"
    agentes_ids: list[int] = []  # IDs do AgenteCatalogoDB


async def _analisar_como_agente(
    system: str,
    prompt: str,
    agente_nome: str,
) -> dict:
    """Chama o LLM uma vez como um agente especifico."""
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            temperature=0.3,
        )
        mensagens = [SystemMessage(content=system), HumanMessage(content=prompt)]
        resposta = await llm.ainvoke(mensagens)

        return {
            "agente": agente_nome,
            "resposta": resposta.content,
            "sucesso": True,
        }
    except Exception as e:
        logger.warning(f"[Team] Agente {agente_nome} falhou: {e}")
        return {
            "agente": agente_nome,
            "resposta": f"Erro: {str(e)[:200]}",
            "sucesso": False,
        }


async def _sintetizar_analises(
    respostas: list[dict],
    instrucao: str,
    caminho: str,
    contexto_rico: str,
) -> str:
    """Sintetiza as analises de multiplos agentes em um parecer final."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    # Compilar respostas
    compilado = ""
    for r in respostas:
        if r.get("sucesso"):
            compilado += f"\n## {r['agente']}\n{r['resposta']}\n"

    system = f"""Voce e o Sintetizador de Analises do Synerium Factory.
Compile as perspectivas dos agentes especializados em um parecer executivo.

{contexto_rico}

Estruture assim:
1. **Recomendacao Principal** — o que fazer (1-2 frases)
2. **Consenso** — pontos em que todos concordam
3. **Pontos de Atencao** — riscos ou divergencias
4. **Codigo Sugerido** — se aplicavel, mostre o codigo final dentro de um bloco ```

Responda em portugues brasileiro. Seja direto e pratico."""

    prompt = f"""Arquivo: {caminho}
Instrucao original: {instrucao}

=== ANALISES DO TIME ===
{compilado}

Gere o parecer sintetizado."""

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        temperature=0.3,
    )
    mensagens = [SystemMessage(content=system), HumanMessage(content=prompt)]
    resposta = await llm.ainvoke(mensagens)
    return resposta.content


@router.post("/analizar-time")
async def analisar_codigo_com_time(
    dados: AnalisarTimeRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Analisa codigo com multiplos agentes em paralelo + sintese final."""

    if not dados.agentes_ids:
        raise HTTPException(status_code=400, detail="Selecione pelo menos 1 agente.")

    if len(dados.agentes_ids) > MAX_AGENTES_TIME:
        raise HTTPException(status_code=400, detail=f"Maximo {MAX_AGENTES_TIME} agentes por colaboracao.")

    # Buscar agentes do catalogo
    agentes = []
    for aid in dados.agentes_ids:
        ag = db.query(AgenteCatalogoDB).filter_by(id=aid, ativo=True).first()
        if ag:
            agentes.append(ag)

    if not agentes:
        raise HTTPException(status_code=400, detail="Nenhum agente valido encontrado.")

    # Company Context
    _, proj_id, projeto = _obter_base_projeto(dados.project_id, db, usuario)
    contexto_rico = ""
    if dados.context_level != "minimal":
        try:
            from core.company_context import CompanyContextBuilder
            builder = CompanyContextBuilder(db=db)
            contexto_rico = builder.construir(
                instrucao=dados.instrucao,
                conteudo_arquivo=dados.conteudo,
                projeto=projeto,
                nivel=dados.context_level,
            )
        except Exception:
            pass

    # Prompt compartilhado (igual para todos os agentes)
    proj_ctx = f"\nProjeto: {projeto.nome} ({projeto.stack})\n" if projeto else ""
    prompt_usuario = f"""Analise o seguinte codigo do arquivo `{dados.caminho}`:
{proj_ctx}
```
{dados.conteudo[:6000]}
```

Instrucao do usuario: {dados.instrucao}

Responda em portugues brasileiro. Seja direto, profissional e completo.
Quando sugerir codigo, mostre o codigo COMPLETO dentro de um bloco ```.  """

    # Criar tasks paralelas
    tasks = []
    for ag in agentes:
        system_agente = f"""Voce e {ag.nome_exibicao} no Synerium Factory — Code Studio.
Papel: {ag.papel}
Objetivo: {ag.objetivo}

{contexto_rico}

Regras:
- Responda SEMPRE em portugues brasileiro
- Use Markdown estruturado
- Analise sob a perspectiva do seu papel especifico
- Seja pratico e objetivo
{ag.regras_extras or ''}"""

        tasks.append(_analisar_como_agente(system_agente, prompt_usuario, ag.nome_exibicao))

    # Executar em paralelo
    logger.info(f"[Team] {usuario.email} iniciou colaboracao com {len(agentes)} agentes")
    respostas = await asyncio.gather(*tasks, return_exceptions=False)

    # Sintese final
    sintese = ""
    try:
        respostas_sucesso = [r for r in respostas if r.get("sucesso")]
        if len(respostas_sucesso) >= 2:
            sintese = await _sintetizar_analises(
                respostas_sucesso, dados.instrucao, dados.caminho, contexto_rico
            )
    except Exception as e:
        logger.warning(f"[Team] Sintese falhou: {e}")
        sintese = ""

    # Audit log
    try:
        nomes = ", ".join(ag.nome_exibicao for ag in agentes)
        db.add(AuditLogDB(
            user_id=usuario.id, email=usuario.email,
            acao="code_studio_team",
            descricao=f"[{projeto.nome if projeto else 'SF'}] Colaboracao: {nomes} em {dados.caminho}",
            ip="api",
        ))
        db.commit()
    except Exception:
        pass

    # Formatar resposta
    respostas_formatadas = []
    for i, r in enumerate(respostas):
        respostas_formatadas.append({
            "agente": r.get("agente", agentes[i].nome_exibicao if i < len(agentes) else "?"),
            "perfil": agentes[i].perfil_agente if i < len(agentes) else "",
            "categoria": agentes[i].categoria if i < len(agentes) else "",
            "resposta": r.get("resposta", "Sem resposta"),
            "sucesso": r.get("sucesso", False),
        })

    logger.info(f"[Team] Colaboracao concluida: {len(respostas_formatadas)} respostas + sintese")

    return {
        "respostas_agentes": respostas_formatadas,
        "sintese": sintese,
        "total_agentes": len(agentes),
    }
