"""
🛡️ CRASHBOT STORE API V2.0
API Flask para gestão de licenças com integração Mercado Pago

Melhorias da V2:
- Segurança reforçada (autenticação admin, rate limiting)
- Código limpo e documentado
- Compatibilidade total com dashboard_v2.py
- Validações robustas
- Logs estruturados
- Tratamento de erros aprimorado
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Tuple

import mercadopago
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request  # Removido 'abort'
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# =============================================================================
# SERVIÇO DE EMAIL (COM FALLBACK SEGURO)
# =============================================================================

try:
    from email_service import enviar_email_licenca

    EMAIL_DISPONIVEL = True
    logger.info("✅ Serviço de email carregado com sucesso")
except ImportError:
    EMAIL_DISPONIVEL = False
    logger.warning("⚠️ email_service.py não encontrado - emails desabilitados")

    def enviar_email_licenca(
        email_cliente: str, nome_cliente: str, chave_licenca: str, link_download: str
    ) -> bool:
        """Mock de email quando serviço não está disponível."""
        logger.info(f"📧 MOCK EMAIL → {email_cliente} | Chave: {chave_licenca}")
        return False


# =============================================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================================

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# =============================================================================
# CONFIGURAÇÕES DA APLICAÇÃO
# =============================================================================


class Config:
    """Centraliza todas as configurações da aplicação."""

    # Mercado Pago
    MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

    # URLs
    BASE_URL = (
        os.getenv("BASE_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or "https://crash-api-jose.onrender.com"
    )

    LINK_DOWNLOAD_BOT = os.getenv("LINK_DOWNLOAD_BOT", "https://google.com")
    LOJA_URL = os.getenv("LOJA_URL", "https://sua-loja.com")

    # Segurança
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD_HASH = os.getenv(
        "ADMIN_PASSWORD_HASH",
        # Hash de "admin123" - TROCAR EM PRODUÇÃO!
        generate_password_hash("admin123"),
    )
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")

    # Banco de Dados
    @staticmethod
    def get_database_uri():
        """Retorna URI do banco com tratamento de URL."""
        database_url = os.environ.get("DATABASE_URL")

        if not database_url:
            logger.warning("⚠️ DATABASE_URL não definida, usando SQLite local")
            return "sqlite:///crashbot_server.db"

        # Corrige formato postgres:// para postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        return database_url

    # Tabela de Preços (Centralizada)
    PRECOS_PLANOS = {
        "experimental": {
            "preco": 4.99,
            "dias": 7,
            "titulo": "CrashBot Experimental (7 Dias)",
        },
        "semanal": {
            "preco": 149.00,
            "dias": 7,
            "titulo": "CrashBot VIP Semanal (7 Dias)",
        },
        "mensal": {
            "preco": 499.00,
            "dias": 30,
            "titulo": "CrashBot PRO Mensal (30 Dias)",
        },
    }

    @classmethod
    def validar_configuracao(cls):
        """Valida configurações críticas na inicialização."""
        erros = []

        if not cls.MP_ACCESS_TOKEN:
            erros.append("MP_ACCESS_TOKEN não configurado")

        if cls.ADMIN_PASSWORD_HASH == generate_password_hash("admin123"):
            logger.warning("⚠️ SENHA ADMIN PADRÃO DETECTADA - TROCAR EM PRODUÇÃO!")

        if erros:
            for erro in erros:
                logger.error(f"❌ {erro}")
            raise ValueError(f"Configuração inválida: {', '.join(erros)}")

        logger.info("✅ Configurações validadas com sucesso")


# Aplicar configurações ao Flask
app.config["SQLALCHEMY_DATABASE_URI"] = Config.get_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = Config.SECRET_KEY

# =============================================================================
# INICIALIZAÇÃO DE EXTENSÕES
# =============================================================================

# SQLAlchemy
db = SQLAlchemy(app)

# Rate Limiter (proteção contra abuso)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=Config.RATELIMIT_STORAGE_URL,
    default_limits=["200 per day", "50 per hour"],
    enabled=Config.RATELIMIT_ENABLED,
)

# =============================================================================
# MODELOS DO BANCO DE DADOS
# =============================================================================


class Licenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    ativa = db.Column(db.Boolean, default=True)
    data_expiracao = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # DADOS CADASTRAIS ATUALIZADOS
    cliente_nome = db.Column(db.String(100))
    email_cliente = db.Column(db.String(120), nullable=True)
    whatsapp = db.Column(db.String(20), nullable=True)

    # --- NOVOS CAMPOS TELEGRAM E PLANO ---
    telegram_chat_id = db.Column(db.String(50), nullable=True)
    plano_tipo = db.Column(db.String(50), nullable=True)

    payment_id = db.Column(db.String(50), unique=True, nullable=True)
    hwid = db.Column(db.String(100), nullable=True)

    def __init__(
        self,
        chave,
        cliente_nome,
        email_cliente=None,
        whatsapp=None,
        telegram_chat_id=None,
        plano_tipo="mensal",
        payment_id=None,
        dias_validade=None,
    ):
        self.chave = chave
        self.cliente_nome = cliente_nome
        self.email_cliente = email_cliente
        self.whatsapp = whatsapp
        self.telegram_chat_id = telegram_chat_id  # Novo
        self.plano_tipo = plano_tipo  # Novo
        self.payment_id = payment_id
        self.hwid = None
        self.ativa = True

        if dias_validade:
            self.data_expiracao = datetime.now(timezone.utc) + timedelta(
                days=dias_validade
            )
        else:
            self.data_expiracao = None

    def esta_expirada(self) -> bool:
        """Verifica se a licença está expirada."""
        if not self.data_expiracao:
            return False

        exp = self.data_expiracao
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        return exp < datetime.now(timezone.utc)

    def dias_restantes(self) -> int:
        """Retorna quantos dias faltam para expirar."""
        if not self.data_expiracao:
            return 999999

        exp = self.data_expiracao
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        delta = exp - datetime.now(timezone.utc)
        return max(0, delta.days)

    def to_dict(self) -> dict:
        """Serializa para JSON."""
        return {
            "id": self.id,
            "chave": self.chave,
            "ativa": self.ativa,
            "data_expiracao": (
                self.data_expiracao.isoformat() if self.data_expiracao else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "cliente_nome": self.cliente_nome,
            "email_cliente": self.email_cliente,
            "whatsapp": self.whatsapp,
            "telegram_chat_id": self.telegram_chat_id,
            "plano_tipo": self.plano_tipo,
            "payment_id": self.payment_id,
            "hwid": self.hwid,
            "dias_restantes": self.dias_restantes(),
        }


class LogBot(db.Model):
    """
    Modelo de Log - Telemetria dos Bots
    """

    __tablename__ = "log_bot"

    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    hwid = db.Column(db.String(100), nullable=True, index=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)
    dados = db.Column(db.Text, nullable=True)
    lucro = db.Column(db.Float, default=0.0, nullable=False)

    def __init__(
        self, sessao_id: str, hwid: str, tipo: str, dados: str, lucro: float = 0.0
    ):
        self.sessao_id = sessao_id
        self.hwid = hwid
        self.tipo = tipo
        self.dados = dados
        self.lucro = lucro

    def to_dict(self) -> dict:
        """Serializa para JSON."""
        return {
            "id": self.id,
            "sessao_id": self.sessao_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "hwid": self.hwid,
            "tipo": self.tipo,
            "dados": self.dados,
            "lucro": self.lucro,
        }


# =============================================================================
# DECORADORES DE SEGURANÇA
# =============================================================================


def require_admin_auth(f):
    """
    Decorator para proteger rotas administrativas.
    Requer autenticação HTTP Basic.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization

        if not auth:
            return (
                jsonify(
                    {
                        "erro": "Autenticação necessária",
                        "detalhes": "Forneça credenciais via HTTP Basic Auth",
                    }
                ),
                401,
            )

        # Valida credenciais
        username_valido = auth.username == Config.ADMIN_USERNAME
        senha_valida = check_password_hash(
            Config.ADMIN_PASSWORD_HASH, auth.password or ""
        )

        if not (username_valido and senha_valida):
            logger.warning(f"❌ Tentativa de acesso admin falhou: {auth.username}")
            return jsonify({"erro": "Credenciais inválidas"}), 403

        logger.info(f"✅ Acesso admin autorizado: {auth.username}")
        return f(*args, **kwargs)

    return decorated_function


