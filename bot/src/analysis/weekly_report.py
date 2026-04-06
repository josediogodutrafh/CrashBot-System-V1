"""
Relatório Semanal - Análise automática por plataforma.

Gera relatório comparativo toda segunda-feira com:
- Rounds, hit rate, lucro por plataforma
- %LOW por plataforma (drift detection)
- Recomendações baseadas em desvios estatísticos

Uso:
    from src.analysis.weekly_report import WeeklyReport
    report = WeeklyReport(db_manager)
    data = report.generate()
    report.save()  # Salva em data/reports/weekly_YYYY-MM-DD.json
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Referência histórica: %LOW da Brabet (~54-56% abaixo de 2.0x)
EXPECTED_PCT_LOW = 55.0
DRIFT_THRESHOLD = 3.0  # Alerta se %LOW desviar mais de 3% da referência


class WeeklyReport:
    """Gera relatório semanal de análise por plataforma."""

    def __init__(self, db_manager):
        self.db = db_manager
        self._report: Optional[Dict] = None
        self._reports_dir = Path("data/reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self) -> Dict:
        """Gera relatório da semana atual (segunda a domingo)."""
        summary = self.db.get_weekly_summary()

        platforms = summary.get("platforms", {})
        recommendations = self._generate_recommendations(platforms)
        drift_alerts = self._check_distribution_drift(platforms)

        # Aggregate
        total_rounds = sum(p.get("total_rounds", 0) for p in platforms.values())
        total_bets = sum(p.get("total_bets", 0) for p in platforms.values())
        total_profit = sum(p.get("profit", 0.0) for p in platforms.values())
        total_hits = sum(p.get("hits", 0) for p in platforms.values())
        agg_hit_rate = (total_hits / total_bets * 100) if total_bets > 0 else 0.0

        self._report = {
            "generated_at": datetime.now().isoformat(),
            "week_start": summary.get("week_start", ""),
            "week_end": summary.get("week_end", ""),
            "per_platform": platforms,
            "aggregate": {
                "total_rounds": total_rounds,
                "total_bets": total_bets,
                "total_hits": total_hits,
                "hit_rate": round(agg_hit_rate, 1),
                "total_profit": round(total_profit, 2),
            },
            "drift_alerts": drift_alerts,
            "recommendations": recommendations,
        }

        logger.info(
            f"Relatório semanal gerado: {total_rounds} rounds, "
            f"{total_bets} apostas, R${total_profit:+.2f}"
        )
        return self._report

    def _check_distribution_drift(self, platforms: Dict) -> List[Dict]:
        """Verifica se %LOW de alguma plataforma desviou significativamente."""
        alerts = []
        for name, stats in platforms.items():
            pct_low = stats.get("pct_low", 0.0)
            total = stats.get("total_rounds", 0)

            if total < 100:
                continue  # Dados insuficientes

            deviation = pct_low - EXPECTED_PCT_LOW

            if abs(deviation) > DRIFT_THRESHOLD:
                direction = "acima" if deviation > 0 else "abaixo"
                alerts.append({
                    "platform": name,
                    "pct_low": pct_low,
                    "expected": EXPECTED_PCT_LOW,
                    "deviation": round(deviation, 1),
                    "severity": "high" if abs(deviation) > 5 else "medium",
                    "message": (
                        f"{name}: %LOW em {pct_low:.1f}% "
                        f"({direction} da referência {EXPECTED_PCT_LOW}%)"
                    ),
                })

        return alerts

    def _generate_recommendations(self, platforms: Dict) -> List[str]:
        """Gera recomendações baseadas nos dados da semana."""
        recs = []

        for name, stats in platforms.items():
            pct_low = stats.get("pct_low", 0.0)
            total_rounds = stats.get("total_rounds", 0)
            hit_rate = stats.get("hit_rate", 0.0)
            profit = stats.get("profit", 0.0)

            if total_rounds < 50:
                recs.append(
                    f"{name}: Poucos rounds ({total_rounds}) — dados insuficientes"
                )
                continue

            # Trigger adjustment
            if pct_low > 58:
                recs.append(
                    f"{name}: %LOW alto ({pct_low:.1f}%) — considere trigger=5"
                )
            elif pct_low < 50:
                recs.append(
                    f"{name}: %LOW baixo ({pct_low:.1f}%) — considere trigger=8"
                )

            # Performance
            if profit < 0:
                recs.append(
                    f"{name}: Prejuízo R${profit:.2f} — revisar setup/banca"
                )
            elif hit_rate > 70:
                recs.append(
                    f"{name}: Hit rate alto ({hit_rate:.0f}%) — período favorável"
                )

        if not recs:
            recs.append("Todas as plataformas dentro dos parâmetros esperados")

        return recs

    def save(self) -> str:
        """Salva relatório em data/reports/weekly_YYYY-MM-DD.json."""
        if not self._report:
            self.generate()

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self._reports_dir / f"weekly_{date_str}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._report, f, indent=2, ensure_ascii=False)

        logger.info(f"Relatório salvo: {filepath}")
        return str(filepath)

    def has_report_for_today(self) -> bool:
        """Verifica se já existe relatório para hoje."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self._reports_dir / f"weekly_{date_str}.json"
        return filepath.exists()

    def get_latest_report(self) -> Optional[Dict]:
        """Carrega o relatório mais recente."""
        try:
            reports = sorted(self._reports_dir.glob("weekly_*.json"), reverse=True)
            if reports:
                with open(reports[0], "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar relatório: {e}")
        return None

    def format_summary(self) -> str:
        """Formata relatório para exibição em texto."""
        if not self._report:
            return "Relatório não disponível"

        lines = ["=" * 50]
        lines.append("RELATÓRIO SEMANAL CRASH LAB")
        lines.append(f"Período: {self._report['week_start'][:10]} a {self._report['week_end'][:10]}")
        lines.append("=" * 50)

        agg = self._report["aggregate"]
        lines.append(f"\nAGREGADO:")
        lines.append(f"  Rounds: {agg['total_rounds']}")
        lines.append(f"  Apostas: {agg['total_bets']}")
        lines.append(f"  Hit rate: {agg['hit_rate']:.1f}%")
        lines.append(f"  Lucro: R${agg['total_profit']:+.2f}")

        lines.append(f"\nPOR PLATAFORMA:")
        for name, stats in self._report["per_platform"].items():
            rounds = stats.get("total_rounds", 0)
            pct_low = stats.get("pct_low", 0.0)
            profit = stats.get("profit", 0.0)
            lines.append(
                f"  {name}: {rounds} rounds | "
                f"%LOW={pct_low:.1f}% | R${profit:+.2f}"
            )

        alerts = self._report.get("drift_alerts", [])
        if alerts:
            lines.append(f"\nALERTAS:")
            for alert in alerts:
                lines.append(f"  ⚠ {alert['message']}")

        recs = self._report.get("recommendations", [])
        if recs:
            lines.append(f"\nRECOMENDAÇÕES:")
            for rec in recs:
                lines.append(f"  → {rec}")

        lines.append("=" * 50)
        return "\n".join(lines)
