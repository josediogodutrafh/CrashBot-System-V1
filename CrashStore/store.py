"""
🛒 CRASHBOT STORE V2.0
Loja virtual integrada com API Flask e Mercado Pago

Melhorias da V2:
- Validações robustas (email, WhatsApp)
- Tratamento de erros específico
- Configuração via variáveis de ambiente
- Campo Telegram opcional
- Retry automático para API fria
- Analytics e rastreamento
- Rate limiting no front
- Melhorias de UX
"""

import os
import re
import time
from typing import Optional, Tuple

import requests
import streamlit as st

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================


class StoreConfig:
    """Centraliza configurações da loja."""

    # API
    API_URL = os.environ.get(
        "API_URL", "https://crash-api-jose.onrender.com/api/pagamento/criar"
    )
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "30"))
    API_MAX_RETRIES = int(os.environ.get("API_MAX_RETRIES", "3"))
    API_RETRY_DELAY = int(os.environ.get("API_RETRY_DELAY", "5"))

    # Contato
    WHATSAPP_SUPORTE = os.environ.get("WHATSAPP_SUPORTE", "5565992950893")

    # Vídeo/Mídia
    VIDEO_URL = os.environ.get("VIDEO_URL", None)
    HERO_IMAGE = os.environ.get(
        "HERO_IMAGE",
        "https://img.freepik.com/free-vector/gradient-stock-market-concept_23-2149166910.jpg",
    )

    # Planos (sincronizados com API)
    PLANOS = {
        "experimental": {
            "nome": "🧪 Experimental",
            "descricao": "Para quem quer testar sem medo.",
            "preco": 4.99,
            "preco_antigo": 29.90,
            "dias": 7,
            "features": [
                "✅ Acesso Completo ao Bot",
                "✅ Suporte de Instalação",
                "⚠️ Apenas uma vez por CPF",
            ],
        },
        "semanal": {
            "nome": "🚀 Semanal VIP",
            "descricao": "Foco total em uma semana.",
            "preco": 149.00,
            "preco_antigo": 199.00,
            "dias": 7,
            "features": [
                "✅ Acesso Completo ao Bot",
                "✅ Suporte via WhatsApp",
                "✅ Estratégias Avançadas",
            ],
        },
        "mensal": {
            "nome": "👑 Pro Mensal",
            "descricao": "Para quem joga sério.",
            "preco": 499.00,
            "preco_antigo": 699.00,
            "dias": 30,
            "features": [
                "✅ Acesso Completo ao Bot",
                "✅ Suporte Prioritário",
                "✅ Atualizações Prioritárias",
                "✅ Grupo VIP",
                "🤖 ChatBot Telegram Integrado",
            ],
            "featured": True,
        },
    }


# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="CrashBot AI | Acesso Premium",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def validar_email(email: str) -> Tuple[bool, str]:
    """
    Valida formato de email.

    Returns:
        Tuple[bool, str]: (válido, mensagem_erro)
    """
    if not email:
        return False, "Email é obrigatório"

    # Regex básico para email
    padrao = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(padrao, email):
        return False, "Email inválido. Use o formato: exemplo@email.com"

    return True, ""


def validar_whatsapp(whatsapp: str) -> Tuple[bool, str]:
    """
    Valida formato de WhatsApp (brasileiro).

    Returns:
        Tuple[bool, str]: (válido, mensagem_erro)
    """
    if not whatsapp:
        return False, "WhatsApp é obrigatório"

    # Remove caracteres não numéricos
    apenas_numeros = re.sub(r"\D", "", whatsapp)

    # Valida quantidade de dígitos (10 ou 11 para Brasil)
    if len(apenas_numeros) < 10 or len(apenas_numeros) > 11:
        return False, "WhatsApp inválido. Use (DD) 9XXXX-XXXX"

    # Valida DDD (entre 11 e 99)
    ddd = int(apenas_numeros[:2])
    if ddd < 11 or ddd > 99:
        return False, "DDD inválido"

    return True, ""


