"""
StrategyAdvisor - Cerebro adaptativo por plataforma.

Usa o SafetyIndex para decidir em tempo real:
- Qual setup usar (swap via StrategyEngine.request_swap)
- Quanto compound aplicar (ajusta BankrollManager.compound_pct)
- Se deve pausar apostas (safety < 0.3)

Modelo default: Half-Kelly 2 bets com trailing banca.
SafetyIndex protege no drawdown mudando para trigger mais alto ou pausa.

Fluxo:
    A cada N rounds (default 25), o Advisor:
    1. Recalcula SafetyIndex
    2. Determina nivel (defensivo/conservador/normal/agressivo)
    3. Se nivel mudou, executa acao correspondente
    4. Loga a decisao

Mapeamento Brabet (%LOW ~55%, trigger 6):
    AGRESSIVO  (0.8-1.0): Half-Kelly 2B trigger 6, aposta x1.20
    NORMAL     (0.5-0.8): Half-Kelly 2B trigger 6, aposta x1.00
    CONSERVADOR(0.3-0.5): Half-Kelly 1B trigger 6, aposta x0.70
    DEFENSIVO  (0.0-0.3): PAUSA (nao aposta)

Mapeamento Onebra/PGWin/Winbra (%LOW ~50-53%, trigger 7):
    AGRESSIVO  (0.8-1.0): Half-Kelly 2B trigger 7, aposta x1.20
    NORMAL     (0.5-0.8): Half-Kelly 2B trigger 7, aposta x1.00
    CONSERVADOR(0.3-0.5): Half-Kelly 1B trigger 7, aposta x0.70
    DEFENSIVO  (0.0-0.3): PAUSA (nao aposta)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from src.bot.safety_index import SafetyIndex, SafetySnapshot

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# STRATEGY MAP — Mapeamento nivel → configuracao
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class LevelConfig:
    """Configuracao para um nivel de seguranca."""
    setup_name: str
    compound_pct: float
    trigger: int
    bet_multiplier: float = 1.0
    pause_bets: bool = False
    description: str = ""


# -- Strategy Map: setup padrao para todos os niveis --
STRATEGY_MAP: Dict[str, LevelConfig] = {
    "agressivo": LevelConfig(
        setup_name="moderado",
        compound_pct=0.0,
        trigger=6,
        bet_multiplier=1.20,
        description="Fase segura: aposta +20%",
    ),
    "normal": LevelConfig(
        setup_name="moderado",
        compound_pct=0.0,
        trigger=6,
        bet_multiplier=1.00,
        description="Fase normal: aposta padrao",
    ),
    "conservador": LevelConfig(
        setup_name="moderado",
        compound_pct=0.0,
        trigger=6,
        bet_multiplier=0.70,
        description="Fase arriscada: aposta -30%",
    ),
    "defensivo": LevelConfig(
        setup_name="moderado",
        compound_pct=0.0,
        trigger=6,
        bet_multiplier=1.00,
        pause_bets=True,
        description="Fase perigosa: PAUSA",
    ),
}

DEFAULT_STRATEGY_MAP = STRATEGY_MAP


def get_strategy_map(
    platform_name: str,
) -> Dict[str, LevelConfig]:
    """Retorna o strategy map (unico para todas)."""
    return dict(STRATEGY_MAP)


class StrategyAdvisor:
    """Cerebro adaptativo que gerencia uma PlatformSession.

    Integra-se com PlatformSession via:
    - session.strategy.request_swap(new_setup)
    - session.bankroll.compound_pct = valor
    - session.paused = True/False

    Args:
        platform_name: Nome da plataforma (para logging).
        strategy_map: Mapeamento nivel->config.
        eval_interval: Rounds entre cada reavaliacao.
        enabled: Se False, advisor nao faz nenhuma acao (modo observacao).
    """

    def __init__(
        self,
        platform_name: str = "brabet",
        strategy_map: Optional[Dict[str, LevelConfig]] = None,
        eval_interval: int = 25,
        enabled: bool = True,
    ):
        self.platform_name = platform_name
        self.strategy_map = strategy_map or dict(DEFAULT_STRATEGY_MAP)
        self.eval_interval = eval_interval
        self.enabled = enabled

        # SafetyIndex interno
        self.safety = SafetyIndex()

        # Estado
        self._current_level: str = "normal"
        self._current_bet_multiplier: float = 1.0
        self._rounds_since_eval: int = 0
        self._total_evals: int = 0
        self._total_swaps: int = 0
        self._last_action: str = ""

        # Historico de decisoes (ultimas 20)
        self._decision_log: list = []

        self.logger = logging.getLogger(f"advisor.{platform_name}")

    def initialize(self, balance: float, banca: float):
        """Inicializa o advisor com saldo e banca da sessao."""
        self.safety.initialize(balance, banca)
        self.logger.info(
            f"Advisor [{self.platform_name}] init: "
            f"saldo={balance:.2f}, "
            f"banca={banca:.2f}, "
            f"enabled={self.enabled}, "
            f"interval={self.eval_interval}r"
        )

    def feed_round(self, explosion: float, threshold: float = 2.0):
        """Alimenta com resultado de um round.

        Returns:
            True se uma reavaliacao foi feita neste round.
        """
        self.safety.feed_round(explosion, threshold)
        self._rounds_since_eval += 1
        return False  # A avaliacao real e feita pelo evaluate()

    def feed_bet_result(self, is_hit: bool):
        """Alimenta com resultado de aposta."""
        self.safety.feed_bet_result(is_hit)

    def update_balance(self, balance: float):
        """Atualiza saldo para calculo de drawdown/profit."""
        self.safety.update_balance(balance)

    def should_evaluate(self) -> bool:
        """Verifica se esta na hora de reavaliar."""
        return self._rounds_since_eval >= self.eval_interval

    def evaluate(self, session) -> Optional[str]:
        """Reavalia e executa acao se necessario.

        Esta e a funcao principal. Chamada a cada eval_interval rounds
        pelo PlatformSession._on_round_end().

        Args:
            session: PlatformSession instance (para executar acoes).

        Returns:
            Mensagem descrevendo a acao tomada, ou None.
        """
        if not self.enabled:
            return None

        self._rounds_since_eval = 0
        self._total_evals += 1

        # Recalcular SafetyIndex
        snap = self.safety.calculate()
        new_level = snap.level

        # Se nivel nao mudou, nada a fazer
        if new_level == self._current_level:
            return None

        # Nivel mudou! Executar transicao
        old_level = self._current_level
        self._current_level = new_level

        action = self._execute_transition(session, old_level, new_level, snap)
        return action

    def _execute_transition(
        self, session, old_level: str, new_level: str, snap: SafetySnapshot
    ) -> str:
        """Executa a transicao de nivel.

        Args:
            session: PlatformSession para aplicar mudancas.
            old_level: Nivel anterior.
            new_level: Novo nivel.
            snap: Snapshot de seguranca com os dados.

        Returns:
            Mensagem descrevendo a acao.
        """
        config = self.strategy_map.get(new_level)
        if not config:
            return f"Nivel '{new_level}' sem config"

        actions = []

        # 1. Trocar setup (via hot-swap seguro)
        try:
            new_setup = self._get_setup(config.setup_name)
            if new_setup:
                # Ajustar trigger antes do swap
                new_setup.trigger_base = config.trigger
                session.strategy.request_swap(new_setup)
                session.active_setup = new_setup
                actions.append(f"setup→{config.setup_name}")
                self._total_swaps += 1
        except Exception as e:
            self.logger.error(f"Erro ao trocar setup: {e}")

        # 2. Ajustar compound
        try:
            session.bankroll.compound_pct = config.compound_pct
            actions.append(f"compound→{config.compound_pct:.0%}")
        except Exception as e:
            self.logger.debug(f"Erro ao ajustar compound: {e}")

        # 3. Ajustar multiplicador de aposta
        self._current_bet_multiplier = config.bet_multiplier
        try:
            session.strategy.bet_multiplier = config.bet_multiplier
            if config.bet_multiplier != 1.0:
                actions.append(f"aposta x{config.bet_multiplier:.2f}")
        except Exception as e:
            self.logger.debug(f"Erro ao ajustar bet_multiplier: {e}")

        # 4. Pausar/retomar se necessario
        if config.pause_bets and not session.paused:
            session.paused = True
            actions.append("PAUSADO")
        elif not config.pause_bets and session.paused:
            # So retomar se foi o advisor que pausou (nao pausa manual)
            session.paused = False
            actions.append("RETOMADO")

        # Montar mensagem
        msg = (
            f"[Advisor {self.platform_name}] "
            f"{old_level.upper()} → {new_level.upper()} "
            f"(safety={snap.index:.2f}) | "
            + ", ".join(actions)
        )

        self._last_action = msg
        self._log_decision(old_level, new_level, snap, actions)
        self.logger.info(msg)

        return msg

    def _get_setup(self, setup_name: str):
        """Obtem instancia do setup."""
        from src.bot.setups import get_setup
        return get_setup(setup_name)

    def _log_decision(
        self, old_level: str, new_level: str,
        snap: SafetySnapshot, actions: list,
    ):
        """Registra decisao no historico."""
        entry = {
            "eval_num": self._total_evals,
            "round": snap.total_rounds,
            "old_level": old_level,
            "new_level": new_level,
            "safety_index": snap.index,
            "pct_low": snap.pct_low,
            "drawdown": snap.drawdown_pct,
            "win_rate": snap.win_rate,
            "profit_pct": snap.session_profit_pct,
            "actions": actions,
        }
        self._decision_log.append(entry)
        # Manter apenas ultimas 50
        if len(self._decision_log) > 50:
            self._decision_log = self._decision_log[-50:]

    # ── Estado para GUI ─────────────────────────────────────────────

    def get_state(self) -> Dict:
        """Retorna estado do advisor para a GUI."""
        snap = self.safety.snapshot
        config = self.strategy_map.get(self._current_level)

        return {
            "enabled": self.enabled,
            "safety_index": snap.index,
            "safety_level": snap.level,
            "safety_color": snap.color,
            "current_setup": config.setup_name if config else "N/A",
            "current_compound": config.compound_pct if config else 0,
            "bet_multiplier": self._current_bet_multiplier,
            "pause_bets": config.pause_bets if config else False,
            "total_evals": self._total_evals,
            "total_swaps": self._total_swaps,
            "last_action": self._last_action,
            # Componentes do safety index
            "distribution_score": snap.distribution_score,
            "drawdown_score": snap.drawdown_score,
            "win_rate_score": snap.win_rate_score,
            "profit_score": snap.profit_score,
            "bankroll_score": snap.bankroll_score,
            "pct_low": snap.pct_low,
            "drawdown_pct": snap.drawdown_pct,
            "win_rate": snap.win_rate,
            "session_profit_pct": snap.session_profit_pct,
            "total_rounds": snap.total_rounds,
        }

    def get_decision_log(self) -> list:
        """Retorna historico de decisoes."""
        return list(self._decision_log)
