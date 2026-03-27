"""
Skill: Enviar Email via Amazon SES (com suporte a anexos)

Permite que os agentes enviem emails reais para o time da Objetiva.
Usa Amazon SES em produção (já configurado e fora do sandbox).

Duas ferramentas:
- enviar_email: texto simples ou HTML (sem anexo)
- enviar_email_com_anexo: com arquivo anexado (.zip, .pdf, etc.)

Segurança:
- Limite de 10 emails por execução (evitar spam)
- Apenas remetente verificado no SES
- Anexos máximo 10 MB (limite do SES)
- Log de todos os emails enviados
"""

import os
import logging
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.exceptions import ClientError
from crewai.tools import BaseTool
from pydantic import Field

logger = logging.getLogger("synerium.tools.email")

# Diretório de output dos agentes
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


class EnviarEmailTool(BaseTool):
    """Ferramenta para enviar emails de texto/HTML via Amazon SES."""

    name: str = "enviar_email"
    description: str = (
        "Envia um email real via Amazon SES (sem anexo). "
        "Use para enviar relatórios, notificações e mensagens para o time. "
        "Formato: destinatario|assunto|corpo "
        "Exemplo: thiago@objetivasolucao.com.br|Relatório Diário|Segue o relatório..."
    )

    aws_region: str = Field(default="us-east-1")
    aws_access_key: str = Field(default="")
    aws_secret_key: str = Field(default="")
    remetente: str = Field(default="")
    emails_enviados: int = Field(default=0)
    limite_por_execucao: int = Field(default=10)

    def _run(self, parametros: str) -> str:
        """Envia email de texto/HTML."""
        if self.emails_enviados >= self.limite_por_execucao:
            return f"[LIMITE] Limite de {self.limite_por_execucao} emails atingido."

        partes = parametros.split("|", 2)
        if len(partes) < 3:
            return "[ERRO] Formato: destinatario|assunto|corpo"

        destinatario = partes[0].strip()
        assunto = partes[1].strip()
        corpo = partes[2].strip()

        if "@" not in destinatario:
            return f"[ERRO] Email inválido: {destinatario}"

        try:
            cliente = boto3.client(
                "ses",
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )

            is_html = "<" in corpo and ">" in corpo
            mensagem = {"Subject": {"Data": assunto, "Charset": "UTF-8"}, "Body": {}}

            if is_html:
                mensagem["Body"]["Html"] = {"Data": corpo, "Charset": "UTF-8"}
                import re
                mensagem["Body"]["Text"] = {"Data": re.sub(r"<[^>]+>", "", corpo), "Charset": "UTF-8"}
            else:
                mensagem["Body"]["Text"] = {"Data": corpo, "Charset": "UTF-8"}

            resposta = cliente.send_email(
                Source=self.remetente,
                Destination={"ToAddresses": [destinatario]},
                Message=mensagem,
            )

            self.emails_enviados += 1
            mid = resposta.get("MessageId", "N/A")
            logger.info(f"[EMAIL] Enviado para {destinatario} | Assunto: {assunto} | ID: {mid}")

            return (
                f"[OK] Email enviado!\n"
                f"  Para: {destinatario}\n"
                f"  Assunto: {assunto}\n"
                f"  MessageId: {mid}"
            )
        except ClientError as e:
            return f"[ERRO] {e.response['Error']['Message']}"
        except Exception as e:
            return f"[ERRO] {str(e)}"


