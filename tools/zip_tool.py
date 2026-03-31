"""
Skill: Criar Arquivo ZIP

Permite que os agentes compactem arquivos e pastas em .zip.
Útil para empacotar projetos, landing pages, relatórios, etc.
"""

import os
import zipfile
import logging
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger("synerium.tools.zip")

# Diretório seguro para outputs dos agentes
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


# Schemas Pydantic para compatibilidade GPT-4o-mini (v0.53.1)
class CriarZipInput(BaseModel):
    """Schema para ferramenta criar_zip."""
    parametros: str = Field(description="Formato: caminho_diretorio|nome_do_zip. Exemplo: output/meu_projeto|meu_projeto.zip")


class CriarProjetoInput(BaseModel):
    """Schema para ferramenta criar_projeto."""
    parametros: str = Field(description="Formato: nome_projeto|||arquivo1.html:::conteudo1|||arquivo2.css:::conteudo2")


class CriarZipTool(BaseTool):
    """Ferramenta para criar arquivos .zip a partir de um diretório."""

    name: str = "criar_zip"
    description: str = (
        "Cria um arquivo .zip a partir de um diretório ou lista de arquivos. "
        "Use após criar arquivos com a ferramenta de escrita. "
        "Formato: caminho_diretorio|nome_do_zip "
        "Exemplo: output/meu_projeto|meu_projeto.zip "
        "O .zip será salvo em output/"
    )
    args_schema: type[BaseModel] = CriarZipInput

    def _run(self, parametros: str) -> str:
        """
        Cria um .zip.

        Args:
            parametros: "caminho_diretorio|nome_do_zip"
        """
        partes = parametros.split("|", 1)
        if len(partes) < 2:
            return "[ERRO] Formato: caminho_diretorio|nome_do_zip"

        diretorio = partes[0].strip()
        nome_zip = partes[1].strip()

        # Garantir que o diretório output existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Resolver caminhos
        if not os.path.isabs(diretorio):
            diretorio = os.path.join(OUTPUT_DIR, diretorio)

        if not nome_zip.endswith(".zip"):
            nome_zip += ".zip"

        caminho_zip = os.path.join(OUTPUT_DIR, nome_zip)

        # Verificar se diretório existe
        if not os.path.exists(diretorio):
            return f"[ERRO] Diretório não encontrado: {diretorio}"

        try:
            arquivos_adicionados = 0
            with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(diretorio):
                    for raiz, dirs, arquivos in os.walk(diretorio):
                        for arquivo in arquivos:
                            caminho_completo = os.path.join(raiz, arquivo)
                            arcname = os.path.relpath(caminho_completo, diretorio)
                            zf.write(caminho_completo, arcname)
                            arquivos_adicionados += 1
                else:
                    # É um arquivo único
                    zf.write(diretorio, os.path.basename(diretorio))
                    arquivos_adicionados = 1

            tamanho = os.path.getsize(caminho_zip)
            tamanho_kb = tamanho / 1024

            logger.info(
                f"[ZIP] Criado: {caminho_zip} | "
                f"{arquivos_adicionados} arquivo(s) | {tamanho_kb:.1f} KB"
            )

            return (
                f"[OK] ZIP criado com sucesso!\n"
                f"  Arquivo: {caminho_zip}\n"
                f"  Arquivos incluídos: {arquivos_adicionados}\n"
                f"  Tamanho: {tamanho_kb:.1f} KB\n"
                f"  Use a ferramenta enviar_email_com_anexo para enviar por email."
            )

        except Exception as e:
            logger.error(f"[ZIP] Erro: {str(e)}")
            return f"[ERRO] Falha ao criar ZIP: {str(e)}"


class CriarProjetoTool(BaseTool):
    """Ferramenta para criar múltiplos arquivos de um projeto de uma vez."""

    name: str = "criar_projeto"
    description: str = (
        "Cria múltiplos arquivos de um projeto (landing page, site, app) de uma vez. "
        "Use para gerar projetos completos com HTML, CSS, JS, imagens, etc. "
        "Formato: nome_projeto|||arquivo1.html:::conteudo1|||arquivo2.css:::conteudo2 "
        "Separador de arquivos: ||| "
        "Separador nome/conteúdo: ::: "
        "Subpastas são suportadas: css/style.css:::conteudo "
        "Os arquivos são salvos em output/nome_projeto/"
    )
    args_schema: type[BaseModel] = CriarProjetoInput

    def _run(self, parametros: str) -> str:
        """
        Cria múltiplos arquivos.

        Args:
            parametros: "nome_projeto|||arq1:::conteudo1|||arq2:::conteudo2"
        """
        partes = parametros.split("|||")
        if len(partes) < 2:
            return (
                "[ERRO] Formato: nome_projeto|||arquivo1:::conteudo1|||arquivo2:::conteudo2\n"
                "Exemplo: minha_landing|||index.html:::<html>...</html>|||css/style.css:::body{...}"
            )

        nome_projeto = partes[0].strip()
        arquivos = partes[1:]

        # Criar diretório do projeto
        dir_projeto = os.path.join(OUTPUT_DIR, nome_projeto)
        os.makedirs(dir_projeto, exist_ok=True)

        criados = []
        erros = []

        for arq in arquivos:
            if ":::" not in arq:
                erros.append(f"Formato inválido (falta :::): {arq[:50]}")
                continue

            nome_arq, conteudo = arq.split(":::", 1)
            nome_arq = nome_arq.strip()
            conteudo = conteudo.strip()

            # Criar subpastas se necessário
            caminho_completo = os.path.join(dir_projeto, nome_arq)
            os.makedirs(os.path.dirname(caminho_completo), exist_ok=True) if "/" in nome_arq else None

            try:
                with open(caminho_completo, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                criados.append(nome_arq)
            except Exception as e:
                erros.append(f"{nome_arq}: {str(e)}")

        logger.info(f"[PROJETO] Criado: {nome_projeto} | {len(criados)} arquivo(s)")

        resultado = (
            f"[OK] Projeto criado com sucesso!\n"
            f"  Diretório: {dir_projeto}\n"
            f"  Arquivos criados: {len(criados)}\n"
        )
        for c in criados:
            resultado += f"    ✅ {c}\n"
        if erros:
            resultado += f"  Erros: {len(erros)}\n"
            for e in erros:
                resultado += f"    ❌ {e}\n"

        resultado += (
            f"\n  Próximo passo: use criar_zip para compactar:\n"
            f"    criar_zip: {nome_projeto}|{nome_projeto}.zip"
        )

        return resultado
