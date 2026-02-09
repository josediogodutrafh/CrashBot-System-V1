"""
Página Overview - Visão geral com KPIs e gráficos principais.
"""

from dash import dcc, html

import dash_bootstrap_components as dbc

from components.charts import (
    conditional_probability,
    hourly_heatmap,
    multiplier_distribution,
    multiplier_timeline,
    streak_distribution,
)
from components.filters import sample_size_dropdown
from components.metrics import kpi_card


def create_overview_layout(kpis: dict) -> html.Div:
    """Cria o layout da página Overview."""
    return html.Div([
        # KPI Row
        dbc.Row(
            className="g-3 mb-4",
            children=[
                dbc.Col(kpi_card(
                    "Total Rounds",
                    f"{kpis['total_rounds']:,}",
                    f"{kpis['date_min'].strftime('%m/%Y')} - {kpis['date_max'].strftime('%m/%Y')}",
                    "#00f0ff",
                ), md=2),
                dbc.Col(kpi_card(
                    "Média",
                    f"{kpis['avg_multiplier']:.2f}x",
                    f"Mediana: {kpis['median_multiplier']:.2f}x",
                    "#ff00ff",
                ), md=2),
                dbc.Col(kpi_card(
                    "% LOW",
                    f"{kpis['pct_low']:.1f}%",
                    f"< {2.0}x",
                    "#ff3366",
                ), md=2),
                dbc.Col(kpi_card(
                    "Max Streak",
                    str(kpis["max_streak"]),
                    "LOWs consecutivos",
                    "#ff8800",
                ), md=2),
                dbc.Col(kpi_card(
                    "Max Mult",
                    f"{kpis['max_multiplier']:.0f}x",
                    "Maior multiplicador",
                    "#00ff88",
                ), md=2),
                dbc.Col(kpi_card(
                    "Tragédias",
                    str(kpis["tragedies"]),
                    "Streaks 12+",
                    "#ffff00",
                ), md=2),
            ],
        ),

        # Filter + Timeline
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(sample_size_dropdown(), md=3),
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("TIMELINE", className="chart-title"),
                    dcc.Graph(id="overview-timeline", config={"displayModeBar": False}),
                ],
            ), md=9),
        ]),

        # Distribution + Streaks
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("DISTRIBUIÇÃO", className="chart-title"),
                    dcc.Graph(id="overview-distribution", config={"displayModeBar": False}),
                ],
            ), md=6),
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("STREAKS: OBSERVADO VS TEÓRICO", className="chart-title"),
                    dcc.Graph(id="overview-streaks", config={"displayModeBar": False}),
                ],
            ), md=6),
        ]),

        # Conditional Probability + Heatmap
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("PROBABILIDADE CONDICIONAL", className="chart-title"),
                    dcc.Graph(id="overview-cond-prob", config={"displayModeBar": False}),
                ],
            ), md=6),
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("HEATMAP: HORA X DIA", className="chart-title"),
                    dcc.Graph(id="overview-heatmap", config={"displayModeBar": False}),
                ],
            ), md=6),
        ]),
    ])
