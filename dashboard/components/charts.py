"""
Gráficos reutilizáveis com tema futurista.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Cores neon
CYAN = "#00f0ff"
MAGENTA = "#ff00ff"
GREEN = "#00ff88"
RED = "#ff3366"
YELLOW = "#ffff00"
ORANGE = "#ff8800"

# Layout base futurista
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#e0e0ff", size=12),
    title_font=dict(family="Orbitron, monospace", size=14, color=CYAN),
    xaxis=dict(
        gridcolor="rgba(42,42,90,0.4)",
        zerolinecolor="rgba(42,42,90,0.4)",
    ),
    yaxis=dict(
        gridcolor="rgba(42,42,90,0.4)",
        zerolinecolor="rgba(42,42,90,0.4)",
    ),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    ),
)


def apply_theme(fig: go.Figure) -> go.Figure:
    """Aplica tema futurista a qualquer figura."""
    fig.update_layout(**BASE_LAYOUT)
    return fig


def multiplier_timeline(df: pd.DataFrame, last_n: int = 500) -> go.Figure:
    """Gráfico de linha dos últimos N multiplicadores."""
    data = df.tail(last_n)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["date"],
        y=data["multiplicador"],
        mode="lines",
        line=dict(color=CYAN, width=1),
        fill="tozeroy",
        fillcolor="rgba(0,240,255,0.05)",
        name="Multiplicador",
    ))
    fig.add_hline(y=2.0, line_dash="dash", line_color=RED, opacity=0.5,
                  annotation_text="2.0x")

    fig = apply_theme(fig)
    fig.update_layout(
        title=f"Últimos {last_n} Multiplicadores",
        xaxis_title="",
        yaxis_title="Multiplicador",
        height=350,
    )
    return fig


def multiplier_distribution(df: pd.DataFrame) -> go.Figure:
    """Histograma da distribuição dos multiplicadores."""
    data = df[df["multiplicador"] <= 20]["multiplicador"]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data, nbinsx=150,
        marker_color=CYAN,
        opacity=0.8,
        name="Distribuição",
    ))
    fig.add_vline(x=2.0, line_dash="dash", line_color=RED,
                  annotation_text="LOW < 2.0x")

    fig = apply_theme(fig)
    fig.update_layout(
        title="Distribuição dos Multiplicadores",
        xaxis_title="Multiplicador",
        yaxis_title="Frequência",
        height=350,
    )
    return fig


def streak_distribution(streak_df: pd.DataFrame) -> go.Figure:
    """Gráfico de streaks observado vs teórico."""
    data = streak_df[streak_df["streak"] <= 20]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["streak"], y=data["observado"],
        name="Observado", marker_color=CYAN, opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=data["streak"], y=data["teorico"],
        name="Teórico (IID)", mode="lines+markers",
        line=dict(color=RED, width=2, dash="dash"),
    ))

    fig = apply_theme(fig)
    fig.update_layout(
        title="Streaks LOW: Observado vs Teórico",
        xaxis_title="Comprimento da Streak",
        yaxis_title="Frequência",
        height=400,
    )
    return fig


def conditional_probability(cond_df: pd.DataFrame, baseline: float) -> go.Figure:
    """Gráfico de probabilidade condicional por posição na streak."""
    fig = go.Figure()
    colors = [GREEN if p < baseline else RED for p in cond_df["prob_next_low"]]

    fig.add_trace(go.Bar(
        x=cond_df["posicao"],
        y=cond_df["prob_next_low"] * 100,
        marker_color=colors,
        text=[f"{p*100:.1f}%" for p in cond_df["prob_next_low"]],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig.add_hline(
        y=baseline * 100, line_dash="dash", line_color=YELLOW,
        annotation_text=f"Baseline: {baseline*100:.1f}%",
    )

    fig = apply_theme(fig)
    fig.update_layout(
        title="P(next=LOW) por Posição na Streak",
        xaxis_title="Posição na Streak",
        yaxis_title="Probabilidade (%)",
        height=400,
        showlegend=False,
    )
    return fig


def hourly_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap de % LOW por Hora x Dia da Semana."""
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    heatmap = df.groupby(["dia_semana", "hora"])["is_low"].mean().unstack(fill_value=0) * 100

    fig = go.Figure(go.Heatmap(
        z=heatmap.values,
        x=[str(h) for h in heatmap.columns],
        y=[dias[i] for i in heatmap.index],
        colorscale="RdYlGn_r",
        colorbar=dict(title="% LOW"),
    ))

    fig = apply_theme(fig)
    fig.update_layout(
        title="% LOW por Hora x Dia da Semana",
        xaxis_title="Hora",
        yaxis_title="",
        height=350,
    )
    return fig


def monthly_evolution(df: pd.DataFrame) -> go.Figure:
    """Evolução mensal: média, % LOW, max streak."""
    monthly = df.groupby("ano_mes").agg(
        media=("multiplicador", "mean"),
        pct_low=("is_low", "mean"),
        max_streak=("low_streak", "max"),
        contagem=("multiplicador", "count"),
    ).reset_index()

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Média Mensal", "% LOWs", "Max Streak"),
        shared_xaxes=True,
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=monthly["ano_mes"], y=monthly["media"],
        mode="lines+markers", name="Média",
        line=dict(color=CYAN, width=2),
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=monthly["ano_mes"], y=monthly["pct_low"] * 100,
        name="% LOW", marker_color=MAGENTA, opacity=0.7,
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        x=monthly["ano_mes"], y=monthly["max_streak"],
        name="Max Streak", marker_color=RED, opacity=0.7,
    ), row=3, col=1)
    fig.add_hline(y=12, line_dash="dash", line_color=YELLOW,
                  row=3, col=1, annotation_text="Tragédia (12+)")

    fig = apply_theme(fig)
    fig.update_layout(height=750, title_text="Evolução Mensal")
    return fig


def last_rounds_table_data(df: pd.DataFrame, n: int = 100) -> list[dict]:
    """Prepara dados dos últimos N rounds para a tabela."""
    last = df.tail(n).copy()
    last["date_str"] = last["date"].dt.strftime("%d/%m %H:%M")
    last["mult_str"] = last["multiplicador"].apply(lambda x: f"{x:.2f}x")

    return last[["date_str", "mult_str", "tipo", "low_streak"]].to_dict("records")


def win_rate_gauge(win_rate: float, target: float = 60.0) -> go.Figure:
    """Gauge de win rate."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=win_rate,
        number=dict(suffix="%", font=dict(family="Orbitron", size=36, color=CYAN)),
        delta=dict(reference=target, suffix="%"),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor="#2a2a5a"),
            bar=dict(color=CYAN),
            bgcolor="#1a1a3a",
            bordercolor="#2a2a5a",
            steps=[
                dict(range=[0, 40], color="rgba(255,51,102,0.2)"),
                dict(range=[40, 55], color="rgba(255,136,0,0.2)"),
                dict(range=[55, 70], color="rgba(255,255,0,0.2)"),
                dict(range=[70, 100], color="rgba(0,255,136,0.2)"),
            ],
            threshold=dict(
                line=dict(color=YELLOW, width=3),
                thickness=0.8,
                value=target,
            ),
        ),
    ))

    fig = apply_theme(fig)
    fig.update_layout(height=280, title="Win Rate")
    return fig
