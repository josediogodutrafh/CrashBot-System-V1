import time

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURAÇÃO ---
st.set_page_config(
    page_title="CrashAdmin",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CONEXÃO COM O BANCO ---
# COLE AQUI A SUA 'EXTERNAL DATABASE URL' DO RENDER
DB_URL = "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"

# Correção para o SQLAlchemy (postgres -> postgresql)
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)


@st.cache_resource
def get_connection():
    return create_engine(DB_URL)


try:
    engine = get_connection()
except Exception as e:
    st.error(f"Erro ao conectar no banco: {e}")
    st.stop()


# --- FUNÇÕES DE DADOS ---
def carregar_licencas():
    query = "SELECT * FROM licenca ORDER BY id DESC"
    return pd.read_sql(query, engine)


def carregar_logs_recentes():
    query = "SELECT * FROM log_bot ORDER BY timestamp DESC LIMIT 50"
    return pd.read_sql(query, engine)


def carregar_kpis():
    """Carrega KPIs principais usando queries diretas (Mais rápido e Type-Safe)."""
    try:
        with engine.connect() as conn:
            # Executa a query e pega apenas o primeiro valor escalar
            total_clientes = conn.execute(text("SELECT COUNT(*) FROM licenca")).scalar()
            total_logs = conn.execute(text("SELECT COUNT(*) FROM log_bot")).scalar()

        # Garante que se vier None (tabela vazia), retorna 0
        return int(total_clientes or 0), int(total_logs or 0)

    except Exception as e:
        st.error(f"Erro ao carregar KPIs: {e}")
        return 0, 0


# --- INTERFACE (SIDEBAR) ---
st.sidebar.title("🚀 Painel de Controle")
pagina = st.sidebar.radio(
    "Navegação", ["Visão Geral", "Gerenciar Licenças", "Telemetria ao Vivo"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

# --- PÁGINA: VISÃO GERAL ---
if pagina == "Visão Geral":
    st.title("📊 Visão Geral do Negócio")

    # A função carregar_kpis agora retorna inteiros puros (int), sem sujeira do Pandas
    total_clientes, total_logs = carregar_kpis()

    col1, col2, col3 = st.columns(3)

    # O Pylance não vai mais reclamar, pois as variáveis são do tipo 'int'
    col1.metric("Clientes Totais", total_clientes)
    col2.metric("Atividade (Logs)", total_logs)
    col3.metric("Status do Servidor", "ONLINE 🟢")

    st.markdown("### 🕒 Últimas Atividades")
    df_logs = carregar_logs_recentes()
    st.dataframe(df_logs, use_container_width=True)

# --- PÁGINA: GERENCIAR LICENÇAS ---
elif pagina == "Gerenciar Licenças":
    st.title("🔑 Gerenciamento de Licenças")

    df_licencas = carregar_licencas()

    # Mostra tabela colorida
    st.dataframe(
        df_licencas,
        use_container_width=True,
        column_config={
            "ativa": st.column_config.CheckboxColumn("Ativa?", disabled=True),
            "data_expiracao": st.column_config.DatetimeColumn(
                "Expira em", format="D/M/Y"
            ),
        },
    )

    st.info("💡 Para criar novas chaves, implementaremos o botão aqui em breve.")

# --- PÁGINA: TELEMETRIA ---
elif pagina == "Telemetria ao Vivo":
    st.title("📡 Telemetria em Tempo Real")

    # Auto-refresh simples
    placeholder = st.empty()

    if st.button("Parar Monitoramento"):
        st.stop()

    # Loop de atualização (simulação de real-time)
    for _ in range(100):
        df_logs = carregar_logs_recentes()
        with placeholder.container():
            st.dataframe(df_logs, height=600, use_container_width=True)
            time.sleep(2)  # Atualiza a cada 2 segundos
