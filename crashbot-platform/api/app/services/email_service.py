"""
Serviço de Email
Envia emails usando Resend ou SMTP.
"""

import os
from typing import Optional

import httpx
from app.config import settings


async def enviar_email(
    para: str,
    assunto: str,
    html: str,
    texto: Optional[str] = None,
) -> bool:
    """
    Envia um email usando Resend API.

    Args:
        para: Email do destinatário
        assunto: Assunto do email
        html: Conteúdo HTML do email
        texto: Conteúdo texto puro (opcional)

    Returns:
        bool: True se enviado com sucesso
    """
    api_key = settings.RESEND_API_KEY or os.getenv("RESEND_API_KEY")

    if not api_key:
        print("⚠️ RESEND_API_KEY não configurada - email não enviado")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "TucunareBot <contato@tucunarebot.com.br>",
                    "to": [para],
                    "subject": assunto,
                    "html": html,
                    "text": texto,
                },
                timeout=30.0,
            )

            if response.status_code in [200, 201]:
                print(f"✅ Email enviado para {para}")
                return True
            else:
                print(
                    f"❌ Erro ao enviar email: {response.status_code} - {response.text}"
                )
                return False

    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False


def template_licenca_criada(
    nome: str,
    email: str,
    senha: str,
    chave_licenca: str,
    plano: str,
    dias: int,
) -> str:
    """
    Gera o HTML do email de licença criada.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #0a0a0f;
                color: #ffffff;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-radius: 16px;
                padding: 40px;
                border: 1px solid #333;
            }}
            .logo {{
                text-align: center;
                font-size: 28px;
                font-weight: bold;
                color: #a855f7;
                margin-bottom: 30px;
            }}
            h1 {{
                color: #a855f7;
                text-align: center;
                margin-bottom: 30px;
            }}
            .box {{
                background: rgba(168, 85, 247, 0.1);
                border: 1px solid #a855f7;
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
            }}
            .box-title {{
                color: #a855f7;
                font-weight: bold;
                margin-bottom: 15px;
                font-size: 16px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            .info-label {{
                color: #888;
            }}
            .info-value {{
                color: #fff;
                font-weight: bold;
            }}
            .licenca-key {{
                background: #0a0a0f;
                border: 2px dashed #a855f7;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                font-size: 24px;
                font-family: monospace;
                color: #a855f7;
                letter-spacing: 2px;
                margin: 20px 0;
            }}
            .button {{
                display: block;
                width: 100%;
                background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
                color: white;
                text-align: center;
                padding: 16px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                font-size: 16px;
                margin-top: 30px;
            }}
            .footer {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #333;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🤖 CrashBot</div>

            <h1>Bem-vindo, {nome}! 🎉</h1>

            <p style="text-align: center; color: #ccc; font-size: 16px;">
                Seu pagamento foi aprovado e sua licença está pronta!
            </p>

            <div class="box">
                <div class="box-title">📋 Sua Licença</div>
                <div class="licenca-key">{chave_licenca}</div>
                <p style="text-align: center; color: #888; font-size: 14px;">
                    Use esta chave para ativar o bot no seu computador
                </p>
            </div>

            <div class="box">
                <div class="box-title">🔐 Dados de Acesso ao Painel</div>
                <div class="info-row">
                    <span class="info-label">Email:</span>
                    <span class="info-value">{email}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Senha:</span>
                    <span class="info-value">{senha}</span>
                </div>
                <p style="color: #f59e0b; font-size: 12px; margin-top: 10px;">
                    ⚠️ Recomendamos alterar sua senha após o primeiro acesso.
                </p>
            </div>

            <div class="box">
                <div class="box-title">📦 Detalhes do Plano</div>
                <div class="info-row">
                    <span class="info-label">Plano:</span>
                    <span class="info-value">{plano.capitalize()}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Duração:</span>
                    <span class="info-value">{dias} dias</span>
                </div>
            </div>

            <a href="https://crashbot-loja.vercel.app/login" class="button">
                Acessar Meu Painel
            </a>

            <div class="footer">
                <p>Precisa de ajuda? Entre em contato pelo WhatsApp.</p>
                <p>© 2025 CrashBot. Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