class EnviarEmailComAnexoTool(BaseTool):
    """Ferramenta para enviar emails com arquivo anexado via Amazon SES."""

    name: str = "enviar_email_com_anexo"
    description: str = (
        "Envia um email com arquivo anexado via Amazon SES. "
        "Use para enviar .zip, .pdf, relatórios e projetos por email. "
        "Formato: destinatario|assunto|corpo|caminho_do_anexo "
        "O caminho do anexo pode ser relativo à pasta output/ "
        "Exemplo: thiago@objetivasolucao.com.br|Landing Page|Segue o projeto|meu_projeto.zip "
        "Limite: 10 MB por anexo (restrição do Amazon SES)."
    )

    aws_region: str = Field(default="us-east-1")
    aws_access_key: str = Field(default="")
    aws_secret_key: str = Field(default="")
    remetente: str = Field(default="")
    emails_enviados: int = Field(default=0)
    limite_por_execucao: int = Field(default=10)

    def _run(self, parametros: str) -> str:
        """Envia email com anexo."""
        if self.emails_enviados >= self.limite_por_execucao:
            return f"[LIMITE] Limite de {self.limite_por_execucao} emails atingido."

        partes = parametros.split("|", 3)
        if len(partes) < 4:
            return "[ERRO] Formato: destinatario|assunto|corpo|caminho_do_anexo"

        destinatario = partes[0].strip()
        assunto = partes[1].strip()
        corpo = partes[2].strip()
        caminho_anexo = partes[3].strip()

        if "@" not in destinatario:
            return f"[ERRO] Email inválido: {destinatario}"

        # Resolver caminho do anexo
        if not os.path.isabs(caminho_anexo):
            caminho_anexo = os.path.join(OUTPUT_DIR, caminho_anexo)

        if not os.path.exists(caminho_anexo):
            return f"[ERRO] Arquivo não encontrado: {caminho_anexo}"

        # Verificar tamanho (max 10 MB para SES)
        tamanho = os.path.getsize(caminho_anexo)
        if tamanho > 10 * 1024 * 1024:
            return f"[ERRO] Arquivo muito grande ({tamanho / 1024 / 1024:.1f} MB). Máximo: 10 MB."

        try:
            cliente = boto3.client(
                "ses",
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )

            # Montar email MIME com anexo
            msg = MIMEMultipart("mixed")
            msg["Subject"] = assunto
            msg["From"] = self.remetente
            msg["To"] = destinatario

            # Corpo do email
            is_html = "<" in corpo and ">" in corpo
            if is_html:
                corpo_mime = MIMEText(corpo, "html", "utf-8")
            else:
                corpo_mime = MIMEText(corpo, "plain", "utf-8")
            msg.attach(corpo_mime)

            # Anexo
            nome_arquivo = os.path.basename(caminho_anexo)
            with open(caminho_anexo, "rb") as f:
                anexo = MIMEApplication(f.read())
            anexo.add_header(
                "Content-Disposition", "attachment",
                filename=nome_arquivo,
            )
            msg.attach(anexo)

            # Enviar via SES raw
            resposta = cliente.send_raw_email(
                Source=self.remetente,
                Destinations=[destinatario],
                RawMessage={"Data": msg.as_string()},
            )

            self.emails_enviados += 1
            mid = resposta.get("MessageId", "N/A")
            tamanho_kb = tamanho / 1024

            logger.info(
                f"[EMAIL+ANEXO] Enviado para {destinatario} | "
                f"Anexo: {nome_arquivo} ({tamanho_kb:.1f} KB) | ID: {mid}"
            )

            return (
                f"[OK] Email com anexo enviado!\n"
                f"  Para: {destinatario}\n"
                f"  Assunto: {assunto}\n"
                f"  Anexo: {nome_arquivo} ({tamanho_kb:.1f} KB)\n"
                f"  MessageId: {mid}"
            )
        except ClientError as e:
            return f"[ERRO] {e.response['Error']['Message']}"
        except Exception as e:
            return f"[ERRO] {str(e)}"


def criar_ferramenta_email() -> EnviarEmailTool:
    """Cria a ferramenta de email simples."""
    return EnviarEmailTool(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        remetente=os.getenv("AWS_SES_SENDER", ""),
    )


def criar_ferramenta_email_com_anexo() -> EnviarEmailComAnexoTool:
    """Cria a ferramenta de email com anexo."""
    return EnviarEmailComAnexoTool(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        remetente=os.getenv("AWS_SES_SENDER", ""),
    )
