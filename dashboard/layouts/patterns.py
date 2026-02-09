"""
Página Patterns - Padrões descobertos e detecção de regimes.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

from config import COLORS


def create_patterns_layout() -> html.Div:
    """Cria o layout da página de padrões."""
    return html.Div([
        # Resumo de padrões
        dbc.Row(className="g-3 mb-4", children=[
            dbc.Col(html.Div(
                className="kpi-card",
                style={"--card-accent": COLORS["cyan"]},
                children=[
                    html.Div("PADRÕES ATIVOS", className="kpi-label"),
                    html.Div(id="patterns-active-count", className="kpi-value",
                             style={"color": COLORS["cyan"]}),
                    html.Div("Baseado na análise dos dados", className="kpi-sub"),
                ],
            ), md=3),
            dbc.Col(html.Div(
                className="kpi-card",
                style={"--card-accent": COLORS["green"]},
                children=[
                    html.Div("OPORTUNIDADES HOJE", className="kpi-label"),
                    html.Div(id="patterns-opportunities", className="kpi-value",
                             style={"color": COLORS["green"]}),
                    html.Div("Sinais no período", className="kpi-sub"),
                ],
            ), md=3),
            dbc.Col(html.Div(
                className="kpi-card",
                style={"--card-accent": COLORS["magenta"]},
                children=[
                    html.Div("TAXA DE ACERTO", className="kpi-label"),
                    html.Div(id="patterns-hit-rate", className="kpi-value",
                             style={"color": COLORS["magenta"]}),
                    html.Div("Nos últimos 30 dias", className="kpi-sub"),
                ],
            ), md=3),
            dbc.Col(html.Div(
                className="kpi-card",
                style={"--card-accent": COLORS["yellow"]},
                children=[
                    html.Div("REGIME ATUAL", className="kpi-label"),
                    html.Div(id="patterns-regime", className="kpi-value",
                             style={"color": COLORS["yellow"]}),
                    html.Div("Detectado via volatilidade", className="kpi-sub"),
                ],
            ), md=3),
        ]),

        # Volatilidade ao longo do tempo
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("VOLATILIDADE ROLLING (STD 20)", className="chart-title"),
                    dcc.Graph(id="patterns-volatility", config={"displayModeBar": False}),
                ],
            ), md=12),
        ]),

        # Distribuição por regime + Concept drift
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("% LOW POR SEMANA (CONCEPT DRIFT)", className="chart-title"),
                    dcc.Graph(id="patterns-concept-drift", config={"displayModeBar": False}),
                ],
            ), md=6),
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("DISTRIBUIÇÃO POR REGIME", className="chart-title"),
                    dcc.Graph(id="patterns-regime-dist", config={"displayModeBar": False}),
                ],
            ), md=6),
        ]),

        # Padrões por horário
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("PERFORMANCE POR FAIXA HORÁRIA", className="chart-title"),
                    dcc.Graph(id="patterns-hourly-perf", config={"displayModeBar": False}),
                ],
            ), md=12),
        ]),
    ])
