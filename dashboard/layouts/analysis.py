"""
Página Analysis - Análise detalhada com filtros.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

from components.filters import date_range_filter, hour_filter, streak_filter
from config import COLORS


def create_analysis_layout(min_date: str, max_date: str) -> html.Div:
    """Cria o layout da página de análise detalhada."""
    return html.Div([
        # Filtros
        dbc.Row(className="g-3 mb-4", children=[
            dbc.Col(date_range_filter(min_date, max_date), md=4),
            dbc.Col(hour_filter(), md=4),
            dbc.Col(streak_filter(), md=4),
        ]),

        # Evolução mensal
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("EVOLUÇÃO MENSAL", className="chart-title"),
                    dcc.Graph(id="analysis-monthly", config={"displayModeBar": False}),
                ],
            ), md=12),
        ]),

        # ACF + Streak por hora
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("AUTOCORRELAÇÃO (LAG 1-50)", className="chart-title"),
                    dcc.Graph(id="analysis-acf", config={"displayModeBar": False}),
                ],
            ), md=6),
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("STREAKS POR HORA DO DIA", className="chart-title"),
                    dcc.Graph(id="analysis-streak-hour", config={"displayModeBar": False}),
                ],
            ), md=6),
        ]),

        # Tabela de estatísticas por período
        dbc.Row(className="g-3 mb-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("ESTATÍSTICAS POR MÊS", className="chart-title"),
                    html.Div(id="analysis-stats-table"),
                ],
            ), md=12),
        ]),
    ])
