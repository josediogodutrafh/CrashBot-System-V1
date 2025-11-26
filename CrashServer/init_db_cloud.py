from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- CONFIGURAÇÃO ---
EXTERNAL_DB_URL = "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"

# Correção de protocolo para o SQLAlchemy (necessário para o Render)
if EXTERNAL_DB_URL.startswith("postgres://"):
    EXTERNAL_DB_URL = EXTERNAL_DB_URL.replace("postgres://", "postgresql://", 1)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = EXTERNAL_DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- DEFINIÇÃO DOS MODELOS (Idênticos ao app.py) ---
class Licenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    hwid = db.Column(db.String(100), nullable=True)
    ativa = db.Column(db.Boolean, default=True)
    data_expiracao = db.Column(db.DateTime, nullable=False)
    cliente_nome = db.Column(db.String(100))

    def __init__(self, chave, data_expiracao, cliente_nome, hwid=None, ativa=True):
        self.chave = chave
        self.data_expiracao = data_expiracao
        self.cliente_nome = cliente_nome
        self.hwid = hwid
        self.ativa = ativa


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
        self.dados = dados
        self.lucro = lucro


def init_db():
    print("🔌 Conectando ao banco de dados remoto no Render...")
    try:
        with app.app_context():
            print("🏗️ Criando tabelas...")
            db.create_all()
            print("✅ Tabelas 'licenca' e 'log_bot' criadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")


if __name__ == "__main__":
    init_db()
