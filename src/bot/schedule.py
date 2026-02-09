#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HORÁRIOS PREMIUM
================

Tabela de horários com menor % de LOWs, extraída do heatmap
do notebook 02 (3.9M rounds, Dez/2022 a Fev/2026).

Slots verdes+amarelos = % LOW abaixo do ponto médio da escala.
Corte: 54.56% (midpoint entre 53.82% e 55.30%).

Fonte: notebooks/08_simulation_no_reds.ipynb
"""

import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)

BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")

# Horários premium por dia da semana (0=Monday, 6=Sunday)
# Slots com % LOW <= 54.56% (verde + amarelo no heatmap)
PREMIUM_SCHEDULE = {
    0: [3, 4, 5, 7, 8, 10, 15, 16, 17, 19, 23],                    # Segunda
    1: [4, 5, 6, 7, 9, 11, 13, 14, 19, 20, 22, 23],                # Terça
    2: [0, 1, 2, 3, 6, 7, 8, 9, 11, 14, 19, 21, 22, 23],           # Quarta
    3: [3, 5, 6, 8, 9, 11, 12, 13, 14, 15, 16, 18, 20],            # Quinta
    4: [0, 1, 2, 3, 4, 8, 10, 15, 18, 20, 23],                     # Sexta
    5: [0, 2, 4, 5, 7, 8, 12, 13, 14, 15, 16, 18, 19, 20, 21],     # Sábado
    6: [1, 2, 5, 6, 7, 8, 10, 13, 14, 18, 19],                     # Domingo
}

# Horários com % LOW mais baixo (verde escuro, <54.2%)
# Estes são os melhores para o Setup Inteligente operar agressivo
STRONG_PREMIUM = {
    0: [7, 8, 10, 19, 23],          # Segunda
    1: [4, 5, 7, 23],               # Terça
    2: [2, 6, 7, 8, 22],            # Quarta
    3: [3, 8, 16, 18],              # Quinta
    4: [4, 8, 10, 23],              # Sexta
    5: [0, 8, 21],                  # Sábado
    6: [7, 8, 14],                  # Domingo
}


class ScheduleManager:
    """Gerencia horários premium para operação do bot."""

    def __init__(self, premium_only: bool = False):
        self.premium_only = premium_only

    def _now_brasilia(self) -> datetime:
        """Hora atual em Brasília."""
        return datetime.now(BRASILIA_TZ)

    def is_premium_now(self) -> bool:
        """Verifica se o horário atual é premium."""
        now = self._now_brasilia()
        dow = now.weekday()
        hour = now.hour
        return hour in PREMIUM_SCHEDULE.get(dow, [])

    def is_strong_premium_now(self) -> bool:
        """Verifica se é horário premium forte (verde escuro)."""
        now = self._now_brasilia()
        dow = now.weekday()
        hour = now.hour
        return hour in STRONG_PREMIUM.get(dow, [])

    def should_operate(self) -> bool:
        """Retorna True se o bot deve operar agora."""
        if not self.premium_only:
            return True
        return self.is_premium_now()

    def get_premium_strength(self) -> str:
        """Retorna nível do horário atual: 'strong', 'normal' ou 'off'."""
        if self.is_strong_premium_now():
            return "strong"
        if self.is_premium_now():
            return "normal"
        return "off"

    def get_current_info(self) -> dict:
        """Info completa do slot atual."""
        now = self._now_brasilia()
        dow = now.weekday()
        hour = now.hour
        is_prem = self.is_premium_now()
        strength = self.get_premium_strength()

        dias_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        today_hours = PREMIUM_SCHEDULE.get(dow, [])

        # Próximo horário premium
        next_premium = None
        if not is_prem and today_hours:
            future = [h for h in today_hours if h > hour]
            if future:
                next_premium = f"{future[0]:02d}h (hoje)"

        return {
            "day": dias_pt[dow],
            "hour": hour,
            "is_premium": is_prem,
            "strength": strength,
            "premium_only_mode": self.premium_only,
            "should_operate": self.should_operate(),
            "today_premium_hours": today_hours,
            "next_premium": next_premium,
        }

    def get_hours_for_today(self) -> list:
        """Lista de horários premium para hoje."""
        dow = self._now_brasilia().weekday()
        return PREMIUM_SCHEDULE.get(dow, [])

    def toggle_premium_mode(self) -> bool:
        """Alterna entre modo premium e 24/7. Retorna novo estado."""
        self.premium_only = not self.premium_only
        mode = "PREMIUM" if self.premium_only else "24/7"
        logger.info(f"Modo de horário alterado para: {mode}")
        return self.premium_only
