"""
Admin Notification Service
Serviço para notificar admin sobre eventos importantes:
- Novo cliente/venda
- Licença expirando
- Problemas técnicos
"""

import os
from datetime import datetime
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class AdminNotificationService:
    """Serviço de notificações para administradores."""

    def __init__(self):
        # Email admin
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@tucunarebot.com.br")
        self.resend_api_key = os.getenv("RESEND_API_KEY")

        # Telegram admin
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

        # WhatsApp admin
        self.whatsapp_admin_number = os.getenv("WHATSAPP_ADMIN_NUMBER")
        self.whatsapp_instance_id = os.getenv("ZAPI_INSTANCE_ID")
        self.whatsapp_token = os.getenv("ZAPI_TOKEN")

    # =========================================================================
    # NOTIFICAÇÃO DE NOVA VENDA
    # =========================================================================

    async def notificar_nova_venda(
        self,
        cliente_nome: str,
        cliente_email: str,
        plano: str,
        valor: float,
        chave_licenca: str,
        is_trial: bool = False,
    ):
        """
        Notifica o admin sobre uma nova venda.
        Envia por email, Telegram e WhatsApp.
        """
        tipo_venda = "🎁 TRIAL" if is_trial else "💰 VENDA"

        mensagem_texto = f"""
{tipo_venda} - NOVO CLIENTE!

👤 Nome: {cliente_nome}
📧 Email: {cliente_email}
📦 Plano: {plano.upper()}
💵 Valor: R$ {valor:.2f}
🔑 Licença: {chave_licenca}
⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """.strip()

        # Enviar por todos os canais disponíveis
        tasks_results = []

        # 1. Email
        if self.resend_api_key and self.admin_email:
            result = await self._enviar_email_nova_venda(
                cliente_nome,
                cliente_email,
                plano,
                valor,
                chave_licenca,
                is_trial,
            )
            tasks_results.append(("email", result))

        # 2. Telegram
        if self.telegram_bot_token and self.telegram_admin_chat_id:
            result = await self._enviar_telegram(mensagem_texto)
            tasks_results.append(("telegram", result))

        # 3. WhatsApp
        if self.whatsapp_admin_number and self.whatsapp_instance_id:
            result = await self._enviar_whatsapp(mensagem_texto)
            tasks_results.append(("whatsapp", result))

        return tasks_results

    async def _enviar_email_nova_venda(
        self,
        cliente_nome: str,
        cliente_email: str,
        plano: str,
        valor: float,
        chave_licenca: str,
        is_trial: bool,
    ) -> bool:
        """Envia email formatado sobre nova venda."""

        tipo_badge = "TRIAL GRATUITO" if is_trial else "VENDA"
        badge_color = "#10B981" if is_trial else "#3B82F6"

        data_fmt = datetime.now().strftime("%d/%m/%Y às %H:%M")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Segoe UI', sans-serif;
                    background: #0f172a;
                    color: #fff;
                    padding: 20px;
                    margin: 0;
                }}
                .container {{
                    max-width: 500px;
                    margin: 0 auto;
                    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                    border-radius: 16px;
                    padding: 30px;
                    border: 1px solid #334155;
                }}
                .badge {{
                    display: inline-block;
                    background: {badge_color};
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #10B981;
                    margin: 0 0 20px 0;
                    font-size: 24px;
                }}
                .info-card {{
                    background: rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 20px;
                    margin: 15px 0;
                }}
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }}
                .info-row:last-child {{
                    border-bottom: none;
                }}
                .label {{
                    color: #94a3b8;
                }}
                .value {{
                    color: #fff;
                    font-weight: 600;
                }}
                .valor-destaque {{
                    font-size: 28px;
                    color: #10B981;
                    font-weight: bold;
                    text-align: center;
                    margin: 20px 0;
                }}
                .licenca-box {{
                    background: #0f172a;
                    border: 2px dashed #8B5CF6;
                    padding: 15px;
                    text-align: center;
                    border-radius: 8px;
                    font-family: monospace;
                    font-size: 18px;
                    color: #8B5CF6;
                    letter-spacing: 2px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <span class="badge">{tipo_badge}</span>
                <h1>🎉 Nova Venda!</h1>
                <div class="info-card">
                    <div class="info-row">
                        <span class="label">Cliente:</span>
                        <span class="value">{cliente_nome}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Email:</span>
                        <span class="value">{cliente_email}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Plano:</span>
                        <span class="value">{plano.upper()}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Data:</span>
                        <span class="value">{data_fmt}</span>
                    </div>
                </div>
                <div class="valor-destaque">
                    R$ {valor:.2f}
                </div>
                <p style="color: #94a3b8; text-align: center; margin-bottom: 10px;">
                    Chave da Licença:
                </p>
                <div class="licenca-box">
                    {chave_licenca}
                </div>
            </div>
        </body>
        </html>
        """

        try:
            subject_line = f"💰 Nova Venda! {cliente_nome} - {plano.upper()}"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": "CrashBot <vendas@tucunarebot.com.br>",
                        "to": [self.admin_email],
                        "subject": subject_line,
                        "html": html,
                    },
                    timeout=30.0,
                )
                return response.status_code in [200, 201]
        except Exception as e:
            print(f"❌ Erro ao enviar email de nova venda: {e}")
            return False

    async def _enviar_telegram(self, mensagem: str) -> bool:
        """Envia mensagem via Telegram."""
        if not self.telegram_bot_token or not self.telegram_admin_chat_id:
            return False

        base_url = "https://api.telegram.org"
        endpoint = f"/bot{self.telegram_bot_token}/sendMessage"
        url = f"{base_url}{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params={
                        "chat_id": self.telegram_admin_chat_id,
                        "text": mensagem,
                        "parse_mode": "Markdown",
                    },
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro ao enviar Telegram: {e}")
            return False

    async def _enviar_whatsapp(self, mensagem: str) -> bool:
        """Envia mensagem via WhatsApp (Z-API)."""
        if not all(
            [
                self.whatsapp_admin_number,
                self.whatsapp_instance_id,
                self.whatsapp_token,
            ]
        ):
            return False

        # Correção E501: Quebrando URL longa
        base_url = "https://api.z-api.io/instances"
        inst_id = self.whatsapp_instance_id
        token = self.whatsapp_token
        url = f"{base_url}/{inst_id}/token/{token}/send-text"

        # Correção Pylance: Garantindo que é string para o filter
        # Se for None (embora o 'if not all' acima previna), usamos string vazia
        raw_number = self.whatsapp_admin_number or ""
        phone = "".join(filter(str.isdigit, raw_number))

        if len(phone) == 11:
            phone = f"55{phone}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={"phone": phone, "message": mensagem},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro ao enviar WhatsApp: {e}")
            return False

    # =========================================================================
    # OUTRAS NOTIFICAÇÕES
    # =========================================================================

    async def notificar_licenca_expirando(
        self,
        cliente_nome: str,
        cliente_email: str,
        dias_restantes: int,
        chave_licenca: str,
    ):
        """Notifica sobre licença prestes a expirar."""
        mensagem = f"""
⚠️ LICENÇA EXPIRANDO

👤 Cliente: {cliente_nome}
📧 Email: {cliente_email}
🔑 Licença: {chave_licenca}
⏳ Dias restantes: {dias_restantes}

💡 Considere entrar em contato para renovação.
        """.strip()

        await self._enviar_telegram(mensagem)

    async def notificar_erro_sistema(
        self,
        erro: str,
        contexto: Optional[str] = None,
    ):
        """Notifica sobre erro crítico no sistema."""
        mensagem = f"""
🚨 ERRO NO SISTEMA

❌ Erro: {erro}
📍 Contexto: {contexto or 'N/A'}
⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """.strip()

        await self._enviar_telegram(mensagem)


# Instância global
admin_notifications = AdminNotificationService()