def validar_json_obrigatorio(campos_obrigatorios: list):
    """
    Decorator para validar presença de campos obrigatórios no JSON.

    Uso:
        @validar_json_obrigatorio(['email', 'nome'])
        def minha_rota():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"erro": "Content-Type deve ser application/json"}), 400

            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou vazio"}), 400

            # Verifica campos obrigatórios
            campos_faltantes = [
                campo
                for campo in campos_obrigatorios
                if campo not in dados or not dados[campo]
            ]

            if campos_faltantes:
                return (
                    jsonify(
                        {
                            "erro": "Campos obrigatórios ausentes",
                            "campos_faltantes": campos_faltantes,
                        }
                    ),
                    400,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def gerar_chave_licenca() -> str:
    """Gera uma chave de licença única."""
    return f"KEY-{str(uuid.uuid4()).upper()[:14]}"


def obter_info_plano(plano: str) -> dict:
    """
    Retorna informações do plano ou fallback para mensal.

    Returns:
        dict com: preco, dias, titulo
    """
    plano_lower = plano.lower().strip()

    if plano_lower in Config.PRECOS_PLANOS:
        return Config.PRECOS_PLANOS[plano_lower]

    # Fallback para mensal
    logger.warning(f"⚠️ Plano desconhecido '{plano}', usando fallback 'mensal'")
    return Config.PRECOS_PLANOS["mensal"]


def extrair_payment_id_do_request() -> Optional[str]:
    """
    Extrai payment_id de diferentes formatos de webhook do Mercado Pago.

    Tenta em ordem:
    1. Query params: ?id=XXX ou ?data.id=XXX
    2. JSON body: { "data": { "id": "XXX" } }
    """
    # Tenta query params (Combina atribuição e verificação)
    if pid := request.args.get("id") or request.args.get("data.id"):
        return str(pid)

    # Tenta JSON body
    if request.is_json and (data := request.get_json(silent=True)):
        # Formato: { "data": { "id": "XXX" } }
        if isinstance(data.get("data"), dict) and (pid := data["data"].get("id")):
            return str(pid)

        if pid := data.get("id"):
            return str(pid)

    return None


# =============================================================================
# ROTAS - INFORMAÇÕES GERAIS
# =============================================================================


@app.route("/", methods=["GET"])
def home():
    """Endpoint raiz com informações da API."""
    return jsonify(
        {
            "nome": "CrashBot Store API",
            "versao": "2.0",
            "status": "online",
            "recursos": {
                "validacao": "/validar",
                "telemetria": "/telemetria/log",
                "pagamento": "/api/pagamento/criar",
                "webhook": "/webhook/mercadopago",
            },
            "email_disponivel": EMAIL_DISPONIVEL,
            "documentacao": f"{Config.BASE_URL}/docs",
        }
    )


@app.route("/health", methods=["GET"])
@limiter.exempt
def health_check():
    """Health check para monitoramento."""
    try:
        # Testa conexão com banco
        db.session.execute(db.text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error(f"❌ Health check falhou: {e}")
        db_status = "erro"

    return jsonify(
        {
            "status": "healthy" if db_status == "ok" else "unhealthy",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


# =============================================================================
# ROTAS - VALIDAÇÃO DE LICENÇA (USADA PELO BOT)
# =============================================================================


@app.route("/validar", methods=["POST"])
@limiter.limit("30 per minute")
@validar_json_obrigatorio(["chave", "hwid"])
def validar_licenca():
    """
    Valida uma licença e vincula ao HWID na primeira utilização.

    Request:
        {
            "chave": "KEY-XXXXXXXXXXXX",
            "hwid": "hardware_id_do_computador"
        }

    Response:
        200: { "status": "sucesso", "mensagem": "...", "dados_licenca": {...} }
        403: { "status": "erro", "mensagem": "..." }
        404: { "status": "erro", "mensagem": "Licença não encontrada" }
    """
    dados = request.get_json()
    chave = dados.get("chave", "").strip()
    hwid = dados.get("hwid", "").strip()

    # Busca licença
    licenca = Licenca.query.filter_by(chave=chave).first()

    if not licenca:
        logger.warning(f"❌ Tentativa de validação com chave inválida: {chave}")
        return jsonify({"status": "erro", "mensagem": "Licença não encontrada"}), 404

    # Verifica se está ativa
    if not licenca.ativa:
        logger.warning(f"❌ Tentativa de usar licença bloqueada: {chave}")
        return (
            jsonify(
                {"status": "erro", "mensagem": "Licença bloqueada pelo administrador"}
            ),
            403,
        )

    # Verifica expiração
    if licenca.esta_expirada():
        logger.warning(f"❌ Tentativa de usar licença expirada: {chave}")
        return (
            jsonify(
                {
                    "status": "erro",
                    "mensagem": f"Licença expirada. Válida até {licenca.data_expiracao.strftime('%d/%m/%Y')}",
                }
            ),
            403,
        )

    # Vinculação de HWID (primeira utilização)
    if not licenca.hwid:
        licenca.hwid = hwid
        db.session.commit()

        logger.info(f"✅ Licença ativada: {chave} → HWID: {hwid}")
        return jsonify(
            {
                "status": "sucesso",
                "mensagem": "Licença ativada com sucesso!",
                "dados_licenca": {
                    "cliente_nome": licenca.cliente_nome,
                    "plano": licenca.plano_tipo,
                    "dias_restantes": licenca.dias_restantes(),
                    "expira_em": (
                        licenca.data_expiracao.strftime("%d/%m/%Y %H:%M")
                        if licenca.data_expiracao
                        else "Sem expiração"
                    ),
                },
            }
        )

    # Valida HWID correspondente
    if licenca.hwid != hwid:
        logger.warning(
            f"❌ HWID incorreto para {chave}. Esperado: {licenca.hwid}, Recebido: {hwid}"
        )
        return (
            jsonify(
                {
                    "status": "erro",
                    "mensagem": "HWID incorreto. Esta licença já está vinculada a outro dispositivo.",
                }
            ),
            403,
        )

    # Sucesso - HWID correto
    logger.info(f"✅ Validação OK: {chave}")
    return jsonify(
        {
            "status": "sucesso",
            "mensagem": "Licença válida",
            "dados_licenca": {
                "cliente_nome": licenca.cliente_nome,
                "plano": licenca.plano_tipo,
                "dias_restantes": licenca.dias_restantes(),
                "expira_em": (
                    licenca.data_expiracao.strftime("%d/%m/%Y %H:%M")
                    if licenca.data_expiracao
                    else "Sem expiração"
                ),
            },
        }
    )


# =============================================================================
# ROTAS - TELEMETRIA (LOGS DO BOT)
# =============================================================================


@app.route("/telemetria/log", methods=["POST"])
@limiter.limit("100 per minute")
def receber_log():
    """
    Recebe logs de telemetria dos bots em operação.

    Request:
        {
            "sessao_id": "uuid_da_sessao",
            "hwid": "hardware_id",
            "tipo": "bet|error|info|win|loss",
            "dados": "detalhes_da_operacao",
            "lucro": 10.50
        }

    Response:
        200: { "status": "ok" }
        400: { "status": "erro", "mensagem": "..." }
    """
    try:
        dados = request.get_json(silent=True)

        if not dados:
            return jsonify({"status": "erro", "mensagem": "JSON inválido"}), 400

        # Campos com valores padrão
        novo_log = LogBot(
            sessao_id=dados.get("sessao_id", "unknown"),
            hwid=dados.get("hwid", "unknown"),
            tipo=dados.get("tipo", "info"),
            dados=dados.get("dados", ""),
            lucro=float(dados.get("lucro", 0.0)),
        )

        db.session.add(novo_log)
        db.session.commit()

        logger.debug(f"📊 Log recebido: {novo_log.tipo} | HWID: {novo_log.hwid}")

        return jsonify({"status": "ok"})

    except ValueError as e:
        logger.error(f"❌ Erro ao processar log: {e}")
        return jsonify({"status": "erro", "mensagem": "Valor de lucro inválido"}), 400

    except Exception as e:
        logger.error(f"❌ Erro ao salvar log: {e}")
        db.session.rollback()
        return (
            jsonify({"status": "erro", "mensagem": "Erro interno ao processar log"}),
            500,
        )


# =============================================================================
# ROTAS - SISTEMA DE PAGAMENTOS
# =============================================================================


@app.route("/api/pagamento/criar", methods=["POST"])
@limiter.limit("10 per minute")
@validar_json_obrigatorio(["email", "nome", "plano"])
def criar_pagamento():
    try:
        dados = request.get_json()
        email = dados.get("email")
        nome = dados.get("nome", "Cliente")
        whatsapp = dados.get("whatsapp", "")
        # Recebe o Telegram (se o site mandar)
        telegram = dados.get("telegram_chat_id", "")
        plano = dados.get("plano", "mensal")

        # --- TABELA DE PREÇOS ATUALIZADA ---
        if plano == "experimental":
            preco = 4.99
            titulo = "CrashBot Experimental (7 Dias)"
        elif plano == "semanal":
            preco = 149.00
            titulo = "CrashBot VIP Semanal (7 Dias)"
        elif plano == "mensal":
            preco = 499.00
            titulo = "CrashBot PRO Mensal (30 Dias)"
        else:
            preco = 499.00
            titulo = "CrashBot Premium"

        token_mp = Config.MP_ACCESS_TOKEN

        if not token_mp:
            return jsonify({"erro": "Token MP ausente"}), 500

        sdk = mercadopago.SDK(token_mp)

        preference_data = {
            "items": [
                {
                    "id": f"bot-{plano}",
                    "title": titulo,
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": preco,
                }
            ],
            "payer": {"email": email, "name": nome},
            # METADATA: O segredo está aqui. Passamos tudo para o MP devolver depois.
            "metadata": {
                "nome_real": nome,
                "whatsapp_real": whatsapp,
                "telegram_real": telegram,  # Enviando Telegram pro MP
                "plano_escolhido": plano,
            },
            "back_urls": {
                "success": "https://google.com",
                "failure": "https://google.com",
                "pending": "https://google.com",
            },
            "auto_return": "approved",
            "notification_url": f"{Config.BASE_URL or ''}/webhook/mercadopago",
        }

        result = sdk.preference().create(preference_data)

        # Verifica se o MP respondeu corretamente
        if "response" not in result or "init_point" not in result["response"]:
            raise ValueError("Resposta inválida do Mercado Pago")

        return jsonify(
            {"status": "sucesso", "checkout_url": result["response"]["init_point"]}
        )

    except Exception as e:
        logger.error(f"Erro criar pagamento: {e}")
        return jsonify({"erro": str(e)}), 500


# =============================================================================
# ROTAS - WEBHOOK (PROCESSAMENTO DE VENDAS)
# =============================================================================
def _calcular_dias_plano(plano: str, descricao: str) -> int:
    """Helper para determinar dias de validade baseado no plano."""
    return 7 if plano in {"experimental", "semanal"} else 30


@app.route("/webhook/mercadopago", methods=["POST"])
@limiter.exempt  # Webhooks não devem ter rate limit
def webhook_mercadopago():
    # 1. Extração do ID (Reutilizando a função que já corrigimos)
    pid = extrair_payment_id_do_request()

    if not pid:
        return jsonify({"status": "ignored"}), 200

    token_mp = Config.MP_ACCESS_TOKEN

    if not token_mp:
        return jsonify({"error": "config_missing"}), 500

    try:
        # 2. Consulta ao Mercado Pago
        payment_info = mercadopago.SDK(token_mp).payment().get(pid)

        if payment_info["status"] != 200:
            return jsonify({"error": "mp_api_error"}), payment_info["status"]

        resp = payment_info["response"]

        # Só processa se aprovado
        if resp.get("status") != "approved":
            return jsonify({"status": "ignored", "reason": "not_approved"}), 200

        # 3. Verificação de Idempotência (Evita duplicidade)
        if Licenca.query.filter_by(payment_id=str(pid)).first():
            return jsonify({"status": "ok", "msg": "already_processed"}), 200

        # 4. Extração de Dados
        meta = resp.get("metadata", {})
        payer = resp.get("payer", {})

        nome = meta.get("nome_real") or payer.get("first_name", "Cliente")
        email = payer.get("email")
        plano = meta.get("plano_escolhido")

        # 5. Criação da Licença
        dias = _calcular_dias_plano(plano, resp.get("description", ""))
        chave = f"KEY-{str(uuid.uuid4()).upper()[:14]}"

        licenca = Licenca(
            chave=chave,
            cliente_nome=nome,
            email_cliente=email,
            whatsapp=meta.get("whatsapp_real"),
            telegram_chat_id=meta.get("telegram_real"),
            plano_tipo=plano,
            payment_id=str(pid),
            dias_validade=dias,
        )

        db.session.add(licenca)
        db.session.commit()

        # 6. Finalização
        enviar_email_licenca(email, nome, chave, Config.LINK_DOWNLOAD_BOT)
        logger.info(f"✅ Venda Webhook Completa: {nome} | Plano: {plano}")

        return jsonify({"status": "created"}), 201

    except Exception as e:
        logger.error(f"Webhook erro crítico: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def _processar_venda_aprovada(
    payment_data: dict, payment_id: str
) -> Tuple[Response, int]:
    """
    Processa uma venda aprovada: cria licença e envia email.

    Args:
        payment_data: Dados do pagamento retornados pelo MP
        payment_id: ID do pagamento

    Returns:
        Tuple[jsonify response, status_code]
    """
    try:
        # 1. Extrair metadata e dados do pagador
        metadata = payment_data.get("metadata", {})
        payer = payment_data.get("payer", {})

        # Dados do cliente
        nome = metadata.get("nome_real") or payer.get("first_name", "Cliente")
        email = payer.get("email", "")
        whatsapp = metadata.get("whatsapp_real")
        telegram_chat_id = metadata.get("telegram_real")
        plano = metadata.get("plano_escolhido", "mensal")

        # 2. Obter informações do plano
        plano_info = obter_info_plano(plano)
        dias_validade = plano_info["dias"]

        # 3. Gerar chave única
        chave = gerar_chave_licenca()

        # 4. Criar licença no banco
        nova_licenca = Licenca(
            chave=chave,
            cliente_nome=nome,
            plano_tipo=plano,
            dias_validade=dias_validade,
            email_cliente=email,
            whatsapp=whatsapp,
            telegram_chat_id=telegram_chat_id,
            payment_id=payment_id,
        )

        db.session.add(nova_licenca)
        db.session.commit()

        logger.info(f"✅ Licença criada: {chave} | Cliente: {nome} | Plano: {plano}")

        # 5. Enviar email com licença
        email_enviado = False
        if email:
            try:
                email_enviado = enviar_email_licenca(
                    email_cliente=email,
                    nome_cliente=nome,
                    chave_licenca=chave,
                    link_download=Config.LINK_DOWNLOAD_BOT,
                )

                if email_enviado:
                    logger.info(f"📧 Email enviado para {email}")
                else:
                    logger.warning(f"⚠️ Falha ao enviar email para {email}")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar email: {e}")

        # 6. Retornar sucesso
        return (
            jsonify(
                {
                    "status": "created",
                    "licenca": {
                        "chave": chave,
                        "cliente": nome,
                        "plano": plano,
                        "dias_validade": dias_validade,
                        "email_enviado": email_enviado,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"❌ Erro ao processar venda: {e}", exc_info=True)
        db.session.rollback()
        raise


# =============================================================================
# ROTAS ADMINISTRATIVAS (PROTEGIDAS)
# =============================================================================


@app.route("/admin/licencas", methods=["GET"])
@require_admin_auth
def listar_licencas():
    """
    Lista todas as licenças com filtros opcionais.

    Query params:
        - ativa: true|false
        - plano: experimental|semanal|mensal
        - limit: número de resultados (padrão: 100)
    """
    try:
        # Filtros
        query = Licenca.query

        if ativa_filter := request.args.get("ativa"):
            ativa_bool = ativa_filter.lower() == "true"
            query = query.filter_by(ativa=ativa_bool)

        if plano_filter := request.args.get("plano"):
            query = query.filter_by(plano_tipo=plano_filter)

        # Limite
        limit = min(int(request.args.get("limit", 100)), 1000)

        licencas = query.order_by(Licenca.created_at.desc()).limit(limit).all()

        return jsonify(
            {"total": len(licencas), "licencas": [lic.to_dict() for lic in licencas]}
        )

    except Exception as e:
        logger.error(f"❌ Erro ao listar licenças: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/admin/licenca/<int:licenca_id>", methods=["GET"])
@require_admin_auth
def detalhes_licenca(licenca_id: int):
    """Retorna detalhes de uma licença específica."""
    licenca = Licenca.query.get_or_404(licenca_id)
    return jsonify(licenca.to_dict())


@app.route("/admin/licenca/<int:licenca_id>/bloquear", methods=["POST"])
@require_admin_auth
def bloquear_licenca(licenca_id: int):
    """Bloqueia (desativa) uma licença."""
    licenca = Licenca.query.get_or_404(licenca_id)
    licenca.ativa = False
    db.session.commit()

    logger.info(f"🔒 Licença bloqueada: {licenca.chave}")

    return jsonify(
        {"status": "sucesso", "mensagem": f"Licença {licenca.chave} bloqueada"}
    )


@app.route("/admin/licenca/<int:licenca_id>/desbloquear", methods=["POST"])
@require_admin_auth
def desbloquear_licenca(licenca_id: int):
    """Desbloqueia (ativa) uma licença."""
    licenca = Licenca.query.get_or_404(licenca_id)
    licenca.ativa = True
    db.session.commit()

    logger.info(f"🔓 Licença desbloqueada: {licenca.chave}")

    return jsonify(
        {"status": "sucesso", "mensagem": f"Licença {licenca.chave} desbloqueada"}
    )


@app.route("/admin/estatisticas", methods=["GET"])
@require_admin_auth
def estatisticas():
    """Retorna estatísticas gerais do sistema."""
    try:
        # Contagens simples
        total_licencas = Licenca.query.count()
        licencas_ativas = Licenca.query.filter_by(ativa=True).count()

        # --- CORREÇÃO DEFINITIVA ---
        # Adicionamos '# type: ignore' para calar o falso positivo do Pylance
        # O código está correto, é apenas o verificador que está confuso.
        stmt = (
            select(Licenca.plano_tipo, func.count(Licenca.id))  # type: ignore
            .where(Licenca.ativa)
            .group_by(Licenca.plano_tipo)  # type: ignore
        )

        resultados = db.session.execute(stmt).all()

        # Converte os resultados em dicionário
        dict_planos = {row[0]: row[1] for row in resultados if row[0]}

        # Total de logs
        total_logs = LogBot.query.count()

        # Lucro total
        lucro_total = db.session.query(func.sum(LogBot.lucro)).scalar() or 0

        return jsonify(
            {
                "licencas": {
                    "total": total_licencas,
                    "ativas": licencas_ativas,
                    "inativas": total_licencas - licencas_ativas,
                    "por_plano": dict_planos,
                },
                "telemetria": {
                    "total_logs": total_logs,
                    "lucro_total": float(lucro_total),
                },
            }
        )

    except Exception as e:
        logger.error(f"❌ Erro ao gerar estatísticas: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/admin/reset_database", methods=["GET"])  # MUDAMOS PARA GET
@require_admin_auth
def reset_database():
    """
    ⚠️ PERIGOSO: Recria todas as tabelas do banco.
    Requer confirmação via query param: ?confirmar=sim
    """
    confirmacao = request.args.get("confirmar", "").lower()

    if confirmacao != "sim":
        return (
            jsonify(
                {
                    "erro": "Confirmação necessária",
                    "instrucoes": "Adicione ?confirmar=sim na URL para confirmar.",
                }
            ),
            400,
        )

    try:
        logger.warning("⚠️ RESET DO BANCO INICIADO!")

        db.drop_all()  # Apaga o velho (que estava dando erro)
        db.create_all()  # Cria o novo (com colunas whatsapp, telegram, etc)

        logger.warning("✅ Banco resetado com sucesso")

        return jsonify(
            {
                "status": "sucesso",
                "mensagem": "Banco de dados resetado. Todas as tabelas foram recriadas com a nova estrutura.",
                "tabelas_agora_no_banco": list(db.metadata.tables.keys()),
            }
        )

    except Exception as e:
        logger.error(f"❌ Erro ao resetar banco: {e}")
        return jsonify({"erro": str(e)}), 500


# =============================================================================
# TRATAMENTO DE ERROS
# =============================================================================


@app.errorhandler(404)
def not_found(error):
    """Handler para 404."""
    return jsonify({"erro": "Recurso não encontrado", "path": request.path}), 404


@app.errorhandler(429)
def ratelimit_handler(error):
    """Handler para rate limit excedido."""
    return (
        jsonify(
            {
                "erro": "Limite de requisições excedido",
                "mensagem": "Aguarde alguns minutos antes de tentar novamente",
            }
        ),
        429,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos."""
    logger.error(f"❌ Erro interno: {error}", exc_info=True)
    db.session.rollback()
    return (
        jsonify(
            {
                "erro": "Erro interno do servidor",
                "mensagem": "Entre em contato com o suporte",
            }
        ),
        500,
    )


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================


def inicializar_app():
    """Inicializa a aplicação e valida configurações."""
    with app.app_context():
        # Validar configurações
        try:
            Config.validar_configuracao()
        except ValueError as e:
            logger.error(f"❌ Erro de configuração: {e}")
            # Em produção, poderia abortar aqui
            # Para desenvolvimento, apenas avisa

        # Criar tabelas se não existirem
        try:
            db.create_all()
            logger.info("✅ Tabelas do banco verificadas/criadas")
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")
            raise

        logger.info("🚀 CrashBot Store API V2 inicializada com sucesso!")
        logger.info(f"📍 Base URL: {Config.BASE_URL}")
        logger.info(f"📧 Email disponível: {EMAIL_DISPONIVEL}")


# =============================================================================
# PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    inicializar_app()

    # Configurações de desenvolvimento
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port, debug=debug_mode)
