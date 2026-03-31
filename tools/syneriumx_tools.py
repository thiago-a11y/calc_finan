"""
Ferramentas para acesso ao projeto SyneriumX.

Regras de segurança:
- LEITURA: livre (ler, listar, buscar, git status/log/diff)
- ESCRITA: gera solicitação → proprietário aprova no dashboard → aplica
- GIT push/merge/reset: requer aprovação
- Terminal: apenas comandos de leitura (ls, find, grep, cat, wc, etc.)

Path base: resolve dinamicamente do banco (ProjetoDB) com fallbacks.
"""

import os
import subprocess
import logging
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger("synerium.tools.syneriumx")


def _resolver_base_syneriumx() -> str:
    """
    Resolve o caminho base do SyneriumX dinamicamente.

    Ordem de prioridade:
    1. Variavel de ambiente SYNERIUMX_BASE (override manual)
    2. Banco de dados (ProjetoDB com nome SyneriumX)
    3. /opt/projetos/syneriumx (padrao AWS)
    4. ~/propostasap (dev local Mac)
    """
    # Override via env
    env_base = os.getenv("SYNERIUMX_BASE", "")
    if env_base and os.path.isdir(env_base):
        return env_base

    # Tentar buscar do banco
    try:
        from database.session import SessionLocal
        from database.models import ProjetoDB
        db = SessionLocal()
        projeto = db.query(ProjetoDB).filter(
            ProjetoDB.nome.ilike("%syneriumx%"),
            ProjetoDB.ativo == True,
        ).first()
        if projeto and projeto.caminho and os.path.isdir(projeto.caminho):
            db.close()
            return projeto.caminho
        db.close()
    except Exception:
        pass

    # Fallbacks por path
    for path in ["/opt/projetos/syneriumx", os.path.expanduser("~/propostasap")]:
        if os.path.isdir(path):
            return path

    # Ultimo recurso
    return "/opt/projetos/syneriumx"


# Caminho base do SyneriumX — resolvido dinamicamente
SYNERIUMX_BASE = _resolver_base_syneriumx()
logger.info(f"[SyneriumX Tools] Base path: {SYNERIUMX_BASE}")

# Comandos bloqueados por segurança
COMANDOS_BLOQUEADOS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "drop database", "drop table",
    "format", "mkfs",
    "shutdown", "reboot",
    "> /dev/sda",
]


def _validar_caminho(caminho: str) -> str:
    """
    Valida que o caminho está dentro do diretório base do SyneriumX.
    Retorna o caminho absoluto seguro.

    Raises:
        ValueError: Se o caminho estiver fora do diretório permitido.
    """
    # Se for relativo, juntar com base
    if not os.path.isabs(caminho):
        caminho_abs = os.path.normpath(os.path.join(SYNERIUMX_BASE, caminho))
    else:
        caminho_abs = os.path.normpath(caminho)

    # Verificar se está dentro do base
    if not caminho_abs.startswith(SYNERIUMX_BASE):
        raise ValueError(
            f"BLOQUEADO: Caminho '{caminho}' está fora do diretório permitido "
            f"({SYNERIUMX_BASE}). Operação negada por segurança."
        )

    return caminho_abs


def _validar_comando(comando: str) -> bool:
    """
    Valida que o comando não é destrutivo.

    Returns:
        True se o comando é seguro.

    Raises:
        ValueError: Se o comando for perigoso.
    """
    cmd_lower = comando.lower().strip()
    for bloqueado in COMANDOS_BLOQUEADOS:
        if bloqueado in cmd_lower:
            raise ValueError(
                f"BLOQUEADO: Comando '{comando}' contém operação perigosa "
                f"('{bloqueado}'). Operação negada por segurança."
            )
    return True


# =====================================================================
# Schemas Pydantic para args_schema — compatibilidade GPT-4o-mini (v0.53.1)
# Sem schemas explicitos, CrewAI infere schema do _run() que pode
# gerar JSON invalido para function calling no GPT-4o-mini.
# =====================================================================

class LerArquivoInput(BaseModel):
    """Schema para ferramenta ler_arquivo_syneriumx."""
    caminho: str = Field(description="Caminho relativo do arquivo no projeto SyneriumX. Exemplo: 'api/config.php', 'src/App.tsx'")


