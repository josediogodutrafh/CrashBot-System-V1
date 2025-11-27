"""
🎯 CRASHBOT ADMIN CENTER - Dashboard Completo
Versão 2.0 - Arquitetura em 4 Etapas

Fluxo de Dados:
1. Ingestão de Dados (Data Loader)
2. Processamento Macro (Visão do Dono)
3. Auditoria Individual (Espião)
4. CRM & Canais (Lista de Contato)
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# =============================================================================
# 📋 CONFIGURAÇÃO INICIAL
# =============================================================================

st.set_page_config(
    page_title="Crash AdminCenter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS
st.markdown(
    """
<style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .stDataFrame { border: 1px solid #444; border-radius: 5px; }
    h1, h2, h3 { color: #00FFA3; }
    .status-ativo { color: #00FF00; font-weight: bold; }
    .status-vencido { color: #FF0000; font-weight: bold; }
    .status-expirando { color: #FFA500; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 🔌 CONEXÃO COM BANCO DE DADOS
# =============================================================================

try:
    if "DB_URL" in st.secrets:
        DB_URL = st.secrets["DB_URL"]
    else:
        # Fallback para código hardcoded (apenas para teste rápido, não recomendado em produção)
        DB_URL = "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"
except FileNotFoundError:
    DB_URL = "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)


@st.cache_resource
def get_connection():
    """Cria e mantém a conexão com o banco de dados."""
    try:
        return create_engine(DB_URL, pool_pre_ping=True)
    except Exception as e:
        st.error(f"❌ Erro crítico ao conectar no banco: {e}")
        st.stop()


# =============================================================================
# 📥 ETAPA 1: INGESTÃO DE DADOS (DATA LOADER)
# =============================================================================


@st.cache_data(ttl=60)
def carregar_dados_crm(dias_analise: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    🎯 ETAPA 1: Ingestão e Higienização de Dados

    Responsabilidades:
    - Conectar no banco e baixar dados
    - Normalizar campos vazios (WhatsApp, Telegram)
    - Calcular status temporal das licenças
    - Garantir tipos de dados corretos

    Args:
        dias_analise: Número de dias para filtrar logs

    Returns:
        Tuple[df_logs, df_licencas]: DataFrames limpos e prontos para uso
    """

    engine = get_connection()
    data_corte = datetime.now() - timedelta(days=dias_analise)
    agora = datetime.now()

    # -------------------------------------------------------------------------
    # Query 1: Logs de Atividade (com filtro temporal para performance)
    # -------------------------------------------------------------------------
    sql_logs = """
        SELECT
            id,
            timestamp,
            tipo,
            hwid,
            lucro,
            dados
        FROM log_bot
        WHERE timestamp >= :data_corte
        ORDER BY timestamp DESC
    """

    # -------------------------------------------------------------------------
    # Query 2: Base de Licenças (CRM completo)
    # -------------------------------------------------------------------------
    sql_licencas = """
        SELECT
            id,
            cliente_nome,
            chave,
            hwid,
            ativa,
            data_expiracao,
            email_cliente,
            whatsapp,
            telegram_chat_id,
            plano_tipo,
            payment_id,
            created_at
        FROM licenca
        ORDER BY id DESC
    """

    try:
        with engine.connect() as conn:
            # Carrega dados usando prepared statements (segurança contra SQL injection)
            df_logs = pd.read_sql(
                text(sql_logs), conn, params={"data_corte": data_corte}
            )
            df_licencas = pd.read_sql(text(sql_licencas), conn)

        # =====================================================================
        # 🧹 HIGIENIZAÇÃO DOS LOGS
        # =====================================================================
        if not df_logs.empty:
            # Converte timestamp para datetime
            df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"])

            # Garante que lucro é numérico
            df_logs["lucro"] = pd.to_numeric(df_logs["lucro"], errors="coerce").fillna(
                0
            )

            # Preenche campos vazios
            df_logs["hwid"] = df_logs["hwid"].fillna("DESCONHECIDO")
            df_logs["tipo"] = df_logs["tipo"].fillna("unknown")
            df_logs["dados"] = df_logs["dados"].fillna("")

        # =====================================================================
        # 🧹 HIGIENIZAÇÃO DAS LICENÇAS
        # =====================================================================
        if not df_licencas.empty:
            # Converte datas
            df_licencas["data_expiracao"] = pd.to_datetime(
                df_licencas["data_expiracao"], errors="coerce"
            )

            if "created_at" in df_licencas.columns:
                df_licencas["created_at"] = pd.to_datetime(
                    df_licencas["created_at"], errors="coerce"
                )

            # Normaliza campos de contato (preenche vazios)
            df_licencas["whatsapp"] = df_licencas["whatsapp"].fillna("Não informado")
            df_licencas["telegram_chat_id"] = df_licencas["telegram_chat_id"].fillna(
                "Não informado"
            )
            df_licencas["email_cliente"] = df_licencas["email_cliente"].fillna(
                "Não informado"
            )

            # Normaliza plano (importante para cálculos financeiros)
            df_licencas["plano_tipo"] = df_licencas["plano_tipo"].fillna(
                "Não especificado"
            )

            # Garante que ativa é booleano
            df_licencas["ativa"] = df_licencas["ativa"].fillna(False).astype(bool)

            # # ===============================================================
            # 🎯 CÁLCULO DE STATUS TEMPORAL (CORRIGIDO)
            # ===============================================================

            # 1. Cria 'agora' como Timestamp do Pandas (Inteligente com Fuso)
            tem_fuso = df_licencas["data_expiracao"].dt.tz is not None
            agora = pd.Timestamp.now(tz="UTC" if tem_fuso else None)

            def calcular_status(row):
                val_expira = row["data_expiracao"]

                if pd.isna(val_expira):
                    return "⚪ Sem Data"

                # 2. Cálculo seguro linha a linha
                try:
                    dias = (val_expira - agora).days
                except TypeError:
                    # Fallback: Se der conflito de fuso, remove de ambos e calcula cru
                    dias = (
                        val_expira.replace(tzinfo=None) - agora.replace(tzinfo=None)
                    ).days

                if dias < 0:
                    return "🔴 Vencida"
                elif dias <= 3:
                    return "🟡 Expirando"
                else:
                    return "🟢 Ativa"

            # Aplica a função de status
            df_licencas["status_tempo"] = df_licencas.apply(calcular_status, axis=1)

            # 3. CORREÇÃO PYLANCE: Cálculo vetorizado explícito
            # Convertemos a coluna para datetime novamente apenas para garantir ao Pylance que é data
            datas_garantidas = pd.to_datetime(
                df_licencas["data_expiracao"], utc=tem_fuso
            )
            df_licencas["dias_restantes"] = (datas_garantidas - agora).dt.days

            # ===============================================================
            # 📊 ENRIQUECIMENTO: Adiciona flag de canal de contato
            # ===============================================================
            df_licencas["tem_whatsapp"] = df_licencas["whatsapp"] != "Não informado"
            df_licencas["tem_telegram"] = (
                df_licencas["telegram_chat_id"] != "Não informado"
            )

        return df_logs, df_licencas

    except Exception as e:
        st.error(f"⚠️ Erro ao buscar dados no banco: {e}")
        st.error(f"Detalhes técnicos: {str(e)}")

        # Retorna DataFrames vazios estruturados
        df_logs_vazio = pd.DataFrame(
            columns=["id", "timestamp", "tipo", "hwid", "lucro", "dados"]
        )
        df_licencas_vazio = pd.DataFrame(
            columns=[
                "id",
                "cliente_nome",
                "chave",
                "hwid",
                "ativa",
                "data_expiracao",
                "email_cliente",
                "whatsapp",
                "telegram_chat_id",
                "plano_tipo",
                "payment_id",
                "status_tempo",
                "dias_restantes",
                "tem_whatsapp",
                "tem_telegram",
            ]
        )
        return df_logs_vazio, df_licencas_vazio


# =============================================================================
# 📊 ETAPA 2: PROCESSAMENTO MACRO (VISÃO DO DONO)
# =============================================================================


def _calcular_metricas_financeiras(df_licencas: pd.DataFrame) -> dict:
    """Helper: Calcula apenas as métricas financeiras."""
    PRECOS_PLANOS = {
        "Experimental": 4.99,
        "Semanal": 149.00,
        "Mensal": 499.00,
        "Não especificado": 0.00,
    }

    if df_licencas.empty:
        return {
            "faturamento_total": 0,
            "distribuicao_planos": {},
            "clientes_ativos": 0,
            "clientes_vencidos": 0,
            "clientes_expirando": 0,
        }

    # Cálculos
    distribuicao_planos = df_licencas[df_licencas["ativa"]]["plano_tipo"].value_counts()

    faturamento_total = sum(
        distribuicao_planos.get(plano, 0) * preco
        for plano, preco in PRECOS_PLANOS.items()
    )

    return {
        "faturamento_total": faturamento_total,
        "distribuicao_planos": distribuicao_planos.to_dict(),
        "clientes_ativos": int(df_licencas["ativa"].sum()),
        "clientes_vencidos": len(
            df_licencas[df_licencas["status_tempo"] == "🔴 Vencida"]
        ),
        "clientes_expirando": len(
            df_licencas[df_licencas["status_tempo"] == "🟡 Expirando"]
        ),
    }


def _calcular_metricas_operacionais(df_logs: pd.DataFrame) -> dict:
    """Helper: Calcula apenas as métricas operacionais dos bots."""
    if df_logs.empty:
        return {
            "lucro_rede": 0,
            "total_apostas": 0,
            "total_erros": 0,
            "total_operacoes": 0,
            "taxa_erro": 0,
        }

    total_operacoes = len(df_logs)
    total_erros = len(df_logs[df_logs["tipo"] == "error"])

    taxa_erro = (total_erros / total_operacoes * 100) if total_operacoes > 0 else 0

    return {
        "lucro_rede": df_logs["lucro"].sum(),
        "total_apostas": len(df_logs[df_logs["tipo"] == "bet"]),
        "total_erros": total_erros,
        "total_operacoes": total_operacoes,
        "taxa_erro": taxa_erro,
    }


def calcular_metricas_macro(df_logs: pd.DataFrame, df_licencas: pd.DataFrame) -> dict:
    """
    ETAPA 2: Cálculos Financeiros e Operacionais Globais
    (Agora refatorada para usar helpers, deixando o Sourcery feliz)
    """
    # Combina os dois dicionários em um só
    metricas_fin = _calcular_metricas_financeiras(df_licencas)
    metricas_ops = _calcular_metricas_operacionais(df_logs)

    return {**metricas_fin, **metricas_ops}


def renderizar_visao_macro(df_logs: pd.DataFrame, df_licencas: pd.DataFrame):
    """Renderiza a aba de Visão Macro (Dono)."""

    st.markdown("### 📊 Saúde Financeira do Sistema")

    metricas = calcular_metricas_macro(df_logs, df_licencas)

    # -------------------------------------------------------------------------
    # 💳 CARTÕES DE MÉTRICAS FINANCEIRAS
    # -------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💰 Faturamento Recorrente",
            f"R$ {metricas['faturamento_total']:.2f}",
            help="Soma dos planos ativos (mensalidades)",
        )

    with col2:
        st.metric(
            "🟢 Clientes Ativos",
            metricas["clientes_ativos"],
            help="Licenças com status 'ativa = True'",
        )

    with col3:
        delta_vencidos = (
            f"-{metricas['clientes_vencidos']}"
            if metricas["clientes_vencidos"] > 0
            else "0"
        )
        st.metric(
            "🔴 Vencidas",
            metricas["clientes_vencidos"],
            delta=delta_vencidos,
            delta_color="inverse",
            help="Licenças que expiraram",
        )

    with col4:
        st.metric(
            "🟡 Expirando (3 dias)",
            metricas["clientes_expirando"],
            help="Renovar urgentemente!",
        )

    st.divider()

    # -------------------------------------------------------------------------
    # 📊 GRÁFICO: DISTRIBUIÇÃO DE VENDAS POR PLANO
    # -------------------------------------------------------------------------

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### 🎯 Distribuição de Planos Vendidos")

        if metricas["distribuicao_planos"]:
            # Prepara dados para o gráfico
            df_planos = pd.DataFrame(
                list(metricas["distribuicao_planos"].items()),
                columns=["Plano", "Quantidade"],
            )

            # Gráfico de barras horizontal
            st.bar_chart(df_planos.set_index("Plano"), color="#00FFA3")
        else:
            st.info("Nenhum plano vendido ainda.")

    with col_chart2:
        st.markdown("#### 🤖 Performance Operacional")

        col_op1, col_op2 = st.columns(2)

        with col_op1:
            st.metric(
                "💵 Lucro da Rede",
                f"R$ {metricas['lucro_rede']:.2f}",
                delta="Positivo" if metricas["lucro_rede"] >= 0 else "Negativo",
            )

        with col_op2:
            st.metric("🎲 Total Apostas", metricas["total_apostas"])

        st.metric(
            "⚠️ Taxa de Erros", f"{metricas['taxa_erro']:.1f}%", delta_color="inverse"
        )

    # -------------------------------------------------------------------------
    # 📈 GRÁFICO: TENDÊNCIA DE LUCRO GLOBAL
    # -------------------------------------------------------------------------

    if not df_logs.empty:
        st.divider()
        st.markdown("#### 📈 Tendência de Lucro Global (Hora a Hora)")

        # Agrupa por hora e soma o lucro
        df_chart = df_logs.copy()
        chart_data = df_chart.set_index("timestamp").resample("H")["lucro"].sum()

        st.area_chart(chart_data, color="#00FFA3")
    else:
        st.info("📊 Nenhum log registrado no período. Os bots ainda não operaram.")


# =============================================================================
# 🕵️ ETAPA 3: AUDITORIA INDIVIDUAL (ESPIÃO)
# =============================================================================


def renderizar_auditoria_individual(df_logs: pd.DataFrame, df_licencas: pd.DataFrame):
    """
    🎯 ETAPA 3: Análise Detalhada por Cliente

    Cruza HWID com logs e mostra:
    - Status da licença (vencida/ativa)
    - Performance financeira individual
    - Histórico de operações
    """

    st.markdown("### 🕵️ Auditoria Individual de Cliente")

    if df_licencas.empty:
        st.error("❌ Nenhuma licença encontrada no banco de dados.")
        return

    # -------------------------------------------------------------------------
    # 🔍 SELETOR DE CLIENTE
    # -------------------------------------------------------------------------

    lista_clientes = sorted(df_licencas["cliente_nome"].unique().tolist())

    cliente_selecionado = st.selectbox(
        "🔎 Pesquise ou Selecione o Cliente:", ["Selecione..."] + lista_clientes
    )

    if cliente_selecionado == "Selecione...":
        st.info("👆 Selecione um cliente acima para visualizar seus dados.")
        return

    # -------------------------------------------------------------------------
    # 📋 RECUPERA DADOS DO CLIENTE
    # -------------------------------------------------------------------------

    dados_cliente = df_licencas[
        df_licencas["cliente_nome"] == cliente_selecionado
    ].iloc[0]

    hwid_alvo = dados_cliente["hwid"]
    email = dados_cliente["email_cliente"]
    whatsapp = dados_cliente["whatsapp"]
    telegram = dados_cliente["telegram_chat_id"]
    plano = dados_cliente["plano_tipo"]
    status_tempo = dados_cliente["status_tempo"]
    dias_rest = dados_cliente["dias_restantes"]
    data_exp = dados_cliente["data_expiracao"]

    # -------------------------------------------------------------------------
    # 🎴 CARD DE INFORMAÇÕES DO CLIENTE
    # -------------------------------------------------------------------------

    st.markdown(
        f"""
    <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #00FFA3;">
        <h3 style="margin-top: 0;">👤 {cliente_selecionado}</h3>
        <p><strong>📧 Email:</strong> {email}</p>
        <p><strong>📱 WhatsApp:</strong> {whatsapp}</p>
        <p><strong>💬 Telegram:</strong> {telegram}</p>
        <p><strong>💎 Plano:</strong> {plano}</p>
        <p><strong>📅 Validade:</strong> {data_exp.strftime('%d/%m/%Y') if pd.notna(data_exp) else 'N/A'}</p>
        <p><strong>Status:</strong> {status_tempo} ({dias_rest} dias restantes)</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    # -------------------------------------------------------------------------
    # 📊 FILTRA LOGS DESSE CLIENTE (HWID)
    # -------------------------------------------------------------------------

    if df_logs.empty:
        st.warning("⚠️ Não há logs globais para filtrar.")
        return

    df_cliente = df_logs[df_logs["hwid"] == hwid_alvo].copy()

    if df_cliente.empty:
        st.warning(
            f"⚠️ O cliente **{cliente_selecionado}** existe no banco, "
            f"mas não há registros de atividade. Possíveis causas:\n"
            f"- Bot desligado\n"
            f"- Sem internet\n"
            f"- HWID não vinculado corretamente"
        )
        return

    # -------------------------------------------------------------------------
    # 📈 KPIs DO CLIENTE
    # -------------------------------------------------------------------------

    lucro_cliente = df_cliente["lucro"].sum()
    total_ops = len(df_cliente)
    total_apostas_cli = len(df_cliente[df_cliente["tipo"] == "bet"])

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("💰 Resultado Financeiro", f"R$ {lucro_cliente:.2f}")
    k2.metric("📊 Total de Ações", total_ops)
    k3.metric("🎲 Apostas", total_apostas_cli)

    with k4:
        if lucro_cliente > 0:
            st.success("✅ LUCRANDO")
        elif lucro_cliente < 0:
            st.error("📉 PREJUÍZO")
        else:
            st.warning("⚪ ZERO A ZERO")

    st.divider()

    # -------------------------------------------------------------------------
    # 📉 GRÁFICO: EVOLUÇÃO DO LUCRO ACUMULADO
    # -------------------------------------------------------------------------

    st.markdown("#### 📉 Evolução do Lucro (Acumulado)")

    df_cliente = df_cliente.sort_values("timestamp")
    df_cliente["saldo_acumulado"] = df_cliente["lucro"].cumsum()

    st.line_chart(df_cliente.set_index("timestamp")["saldo_acumulado"], color="#00FFA3")

    # -------------------------------------------------------------------------
    # 📜 TABELA DETALHADA (LOG DE AUDITORIA)
    # -------------------------------------------------------------------------

    st.markdown("#### 📜 Registro de Atividades")

    st.dataframe(
        df_cliente[["timestamp", "tipo", "dados", "lucro"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.DatetimeColumn(
                "Horário", format="DD/MM HH:mm:ss"
            ),
            "tipo": st.column_config.TextColumn("Tipo"),
            "dados": st.column_config.TextColumn("Detalhes"),
            "lucro": st.column_config.NumberColumn("Resultado", format="R$ %.2f"),
        },
    )


# =============================================================================
# 💼 ETAPA 4: CRM & CANAIS (LISTA DE CONTATO)
# =============================================================================


def renderizar_crm(df_licencas: pd.DataFrame):
    """
    🎯 ETAPA 4: Gestão de Base de Clientes e Canais de Contato

    Exibe tabela filtrada por:
    - Status da licença
    - Canal de contato (WhatsApp/Telegram)
    - Tipo de plano
    """

    st.markdown("### 💼 Base de Clientes & Contato")
    st.caption("Dados capturados na Loja. Use para suporte, renovação ou campanhas.")

    if df_licencas.empty:
        st.error("❌ Nenhuma licença encontrada no banco de dados.")
        return

    # -------------------------------------------------------------------------
    # 🔍 FILTROS INTERATIVOS
    # -------------------------------------------------------------------------

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        filtro_status = st.multiselect(
            "Status:",
            options=df_licencas["status_tempo"].unique(),
            default=df_licencas["status_tempo"].unique(),
        )

    with col_f2:
        filtro_plano = st.multiselect(
            "Plano:",
            options=df_licencas["plano_tipo"].unique(),
            default=df_licencas["plano_tipo"].unique(),
        )

    with col_f3:
        filtro_canal = st.selectbox(
            "Canal de Contato:",
            ["Todos", "Tem WhatsApp", "Tem Telegram", "Ambos", "Nenhum"],
        )

    # -------------------------------------------------------------------------
    # 🎯 APLICA FILTROS
    # -------------------------------------------------------------------------

    df_filtrado = df_licencas[
        (df_licencas["status_tempo"].isin(filtro_status))
        & (df_licencas["plano_tipo"].isin(filtro_plano))
    ].copy()

    # Filtro de canal
    if filtro_canal == "Tem WhatsApp":
        df_filtrado = df_filtrado[df_filtrado["tem_whatsapp"]]
    elif filtro_canal == "Tem Telegram":
        df_filtrado = df_filtrado[df_filtrado["tem_telegram"]]
    elif filtro_canal == "Ambos":
        df_filtrado = df_filtrado[
            (df_filtrado["tem_whatsapp"]) & (df_filtrado["tem_telegram"])
        ]
    elif filtro_canal == "Nenhum":
        df_filtrado = df_filtrado[
            (~df_filtrado["tem_whatsapp"]) & (~df_filtrado["tem_telegram"])
        ]

    # -------------------------------------------------------------------------
    # 📊 ESTATÍSTICAS RÁPIDAS
    # -------------------------------------------------------------------------

    total_filtrado = len(df_filtrado)
    com_whatsapp = df_filtrado["tem_whatsapp"].sum()
    com_telegram = df_filtrado["tem_telegram"].sum()

    st.markdown(
        f"""
    **📊 Resumo da Filtragem:** {total_filtrado} clientes |
    📱 {com_whatsapp} com WhatsApp |
    💬 {com_telegram} com Telegram
    """
    )

    # -------------------------------------------------------------------------
    # 📋 TABELA PRINCIPAL
    # -------------------------------------------------------------------------

    st.dataframe(
        df_filtrado[
            [
                "cliente_nome",
                "status_tempo",
                "plano_tipo",
                "dias_restantes",
                "whatsapp",
                "telegram_chat_id",
                "email_cliente",
                "chave",
                "ativa",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente_nome": "👤 Cliente",
            "status_tempo": "📊 Status",
            "plano_tipo": "💎 Plano",
            "dias_restantes": st.column_config.NumberColumn(
                "⏰ Dias Rest.", help="Dias até expiração"
            ),
            "whatsapp": "📱 WhatsApp",
            "telegram_chat_id": "💬 Telegram",
            "email_cliente": "📧 Email",
            "chave": "🔑 Licença",
            "ativa": st.column_config.CheckboxColumn("✅ Ativa", disabled=True),
        },
    )

    # -------------------------------------------------------------------------
    # 📥 BOTÃO DE EXPORTAÇÃO
    # -------------------------------------------------------------------------

    st.divider()

    col_exp1, col_exp2 = st.columns([3, 1])

    with col_exp2:
        csv = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar para CSV",
            data=csv,
            file_name=f"crm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


# =============================================================================
# 🛠️ ETAPA 5: ADMIN & AÇÕES - REFATORADO (CORREÇÃO SOURCERY)
# =============================================================================


def _renderizar_aba_gerar_licenca(engine):
    """Sub-função: Gerencia o formulário de criação de licenças."""
    st.caption("Use para criar cortesias ou vendas feitas fora do site.")

    with st.form("form_licenca"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Cliente", placeholder="Ex: João Silva")
            whatsapp = st.text_input("WhatsApp", placeholder="Ex: 11999999999")
            plano = st.selectbox(
                "Tipo de Plano", ["mensal", "semanal", "experimental", "anual"]
            )

        with col2:
            email = st.text_input("Email (Opcional)", placeholder="joao@email.com")
            telegram = st.text_input("Telegram (Opcional)")
            dias = st.number_input("Dias de Validade", min_value=1, value=30, step=1)

        if st.form_submit_button("🚀 Gerar Licença Agora", use_container_width=True):
            if not nome:
                st.error("O campo 'Nome' é obrigatório.")
                return

            # Lógica de Geração
            chave = f"KEY-{str(uuid.uuid4()).upper()[:14]}"
            payment_id_fake = f"MANUAL-{uuid.uuid4().hex[:8]}"
            data_expiracao = datetime.now() + timedelta(days=dias)

            sql_insert = text(
                """
                INSERT INTO licenca (
                    chave, cliente_nome, email_cliente, whatsapp,
                    telegram_chat_id, plano_tipo, payment_id,
                    dias_validade, data_expiracao, ativa, created_at, hwid
                ) VALUES (
                    :chave, :nome, :email, :whatsapp,
                    :telegram, :plano, :pid,
                    :dias, :data_exp, :ativa, :created_at, :hwid
                )
            """
            )

            params = {
                "chave": chave,
                "nome": nome,
                "email": email or "manual@sem_email.com",
                "whatsapp": whatsapp or "Não informado",
                "telegram": telegram or "Não informado",
                "plano": plano,
                "pid": payment_id_fake,
                "dias": dias,
                "data_exp": data_expiracao,
                "ativa": True,
                "created_at": datetime.now(),
                "hwid": None,
            }

            try:
                with engine.begin() as conn:
                    conn.execute(sql_insert, params)
                st.success("✅ Licença criada com sucesso!")
                st.code(chave, language="text")
            except Exception as e:
                st.error(f"Erro ao gravar no banco: {e}")


def _renderizar_aba_cancelar_licenca(engine):
    """Sub-função: Gerencia a busca e cancelamento de licenças."""
    st.warning(
        "⚠️ Atenção: Ao cancelar uma licença, o bot do cliente parará de funcionar imediatamente."
    )

    termo_busca = st.text_input("🔍 Buscar Cliente (Nome, Email ou Chave):")

    if not termo_busca:
        return

    sql_busca = text(
        """
        SELECT id, cliente_nome, email_cliente, chave, ativa, plano_tipo
        FROM licenca
        WHERE cliente_nome ILIKE :busca OR email_cliente ILIKE :busca OR chave ILIKE :busca
        LIMIT 10
    """
    )

    try:
        with engine.connect() as conn:
            resultados = pd.read_sql(
                sql_busca, conn, params={"busca": f"%{termo_busca}%"}
            )

        if resultados.empty:
            st.info("Nenhum cliente encontrado com esse termo.")
            return

        st.write("Resultados encontrados:")

        opcoes = resultados.apply(
            lambda x: f"[{'🟢 ATIVA' if x['ativa'] else '🔴 CANCELADA'}] {x['cliente_nome']} ({x['email_cliente']}) - {x['chave']}",
            axis=1,
        ).tolist()

        selecionado_str = st.selectbox(
            "Selecione a licença para alterar:", options=opcoes
        )

        index_sel = opcoes.index(selecionado_str)
        licenca = resultados.iloc[index_sel]

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if licenca["ativa"]:
                if st.button(
                    f"🚫 BLOQUEAR {licenca['cliente_nome']}",
                    type="primary",
                    use_container_width=True,
                ):
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE licenca SET ativa = FALSE WHERE id = :id"),
                            {"id": int(licenca["id"])},
                        )
                    st.rerun()
            else:
                st.info("Esta licença já está bloqueada.")

        with col_btn2:
            if not licenca["ativa"]:
                if st.button(
                    f"✅ REATIVAR {licenca['cliente_nome']}", use_container_width=True
                ):
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE licenca SET ativa = TRUE WHERE id = :id"),
                            {"id": int(licenca["id"])},
                        )
                    st.rerun()
            else:
                st.info("Esta licença já está ativa.")

    except Exception as e:
        st.error(f"Erro na busca: {e}")


def renderizar_acoes_admin(engine):
    """
    🎯 ETAPA 5: Painel Administrativo (Controlador Principal)
    Agora atua apenas como um gerenciador de fluxo, delegando o trabalho pesado.
    """
    st.markdown("### 🛠️ Painel Administrativo")

    acao = st.radio(
        "O que deseja fazer?",
        ["✨ Gerar Nova Licença", "🚫 Cancelar/Revogar Licença"],
        horizontal=True,
    )
    st.divider()

    if acao == "✨ Gerar Nova Licença":
        _renderizar_aba_gerar_licenca(engine)
    elif acao == "🚫 Cancelar/Revogar Licença":
        _renderizar_aba_cancelar_licenca(engine)


# =============================================================================
# 🚀 APLICAÇÃO PRINCIPAL
# =============================================================================
def main():
    """Função principal que orquestra todo o dashboard."""

    # -------------------------------------------------------------------------
    # 🎛️ SIDEBAR - CONTROLES
    # -------------------------------------------------------------------------

    st.sidebar.header("🎛️ Filtros de Análise")

    filtro_dias = st.sidebar.slider(
        "📅 Período de Análise (Dias)",
        min_value=1,
        max_value=30,
        value=7,
        help="Quantos dias de logs carregar",
    )

    if st.sidebar.button("🔄 Atualizar Dados Agora"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    st.sidebar.info(
        "💡 **Dica:** O 'Lucro da Rede' soma o resultado de TODOS os bots ativos."
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"🕐 Última atualização: {time.strftime('%H:%M:%S')}")

    # -------------------------------------------------------------------------
    # 📥 CARREGAMENTO DE DADOS (ETAPA 1)
    # -------------------------------------------------------------------------

    with st.spinner(f"🔄 Carregando dados dos últimos {filtro_dias} dias..."):
        df_logs, df_licencas = carregar_dados_crm(filtro_dias)

    # -------------------------------------------------------------------------
    # 🎨 HEADER PRINCIPAL
    # -------------------------------------------------------------------------

    st.title("🚀 CrashBot Command Center")
    st.markdown("**Dashboard de Gestão Completa** | Vendas • Performance • CRM")

    st.divider()

    # -------------------------------------------------------------------------
    # 📑 SISTEMA DE ABAS
    # -------------------------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🦅 Visão Macro (Dono)",
            "🕵️ Espionar Bot (Cliente)",
            "💼 CRM & Vendas",
            "🛠️ Gerar Licença",
        ]
    )

    # ETAPA 2: Visão Macro
    with tab1:
        renderizar_visao_macro(df_logs, df_licencas)

    # ETAPA 3: Auditoria Individual
    with tab2:
        renderizar_auditoria_individual(df_logs, df_licencas)

    # ETAPA 4: CRM
    with tab3:
        renderizar_crm(df_licencas)

    # ETAPA 5: Gerador Manual (NOVO)
    with tab4:
        # Precisamos passar o engine para gravar no banco
        engine = get_connection()
        renderizar_acoes_admin(engine)

    # -------------------------------------------------------------------------
    # 📍 RODAPÉ
    # -------------------------------------------------------------------------

    st.markdown("---")
    st.caption(
        f"⚡ Powered by Streamlit | "
        f"🗄️ Render PostgreSQL | "
        f"🕐 {time.strftime('%d/%m/%Y %H:%M:%S')}"
    )


# =============================================================================
# 🎬 PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    main()
