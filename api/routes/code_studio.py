"""
Code Studio — Editor de código integrado ao Synerium Factory.

Endpoints:
- GET /api/code-studio/tree — árvore de arquivos do projeto
- GET /api/code-studio/file — ler conteúdo de um arquivo
- POST /api/code-studio/file — salvar arquivo (com backup e audit log)
- POST /api/code-studio/analyze — análise de código via Smart Router

Segurança:
- Path traversal bloqueado via Path.resolve() + is_relative_to()
- Escrita restrita a papéis: CEO, operations_lead, dev, diretor_tecnico
- Binários bloqueados para leitura
- Audit log LGPD em todas as escritas
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencias import obter_usuario_atual
from database.session import get_db
from database.models import UsuarioDB, AuditLogDB

logger = logging.getLogger("synerium.code_studio")

router = APIRouter(prefix="/api/code-studio", tags=["Code Studio"])

# ============================================================
# Configuração de segurança
# ============================================================

# Base permitida — nunca acessar fora disso
if os.path.exists("/opt/synerium-factory"):
    ALLOWED_BASE = Path("/opt/synerium-factory")
else:
    ALLOWED_BASE = Path(__file__).parent.parent.parent.resolve()

# Diretórios ignorados na árvore
IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".claude", ".next", ".cache", "dist",
}

# Extensões bloqueadas para leitura (binários)
BLOCKED_EXTENSIONS = {
    ".pyc", ".pyo", ".db", ".sqlite", ".sqlite3",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".xz",
    ".exe", ".dll", ".so", ".dylib",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
}

# Mapeamento extensão → linguagem CodeMirror
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

# Papéis que podem escrever arquivos
PAPEIS_ESCRITA = {"ceo", "operations_lead", "dev", "desenvolvedor", "diretor_tecnico"}


# ============================================================
# Helpers
# ============================================================

def _validar_caminho(caminho_relativo: str) -> Path:
    """Valida e resolve caminho, bloqueando traversal."""
    # Limpar caminho
    caminho_relativo = caminho_relativo.strip().lstrip("/")
    if not caminho_relativo:
        raise HTTPException(status_code=400, detail="Caminho não informado.")

    caminho = (ALLOWED_BASE / caminho_relativo).resolve()

    if not caminho.is_relative_to(ALLOWED_BASE):
        logger.warning(f"Path traversal bloqueado: {caminho_relativo}")
        raise HTTPException(status_code=403, detail="Acesso negado: caminho fora do projeto.")

    return caminho


def _verificar_escrita(usuario: UsuarioDB):
    """Verifica se o usuário tem permissão de escrita."""
    papeis = set(usuario.papeis or [])
    if not papeis.intersection(PAPEIS_ESCRITA):
        raise HTTPException(status_code=403, detail="Sem permissão para editar arquivos.")


def _detectar_linguagem(extensao: str) -> str:
    """Retorna a linguagem do CodeMirror baseada na extensão."""
    return LANG_MAP.get(extensao.lower(), "text")


def _listar_diretorio(caminho: Path, profundidade: int = 0, max_prof: int = 4) -> list:
    """Lista recursivamente os arquivos/pastas de um diretório."""
    if profundidade > max_prof:
        return []

    resultado = []

    try:
        itens = sorted(caminho.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return []

    for item in itens:
        nome = item.name

        # Ignorar diretórios bloqueados
        if item.is_dir() and nome in IGNORED_DIRS:
            continue

        # Ignorar arquivos ocultos (exceto .env)
        if nome.startswith(".") and nome != ".env":
            continue

        caminho_rel = str(item.relative_to(ALLOWED_BASE))

        if item.is_dir():
            filhos = _listar_diretorio(item, profundidade + 1, max_prof)
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


class AnalisarCodigoRequest(BaseModel):
    caminho: str
    conteudo: str
    instrucao: str
    modelo: str = "auto"


class AplicarAcaoRequest(BaseModel):
    """Aplica código gerado pelo agente no arquivo original ou cria novo arquivo."""
    caminho_destino: str
    conteudo_novo: str
    tipo_acao: str = "substituir"  # substituir | criar


# ============================================================
# Endpoints
# ============================================================

@router.get("/tree")
async def listar_arvore(
    path: str = Query("", description="Subdiretório relativo"),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Retorna a árvore de arquivos do projeto."""
    if path:
        base = _validar_caminho(path)
        if not base.is_dir():
            raise HTTPException(status_code=404, detail="Diretório não encontrado.")
    else:
        base = ALLOWED_BASE

    arvore = _listar_diretorio(base)
    return {"arvore": arvore, "base": str(ALLOWED_BASE)}