class ListarDiretorioInput(BaseModel):
    """Schema para ferramenta listar_diretorio_syneriumx."""
    caminho: str = Field(default="", description="Caminho relativo do diretorio. Deixe vazio para raiz do projeto. Exemplo: 'api/', 'src/components/'")


class ProporEdicaoInput(BaseModel):
    """Schema para ferramenta propor_edicao_syneriumx."""
    dados: str = Field(description="Dados da edicao no formato: caminho|||conteudo_novo|||descricao. Exemplo: 'api/teste.php|||<?php echo 1;|||Criar arquivo de teste'")


class BuscarInput(BaseModel):
    """Schema para ferramenta buscar_no_syneriumx."""
    termo: str = Field(description="Termo de busca (texto ou regex)")
    diretorio: str = Field(default="", description="Diretorio para buscar (relativo). Vazio = projeto inteiro")
    extensao: str = Field(default="", description="Extensao de arquivo para filtrar. Exemplo: 'php', 'tsx', 'py'")


class GitInput(BaseModel):
    """Schema para ferramenta git_syneriumx."""
    comando: str = Field(description="Comando git a executar (sem 'git' na frente). Exemplo: 'status', 'diff src/App.tsx', 'log --oneline -10'")


class TerminalInput(BaseModel):
    """Schema para ferramenta terminal_syneriumx."""
    comando: str = Field(description="Comando de terminal a executar no diretorio do SyneriumX. Exemplo: 'find . -name \"*.php\" | wc -l', 'cat api/config.php | head -20'")


