import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import mercadopago  # BIBLIOTECA DE PAGAMENTOS
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

try:
    from email_service import enviar_email_licenca
except ImportError:
    print("⚠️ AVISO: email_service.py não encontrado! O envio de e-mail falhará.")

    def enviar_email_licenca(
        email_cliente: str, nome_cliente: str, chave_licenca: str, link_download: str
    ) -> bool:
        """Mock da função de envio de email para desenvolvimento."""
        logger.info(f"MOCK EMAIL: Para {email_cliente} | Chave: {chave_licenca}")
        return False


# Configuração de Logs (Para ver o que acontece no Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- VARIÁVEIS DE VENDA ---
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")  # A senha que colamos no Render
LINK_DOWNLOAD_PADRAO = os.environ.get(
    "LINK_DOWNLOAD_BOT", "https://seu-link.com/bot.zip"
)

# --- BANCO DE DADOS ---
if database_url := os.environ.get("DATABASE_URL"):
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///server.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- TABELAS (MODELOS) ---


class Licenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Dados de Controle
    chave = db.Column(db.String(50), unique=True, nullable=False)
    ativa = db.Column(db.Boolean, default=True)
    data_expiracao = db.Column(db.DateTime, nullable=True)  # None = Vitalício

    # Dados do Cliente
    cliente_nome = db.Column(db.String(100))
    email_cliente = db.Column(db.String(120), nullable=True)  # NOVO: Para suporte
    payment_id = db.Column(db.String(50), unique=True, nullable=True)  # NOVO: Segurança
    hwid = db.Column(db.String(100), nullable=True)

    def __init__(
        self,
        chave,
        cliente_nome,
        email_cliente=None,
        payment_id=None,
        dias_validade=None,
    ):
        self.chave = chave
        self.cliente_nome = cliente_nome
        self.email_cliente = email_cliente
        self.payment_id = payment_id
        self.hwid = None
        self.ativa = True

        if dias_validade:
            # CORREÇÃO SOURCERY: Usar datetime com fuso horário explícito (UTC)
            self.data_expiracao = datetime.now(timezone.utc) + timedelta(
                days=dias_validade
            )
        else:
            self.data_expiracao = None


class LogBot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    hwid = db.Column(db.String(100))
    tipo = db.Column(db.String(50))
    dados = db.Column(db.String(500))
    lucro = db.Column(db.Float, default=0.0)

    def __init__(self, sessao_id, hwid, tipo, dados, lucro=0.0):
        self.sessao_id = sessao_id
        self.hwid = hwid
        self.tipo = tipo
        self.dados = str(dados)
        self.lucro = lucro


# --- ROTAS DE UTILIDADE ---


@app.route("/")
def home():
    return "CrashBot API V2 - Sistema de Vendas Ativo 🚀"


@app.route("/admin/reset_total_db", methods=["GET"])
def reset_total_db():
    """⚠️ Reseta o banco para aplicar as novas colunas de email e pagamento."""
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
        return "✅ Banco RESETADO. Novas colunas criadas com sucesso!", 200
    except Exception as e:
        return f"Erro: {str(e)}", 500


# --- ROTAS DO BOT (CLIENTE) ---


@app.route("/validar", methods=["POST"])
def validar_licenca():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"status": "erro"}), 400

    chave = dados.get("chave")
    hwid = dados.get("hwid")

    licenca = Licenca.query.filter_by(chave=chave).first()

    if not licenca:
        return jsonify({"status": "erro", "mensagem": "Chave inválida"}), 403
    if not licenca.ativa:
        return jsonify({"status": "erro", "mensagem": "Bloqueada"}), 403

    # --- CORREÇÃO DE DATA (FUSO HORÁRIO) ---
    if licenca.data_expiracao:
        # 1. Pega a data do banco
        expiracao = licenca.data_expiracao

        # 2. Se ela vier sem fuso (Naive), colocamos o selo UTC nela
        if expiracao.tzinfo is None:
            expiracao = expiracao.replace(tzinfo=timezone.utc)

        # 3. Agora comparamos maçã com maçã (Aware vs Aware)
        if expiracao < datetime.now(timezone.utc):
            return jsonify({"status": "erro", "mensagem": "Expirada"}), 403

    if licenca.hwid is None:
        licenca.hwid = hwid
        db.session.commit()
        return jsonify({"status": "sucesso", "mensagem": "Ativada!"})
    elif licenca.hwid != hwid:
        return jsonify({"status": "erro", "mensagem": "HWID Incorreto"}), 403

    return jsonify({"status": "sucesso", "mensagem": "OK"})


@app.route("/telemetria/log", methods=["POST"])
def receber_log():
    # Tenta processar o log
    try:
        # CORREÇÃO SOURCERY: O operador Walrus (:=) atribui e testa na mesma linha
        if dados := request.get_json(silent=True):
            novo_log = LogBot(
                sessao_id=dados.get("sessao_id", "?"),
                hwid=dados.get("hwid", "?"),
                tipo=dados.get("tipo", "info"),
                dados=dados.get("dados", ""),
                lucro=dados.get("lucro", 0.0),
            )
            db.session.add(novo_log)
            db.session.commit()
            return jsonify({"status": "ok"})

    except Exception as e:
        # 1. Registra o erro específico
        logger.error(f"Erro ao salvar log: {e}")

        # 2. Reseta a conexão com o banco para não travar
        db.session.rollback()

    # Retorna erro se falhou ou se não vieram dados
    return jsonify({"status": "erro"}), 400