@router.get("/file")
async def ler_arquivo(
    path: str = Query(..., description="Caminho relativo do arquivo"),
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Lê o conteúdo de um arquivo do projeto."""
    caminho = _validar_caminho(path)

    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    ext = caminho.suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Tipo de arquivo não suportado: {ext}")

    tamanho = caminho.stat().st_size
    if tamanho > 1_048_576:  # 1MB
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máximo 1MB).")

    try:
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")

    # Verificar permissão de escrita
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
    """Salva o conteúdo de um arquivo (com backup e audit log)."""
    _verificar_escrita(usuario)

    caminho = _validar_caminho(dados.caminho)

    # Verificar extensão
    ext = caminho.suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Não é permitido editar arquivos {ext}.")

    # Criar backup se o arquivo já existe
    if caminho.is_file():
        backup_dir = ALLOWED_BASE / "data" / "backups" / "code-studio"
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
        audit = AuditLogDB(
            user_id=usuario.id,
            email=usuario.email,
            acao="CODE_STUDIO_WRITE",
            descricao=f"Arquivo editado: {dados.caminho}",
            ip=request.client.host if request.client else "",
        )
        db.add(audit)
        db.commit()
    except Exception:
        pass  # Não falhar por causa do audit log

    logger.info(f"Arquivo salvo por {usuario.email}: {dados.caminho}")

    return {"sucesso": True, "caminho": dados.caminho, "tamanho": len(dados.conteudo)}


@router.post("/analyze")
async def analisar_codigo(
    dados: AnalisarCodigoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
):
    """Analisa código usando o Smart Router Global + LLM."""
    try:
        prompt = f"""Analise o seguinte código do arquivo `{dados.caminho}`:

```
{dados.conteudo[:8000]}
```

Instrução do usuário: {dados.instrucao}

Responda em português brasileiro. Seja direto e objetivo."""

        # Tentar usar Smart Router para decidir o modelo
        provider_nome = "sonnet"
        modelo_nome = "claude-sonnet-4-20250514"
        motivo = "padrão"

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
        system = """Você é o agente de código do Synerium Factory — Code Studio.

Regras obrigatórias:
- Responda SEMPRE em português brasileiro
- Use Markdown estruturado (títulos, listas, blocos de código)
- Quando mostrar código, SEMPRE use blocos ```linguagem com a linguagem correta
- Estruture suas respostas assim:
  1. **Análise** — o que o código faz (breve)
  2. **Resposta** — responda a instrução com código se necessário
  3. **Motivo** — por que essa é a melhor abordagem
- Seja direto, profissional e completo
- Quando sugerir código, mostre o código COMPLETO (não parcial)"""

        from langchain_core.messages import HumanMessage, SystemMessage
        mensagens = [SystemMessage(content=system), HumanMessage(content=prompt)]

        # Cadeia de fallback: tentar múltiplos providers
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
        raise HTTPException(status_code=500, detail=f"Todos os providers falharam. Tente novamente em alguns minutos.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na análise: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")


@router.post("/apply-action")
async def aplicar_acao(
    dados: AplicarAcaoRequest,
    usuario: UsuarioDB = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Aplica uma ação do agente IA — substituir conteúdo ou criar novo arquivo."""
    _verificar_escrita(usuario)
    caminho = _validar_caminho(dados.caminho_destino)

    if dados.tipo_acao == "criar":
        # Criar diretórios pais se necessário
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if caminho.exists():
            # Backup antes de sobrescrever
            backup_dir = Path(PROJETO_BASE) / "data" / "backups" / "code-studio"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(str(caminho), str(backup_dir / f"{caminho.name}.{ts}.bak"))
    else:
        # Substituir — arquivo deve existir
        if not caminho.exists():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        # Backup
        backup_dir = Path(PROJETO_BASE) / "data" / "backups" / "code-studio"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(str(caminho), str(backup_dir / f"{caminho.name}.{ts}.bak"))

    # Escrever
    caminho.write_text(dados.conteudo_novo, encoding="utf-8")

    # Audit log
    try:
        db.add(AuditLogDB(
            usuario_id=usuario.id,
            acao=f"code_studio_apply_{dados.tipo_acao}",
            detalhes=f"Ação IA em {dados.caminho_destino} ({len(dados.conteudo_novo)} chars)",
            ip="api",
        ))
        db.commit()
    except Exception:
        pass

    logger.info(f"[CodeStudio] {usuario.email} aplicou ação '{dados.tipo_acao}' em {dados.caminho_destino}")

    return {
        "ok": True,
        "caminho": dados.caminho_destino,
        "tipo": dados.tipo_acao,
        "tamanho": len(dados.conteudo_novo),
    }
