import re
import time

import mercadopago
import streamlit as st
from PIL import Image  # Requer: pip install pillow

# --- 1. CONFIGURAÇÃO DA PÁGINA (MODERNA) ---
st.set_page_config(
    page_title="CrashBot AI - A Revolução",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 2. CONFIGURAÇÕES DE BACKEND ---
# ⚠️ SEU TOKEN AQUI
MP_ACCESS_TOKEN = (
    "APP_USR-1745556017385187-112515-e566b5dbb86141184e08e017990ec62c-3015690291"
)
NOTIFICATION_URL = "https://crash-api-jose.onrender.com/webhook/mercadopago"

try:
    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
except Exception as e:
    st.error(f"Erro de configuração: {e}")

# --- 3. ESTILOS CSS AVANÇADOS (DESIGN SYSTEM) ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* Fundo Global */
    .stApp {
        background-color: #0E1117;
        font-family: 'Inter', sans-serif;
    }

    /* Títulos */
    h1 {
        background: -webkit-linear-gradient(45deg, #00FF99, #00CCFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        font-size: 3.5rem !important;
        text-align: center;
        margin-bottom: 0px;
    }
    h2 {
        color: #E0E0E0;
        font-weight: 600;
        text-align: center;
        margin-top: -10px;
    }
    h3 {
        color: #00FF99;
    }

    /* Cards de Benefícios */
    .feature-card {
        background: linear-gradient(145deg, #1E1E1E, #252525);
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #333;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        text-align: center;
        transition: transform 0.2s;
        height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        border-color: #00FF99;
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 15px;
    }

    /* Botão Principal (CTA) */
    .stButton>button {
        background: linear-gradient(90deg, #00FF99 0%, #00CC88 100%);
        color: #000;
        font-weight: 800;
        border: none;
        padding: 15px 30px;
        font-size: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 0 20px rgba(0, 255, 153, 0.4);
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 30px rgba(0, 255, 153, 0.7);
        transform: scale(1.02);
        color: #000;
    }

    /* Área de Checkout */
    .checkout-box {
        background-color: #161920;
        border: 1px solid #333;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        background-color: #0E1117;
        color: white;
        border: 1px solid #333;
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #00FF99;
        box-shadow: 0 0 0 1px #00FF99;
    }

    /* Preço */
    .price-tag {
        font-size: 2.5rem;
        font-weight: bold;
        color: white;
        text-align: center;
    }
    .old-price {
        text-decoration: line-through;
        color: #666;
        font-size: 1.2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- 4. LÓGICA DE BACKEND ---
def limpar_cpf(cpf_bruto):
    return re.sub(r"[^0-9]", "", cpf_bruto)


def _montar_dados_pagamento(email, nome, cpf_limpo):
    return {
        "transaction_amount": 49.90,
        "description": "Licença Vitalícia CrashBot AI",
        "payment_method_id": "pix",
        "payer": {
            "email": email,
            "first_name": nome,
            "identification": {"type": "CPF", "number": cpf_limpo},
        },
        "notification_url": NOTIFICATION_URL,
    }


def _extrair_erro_mp(resultado):
    status = resultado.get("status")
    msg = resultado.get("response", {}).get("message", "Erro desconhecido")
    st.error(f"🚫 Falha: {msg} (Status: {status})")


def gerar_pix(email, nome, cpf):
    cpf_limpo = limpar_cpf(cpf)
    payment_data = _montar_dados_pagamento(email, nome, cpf_limpo)
    try:
        resultado = sdk.payment().create(payment_data)
        if resultado["status"] == 201:
            return resultado["response"]
        _extrair_erro_mp(resultado)
        return None
    except Exception as e:
        st.error(f"Erro técnico: {e}")
        return None


# --- 5. FRONTEND (INTERFACE) ---


def hero_section():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1>CRASHBOT AI 2.0</h1>", unsafe_allow_html=True)
    st.markdown(
        "<h2>A Inteligência Artificial que opera enquanto você lucra.</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # Métricas Visuais
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Precisão", "94.2%", "+1.5%")
    col2.metric("🤖 Automação", "100%", "Hands-free")
    col3.metric("⚡ Latência", "50ms", "Ultra Rápido")
    col4.metric("🛡️ Stop-Loss", "Ativo", "Segurança")

    st.markdown("---")


def benefits_section():
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <h3>IA Preditiva</h3>
            <p>Algoritmo treinado com milhões de rodadas. Identifica padrões que humanos não veem.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
        <div class="feature-card">
            <div class="feature-icon">👁️</div>
            <h3>Visão Computacional</h3>
            <p>Lê a tela do jogo em tempo real. Não precisa de API da casa, impossível de detectar.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
        <div class="feature-card">
            <div class="feature-icon">🚀</div>
            <h3>Instalação Zero</h3>
            <p>Sistema portátil. Baixou, colou a chave, lucrou. Sem instalação complicada.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)


def checkout_area():
    _, center, _ = st.columns([1, 2, 1])

    with center:
        # Caixa de Compra Estilizada
        st.markdown('<div class="checkout-box">', unsafe_allow_html=True)
        st.markdown('<p class="old-price">De R$ 197,00</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="price-tag">Por R$ 49,90 <span style="font-size:1rem;color:#00FF99">Vitalício</span></p>',
            unsafe_allow_html=True,
        )

        with st.form("checkout_form"):
            st.markdown("### 🔒 Checkout Seguro")
            nome = st.text_input("Nome Completo", placeholder="Ex: João Silva")
            email = st.text_input(
                "E-mail de Acesso", placeholder="Onde você receberá o bot"
            )
            cpf = st.text_input(
                "CPF (Para emissão do PIX)", placeholder="000.000.000-00"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("GARANTIR MINHA LICENÇA AGORA")

        st.markdown("</div>", unsafe_allow_html=True)

    return center, submit, nome, email, cpf


def process_payment(container, nome, email, cpf):
    with container:
        if not nome or not email or len(limpar_cpf(cpf)) < 11:
            st.warning("⚠️ Preencha todos os dados para gerar sua licença.")
            return

        with st.spinner("Conectando ao Banco Central..."):
            time.sleep(1.5)  # UX
            dados = gerar_pix(email, nome, cpf)

        if dados:
            qr = dados["point_of_interaction"]["transaction_data"]["qr_code_base64"]
            code = dados["point_of_interaction"]["transaction_data"]["qr_code"]

            st.success("🎉 PIX GERADO COM SUCESSO!")

            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(f"data:image/jpeg;base64,{qr}", width=200)
            with c2:
                st.markdown("### Escaneie para Pagar")
                st.text_area("Copia e Cola:", code, height=100)
                st.info(
                    "📧 Assim que pagar, verifique seu e-mail. A entrega é automática (24/7)."
                )


def main():
    hero_section()
    benefits_section()
    container, submitted, nome, email, cpf = checkout_area()

    if submitted:
        process_payment(container, nome, email, cpf)

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    st.markdown(
        "<center style='color:#666'>CrashBot AI © 2025 • Tecnologia de Ponta</center>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