@app.route("/webhook/mercadopago", methods=["POST"])
def webhook_mp():
    # 1. Tenta pegar ID da URL (Padrão GET)
    payment_id = request.args.get("id") or request.args.get("data.id")

    # 2. Se não achou, tenta pegar do JSON (Padrão POST) de forma SEGURA e OTIMIZADA
    if not payment_id and request.is_json:
        # Sourcery: Usando 'named expression' (:=) para atribuir e checar numa linha só
        if data := request.get_json(silent=True):
            if data.get("action") == "payment.created" or data.get("type") == "payment":
                # Blindagem contra erro de tipo do Pylance
                raw_data = data.get("data")
                if isinstance(raw_data, dict):
                    payment_id = raw_data.get("id")

    if not payment_id:
        return jsonify({"status": "ignored"}), 200

    logger.info(f"🔔 Webhook recebido: {payment_id}")

    # 3. Verificar se é real (Segurança)
    try:
        if not MP_ACCESS_TOKEN:
            logger.error("❌ Token MP não configurado!")
            return jsonify({"error": "config missing"}), 500

        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        payment_info = sdk.payment().get(payment_id)

        if payment_info["status"] == 404:
            return jsonify({"error": "not found"}), 404

        response = payment_info["response"]
        status = response.get("status")

        email = response.get("payer", {}).get("email")
        nome = response.get("payer", {}).get("first_name", "Cliente")
        desc = response.get("description", "")

        logger.info(f"🔎 Status: {status} | Email: {email}")

        # 4. Se Aprovado -> Entregar Produto
        if status == "approved":
            # Evitar duplicidade
            if Licenca.query.filter_by(payment_id=str(payment_id)).first():
                return jsonify({"status": "ok", "msg": "already processed"}), 200

            # Gerar Chave
            nova_chave = f"KEY-{str(uuid.uuid4()).upper()[:14]}"
            dias = 30 if "Mensal" in desc else None

            # Salvar no Banco
            nova_licenca = Licenca(
                chave=nova_chave,
                cliente_nome=nome,
                email_cliente=email,
                payment_id=str(payment_id),
                dias_validade=dias,
            )
            db.session.add(nova_licenca)
            db.session.commit()

            # Enviar Email
            enviar_email_licenca(email, nome, nova_chave, LINK_DOWNLOAD_PADRAO)
            logger.info("✅ Venda concluída e entregue!")

            return jsonify({"status": "created"}), 201

    except Exception as e:
        logger.error(f"❌ Erro Webhook: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok"}), 200


# --- 🛒 NOVA ROTA: CRIAR PAGAMENTO (PARA A LOJA) 🛒 ---
@app.route("/api/pagamento/criar", methods=["POST"])
def criar_pagamento():
    """
    Recebe dados da loja e gera um link de checkout do Mercado Pago.
    Payload esperado: { "email": "cliente@email.com", "plano": "mensal" }
    """
    try:
        dados = request.get_json()
        email_comprador = dados.get("email")
        plano = dados.get("plano", "mensal")

        # URL base do servidor (para o Webhook)
        # Se estiver no Render, ele usa a própria URL. Se local, define uma.
        BASE_URL = "https://crash-api-jose.onrender.com"

        # Define preço baseado no plano
        if plano == "mensal":
            preco = 99.90
            titulo = "Licença CrashBot (Mensal)"
        else:
            preco = 199.90
            titulo = "Licença CrashBot (Vitalício)"

        if not MP_ACCESS_TOKEN:
            return jsonify({"erro": "Servidor sem token MP"}), 500

        # 1. Configura o SDK
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

        # 2. Cria a preferência de pagamento
        preference_data = {
            "items": [
                {
                    "id": f"bot-{plano}",
                    "title": titulo,
                    "quantity": 1,
                    "currency_id": "BRL",
                    # CORREÇÃO SOURCERY: Removemos o float(), pois 'preco' já é float
                    "unit_price": preco,
                }
            ],
            "payer": {"email": email_comprador},
            # Para onde o cliente vai depois de pagar
            "back_urls": {
                "success": "https://google.com",  # Futuramente sua página de 'Obrigado'
                "failure": "https://google.com",
                "pending": "https://google.com",
            },
            "auto_return": "approved",
            # AQUI ESTÁ A MÁGICA: O Webhook que configuramos
            "notification_url": f"{BASE_URL}/webhook/mercadopago",
        }

        preference_response = sdk.preference().create(preference_data)

        # Extrai o link de pagamento
        checkout_url = preference_response["response"]["init_point"]
        sandbox_url = preference_response["response"]["sandbox_init_point"]

        return jsonify(
            {
                "status": "sucesso",
                "checkout_url": checkout_url,
                "sandbox_url": sandbox_url,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao criar pagamento: {e}")
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
