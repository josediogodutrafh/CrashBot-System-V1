"""
Componentes de filtro para o dashboard.
"""

from dash import dcc, html


def date_range_filter(min_date: str, max_date: str) -> html.Div:
    """Filtro de intervalo de datas."""
    return html.Div(
        className="filter-panel",
        children=[
            html.Div("Período", className="filter-label"),
            dcc.DatePickerRange(
                id="date-filter",
                start_date=min_date,
                end_date=max_date,
                display_format="DD/MM/YYYY",
                style={"width": "100%"},
            ),
        ],
    )


def hour_filter() -> html.Div:
    """Filtro de hora do dia."""
    return html.Div(
        className="filter-panel",
        children=[
            html.Div("Hora do Dia", className="filter-label"),
            dcc.RangeSlider(
                id="hour-filter",
                min=0, max=23, step=1,
                value=[0, 23],
                marks={h: str(h) for h in range(0, 24, 3)},
                tooltip={"placement": "bottom"},
            ),
        ],
    )


def streak_filter() -> html.Div:
    """Filtro de tamanho de streak."""
    return html.Div(
        className="filter-panel",
        children=[
            html.Div("Streak Mínima", className="filter-label"),
            dcc.Slider(
                id="streak-filter",
                min=0, max=20, step=1,
                value=0,
                marks={i: str(i) for i in range(0, 21, 5)},
                tooltip={"placement": "bottom"},
            ),
        ],
    )


def sample_size_dropdown() -> html.Div:
    """Dropdown para selecionar quantidade de dados."""
    return html.Div(
        className="filter-panel",
        children=[
            html.Div("Amostra", className="filter-label"),
            dcc.Dropdown(
                id="sample-size",
                options=[
                    {"label": "Últimos 10K", "value": 10000},
                    {"label": "Últimos 50K", "value": 50000},
                    {"label": "Últimos 100K", "value": 100000},
                    {"label": "Últimos 500K", "value": 500000},
                    {"label": "Último Ano", "value": -365},
                    {"label": "Tudo (3.9M)", "value": -1},
                ],
                value=100000,
                clearable=False,
                style={
                    "backgroundColor": "#1a1a3a",
                    "color": "#e0e0ff",
                    "border": "1px solid #2a2a5a",
                    "borderRadius": "8px",
                },
            ),
        ],
    )
