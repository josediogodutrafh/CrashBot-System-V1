import re  # Para limpar o CPF
import time
from dataclasses import dataclass

import mercadopago
import streamlit as st


@dataclass
class ResultadoErro:
    status: str = ""
    mensagem: str = ""
    codigo: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "ResultadoErro":
        return cls(
            status=data.get("status", ""),
            mensagem=data.get("mensagem", ""),
            codigo=data.get("codigo", 0),
        )


# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Comprar CrashBot", page_icon="🤖", layout="centered")

# ⚠️ IMPORTANTE: Substitua abaixo pelo seu ACCESS TOKEN DE PRODUÇÃO (Começa com APP_USR-...)
MP_ACCESS_TOKEN = (
    "APP_USR-1745556017385187-112515-e566b5dbb86141184e08e017990ec62c-3015690291"
)

# URL do seu Webhook (O servidor do Render)
NOTIFICATION_URL = "https://crash-api-jose.onrender.com/webhook/mercadopago"

# Inicializa o SDK
try:
    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
except Exception as e:
    st.error(f"Erro grave ao iniciar SDK: {e}")


def limpar_cpf(cpf_bruto):
    """Remove pontos e traços do CPF."""
    return re.sub(r"[^0-9]", "", cpf_bruto)


def exibir_erro_pagamento(resultado):
    """Exibe detalhes do erro de pagamento na interface."""
    status_erro = resultado.get("status")
    mensagem_erro = resultado.get("response", {}).get("message", "Sem mensagem")
    detalhes = resultado.get("response", {}).get("cause", [])

    st.error(f"❌ O Mercado Pago recusou! Status: {status_erro}")
    st.error(f"Motivo: {mensagem_erro}")
    if detalhes:
        st.json(detalhes)


def gerar_pix(email, nome, cpf):
    """Gera um pagamento PIX no Mercado Pago."""

    # Limpa o CPF antes de enviar
    cpf_limpo = limpar_cpf(cpf)

    payment_data = {
        "transaction_amount": 49.90,  # Valor do Bot
        "description": "Licença Vitalícia CrashBot",
        "payment_method_id": "pix",
        "payer": {
            "email": email,
            "first_name": nome,
            "identification": {"type": "CPF", "number": cpf_limpo},
        },
        "notification_url": NOTIFICATION_URL,
    }

    try:
        resultado = sdk.payment().create(payment_data)

        if resultado["status"] == 201:
            return resultado["response"]

        exibir_erro_pagamento(resultado)
        return None

    except Exception as e:
        st.error(f"Erro de conexão/código: {e}")
        return None
        # --------------------------


# --- INTERFACE ---
st.title("🤖 CrashBot Auto")
st.subheader("Aumente seus lucros com Inteligência Artificial.")
st.write("Adquira sua licença vitalícia agora.")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.info("💰 **Preço: R$ 49,90**")
with col2:
    st.success("⚡ **Entrega Automática**")

with st.form("form_compra"):
    nome = st.text_input("Seu Nome Completo")
    email = st.text_input("Seu Melhor E-mail")
    cpf = st.text_input("CPF (Apenas números)")

    submit = st.form_submit_button("GERAR PIX E COMPRAR", use_container_width=True)

if submit:
    if not nome or not email or len(limpar_cpf(cpf)) < 11:
        st.warning("⚠️ Por favor, preencha nome, email e CPF corretamente.")
    else:
        with st.spinner("Conectando ao Mercado Pago..."):
            # Simula um tempinho para UX
            time.sleep(1)
            dados_pagamento = gerar_pix(email, nome, cpf)

        if dados_pagamento:
            # Extrai dados do PIX
            point = dados_pagamento.get("point_of_interaction", {})
            trans_data = point.get("transaction_data", {})

            qr_code_base64 = trans_data.get("qr_code_base64")
            qr_code_copia_cola = trans_data.get("qr_code")
            id_pagamento = dados_pagamento.get("id")

            st.balloons()
            st.success("🎉 Pedido Criado! Pague para receber o acesso.")

            if qr_code_base64:
                st.image(
                    f"data:image/jpeg;base64,{qr_code_base64}",
                    width=250,
                    caption="Escaneie no App do Banco",
                )

            if qr_code_copia_cola:
                st.text_area("Copia e Cola:", qr_code_copia_cola)

            st.info(f"ID do Pedido: {id_pagamento}")
            st.warning("Assim que pagar, verifique seu e-mail!")
