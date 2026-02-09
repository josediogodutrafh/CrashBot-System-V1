"""
Configurações do Dashboard - Metas e Parâmetros.
Edite os valores abaixo para ajustar metas e comportamento.
"""

from pathlib import Path

# ==============================================================================
# PATHS
# ==============================================================================
DASHBOARD_DIR = Path(__file__).parent
PROJECT_ROOT = DASHBOARD_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "brabet_crash_COMPLETO.db"
PROCESSED_PARQUET = PROJECT_ROOT / "data" / "processed" / "crash_features.parquet"

# ==============================================================================
# CONSTANTES DO JOGO
# ==============================================================================
LOW_THRESHOLD = 2.0
TRAGEDY_STREAK = 12

# ==============================================================================
# METAS DE ÊXITO (editáveis)
# ==============================================================================
GOALS = {
    "daily_profit": {
        "label": "Lucro Diário",
        "target": 100.0,
        "unit": "R$",
        "icon": "currency-dollar",
        "color": "#00ff88",
        "description": "Meta de lucro líquido por dia de operação",
    },
    "weekly_profit": {
        "label": "Lucro Semanal",
        "target": 500.0,
        "unit": "R$",
        "icon": "graph-up-arrow",
        "color": "#00f0ff",
        "description": "Meta de lucro acumulado na semana",
    },
    "min_win_rate": {
        "label": "Win Rate Mínimo",
        "target": 60.0,
        "unit": "%",
        "icon": "bullseye",
        "color": "#ffff00",
        "description": "Taxa de acerto mínima para validar a estratégia",
    },
    "max_drawdown": {
        "label": "Drawdown Máximo",
        "target": -200.0,
        "unit": "R$",
        "icon": "shield-exclamation",
        "color": "#ff3366",
        "description": "Perda máxima aceitável antes de pausar",
    },
    "patterns_per_day": {
        "label": "Padrões/Dia",
        "target": 80,
        "unit": "sinais",
        "icon": "search",
        "color": "#ff00ff",
        "description": "Quantidade de sinais identificados por dia",
    },
}

# ==============================================================================
# ESTRATÉGIA
# ==============================================================================
STRATEGY = {
    "name": "1-2-4-1-2-4",
    "trigger": 6,
    "target_multiplier": 2.0,
    "pattern": [1, 2, 4, 1, 2, 4],
    "break_at": 12,
}

# ==============================================================================
# VISUAL
# ==============================================================================
COLORS = {
    "bg_primary": "#0a0a1a",
    "bg_secondary": "#111128",
    "bg_card": "#161637",
    "border": "#2a2a5a",
    "text_primary": "#e0e0ff",
    "text_secondary": "#8888aa",
    "cyan": "#00f0ff",
    "magenta": "#ff00ff",
    "green": "#00ff88",
    "red": "#ff3366",
    "yellow": "#ffff00",
    "orange": "#ff8800",
}
