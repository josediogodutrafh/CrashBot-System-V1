"""
Página Goals - Metas de êxito configuráveis.
"""

from dash import dcc, html, callback, Input, Output, State
import dash_bootstrap_components as dbc

from components.charts import win_rate_gauge
from components.metrics import goal_card
from config import GOALS, COLORS


def create_goals_layout() -> html.Div:
    """Cria o layout da página de metas."""
    return html.Div([
        dbc.Row(className="g-3 mb-4", children=[
            # Coluna esquerda: Cards de metas
            dbc.Col(md=8, children=[
                html.Div(
                    "METAS DE ÊXITO",
                    style={
                        "fontFamily": "'Orbitron', monospace",
                        "fontSize": "1rem",
                        "color": COLORS["cyan"],
                        "letterSpacing": "2px",
                        "marginBottom": "1.5rem",
                    },
                ),
                html.Div(id="goals-cards"),
            ]),

            # Coluna direita: Configuração
            dbc.Col(md=4, children=[
                html.Div(
                    className="filter-panel",
                    children=[
                        html.Div(
                            "CONFIGURAR METAS",
                            style={
                                "fontFamily": "'Orbitron', monospace",
                                "fontSize": "0.85rem",
                                "color": COLORS["magenta"],
                                "letterSpacing": "1.5px",
                                "marginBottom": "1.5rem",
                            },
                        ),
                        # Campos editáveis para cada meta
                        *_create_goal_inputs(),
                        html.Br(),
                        dbc.Button(
                            "APLICAR METAS",
                            id="apply-goals-btn",
                            className="w-100",
                            style={
                                "background": f"linear-gradient(135deg, {COLORS['cyan']}, {COLORS['magenta']})",
                                "border": "none",
                                "fontFamily": "'Orbitron', monospace",
                                "fontSize": "0.8rem",
                                "letterSpacing": "1.5px",
                                "padding": "0.8rem",
                                "borderRadius": "10px",
                            },
                        ),
                    ],
                ),

                # Gauge de Win Rate
                html.Div(
                    className="chart-container mt-3",
                    children=[
                        html.Div("WIN RATE", className="chart-title"),
                        dcc.Graph(id="goals-winrate-gauge", config={"displayModeBar": False}),
                    ],
                ),
            ]),
        ]),

        # Simulação de metas (baseada nos dados históricos)
        dbc.Row(className="g-3", children=[
            dbc.Col(html.Div(
                className="chart-container",
                children=[
                    html.Div("SIMULAÇÃO HISTÓRICA DE METAS", className="chart-title"),
                    dcc.Graph(id="goals-simulation", config={"displayModeBar": False}),
                ],
            ), md=12),
        ]),
    ])


def _create_goal_inputs() -> list:
    """Cria inputs editáveis para cada meta."""
    inputs = []
    for key, goal in GOALS.items():
        inputs.append(html.Div(
            className="mb-3",
            children=[
                html.Label(
                    f"{goal['label']} ({goal['unit']})",
                    className="filter-label",
                ),
                dcc.Input(
                    id=f"goal-input-{key}",
                    type="number",
                    value=goal["target"],
                    className="dash-input w-100",
                    style={"color": goal["color"]},
                ),
            ],
        ))
    return inputs