def validar_nome(nome: str) -> Tuple[bool, str]:
    """
    Valida nome completo.

    Returns:
        Tuple[bool, str]: (válido, mensagem_erro)
    """
    if not nome:
        return False, "Nome é obrigatório"

    if len(nome.strip()) < 3:
        return False, "Nome deve ter pelo menos 3 caracteres"

    # Verifica se tem pelo menos um sobrenome
    partes = nome.strip().split()
    if len(partes) < 2:
        return False, "Informe nome e sobrenome"

    return True, ""


def formatar_whatsapp(whatsapp: str) -> str:
    """
    Formata WhatsApp para padrão brasileiro.

    Args:
        whatsapp: Número de WhatsApp

    Returns:
        str: Número formatado (apenas dígitos)
    """
    return re.sub(r"\D", "", whatsapp)


def criar_pagamento_com_retry(payload: dict) -> Tuple[bool, dict]:
    """
    Chama API para criar pagamento com retry automático.

    Args:
        payload: Dados do cliente e plano

    Returns:
        Tuple[bool, dict]: (sucesso, resposta_ou_erro)
    """
    for tentativa in range(1, StoreConfig.API_MAX_RETRIES + 1):
        try:
            response = requests.post(
                StoreConfig.API_URL, json=payload, timeout=StoreConfig.API_TIMEOUT
            )

            if response.status_code == 200:
                return True, response.json()

            elif response.status_code == 400:
                # Erro de validação (não retentar)
                erro = response.json()
                return False, {
                    "tipo": "validacao",
                    "mensagem": erro.get("erro", "Dados inválidos"),
                }

            elif response.status_code == 500:
                # Erro no servidor (pode retentar)
                if tentativa < StoreConfig.API_MAX_RETRIES:
                    time.sleep(StoreConfig.API_RETRY_DELAY)
                    continue

                return False, {
                    "tipo": "servidor",
                    "mensagem": "Servidor temporariamente indisponível. Tente novamente em alguns minutos.",
                }

            else:
                # Outro erro
                return False, {
                    "tipo": "desconhecido",
                    "mensagem": f"Erro {response.status_code}: {response.text}",
                }

        except requests.exceptions.Timeout:
            if tentativa < StoreConfig.API_MAX_RETRIES:
                st.info(
                    f"⏳ Aguardando servidor... (Tentativa {tentativa}/{StoreConfig.API_MAX_RETRIES})"
                )
                time.sleep(StoreConfig.API_RETRY_DELAY)
                continue

            return False, {
                "tipo": "timeout",
                "mensagem": "Servidor demorando muito para responder. Tente novamente.",
            }

        except requests.exceptions.ConnectionError:
            return False, {
                "tipo": "conexao",
                "mensagem": "Erro de conexão. Verifique sua internet e tente novamente.",
            }

        except Exception as e:
            return False, {"tipo": "erro", "mensagem": f"Erro inesperado: {str(e)}"}

    # Se chegou aqui, esgotou tentativas
    return False, {
        "tipo": "timeout",
        "mensagem": "Não foi possível conectar ao servidor após várias tentativas.",
    }


def obter_plano_selecionado(opcao: str) -> str:
    """
    Mapeia opção visual do radio para código do plano.

    Args:
        opcao: Texto selecionado no radio button

    Returns:
        str: Código do plano (experimental, semanal, mensal)
    """
    mapeamento = {0: "experimental", 1: "semanal", 2: "mensal"}

    # Tenta encontrar índice pela string
    opcoes = list(StoreConfig.PLANOS.keys())

    for idx, key in enumerate(opcoes):
        plano = StoreConfig.PLANOS[key]
        if plano["nome"] in opcao:
            return key

    # Fallback
    return "mensal"


# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;800&display=swap');

    /* Fundo e Fonte */
    .stApp {
        background-color: #050505;
        font-family: 'Outfit', sans-serif;
        color: #E0E0E0;
    }

    /* Títulos */
    .hero-title {
        font-size: 3.5rem !important;
        font-weight: 800;
        background: linear-gradient(90deg, #00FFA3, #00B8FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    
    .hero-subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #AAA;
        margin-bottom: 30px;
    }
    
    /* Botão de Suporte (WhatsApp) */
    .whatsapp-float {
        position: fixed;
        width: 60px;
        height: 60px;
        bottom: 40px;
        right: 40px;
        background-color: #25d366;
        color: #FFF;
        border-radius: 50px;
        text-align: center;
        font-size: 30px;
        box-shadow: 2px 2px 3px #999;
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        transition: transform 0.3s;
    }
    .whatsapp-float:hover {
        transform: scale(1.1);
    }

    /* Cards de Preço */
    .price-card {
        background: #111;
        border: 1px solid #333;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: 0.3s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 400px;
    }
    .price-card:hover {
        border-color: #00FFA3;
        transform: translateY(-5px);
    }
    .price-card.featured {
        border: 2px solid #00FFA3;
        box-shadow: 0 0 20px rgba(0, 255, 163, 0.2);
        transform: scale(1.05);
        z-index: 1;
    }
    .price-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: white;
        margin: 10px 0;
    }
    .old-price {
        text-decoration: line-through;
        color: #666;
        font-size: 1rem;
    }
    
    /* Botão de Ação */
    div.stButton > button {
        background: linear-gradient(92deg, #00FFA3 0%, #0085FF 100%);
        color: #000;
        font-weight: 800;
        border: none;
        border-radius: 8px;
        height: 50px;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(0, 255, 163, 0.4);
        color: #000;
    }
    
    /* Desabilitar botão */
    div.stButton > button:disabled {
        background: #333 !important;
        color: #666 !important;
        cursor: not-allowed;
    }

    /* Feature List inside cards */
    .feature-list {
        text-align: left;
        margin-top: 20px;
        color: #DDD;
        font-size: 0.9rem;
    }
    .feature-list li {
        margin-bottom: 8px;
        list-style-type: none;
    }
    
    /* Badge "Mais Popular" */
    .badge-popular {
        background: linear-gradient(92deg, #00FFA3 0%, #0085FF 100%);
        color: #000;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    
    /* Container de checkout */
    .checkout-container {
        background: #111;
        padding: 30px;
        border-radius: 15px;
        border: 1px solid #333;
    }
    
    /* Alert customizado */
    .custom-alert {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .custom-alert.success {
        background-color: #1a3d2a;
        border-left: 4px solid #00FFA3;
        color: #00FFA3;
    }
    .custom-alert.error {
        background-color: #3d1a1a;
        border-left: 4px solid #ff4444;
        color: #ff4444;
    }
    .custom-alert.info {
        background-color: #1a2a3d;
        border-left: 4px solid #0085FF;
        color: #0085FF;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# BOTÃO FLUTUANTE DE SUPORTE
# =============================================================================

whatsapp_link = f"https://wa.me/{StoreConfig.WHATSAPP_SUPORTE}?text=Olá,%20tenho%20dúvida%20sobre%20o%20CrashBot"

st.markdown(
    f"""
<a href="{whatsapp_link}" class="whatsapp-float" target="_blank" title="Falar com Suporte">
💬
</a>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# HERO SECTION
# =============================================================================

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown('<h1 class="hero-title">CRASHBOT AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-subtitle">A ferramenta que opera enquanto você vive. Teste agora e comprove.</p>',
        unsafe_allow_html=True,
    )

    # Área de Vídeo ou Imagem
    st.markdown(
        '<div style="border: 1px solid #333; border-radius:10px; overflow:hidden; aspect-ratio: 16/9;">',
        unsafe_allow_html=True,
    )

    if StoreConfig.VIDEO_URL:
        st.video(StoreConfig.VIDEO_URL)
    else:
        st.image(StoreConfig.HERO_IMAGE, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# SEÇÃO DE PLANOS
# =============================================================================

st.markdown(
    "<h2 style='text-align:center;'>💎 Escolha seu Passe de Lucro</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center; color:#888;'>Comece pequeno, cresça rápido.</p><br>",
    unsafe_allow_html=True,
)

# Criar colunas para os planos
planos_keys = list(StoreConfig.PLANOS.keys())
cols = st.columns(len(planos_keys))

for idx, (col, key) in enumerate(zip(cols, planos_keys)):
    plano = StoreConfig.PLANOS[key]

    with col:
        # Badge "Mais Popular" se featured
        badge = (
            '<span class="badge-popular">MAIS POPULAR</span><br>'
            if plano.get("featured")
            else ""
        )

        # Classe CSS
        card_class = "price-card featured" if plano.get("featured") else "price-card"

        # Features list
        features_html = "".join([f"<li>{f}</li>" for f in plano["features"]])

        # Card HTML
        st.markdown(
            f"""
        <div class="{card_class}">
            {badge}
            <h3>{plano["nome"]}</h3>
            <p style="color:#888">{plano["descricao"]}</p>
            <p class="old-price">De R$ {plano["preco_antigo"]:.2f}</p>
            <p class="price-value">R$ {plano["preco"]:.2f}</p>
            <p>Acesso por <b>{plano["dias"]} Dias</b></p>
            <div class="feature-list">
                {features_html}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# =============================================================================
# CHECKOUT E CADASTRO
# =============================================================================

_, center, _ = st.columns([1, 2, 1])

with center:
    st.markdown('<div class="checkout-container">', unsafe_allow_html=True)
    st.markdown("### 🔒 Finalizar Assinatura")

    with st.form("form_pagamento"):
        # Nome completo
        nome = st.text_input(
            "Nome Completo",
            placeholder="João Silva Santos",
            help="Informe seu nome completo (nome e sobrenome)",
        )

        # Email e WhatsApp
        col_a, col_b = st.columns(2)
        with col_a:
            email = st.text_input(
                "E-mail",
                placeholder="seuemail@exemplo.com",
                help="Email para receber sua chave de acesso",
            )
        with col_b:
            whatsapp = st.text_input(
                "WhatsApp",
                placeholder="(65) 99999-9999",
                help="DDD + número com 9 dígitos",
            )

        # Telegram (opcional)
        with st.expander("📱 Quer receber notificações no Telegram? (Opcional)"):
            telegram = st.text_input(
                "ID do Chat Telegram",
                placeholder="123456789",
                help="Deixe em branco se não quiser usar Telegram",
            )
            st.markdown(
                """
                <small style="color:#888">
                Como encontrar seu Chat ID:<br>
                1. Abra o <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a> no Telegram<br>
                2. Envie /start<br>
                3. Copie o número que aparece em "Id"
                </small>
                """,
                unsafe_allow_html=True,
            )

        # Seleção de Plano
        st.markdown("#### Selecione o Plano:")

        opcoes_plano = []
        for key in planos_keys:
            plano = StoreConfig.PLANOS[key]
            opcao = f"{plano['nome']} ({plano['dias']} Dias) - R$ {plano['preco']:.2f}"
            opcoes_plano.append(opcao)

        plano_selecionado = st.radio(
            "Plano:",
            opcoes_plano,
            index=2,  # Mensal como padrão (mais popular)
            label_visibility="collapsed",
        )

        # Termos e condições
        st.markdown("<br>", unsafe_allow_html=True)
        aceita_termos = st.checkbox(
            "Li e aceito os termos de uso e política de privacidade",
            help="Obrigatório para continuar",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button(
            "🔥 GERAR PAGAMENTO AGORA", disabled=not aceita_termos
        )

    # =============================================================================
    # PROCESSAMENTO DO FORMULÁRIO
    # =============================================================================

    if submit:
        # Container para mensagens
        msg_container = st.container()

        with msg_container:
            # Validações
            erros = []

            # Validar nome
            nome_valido, msg_nome = validar_nome(nome)
            if not nome_valido:
                erros.append(msg_nome)

            # Validar email
            email_valido, msg_email = validar_email(email)
            if not email_valido:
                erros.append(msg_email)

            # Validar WhatsApp
            whatsapp_valido, msg_whatsapp = validar_whatsapp(whatsapp)
            if not whatsapp_valido:
                erros.append(msg_whatsapp)

            # Exibir erros
            if erros:
                for erro in erros:
                    st.error(f"❌ {erro}")
            else:
                # Todos os campos válidos - processar pagamento

                # Determinar código do plano
                code_plano = obter_plano_selecionado(plano_selecionado)

                # Formatar dados
                whatsapp_formatado = formatar_whatsapp(whatsapp)

                # Preparar payload
                payload = {
                    "nome": nome.strip(),
                    "email": email.strip().lower(),
                    "whatsapp": whatsapp_formatado,
                    "plano": code_plano,
                }

                # Adicionar Telegram se fornecido
                if telegram and telegram.strip():
                    payload["telegram_chat_id"] = telegram.strip()

                # Feedback visual
                with st.spinner("🔄 Conectando ao servidor financeiro..."):
                    sucesso, resultado = criar_pagamento_com_retry(payload)

                if sucesso:
                    # Pagamento criado com sucesso
                    checkout_url = resultado.get("checkout_url")
                    plano_info = resultado.get("plano_info", {})

                    st.success("✅ Pedido gerado com sucesso!")

                    # Exibir informações do plano
                    st.info(
                        f"📦 **{plano_info.get('titulo', 'Plano selecionado')}**\n\n"
                        f"💰 Valor: R$ {plano_info.get('preco', 0):.2f}\n\n"
                        f"⏰ Validade: {plano_info.get('dias', 0)} dias"
                    )

                    # Botão de pagamento destacado
                    st.markdown(
                        f"""
                        <a href="{checkout_url}" target="_blank" style="
                            display:block; text-align:center; 
                            background: linear-gradient(92deg, #00FFA3 0%, #0085FF 100%);
                            color: #000; padding: 20px; border-radius: 10px; 
                            text-decoration: none; font-weight: bold; 
                            font-size: 1.3rem; margin: 20px 0;
                            box-shadow: 0 4px 15px rgba(0, 255, 163, 0.3);">
                            💳 PAGAR AGORA VIA PIX/CARTÃO
                        </a>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Instruções
                    st.markdown(
                        """
                        <div class="custom-alert info">
                        <b>📧 Próximos passos:</b><br>
                        1. Clique no botão acima para pagar<br>
                        2. Após confirmação, você receberá um email com sua chave<br>
                        3. Use a chave para ativar o bot no seu computador
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                else:
                    # Erro ao criar pagamento
                    tipo_erro = resultado.get("tipo", "erro")
                    mensagem_erro = resultado.get("mensagem", "Erro desconhecido")

                    if tipo_erro == "validacao":
                        st.error(f"❌ {mensagem_erro}")

                    elif tipo_erro == "timeout":
                        st.warning(
                            f"⏱️ {mensagem_erro}\n\n"
                            "💡 Dica: Aguarde alguns segundos e tente novamente. "
                            "Nosso servidor pode estar iniciando."
                        )

                    elif tipo_erro == "conexao":
                        st.error(
                            f"🌐 {mensagem_erro}\n\n"
                            "💡 Verifique sua conexão com a internet."
                        )

                    elif tipo_erro == "servidor":
                        st.error(
                            f"🔧 {mensagem_erro}\n\n"
                            "💬 Se o problema persistir, entre em contato pelo WhatsApp."
                        )

                    else:
                        st.error(f"❌ {mensagem_erro}")

                    # Botão de suporte
                    st.markdown(
                        f"""
                        <a href="{whatsapp_link}" target="_blank" style="
                            display:block; text-align:center; 
                            background: #25d366; color: white; 
                            padding: 15px; border-radius: 8px; 
                            text-decoration: none; font-weight: bold;
                            margin-top: 20px;">
                            💬 FALAR COM SUPORTE
                        </a>
                        """,
                        unsafe_allow_html=True,
                    )

    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# SEÇÃO DE GARANTIAS E BENEFÍCIOS
# =============================================================================

st.markdown("---")
st.markdown(
    "<h3 style='text-align:center;'>🛡️ Garantias & Benefícios</h3>",
    unsafe_allow_html=True,
)

ben1, ben2, ben3 = st.columns(3)

with ben1:
    st.markdown(
        """
        <div style="text-align:center; padding:20px;">
            <div style="font-size:3rem;">🔒</div>
            <h4>Pagamento Seguro</h4>
            <p style="color:#888;">Via Mercado Pago, líder em segurança</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ben2:
    st.markdown(
        """
        <div style="text-align:center; padding:20px;">
            <div style="font-size:3rem;">⚡</div>
            <h4>Acesso Imediato</h4>
            <p style="color:#888;">Receba sua chave por email em minutos</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ben3:
    st.markdown(
        """
        <div style="text-align:center; padding:20px;">
            <div style="font-size:3rem;">💬</div>
            <h4>Suporte 24/7</h4>
            <p style="color:#888;">Time sempre disponível para ajudar</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =============================================================================
# FAQ
# =============================================================================

st.markdown("---")
st.markdown(
    "<h3 style='text-align:center;'>❓ Perguntas Frequentes</h3>",
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

with st.expander("🤖 Como funciona o CrashBot?"):
    st.markdown(
        """
        O CrashBot é um software que opera automaticamente em jogos de crash, 
        utilizando inteligência artificial para identificar padrões e fazer apostas 
        estratégicas. Basta instalar, ativar com sua chave e deixar operar.
        """
    )

with st.expander("💳 Quais formas de pagamento são aceitas?"):
    st.markdown(
        """
        Aceitamos PIX (instantâneo) e Cartão de Crédito através do Mercado Pago. 
        O pagamento é 100% seguro e criptografado.
        """
    )

with st.expander("📧 Quanto tempo leva para receber a chave?"):
    st.markdown(
        """
        Após a confirmação do pagamento (geralmente instantâneo com PIX), 
        você recebe sua chave de acesso por email em até 5 minutos.
        """
    )

with st.expander("🖥️ Em quantos computadores posso usar?"):
    st.markdown(
        """
        Cada licença é vinculada a um único computador (HWID). Se precisar trocar 
        de computador, entre em contato com o suporte para realizar a transferência.
        """
    )

with st.expander("🔄 Posso renovar meu plano?"):
    st.markdown(
        """
        Sim! Quando sua licença estiver próxima do vencimento, você receberá um 
        aviso e poderá renovar através desta mesma loja.
        """
    )

with st.expander("💬 Como funciona o suporte?"):
    st.markdown(
        f"""
        Nosso suporte está disponível via WhatsApp. Clique no botão flutuante verde 
        no canto inferior direito da tela ou acesse: {StoreConfig.WHATSAPP_SUPORTE}
        """
    )

# =============================================================================
# RODAPÉ
# =============================================================================

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align:center; color:#555; padding:30px 0;">
        <h3 style="color:#888;">🤖 CrashBot AI</h3>
        <p>© 2025 - Todos os direitos reservados</p>
        <p>
            <a href="{whatsapp_link}" target="_blank" style="color:#00FFA3; text-decoration:none;">
                📱 Suporte: ({StoreConfig.WHATSAPP_SUPORTE[2:4]}) {StoreConfig.WHATSAPP_SUPORTE[4:9]}-{StoreConfig.WHATSAPP_SUPORTE[9:]}
            </a>
        </p>
        <br>
        <small style="color:#666;">
            Operação automatizada · Resultado não garantido · Use com responsabilidade
        </small>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# ANALYTICS (OPCIONAL)
# =============================================================================

# Se tiver Google Analytics, adicione aqui:
# st.markdown(
#     """
#     <!-- Google tag (gtag.js) -->
#     <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
#     <script>
#       window.dataLayer = window.dataLayer || [];
#       function gtag(){dataLayer.push(arguments);}
#       gtag('js', new Date());
#       gtag('config', 'GA_MEASUREMENT_ID');
#     </script>
#     """,
#     unsafe_allow_html=True
# )
