"""
Serviço de Email — Amazon SES (reutilizável)

Funções:
- enviar_email_html: envia email com HTML bonito
- enviar_convite: envia convite para novo usuário
- enviar_notificacao: envia notificação genérica

Configuração via .env:
- AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- AWS_SES_SENDER (remetente verificado)
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("synerium.email")

# URL base do sistema (produção ou local)
BASE_URL = os.getenv("SYNERIUM_BASE_URL", "https://synerium-factory.objetivasolucao.com.br")

# Configuração SES
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_SES_SENDER = os.getenv("AWS_SES_SENDER", "noreply@objetivasolucao.com.br")


def _get_ses_client():
    """Cria cliente SES com credenciais do .env."""
    return boto3.client(
        "ses",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def enviar_email_html(
    destinatario: str,
    assunto: str,
    html: str,
    texto_fallback: str = "",
    remetente: str = "",
) -> dict:
    """
    Envia email HTML via Amazon SES.

    Returns:
        dict com 'sucesso', 'message_id' ou 'erro'
    """
    sender = remetente or f"Synerium Factory <{AWS_SES_SENDER}>"

    try:
        client = _get_ses_client()

        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = sender
        msg["To"] = destinatario

        # Texto fallback
        if texto_fallback:
            msg.attach(MIMEText(texto_fallback, "plain", "utf-8"))

        # HTML principal
        msg.attach(MIMEText(html, "html", "utf-8"))

        response = client.send_raw_email(
            Source=sender,
            Destinations=[destinatario],
            RawMessage={"Data": msg.as_string()},
        )

        message_id = response.get("MessageId", "")
        logger.info(f"[EMAIL] Enviado para {destinatario} — ID: {message_id} — Assunto: {assunto}")

        return {"sucesso": True, "message_id": message_id}

    except ClientError as e:
        erro = e.response["Error"]["Message"]
        logger.error(f"[EMAIL] Falha ao enviar para {destinatario}: {erro}")
        return {"sucesso": False, "erro": erro}
    except Exception as e:
        logger.error(f"[EMAIL] Erro inesperado: {e}")
        return {"sucesso": False, "erro": str(e)}


def enviar_convite(
    nome: str,
    email: str,
    token: str,
    cargo: str = "",
    convidado_por: str = "Thiago Xavier",
) -> dict:
    """
    Envia email de convite para novo usuário.
    """
    link = f"{BASE_URL}/registrar?token={token}"

    assunto = "Bem-vindo ao Synerium Factory — Seu convite para acessar o sistema"

    html = _template_convite(
        nome=nome,
        email=email,
        link=link,
        cargo=cargo,
        convidado_por=convidado_por,
    )

    texto = (
        f"Olá {nome},\n\n"
        f"Você foi convidado(a) por {convidado_por} para acessar o Synerium Factory.\n\n"
        f"Acesse o link para criar sua senha e começar: {link}\n\n"
        f"Este convite expira em 7 dias.\n\n"
        f"Equipe Synerium Factory — Objetiva Solução"
    )

    resultado = enviar_email_html(
        destinatario=email,
        assunto=assunto,
        html=html,
        texto_fallback=texto,
    )

    if resultado["sucesso"]:
        logger.info(f"[CONVITE] Email enviado para {nome} ({email}) — token: {token[:8]}...")
    else:
        logger.error(f"[CONVITE] Falha ao enviar para {nome} ({email}): {resultado.get('erro')}")

    return resultado


def _template_convite(nome: str, email: str, link: str, cargo: str, convidado_por: str) -> str:
    """Gera HTML premium do email de convite."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Convite Synerium Factory</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0f;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0f;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#111118;border-radius:16px;border:1px solid rgba(255,255,255,0.06);overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#10b981 0%,#059669 100%);padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.02em;">
                Synerium Factory
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">
                Centro de Comando — Objetiva Solução
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 8px;color:#f8f8f8;font-size:20px;font-weight:600;">
                Olá, {nome}! 👋
              </h2>
              <p style="margin:0 0 24px;color:#9ca3af;font-size:14px;line-height:1.6;">
                Você foi convidado(a) por <strong style="color:#10b981;">{convidado_por}</strong>
                para acessar o <strong style="color:#f8f8f8;">Synerium Factory</strong>
                {f' como <strong style="color:#f8f8f8;">{cargo}</strong>' if cargo else ''}.
              </p>

              <p style="margin:0 0 16px;color:#9ca3af;font-size:14px;line-height:1.6;">
                O Synerium Factory é a plataforma de agentes IA da Objetiva Solução.
                Com ele, você terá seu próprio squad de agentes inteligentes para
                multiplicar sua produtividade.
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin:32px 0;">
                <tr>
                  <td align="center">
                    <a href="{link}"
                       style="display:inline-block;background:linear-gradient(135deg,#10b981,#059669);
                              color:#ffffff;text-decoration:none;font-size:16px;font-weight:600;
                              padding:16px 48px;border-radius:12px;letter-spacing:0.02em;">
                      Aceitar Convite
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Info box -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                            border-radius:12px;margin:24px 0;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0 0 8px;color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;">
                      Detalhes do convite
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color:#9ca3af;font-size:13px;padding:4px 0;">Email:</td>
                        <td style="color:#f8f8f8;font-size:13px;padding:4px 0;text-align:right;font-family:monospace;">{email}</td>
                      </tr>
                      {f'<tr><td style="color:#9ca3af;font-size:13px;padding:4px 0;">Cargo:</td><td style="color:#f8f8f8;font-size:13px;padding:4px 0;text-align:right;">{cargo}</td></tr>' if cargo else ''}
                      <tr>
                        <td style="color:#9ca3af;font-size:13px;padding:4px 0;">Convidado por:</td>
                        <td style="color:#10b981;font-size:13px;padding:4px 0;text-align:right;">{convidado_por}</td>
                      </tr>
                      <tr>
                        <td style="color:#9ca3af;font-size:13px;padding:4px 0;">Expira em:</td>
                        <td style="color:#f59e0b;font-size:13px;padding:4px 0;text-align:right;">7 dias</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:24px 0 0;color:#6b7280;font-size:12px;line-height:1.5;">
                Se o botão não funcionar, copie e cole este link no seu navegador:<br>
                <a href="{link}" style="color:#10b981;word-break:break-all;font-size:11px;">{link}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:rgba(255,255,255,0.02);padding:24px 40px;border-top:1px solid rgba(255,255,255,0.04);">
              <p style="margin:0 0 4px;color:#4b5563;font-size:11px;">
                Synerium Factory — Objetiva Solução Empresarial
              </p>
              <p style="margin:0 0 4px;color:#374151;font-size:10px;">
                Ipatinga, MG · objetivasolucao.com.br
              </p>
              <p style="margin:12px 0 0;color:#374151;font-size:10px;">
                Dúvidas? Responda este email ou entre em contato com thiago@objetivasolucao.com.br
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
