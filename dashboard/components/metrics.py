"""
Componentes de métricas KPI reutilizáveis.
"""

from dash import html


def kpi_card(label: str, value: str, sub: str = "", color: str = "#00f0ff") -> html.Div:
    """Cria um card KPI futurista."""
    return html.Div(
        className="kpi-card",
        style={"--card-accent": color},
        children=[
            html.Div(label, className="kpi-label"),
            html.Div(value, className="kpi-value", style={"color": color}),
            html.Div(sub, className="kpi-sub") if sub else None,
        ],
    )


def goal_card(
    label: str,
    current: float,
    target: float,
    unit: str,
    color: str = "#00f0ff",
    description: str = "",
) -> html.Div:
    """Cria um card de meta com barra de progresso."""
    if target == 0:
        pct = 0
    elif target < 0:
        # Drawdown: progresso invertido (quanto mais negativo, pior)
        pct = max(0, min(100, (1 - abs(current) / abs(target)) * 100))
    else:
        pct = max(0, min(100, (current / target) * 100))

    achieved = pct >= 100
    bar_color = "#00ff88" if achieved else color

    if target < 0:
        display_current = f"{current:+,.0f}"
        display_target = f"{target:+,.0f}"
    elif isinstance(target, float) and unit == "%":
        display_current = f"{current:.1f}"
        display_target = f"{target:.1f}"
    else:
        display_current = f"{current:,.0f}"
        display_target = f"{target:,.0f}"

    return html.Div(
        className="goal-card",
        style={"--goal-color": color},
        children=[
            html.Div(
                className="d-flex justify-content-between align-items-start",
                children=[
                    html.Div([
                        html.Div(label, className="goal-label", style={"color": color}),
                        html.Div(description, style={
                            "fontSize": "0.7rem", "color": "#6666aa", "marginTop": "0.2rem"
                        }) if description else None,
                    ]),
                    html.Div(
                        "ATINGIDA" if achieved else f"{pct:.0f}%",
                        style={
                            "color": "#00ff88" if achieved else "#8888aa",
                            "fontFamily": "'JetBrains Mono', monospace",
                            "fontSize": "0.75rem",
                            "fontWeight": "700",
                            "padding": "0.2rem 0.6rem",
                            "background": "rgba(0,255,136,0.1)" if achieved else "rgba(136,136,170,0.1)",
                            "borderRadius": "6px",
                        }
                    ),
                ],
            ),
            html.Div(
                className="goal-progress",
                children=[
                    html.Div(
                        className="goal-progress-bar",
                        style={
                            "width": f"{min(pct, 100)}%",
                            "background": f"linear-gradient(90deg, {bar_color}, {bar_color}88)",
                            "--goal-color": bar_color,
                        },
                    )
                ],
            ),
            html.Div(
                className="d-flex justify-content-between",
                children=[
                    html.Span(
                        f"{display_current} {unit}",
                        className="goal-value",
                        style={"color": bar_color},
                    ),
                    html.Span(
                        f"Meta: {display_target} {unit}",
                        className="goal-target",
                    ),
                ],
            ),
        ],
    )
