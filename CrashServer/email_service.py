import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- CONFIGURAÇÕES DO CARTEIRO ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMETENTE = "contato.tucunare.bot@gmail.com"
# COLE SUA SENHA DE 16 LETRAS AQUI (Mantenha as aspas)
SENHA_APP = "ucgz cewf sspu jpwn"


def _criar_mensagem_email(email_cliente, nome_cliente, chave_licenca):
    """
    Função auxiliar que apenas monta o objeto de e-mail (HTML e Cabeçalhos).
    Isso resolve o aviso do Sourcery ao tirar complexidade da função principal.
    """
    assunto = "🚀 Acesso Liberado: Seu Bot Chegou!"
    link_download = "https://seu-link-de-download-aqui.com"

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
                <li><a href="{link_download}" style="color: #2E86C1; font-weight: bold;">Clique aqui para baixar o Robô (ZIP)</a></li>
                <li>Extraia a pasta no seu computador.</li>
                <li>Abra o arquivo <b>license_key.txt</b>.</li>
                <li>Apague o texto que estiver lá e cole a sua chave acima.</li>
                <li>Execute o arquivo <b>CrashBot.exe</b>.</li>
            </ol>

            <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="font-size: 12px; color: #999;">Este é um e-mail automático. Se precisar de ajuda, responda esta mensagem.</p>
        </div>
    </body>
    </html>
    """

    mensagem = MIMEMultipart()
    mensagem["From"] = f"Suporte Tucunaré <{EMAIL_REMETENTE}>"
    mensagem["To"] = email_cliente
    mensagem["Subject"] = assunto
    mensagem.attach(MIMEText(corpo_html, "html"))

    return mensagem


def enviar_email_licenca(email_cliente, nome_cliente, chave_licenca):
    """
    Envia o e-mail usando a função auxiliar para montar a mensagem.
    """
    try:
        # 1. Monta a mensagem (Código extraído para satisfazer o Sourcery)
        mensagem = _criar_mensagem_email(email_cliente, nome_cliente, chave_licenca)

        # 2. Conecta e Envia
        contexto = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=contexto)
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(mensagem)

        print(f"✅ E-mail enviado com sucesso para: {email_cliente}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False


# --- TESTE RÁPIDO ---
if __name__ == "__main__":
    print("Testando envio de e-mail...")
    # Coloque seu próprio e-mail pessoal aqui para testar
    enviar_email_licenca("josediogo8@hotmail.com", "Teste Admin", "ABCD-1234-TEST-KEY")