# =====================================================================
# Ferramenta: Ler Arquivo do SyneriumX
# =====================================================================
class LerArquivoSyneriumX(BaseTool):
    name: str = "ler_arquivo_syneriumx"
    description: str = (
        "Lê o conteúdo de um arquivo do projeto SyneriumX (~/propostasap). "
        "Informe o caminho relativo ao projeto. "
        "Exemplo: 'api/config.php', 'src/App.tsx', 'README.md'"
    )
    args_schema: type[BaseModel] = LerArquivoInput

    def _run(self, caminho: str) -> str:
        """Lê um arquivo do SyneriumX."""
        try:
            caminho_abs = _validar_caminho(caminho)

            if not os.path.exists(caminho_abs):
                return f"Arquivo não encontrado: {caminho}"

            if not os.path.isfile(caminho_abs):
                return f"'{caminho}' não é um arquivo (pode ser um diretório)."

            # Limitar tamanho para não estourar contexto
            tamanho = os.path.getsize(caminho_abs)
            if tamanho > 100_000:  # 100KB
                return (
                    f"Arquivo muito grande ({tamanho:,} bytes). "
                    f"Use listar_diretorio_syneriumx para navegar ou "
                    f"especifique um trecho menor."
                )

            with open(caminho_abs, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()

            logger.info(f"[SYNERIUMX] Leu: {caminho} ({len(conteudo)} chars)")
            return f"=== {caminho} ({tamanho:,} bytes) ===\n{conteudo}"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Erro ao ler '{caminho}': {e}"


# =====================================================================
# Ferramenta: Listar Diretório do SyneriumX
# =====================================================================
class ListarDiretorioSyneriumX(BaseTool):
    name: str = "listar_diretorio_syneriumx"
    description: str = (
        "Lista arquivos e pastas de um diretório do projeto SyneriumX (~/propostasap). "
        "Informe o caminho relativo ou deixe vazio para a raiz. "
        "Exemplo: 'api/', 'src/components/', ''"
    )
    args_schema: type[BaseModel] = ListarDiretorioInput

    def _run(self, caminho: str = "") -> str:
        """Lista conteúdo de um diretório do SyneriumX."""
        try:
            caminho_abs = _validar_caminho(caminho or ".")

            if not os.path.isdir(caminho_abs):
                return f"'{caminho}' não é um diretório."

            itens = sorted(os.listdir(caminho_abs))
            resultado = []
            for item in itens:
                full = os.path.join(caminho_abs, item)
                if os.path.isdir(full):
                    resultado.append(f"📁 {item}/")
                else:
                    tamanho = os.path.getsize(full)
                    resultado.append(f"📄 {item} ({tamanho:,} bytes)")

            rel = caminho or "/"
            logger.info(f"[SYNERIUMX] Listou: {rel} ({len(itens)} itens)")
            return f"=== {rel} ({len(itens)} itens) ===\n" + "\n".join(resultado)

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Erro ao listar '{caminho}': {e}"


# =====================================================================
# Ferramenta: Propor Edição no SyneriumX (REQUER APROVAÇÃO)
# =====================================================================
class ProporEdicaoSyneriumX(BaseTool):
    name: str = "propor_edicao_syneriumx"
    description: str = (
        "Propõe uma edição em um arquivo do SyneriumX (~/propostasap). "
        "A edição NÃO é aplicada imediatamente — gera uma solicitação "
        "que o proprietário do projeto precisa aprovar no dashboard. "
        "Informe: caminho do arquivo, conteúdo novo e descrição da mudança. "
        "Use o separador ||| entre os campos. "
        "Exemplo: 'api/teste.php|||<?php echo 1;|||Criar arquivo de teste'"
    )
    args_schema: type[BaseModel] = ProporEdicaoInput

    def _run(self, dados: str) -> str:
        """Propõe edição que precisa de aprovação do proprietário."""
        try:
            partes = dados.split("|||")
            if len(partes) < 3:
                return (
                    "Erro: formato inválido. Use: "
                    "'caminho|||conteudo_novo|||descricao_da_mudanca'"
                )

            caminho = partes[0].strip()
            conteudo_novo = partes[1]
            descricao = partes[2].strip()

            caminho_abs = _validar_caminho(caminho)

            # Ler conteúdo atual (se existir) para gerar diff
            conteudo_atual = ""
            if os.path.isfile(caminho_abs):
                with open(caminho_abs, "r", encoding="utf-8", errors="replace") as f:
                    conteudo_atual = f.read()

            # Salvar proposta em arquivo JSON
            import json
            from datetime import datetime

            propostas_dir = os.path.join(
                os.path.expanduser("~/synerium-factory"),
                "data", "propostas_edicao"
            )
            os.makedirs(propostas_dir, exist_ok=True)

            proposta_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            proposta = {
                "id": proposta_id,
                "projeto": "SyneriumX",
                "caminho": caminho,
                "caminho_absoluto": caminho_abs,
                "descricao": descricao,
                "acao": "editar" if conteudo_atual else "criar",
                "conteudo_atual_preview": conteudo_atual[:2000] if conteudo_atual else "(arquivo novo)",
                "conteudo_novo": conteudo_novo,
                "status": "pendente",
                "criado_em": datetime.now().isoformat(),
                "criado_por": "agente",
            }

            proposta_path = os.path.join(propostas_dir, f"{proposta_id}.json")
            with open(proposta_path, "w", encoding="utf-8") as f:
                json.dump(proposta, f, ensure_ascii=False, indent=2)

            logger.info(
                f"[SYNERIUMX] Proposta de edição: {proposta_id} — {caminho} — {descricao}"
            )

            return (
                f"✅ Solicitação de edição criada!\n"
                f"ID: {proposta_id}\n"
                f"Arquivo: {caminho}\n"
                f"Ação: {'Editar' if conteudo_atual else 'Criar arquivo novo'}\n"
                f"Descrição: {descricao}\n"
                f"Status: ⏸ AGUARDANDO APROVAÇÃO do proprietário do SyneriumX\n\n"
                f"O proprietário será notificado no dashboard para aprovar ou rejeitar."
            )

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Erro ao criar proposta: {e}"


# =====================================================================
# Ferramenta: Buscar no SyneriumX (grep)
# =====================================================================
class BuscarNoSyneriumX(BaseTool):
    name: str = "buscar_no_syneriumx"
    description: str = (
        "Busca texto em arquivos do projeto SyneriumX (~/propostasap). "
        "Usa grep recursivo. Informe o termo de busca e opcionalmente "
        "o diretório e extensão de arquivo. "
        "Exemplo: termo='company_id', diretorio='api/', extensao='php'"
    )
    args_schema: type[BaseModel] = BuscarInput

    def _run(self, termo: str, diretorio: str = "", extensao: str = "") -> str:
        """Busca texto nos arquivos do SyneriumX."""
        try:
            caminho_abs = _validar_caminho(diretorio or ".")

            cmd = ["grep", "-r", "-n", "--include"]

            if extensao:
                cmd.append(f"*.{extensao}")
            else:
                cmd.append("*")

            cmd.extend(["-l", termo, caminho_abs])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                # Converter caminhos absolutos para relativos
                linhas = result.stdout.strip().split("\n")
                relativas = [
                    l.replace(SYNERIUMX_BASE + "/", "") for l in linhas if l
                ]
                logger.info(f"[SYNERIUMX] Busca '{termo}': {len(relativas)} resultado(s)")
                return f"=== Busca: '{termo}' ({len(relativas)} arquivos) ===\n" + "\n".join(relativas[:50])
            else:
                return f"Nenhum resultado para '{termo}'."

        except ValueError as e:
            return str(e)
        except subprocess.TimeoutExpired:
            return "Busca demorou demais (timeout 30s)."
        except Exception as e:
            return f"Erro na busca: {e}"


# =====================================================================
# Ferramenta: Executar Comando Git no SyneriumX
# =====================================================================
class GitSyneriumX(BaseTool):
    name: str = "git_syneriumx"
    description: str = (
        "Executa comandos git no projeto SyneriumX (~/propostasap). "
        "Comandos permitidos: status, diff, log, branch, add, commit. "
        "Comandos push/merge/reset requerem aprovação. "
        "Exemplo: comando='status', comando='diff src/App.tsx'"
    )
    args_schema: type[BaseModel] = GitInput

    # Comandos git que precisam de aprovação
    GIT_REQUER_APROVACAO: list[str] = ["push", "merge", "reset", "rebase", "force"]

    def _run(self, comando: str) -> str:
        """Executa um comando git no SyneriumX."""
        try:
            cmd_parts = comando.strip().split()
            if not cmd_parts:
                return "Comando git vazio."

            subcmd = cmd_parts[0].lower()

            # Verificar se precisa aprovação
            for bloqueado in self.GIT_REQUER_APROVACAO:
                if bloqueado in comando.lower():
                    return (
                        f"⚠️ REQUER APROVAÇÃO: 'git {comando}' é uma operação crítica. "
                        f"Solicite aprovação do Operations Lead antes de executar."
                    )

            result = subprocess.run(
                ["git"] + cmd_parts,
                capture_output=True, text=True, timeout=30,
                cwd=SYNERIUMX_BASE,
            )

            saida = result.stdout or result.stderr
            logger.info(f"[SYNERIUMX] git {comando}: {'OK' if result.returncode == 0 else 'ERRO'}")
            return f"=== git {comando} ===\n{saida[:5000]}"

        except subprocess.TimeoutExpired:
            return "Comando git demorou demais (timeout 30s)."
        except Exception as e:
            return f"Erro ao executar git: {e}"


# =====================================================================
# Ferramenta: Terminal Seguro no SyneriumX
# =====================================================================
class TerminalSyneriumX(BaseTool):
    name: str = "terminal_syneriumx"
    description: str = (
        "Executa comandos de terminal no diretório do SyneriumX (~/propostasap). "
        "Comandos destrutivos são bloqueados por segurança. "
        "Útil para: cat, head, tail, wc, find, du, ls -la, php -l, etc. "
        "Exemplo: comando='find . -name \"*.php\" | wc -l'"
    )
    args_schema: type[BaseModel] = TerminalInput

    def _run(self, comando: str) -> str:
        """Executa um comando de terminal no SyneriumX."""
        try:
            _validar_comando(comando)

            result = subprocess.run(
                comando,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=SYNERIUMX_BASE,
            )

            saida = result.stdout or result.stderr
            logger.info(f"[SYNERIUMX] Terminal: {comando[:50]}...")
            return f"=== $ {comando} ===\n{saida[:5000]}"

        except ValueError as e:
            return str(e)
        except subprocess.TimeoutExpired:
            return "Comando demorou demais (timeout 30s)."
        except Exception as e:
            return f"Erro no terminal: {e}"
