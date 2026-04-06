"""
Scheduler - Verifica se é hora de gerar relatório semanal.

Integração com MultiPlatformController:
    Na inicialização, chamar check_weekly_report(db_manager).
    Se for segunda-feira e não houver relatório do dia, gera automaticamente.
"""

import logging
from datetime import datetime

from src.analysis.weekly_report import WeeklyReport

logger = logging.getLogger(__name__)


def check_weekly_report(db_manager) -> dict:
    """Verifica e gera relatório semanal se necessário.

    Deve ser chamado no start do MultiPlatformController.
    Retorna dict com status e caminho do relatório.

    Returns:
        {"generated": bool, "path": str, "is_monday": bool}
    """
    today = datetime.now()
    is_monday = today.weekday() == 0  # 0 = segunda-feira

    report = WeeklyReport(db_manager)

    if is_monday and not report.has_report_for_today():
        logger.info("Segunda-feira — gerando relatório semanal...")
        data = report.generate()
        path = report.save()

        # Log resumo no console
        summary = report.format_summary()
        logger.info(f"\n{summary}")

        return {"generated": True, "path": path, "is_monday": True}

    if is_monday:
        logger.info("Relatório semanal já existe para hoje")
        return {"generated": False, "path": "", "is_monday": True}

    return {"generated": False, "path": "", "is_monday": False}
