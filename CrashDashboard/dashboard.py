from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Crash AdminCenter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILO CSS PERSONALIZADO (Para ficar bonito) ---
st.markdown(
    """
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    .stDataFrame { border: 1px solid #333; }
</style>
""",
    unsafe_allow_html=True,
)

# --- CONEXÃO COM O BANCO (RENDER) ---
# Substitua pela sua URL Externa do Render se mudar
DB_URL = "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)


@st.cache_resource
def get_connection():
    return create_engine(DB_URL)


try:
    engine = get_connection()
except Exception as e:
    st.error(f"❌ Erro crítico de conexão: {e}")
    st.stop()


# --- CARREGAMENTO DE DADOS OTIMIZADO ---
def get_data(dias=7):
    """Puxa logs e licenças dos últimos X dias"""
    data_corte = datetime.now() - timedelta(days=dias)

    with engine.connect() as conn:
        # 1. Puxar Logs (Com filtro de data - query parametrizada e segura)
        query_logs = text(
            """
            SELECT * FROM log_bot
            WHERE timestamp >= :data_corte
            ORDER BY timestamp DESC
        """
        )
        df_logs = pd.read_sql(query_logs, conn, params={"data_corte": data_corte})

        # 2. Puxar Licenças (Todas)
        query_licencas = text("SELECT * FROM licenca ORDER BY id DESC")
        df_licencas = pd.read_sql(query_licencas, conn)

    return df_logs, df_licencas


# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🎛️ Filtros")
filtro_dias = st.sidebar.slider("Período de Análise (Dias)", 1, 30, 7)

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Carrega os dados
with st.spinner("Baixando dados da nuvem..."):
    df_logs, df_licencas = get_data(filtro_dias)

# --- CORPO PRINCIPAL ---
st.title("🚀 CrashBot Command Center")

# Abas para organizar a bagunça
tab1, tab2, tab3 = st.tabs(["🦅 Visão Macro", "🕵️ Espionar Cliente", "💼 Gestão & CRM"])

# ===================================================
# ABA 1: VISÃO MACRO (Resumo do Negócio)
# ===================================================
with tab1:
    st.markdown("### 📊 Performance Global do Sistema")

    if not df_logs.empty:
        # Métricas Calculadas
        total_lucro_rede = df_logs["lucro"].sum()
        total_apostas = df_logs[df_logs["tipo"] == "bet"].shape[0]
        total_erros = df_logs[df_logs["tipo"] == "error"].shape[0]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Lucro da Rede (Pontos)", f"{total_lucro_rede:.2f}", delta_color="normal"
        )
        col2.metric("Total de Apostas", total_apostas)
        col3.metric(
            "Erros Registrados", total_erros, delta_color="inverse"
        )  # Vermelho se subir
        col4.metric("Licenças Ativas", int(df_licencas["ativa"].sum()))

        # Gráfico de Lucro Global (Agrupado por hora)
        st.subheader("📈 Tendência de Lucro (Todos os Bots)")
        # Converter timestamp para datetime se necessário
        df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"])
        chart_data = df_logs.set_index("timestamp").resample("H")["lucro"].sum()
        st.line_chart(chart_data)

    else:
        st.info("Nenhum dado de log encontrado no período selecionado.")

# ===================================================
# ABA 2: ESPIONAR CLIENTE (Detalhe Individual)
# ===================================================
with tab2:
    st.markdown("### 🕵️ Análise Individual")

    # Seletor de Cliente (Pelo nome ou HWID)
    lista_clientes = df_licencas["cliente_nome"].unique().tolist()
    cliente_selecionado = st.selectbox(
        "Selecione o Cliente:", ["Todos"] + lista_clientes
    )

    if cliente_selecionado != "Todos":
        # Descobrir o HWID desse cliente
        hwid_alvo = df_licencas[df_licencas["cliente_nome"] == cliente_selecionado][
            "hwid"
        ].iloc[0]

        # Filtrar logs só desse cara
        df_cliente = df_logs[df_logs["hwid"] == hwid_alvo]

        if not df_cliente.empty:
            lucro_cliente = df_cliente["lucro"].sum()

            c1, c2 = st.columns(2)
            c1.metric(f"Lucro de {cliente_selecionado}", f"{lucro_cliente:.2f}")

            if lucro_cliente > 0:
                c2.success("✅ Este cliente está Lucrando!")
            else:
                c2.error("🔻 Este cliente está no Prejuízo!")

            # Gráfico do Cliente
            st.markdown("#### Performance Financeira")
            st.line_chart(df_cliente.set_index("timestamp")["lucro"].cumsum())

            # Tabela de Ações
            st.markdown("#### 📜 Últimas Ações do Bot")
            st.dataframe(
                df_cliente[["timestamp", "tipo", "dados", "lucro"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Este cliente ainda não rodou o bot ou não enviou logs.")
    else:
        st.info("Selecione um cliente acima para ver os detalhes.")

# ===================================================
# ABA 3: GESTÃO & CRM (Dados Cadastrais)
# ===================================================
with tab3:
    st.markdown("### 💼 Base de Clientes")

    # Tratamento para link de WhatsApp
    df_view = df_licencas.copy()

    # Tabela Bonita
    st.dataframe(
        df_view,
        use_container_width=True,
        column_config={
            "chave": "Licença (Key)",
            "cliente_nome": "Nome",
            "email_cliente": "E-mail",
            "whatsapp": "WhatsApp",
            "ativa": st.column_config.CheckboxColumn("Status", disabled=True),
            "data_expiracao": st.column_config.DatetimeColumn(
                "Vencimento", format="D/M/Y"
            ),
            "payment_id": "ID Pagamento",
        },
        hide_index=True,
    )

    st.divider()
    st.markdown("#### 🛠️ Ferramentas Rápidas")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(
            "Para criar licenças manuais, use o script ou o endpoint da API por enquanto."
        )
    with col_b:
        st.warning("⚠️ Cuidado ao alterar dados diretamente no banco.")

# Rodapé
st.markdown("---")
st.caption(f"Dados atualizados em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
