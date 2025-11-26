import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# Configuração do App
app = Flask(__name__)

# --- CONFIGURAÇÃO HÍBRIDA DE BANCO DE DADOS ---
# Usa o operador := para pegar e testar a variável ao mesmo tempo
if database_url := os.environ.get("DATABASE_URL"):
    # Estamos na Nuvem (Render) -> Usar PostgreSQL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Estamos no PC Local -> Usar SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///server.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS (AS TABELAS) ---


class Licenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(
        db.String(50), unique=True, nullable=False
    )  # A chave (ex: CRASH-1234)
    hwid = db.Column(db.String(100), nullable=True)  # O ID do PC do usuário
    ativa = db.Column(db.Boolean, default=True)  # Se a gente bloqueou ou não
    data_expiracao = db.Column(db.DateTime, nullable=False)  # Até quando vale
    cliente_nome = db.Column(db.String(100))  # Nome do cliente (opcional)

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
    tipo = db.Column(db.String(50))  # 'round', 'bet', 'alert', 'error'
    dados = db.Column(db.String(500))  # Conteúdo do log (JSON string ou mensagem)
    lucro = db.Column(db.Float, default=0.0)

    def __init__(self, sessao_id, hwid, tipo, dados, lucro=0.0):
        self.sessao_id = sessao_id
        self.hwid = hwid
        self.tipo = tipo
        self.dados = dados
        self.lucro = lucro


# --- ROTAS (O PORTEIRO) ---


# 1. Rota para criar o banco de dados (apenas na primeira vez)
@app.route("/setup")
def setup():
    with app.app_context():
        db.create_all()
        return "Banco de dados criado com sucesso!"


# 2. Rota de Verificação (O Bot chama esta rota)
@app.route("/validar", methods=["POST"])
def validar_licenca():
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({"status": "erro", "mensagem": "JSON inválido ou ausente"}), 400

    chave_recebida = dados.get("chave")
    hwid_recebido = dados.get("hwid")

    if not chave_recebida or not hwid_recebido:
        return jsonify({"status": "erro", "mensagem": "Dados incompletos"}), 400

    # Busca a licença no banco
    licenca = Licenca.query.filter_by(chave=chave_recebida).first()

    # 2.1 Checa se a licença existe
    if not licenca:
        return jsonify({"status": "erro", "mensagem": "Chave inválida"}), 403

    # 2.2 Checa se está bloqueada manualmente por você
    if not licenca.ativa:
        return (
            jsonify(
                {"status": "erro", "mensagem": "Licença bloqueada pelo administrador"}
            ),
            403,
        )

    # 2.3 Checa a data de validade
    if licenca.data_expiracao < datetime.now():
        return jsonify({"status": "erro", "mensagem": "Licença expirada"}), 403

    # 2.4 Checa o HWID (Hardware ID)
    if licenca.hwid is None:
        # É o primeiro acesso! Vamos "casar" a chave com este PC.
        licenca.hwid = hwid_recebido
        db.session.commit()
        return jsonify(
            {"status": "sucesso", "mensagem": "Licença ativada neste computador!"}
        )

    elif licenca.hwid != hwid_recebido:
        # A chave já tem um dono e o HWID não bate
        return (
            jsonify(
                {"status": "erro", "mensagem": "Esta chave já está em uso em outro PC!"}
            ),
            403,
        )

    # Se passou por tudo...
    return jsonify({"status": "sucesso", "mensagem": "Acesso permitido"})


@app.route("/telemetria/log", methods=["POST"])
def receber_log():
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({"status": "erro", "mensagem": "JSON inválido ou ausente"}), 400

    # 1. Validação básica (HWID é necessário para rastrear)
    if not dados.get("hwid") or not dados.get("sessao_id") or not dados.get("tipo"):
        return jsonify({"status": "erro", "mensagem": "Dados de log incompletos"}), 400

    # 2. Cria o novo registro de log
    novo_log = LogBot(
        sessao_id=dados["sessao_id"],
        hwid=dados["hwid"],
        tipo=dados["tipo"],
        dados=dados.get("dados", "N/A"),
        lucro=dados.get("lucro", 0.0),
    )

    try:
        db.session.add(novo_log)
        db.session.commit()
        return jsonify({"status": "sucesso", "mensagem": "Log recebido"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# 3. Rota para VOCÊ criar licenças (Painel Admin simplificado)
@app.route("/admin/criar_licenca", methods=["POST"])
def criar_licenca():
    # IMPORTANTE: Em produção, precisaremos proteger esta rota com senha!
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"status": "erro", "mensagem": "JSON inválido ou ausente"}), 400

    nova_chave = dados.get("chave")
    dias_validade = dados.get("dias", 30)
    nome = dados.get("nome", "Cliente")

    from datetime import timedelta

    expiracao = datetime.now() + timedelta(days=dias_validade)

    nova_licenca = Licenca(
        chave=nova_chave, data_expiracao=expiracao, cliente_nome=nome
    )

    try:
        db.session.add(nova_licenca)
        db.session.commit()
        return jsonify({"status": "sucesso", "mensagem": f"Chave {nova_chave} criada!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


# ADICIONE ISTO no app.py (junto com as outras rotas)
@app.route("/admin/limpar_licencas", methods=["POST"])
def limpar_licencas():
    # Isso apaga TUDO da tabela de Licencas!
    try:
        db.session.query(Licenca).delete()
        db.session.commit()
        return jsonify(
            {"status": "sucesso", "mensagem": "Todas as licenças foram excluídas."}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# --- ROTA DE EMERGÊNCIA (ADICIONE NO FINAL DO ARQUIVO) ---
@app.route("/admin/reset_total_db", methods=["GET"])
def reset_total_db():
    """Apaga e recria o banco de dados do zero."""
    try:
        with app.app_context():
            db.drop_all()  # Apaga todas as tabelas velhas
            db.create_all()  # Cria as tabelas novas e corretas
        return "✅ Banco de dados RESETADO e RECRIADO com sucesso!", 200
    except Exception as e:
        return f"❌ Erro ao resetar: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True)

# Forcando atualizacao do servidor
