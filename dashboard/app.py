"""
CRASH AI DASHBOARD - Painel Futurista
=====================================
Execute: python app.py
Acesse:  http://localhost:8050
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, dash_table

# Paths setup
sys.path.insert(0, str(Path(__file__).parent))

from config import COLORS, GOALS, STRATEGY
from data_loader import (
    compute_conditional_probs,
    compute_kpis,
    compute_streak_distribution,
    get_data,
)
from components.charts import (
    apply_theme,
    conditional_probability,
    hourly_heatmap,
    monthly_evolution,
    multiplier_distribution,
    multiplier_timeline,
    streak_distribution,
    win_rate_gauge,
    CYAN, MAGENTA, GREEN, RED, YELLOW, ORANGE,
)
from components.metrics import goal_card, kpi_card
from layouts.overview import create_overview_layout
from layouts.goals import create_goals_layout
from layouts.analysis import create_analysis_layout
from layouts.patterns import create_patterns_layout

# ==============================================================================
# LOAD DATA
# ==============================================================================
print("Carregando dados...")
DF = get_data()
KPIS = compute_kpis(DF)
COND_PROBS = compute_conditional_probs(DF)
STREAK_DIST = compute_streak_distribution(DF)
print(f"Dados carregados: {len(DF):,} registros")

# ==============================================================================
# APP INITIALIZATION
# ==============================================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Crash AI Dashboard",
    update_title="Carregando...",
)

# ==============================================================================
# NAVBAR
# ==============================================================================
navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand("CRASH AI", className="navbar-brand"),
        dbc.Nav([
            dbc.NavLink("OVERVIEW", href="/", active="exact", className="nav-link"),
            dbc.NavLink("GOALS", href="/goals", active="exact", className="nav-link"),
            dbc.NavLink("ANALYSIS", href="/analysis", active="exact", className="nav-link"),
            dbc.NavLink("PATTERNS", href="/patterns", active="exact", className="nav-link"),
        ], className="ms-auto", navbar=True),
    ], fluid=True),
    className="navbar",
    dark=True,
)

# ==============================================================================
# MAIN LAYOUT
# ==============================================================================
app.layout = html.Div(
    style={"backgroundColor": COLORS["bg_primary"], "minHeight": "100vh"},
    children=[
        dcc.Location(id="url", refresh=False),
        navbar,
        dbc.Container(
            id="page-content",
            fluid=True,
            className="py-4 px-4",
        ),
        # Footer
        html.Div(
            className="footer",
            children=[
                f"CRASH AI DASHBOARD // {len(DF):,} registros // "
                f"{DF['date'].min().strftime('%Y-%m')} a {DF['date'].max().strftime('%Y-%m')}"
            ],
        ),
    ],
)


# ==============================================================================
# ROUTING
# ==============================================================================
@callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/goals":
        return create_goals_layout()
    elif pathname == "/analysis":
        min_d = DF["date"].min().strftime("%Y-%m-%d")
        max_d = DF["date"].max().strftime("%Y-%m-%d")
        return create_analysis_layout(min_d, max_d)
    elif pathname == "/patterns":
        return create_patterns_layout()
    else:
        return create_overview_layout(KPIS)


# ==============================================================================
# OVERVIEW CALLBACKS
# ==============================================================================
@callback(
    Output("overview-timeline", "figure"),
    Output("overview-distribution", "figure"),
    Output("overview-streaks", "figure"),
    Output("overview-cond-prob", "figure"),
    Output("overview-heatmap", "figure"),
    Input("sample-size", "value"),
)
def update_overview(sample_size):
    if sample_size == -1:
        df = DF
    elif sample_size < 0:
        days = abs(sample_size)
        cutoff = DF["date"].max() - pd.Timedelta(days=days)
        df = DF[DF["date"] >= cutoff]
    else:
        df = DF.tail(sample_size)

    baseline = df["is_low"].mean()
    cond = compute_conditional_probs(df)
    streaks = compute_streak_distribution(df)

    return (
        multiplier_timeline(df, last_n=min(500, len(df))),
        multiplier_distribution(df),
        streak_distribution(streaks),
        conditional_probability(cond, baseline),
        hourly_heatmap(df),
    )


# ==============================================================================
# GOALS CALLBACKS
# ==============================================================================
@callback(
    Output("goals-cards", "children"),
    Output("goals-winrate-gauge", "figure"),
    Output("goals-simulation", "figure"),
    Input("apply-goals-btn", "n_clicks"),
    *[State(f"goal-input-{key}", "value") for key in GOALS],
    prevent_initial_call=False,
)
def update_goals(n_clicks, *goal_values):
    # Atualizar metas com valores do formulário
    current_goals = {}
    for (key, goal), value in zip(GOALS.items(), goal_values):
        target = value if value is not None else goal["target"]
        current_goals[key] = {**goal, "target": target}

    # Calcular valores atuais baseados na estratégia
    trigger = STRATEGY["trigger"]
    target_mult = STRATEGY["target_multiplier"]

    # Simular sinais: quantas vezes a streak atingiu o trigger
    signals = DF[DF["low_streak"] == trigger]
    total_signals = len(signals)
    total_days = (DF["date"].max() - DF["date"].min()).days
    signals_per_day = total_signals / max(total_days, 1)

    # Win rate: quando trigger ativou, próximo multiplicador >= target
    if len(signals) > 0:
        signal_indices = signals.index
        valid = signal_indices[signal_indices < len(DF) - 1]
        next_mults = DF.loc[valid + 1, "multiplicador"]
        hits = (next_mults >= target_mult).sum()
        win_rate = (hits / len(valid)) * 100 if len(valid) > 0 else 0
    else:
        win_rate = 0

    # Gerar cards
    simulated = {
        "daily_profit": signals_per_day * (target_mult - 1) * win_rate / 100,
        "weekly_profit": signals_per_day * 7 * (target_mult - 1) * win_rate / 100,
        "min_win_rate": win_rate,
        "max_drawdown": -max(DF["low_streak"].max() - trigger, 0) * 4,
        "patterns_per_day": signals_per_day,
    }

    cards = []
    for key, goal in current_goals.items():
        cards.append(goal_card(
            label=goal["label"],
            current=simulated.get(key, 0),
            target=goal["target"],
            unit=goal["unit"],
            color=goal["color"],
            description=goal["description"],
        ))

    # Win rate gauge
    gauge = win_rate_gauge(win_rate, current_goals["min_win_rate"]["target"])

    # Simulação histórica: equity curve
    sim_fig = _build_equity_simulation(DF, trigger, target_mult)

    return cards, gauge, sim_fig


def _build_equity_simulation(df, trigger, target_mult):
    """Constrói curva de equity simulada."""
    is_low = df["is_low"].values
    streaks = df["low_streak"].values
    mults = df["multiplicador"].values
    dates = df["date"].values

    equity = [0.0]
    equity_dates = [dates[0]]
    pattern = STRATEGY["pattern"]
    unit = 1.0

    i = 0
    while i < len(df) - 1:
        if streaks[i] >= trigger:
            dobra = streaks[i] - trigger
            if dobra < len(pattern):
                bet = unit * pattern[dobra]
                if mults[i + 1] >= target_mult:
                    equity.append(equity[-1] + bet * (target_mult - 1))
                else:
                    equity.append(equity[-1] - bet)
                equity_dates.append(dates[i + 1])
        i += 1

    eq_df = pd.DataFrame({"date": equity_dates, "equity": equity})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eq_df["date"], y=eq_df["equity"],
        mode="lines", fill="tozeroy",
        line=dict(color=GREEN, width=2),
        fillcolor="rgba(0,255,136,0.1)",
        name="Equity",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.5)

    fig = apply_theme(fig)
    fig.update_layout(
        xaxis_title="", yaxis_title="Equity (unidades)",
        height=350,
        title="Curva de Equity - Simulação Histórica",
    )
    return fig


# ==============================================================================
# ANALYSIS CALLBACKS
# ==============================================================================
@callback(
    Output("analysis-monthly", "figure"),
    Output("analysis-acf", "figure"),
    Output("analysis-streak-hour", "figure"),
    Output("analysis-stats-table", "children"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("hour-filter", "value"),
    Input("streak-filter", "value"),
)
def update_analysis(start_date, end_date, hour_range, min_streak):
    df = DF.copy()

    if start_date and end_date:
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if hour_range:
        df = df[(df["hora"] >= hour_range[0]) & (df["hora"] <= hour_range[1])]
    if min_streak and min_streak > 0:
        df = df[df["low_streak"] >= min_streak]

    if len(df) == 0:
        empty = go.Figure()
        empty = apply_theme(empty)
        empty.add_annotation(text="Sem dados para os filtros selecionados",
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return empty, empty, empty, html.Div("Sem dados")

    # Monthly evolution
    monthly_fig = monthly_evolution(df)

    # ACF manual
    acf_fig = _build_acf(df)

    # Streak por hora
    streak_hour_fig = _build_streak_by_hour(df)

    # Stats table
    stats_table = _build_stats_table(df)

    return monthly_fig, acf_fig, streak_hour_fig, stats_table


def _build_acf(df, max_lag=50):
    """Autocorrelação manual."""
    series = df["is_low"].values.astype(float)
    n = len(series)
    mean = series.mean()
    var = np.var(series)

    acf_vals = []
    for lag in range(1, min(max_lag + 1, n)):
        cov = np.mean((series[lag:] - mean) * (series[:-lag] - mean))
        acf_vals.append(cov / var if var > 0 else 0)

    ci = 1.96 / np.sqrt(n)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, len(acf_vals) + 1)),
        y=acf_vals,
        marker_color=[CYAN if abs(v) > ci else "#2a2a5a" for v in acf_vals],
    ))
    fig.add_hline(y=ci, line_dash="dash", line_color=RED, opacity=0.5)
    fig.add_hline(y=-ci, line_dash="dash", line_color=RED, opacity=0.5)
    fig.add_hline(y=0, line_color="#2a2a5a")

    fig = apply_theme(fig)
    fig.update_layout(
        xaxis_title="Lag", yaxis_title="ACF",
        height=350, showlegend=False,
    )
    return fig


def _build_streak_by_hour(df):
    """Streak média e máxima por hora do dia."""
    hourly = df[df["low_streak"] > 0].groupby("hora").agg(
        media=("low_streak", "mean"),
        maxima=("low_streak", "max"),
        contagem=("low_streak", "count"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=hourly["hora"], y=hourly["media"],
        name="Média", marker_color=CYAN, opacity=0.7,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=hourly["hora"], y=hourly["maxima"],
        name="Máxima", mode="lines+markers",
        line=dict(color=RED, width=2),
    ), secondary_y=True)

    fig = apply_theme(fig)
    fig.update_layout(height=350)
    fig.update_yaxes(title_text="Streak Média", secondary_y=False)
    fig.update_yaxes(title_text="Streak Máxima", secondary_y=True)
    return fig


def _build_stats_table(df):
    """Tabela de estatísticas por mês."""
    if "ano_mes" not in df.columns:
        df["ano_mes"] = df["date"].dt.to_period("M").astype(str)

    monthly = df.groupby("ano_mes").agg(
        rounds=("multiplicador", "count"),
        media=("multiplicador", "mean"),
        mediana=("multiplicador", "median"),
        pct_low=("is_low", "mean"),
        max_streak=("low_streak", "max"),
        std=("multiplicador", "std"),
    ).reset_index()

    monthly["pct_low"] = (monthly["pct_low"] * 100).round(1)
    monthly["media"] = monthly["media"].round(3)
    monthly["mediana"] = monthly["mediana"].round(3)
    monthly["std"] = monthly["std"].round(3)

    return dash_table.DataTable(
        data=monthly.tail(24).to_dict("records"),
        columns=[
            {"name": "Mês", "id": "ano_mes"},
            {"name": "Rounds", "id": "rounds", "type": "numeric", "format": {"specifier": ","}},
            {"name": "Média", "id": "media"},
            {"name": "Mediana", "id": "mediana"},
            {"name": "% LOW", "id": "pct_low"},
            {"name": "Max Streak", "id": "max_streak"},
            {"name": "Std Dev", "id": "std"},
        ],
        style_header={
            "backgroundColor": "#161637",
            "color": CYAN,
            "fontFamily": "'JetBrains Mono', monospace",
            "fontSize": "0.8rem",
            "fontWeight": "600",
            "borderBottom": f"2px solid {COLORS['border']}",
        },
        style_cell={
            "backgroundColor": "#111128",
            "color": "#e0e0ff",
            "fontFamily": "'JetBrains Mono', monospace",
            "fontSize": "0.8rem",
            "borderBottom": f"1px solid #1a1a3a",
            "padding": "10px 16px",
            "textAlign": "center",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{max_streak} >= 12"},
                "color": RED,
                "fontWeight": "bold",
            },
            {
                "if": {"filter_query": "{pct_low} >= 56"},
                "color": ORANGE,
            },
        ],
        page_size=12,
    )


# ==============================================================================
# PATTERNS CALLBACKS
# ==============================================================================
@callback(
    Output("patterns-active-count", "children"),
    Output("patterns-opportunities", "children"),
    Output("patterns-hit-rate", "children"),
    Output("patterns-regime", "children"),
    Output("patterns-volatility", "figure"),
    Output("patterns-concept-drift", "figure"),
    Output("patterns-regime-dist", "figure"),
    Output("patterns-hourly-perf", "figure"),
    Input("url", "pathname"),
)
def update_patterns(pathname):
    if pathname != "/patterns":
        raise dash.exceptions.PreventUpdate

    trigger = STRATEGY["trigger"]
    target_mult = STRATEGY["target_multiplier"]

    # KPIs
    signals = DF[DF["low_streak"] == trigger]
    total_days = (DF["date"].max() - DF["date"].min()).days
    signals_per_day = len(signals) / max(total_days, 1)

    # Win rate últimos 30 dias
    last_30 = DF[DF["date"] >= DF["date"].max() - pd.Timedelta(days=30)]
    sig_30 = last_30[last_30["low_streak"] == trigger]
    if len(sig_30) > 0:
        valid_idx = sig_30.index[sig_30.index < len(DF) - 1]
        next_m = DF.loc[valid_idx + 1, "multiplicador"]
        hit_rate = f"{(next_m >= target_mult).mean() * 100:.1f}%"
    else:
        hit_rate = "N/A"

    # Regime atual (baseado em volatilidade dos últimos 100 rounds)
    last_100 = DF.tail(100)
    vol = last_100["multiplicador"].std()
    if vol < 2.0:
        regime = "BAIXA VOL"
    elif vol < 5.0:
        regime = "NORMAL"
    else:
        regime = "ALTA VOL"

    # Volatilidade ao longo do tempo
    vol_fig = _build_volatility_chart(DF)

    # Concept drift
    drift_fig = _build_concept_drift(DF)

    # Distribuição por regime
    regime_fig = _build_regime_distribution(DF)

    # Performance por hora
    hourly_fig = _build_hourly_performance(DF)

    return (
        f"{trigger}+",
        f"{signals_per_day:.0f}/dia",
        hit_rate,
        regime,
        vol_fig,
        drift_fig,
        regime_fig,
        hourly_fig,
    )


def _build_volatility_chart(df):
    """Rolling volatility ao longo do tempo."""
    # Amostragem para performance (1 a cada 100 pontos)
    sample = df.iloc[::100].copy()
    if "rolling_std_20" in sample.columns:
        vol = sample["rolling_std_20"]
    else:
        vol = sample["multiplicador"].rolling(20, min_periods=1).std()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sample["date"], y=vol,
        mode="lines", line=dict(color=CYAN, width=1),
        fill="tozeroy", fillcolor="rgba(0,240,255,0.05)",
        name="Volatilidade",
    ))
    fig.add_hline(y=2.0, line_dash="dash", line_color=RED,
                  annotation_text="Threshold")

    fig = apply_theme(fig)
    fig.update_layout(
        xaxis_title="", yaxis_title="Rolling Std (20)",
        height=350,
    )
    return fig


def _build_concept_drift(df):
    """% LOW por semana para detectar concept drift."""
    df_temp = df.copy()
    df_temp["semana"] = df_temp["date"].dt.to_period("W").astype(str)
    weekly = df_temp.groupby("semana")["is_low"].mean().reset_index()
    weekly.columns = ["semana", "pct_low"]

    baseline = df["is_low"].mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["semana"], y=weekly["pct_low"] * 100,
        mode="lines", line=dict(color=MAGENTA, width=1.5),
        name="% LOW Semanal",
    ))
    fig.add_hline(y=baseline * 100, line_dash="dash", line_color=YELLOW,
                  annotation_text=f"Baseline: {baseline*100:.1f}%")

    fig = apply_theme(fig)
    fig.update_layout(
        xaxis_title="", yaxis_title="% LOW",
        height=350, showlegend=False,
        xaxis=dict(tickangle=45, nticks=20),
    )
    return fig


def _build_regime_distribution(df):
    """Distribuição de multiplicadores por regime de volatilidade."""
    if "rolling_std_20" in df.columns:
        vol = df["rolling_std_20"]
    else:
        vol = df["multiplicador"].rolling(20, min_periods=1).std()

    df_temp = df.copy()
    df_temp["regime"] = pd.cut(
        vol, bins=[0, 2, 5, float("inf")],
        labels=["Baixa Vol", "Normal", "Alta Vol"],
    )

    fig = go.Figure()
    for regime, color in [("Baixa Vol", RED), ("Normal", CYAN), ("Alta Vol", GREEN)]:
        mask = df_temp["regime"] == regime
        data = df_temp.loc[mask, "multiplicador"]
        data = data[data <= 15]
        if len(data) > 0:
            fig.add_trace(go.Histogram(
                x=data, name=regime, marker_color=color,
                opacity=0.6, nbinsx=80,
            ))

    fig = apply_theme(fig)
    fig.update_layout(
        barmode="overlay",
        xaxis_title="Multiplicador", yaxis_title="Frequência",
        height=350,
    )
    return fig


def _build_hourly_performance(df):
    """Performance da estratégia por hora do dia."""
    trigger = STRATEGY["trigger"]
    target_mult = STRATEGY["target_multiplier"]

    signals = df[df["low_streak"] == trigger].copy()
    signals["hora_signal"] = signals["hora"]

    results = []
    for hora in range(24):
        mask = signals["hora_signal"] == hora
        sig_hora = signals[mask]
        if len(sig_hora) == 0:
            results.append({"hora": hora, "sinais": 0, "win_rate": 0})
            continue
        valid_idx = sig_hora.index[sig_hora.index < len(df) - 1]
        if len(valid_idx) == 0:
            results.append({"hora": hora, "sinais": len(sig_hora), "win_rate": 0})
            continue
        next_m = df.loc[valid_idx + 1, "multiplicador"]
        wr = (next_m >= target_mult).mean() * 100
        results.append({"hora": hora, "sinais": len(sig_hora), "win_rate": wr})

    res_df = pd.DataFrame(results)
    avg_wr = res_df[res_df["win_rate"] > 0]["win_rate"].mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=res_df["hora"], y=res_df["sinais"],
        name="Sinais", marker_color=CYAN, opacity=0.6,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=res_df["hora"], y=res_df["win_rate"],
        name="Win Rate %", mode="lines+markers",
        line=dict(color=GREEN, width=2),
    ), secondary_y=True)
    fig.add_hline(y=avg_wr, line_dash="dash", line_color=YELLOW,
                  secondary_y=True, annotation_text=f"Média: {avg_wr:.1f}%")

    fig = apply_theme(fig)
    fig.update_layout(height=400)
    fig.update_yaxes(title_text="Sinais", secondary_y=False)
    fig.update_yaxes(title_text="Win Rate %", secondary_y=True)
    return fig


# ==============================================================================
# RUN
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  CRASH AI DASHBOARD")
    print(f"  {len(DF):,} registros carregados")
    print("  http://localhost:8050")
    print("=" * 50 + "\n")
    app.run(debug=True, port=8050)
