import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- CONFIGURAÇÕES DO CARTEIRO ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMETENTE = "contato.tucunare.bot@gmail.com"
# COLE SUA SENHA DE 16 LETRAS AQUI (Mantenha as aspas)
SENHA_APP = os.environ.get("EMAIL_SENHA_APP", "ucgz cewf sspu jpwn")


def _enviar_smtp_gmail(destinatario, assunto, corpo_html):
    """
    Função auxiliar (PRIVADA) que faz a conexão técnica com o Gmail.
    É AQUI que usamos o 'smtplib' e 'ssl', resolvendo os erros F401.
    """
    try:
        # 1. Monta o objeto da mensagem
        mensagem = MIMEMultipart()
        mensagem["From"] = f"Suporte Tucunaré <{EMAIL_REMETENTE}>"
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        mensagem.attach(MIMEText(corpo_html, "html"))

        # 2. Cria contexto de segurança (Uso do import 'ssl')
        contexto = ssl.create_default_context()

        # 3. Conecta e Envia (Uso do import 'smtplib')
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=contexto)  # Criptografa a conexão
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(mensagem)

        print(f"✅ E-mail enviado com sucesso para: {destinatario}")
        return True

    except Exception as e:
        print(f"❌ Erro técnico ao enviar e-mail: {e}")
        return False


def enviar_email_licenca(email_cliente, nome_cliente, chave_licenca, link_download):
    """
    Envia um e-mail HTML com a chave e link.
    Agora aceita 4 parâmetros obrigatórios.
    """
    assunto = "🚀 Acesso Liberado: Seu Bot Chegou!"

    # REMOVEMOS A LINHA QUE TINHA O LINK FIXO AQUI
    # Agora o link_download vem direto dos parenteses da função (argumento)

    # O Corpo do email em HTML
    corpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <h2 style="color: #2E86C1;">Olá, {nome_cliente}!</h2>
            <p>Seu pagamento foi confirmado com sucesso. Bem-vindo ao time!</p>

            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 5px solid #28a745; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #666;">Sua Chave de Acesso Única:</p>
                <h1 style="margin: 10px 0; font-family: monospace; color: #000; letter-spacing: 2px;">{chave_licenca}</h1>
            </div>

            <h3>📥 Como Instalar:</h3>
            <ol style="line-height: 1.6;">
                <li><a href="{link_download}" style="color: #2E86C1; font-weight: bold;">Clique aqui para baixar o Robô</a></li>
                <li>Extraia a pasta no seu computador.</li>
                <li>Abra o arquivo <b>license_key.txt</b>.</li>
                <li>Cole a chave acima dentro dele e salve.</li>
                <li>Execute o arquivo <b>CrashBot.exe</b>.</li>
            </ol>

            <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="font-size: 12px; color: #999;">Este é um e-mail automático. Não responda.</p>
        </div>
    </body>
    </html>
    """

    # Chama a função técnica de envio (certifique-se de que a função _enviar_smtp_gmail existe acima desta)
    return _enviar_smtp_gmail(email_cliente, assunto, corpo_html)


# --- TESTE RÁPIDO ---
# --- TESTE RÁPIDO ---
if __name__ == "__main__":
    print("Testando envio de e-mail...")
    # Agora passamos os 4 argumentos obrigatórios (incluindo o link no final)
    enviar_email_licenca(
        "josediogo8@hotmail.com",
        "Teste Admin",
        "ABCD-1234-TEST-KEY",
        "https://google.com",
    )
