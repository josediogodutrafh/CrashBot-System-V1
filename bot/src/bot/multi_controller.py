"""
MultiPlatformController - Cérebro que gerencia 4 plataformas simultâneas.

Orquestra múltiplas PlatformSessions, cada uma com captura WS,
strategy e bankroll independentes. O cérebro coordena:
- Lançamento sequencial de Chromes (evita conflitos de porta)
- Start/stop individual ou coletivo
- Agregação de estatísticas
- Estado para a GUI multi-plataforma

Uso:
    from src.bot.multi_controller import MultiPlatformController
    from src.bot.platform_session import PlatformConfig

    configs = [
        PlatformConfig("brabet", port=9222, ...),
        PlatformConfig("onebra", port=9223, ...),
    ]
    brain = MultiPlatformController(configs)
    brain.start_all()
"""

import ctypes
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from src.bot.platform_session import PlatformConfig, PlatformSession

logger = logging.getLogger(__name__)


class MultiPlatformController:
    """Cérebro multi-plataforma — gerencia N sessões simultâneas."""

    def __init__(self, platform_configs: List[PlatformConfig]):
        self.sessions: Dict[str, PlatformSession] = {}
        self._configs = {c.platform_name: c for c in platform_configs}

        for cfg in platform_configs:
            if cfg.enabled:
                self.sessions[cfg.platform_name] = PlatformSession(cfg)

        self.running = False
        self._stop_requested = False
        self.last_action = ""

        # Relatório semanal
        self._weekly_report_pending = False

        # Callback para notificar GUI de mudanças
        self._on_state_change: Optional[Callable] = None

        logger.info(
            f"MultiPlatformController: {len(self.sessions)} plataformas "
            f"({', '.join(self.sessions.keys())})"
        )

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start_all(self):
        """Inicia todas as plataformas habilitadas.

        Chromes são lançados sequencialmente (1s delay entre cada)
        para evitar conflitos de porta. Cada sessão roda em thread própria.
        """
        self.running = True
        self._stop_requested = False
        self.last_action = "Iniciando plataformas..."
        logger.info("=== INICIANDO TODAS AS PLATAFORMAS ===")

        # Verificar relatório semanal (segunda-feira)
        try:
            from src.analysis.scheduler import check_weekly_report
            first_session = next(iter(self.sessions.values()), None)
            if first_session:
                result = check_weekly_report(first_session.db_manager)
                if result.get("generated"):
                    self.last_action = "Relatório semanal gerado!"
                    self._weekly_report_pending = True
        except Exception as e:
            logger.debug(f"Scheduler check: {e}")

        for i, (name, session) in enumerate(self.sessions.items()):
            if self._stop_requested:
                break
            self.last_action = f"Lançando {name} ({i+1}/{len(self.sessions)})..."
            logger.info(f"Lançando sessão: {name} (porta {session.config.port})")
            session.start_async()
            # Delay entre lançamentos para evitar conflitos
            if i < len(self.sessions) - 1:
                time.sleep(2)

        self.last_action = f"{len(self.sessions)} plataformas ativas"
        logger.info(f"Todas as {len(self.sessions)} plataformas lançadas")

        # Posicionar janelas Chrome em grid após todas lançadas
        threading.Thread(
            target=self._position_windows_when_ready,
            daemon=True,
            name="window-positioner",
        ).start()

    # ── Window Positioning ───────────────────────────────────────────

    # Ordem fixa das plataformas (esquerda → direita)
    PLATFORM_ORDER = ["brabet", "onebra", "7bra", "k813bet"]

    def _position_windows_when_ready(self):
        """Aguarda HWNDs de todos os Chromes e posiciona em grid.

        Roda em thread separada. Espera até 90s para HWNDs aparecerem.
        O HWND é capturado logo após o Chrome abrir (fase 1), antes do
        game tab e WS — então fica disponível rapidamente.
        """
        if os.name != "nt":
            return

        logger.info("Aguardando HWNDs para posicionar janelas...")
        total = len(self.sessions)
        deadline = time.time() + 90

        while time.time() < deadline:
            if self._stop_requested:
                return
            hwnds = self._collect_hwnds_ordered()
            if len(hwnds) >= total:
                break
            found = len(hwnds)
            self.last_action = f"Posicionando janelas... ({found}/{total})"
            time.sleep(2)

        hwnds = self._collect_hwnds_ordered()
        if not hwnds:
            logger.warning("Nenhum HWND encontrado — posicionamento cancelado")
            return

        self._position_windows_grid(hwnds)

    def _collect_hwnds_ordered(self) -> List[tuple]:
        """Coleta HWNDs na ordem fixa: brabet → onebra → 7bra → k813bet.

        Returns:
            Lista de (name, hwnd) na ordem PLATFORM_ORDER.
        """
        result = []
        # Primeiro as plataformas na ordem definida
        for name in self.PLATFORM_ORDER:
            session = self.sessions.get(name)
            if session and session._chrome_hwnd:
                result.append((name, session._chrome_hwnd))
        # Depois qualquer outra plataforma não listada na ordem
        for name, session in self.sessions.items():
            if name not in self.PLATFORM_ORDER and session._chrome_hwnd:
                result.append((name, session._chrome_hwnd))
        return result

    def _position_windows_grid(self, hwnds: List[tuple]):
        """Posiciona janelas Chrome em grid usando Win32 API.

        Args:
            hwnds: Lista de (name, hwnd) já na ordem desejada (esq→dir).
        """
        try:
            user32 = ctypes.windll.user32

            # Área útil da tela (exclui taskbar)
            from ctypes import wintypes
            work_area = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_area), 0)

            screen_x = work_area.left
            screen_y = work_area.top
            screen_w = work_area.right - work_area.left
            screen_h = work_area.bottom - work_area.top

            count = len(hwnds)
            if count <= 4:
                cols = count
                rows = 1
            else:
                import math
                cols = math.ceil(math.sqrt(count))
                rows = math.ceil(count / cols)

            col_w = screen_w // cols
            row_h = screen_h // rows

            logger.info(
                f"Posicionando {count} janelas em {cols}x{rows} "
                f"({col_w}x{row_h} cada) na tela {screen_w}x{screen_h}"
            )

            SW_RESTORE = 9
            for i, (name, hwnd) in enumerate(hwnds):
                col = i % cols
                row = i // cols
                x = screen_x + col * col_w
                y = screen_y + row * row_h

                # Restaurar se minimizado/maximizado
                user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.15)
                # Mover e redimensionar
                user32.MoveWindow(hwnd, x, y, col_w, row_h, True)
                logger.info(
                    f"  [{name}] col={col+1} pos=({x},{y}) "
                    f"size={col_w}x{row_h}"
                )

            self.last_action = (
                f"{count} janelas posicionadas: "
                + " | ".join(n for n, _ in hwnds)
            )
            logger.info(f"Janelas posicionadas: {[n for n, _ in hwnds]}")

        except Exception as e:
            logger.error(f"Erro ao posicionar janelas: {e}")

    def stop_all(self):
        """Para todas as plataformas."""
        self._stop_requested = True
        self.running = False
        self.last_action = "Encerrando todas as plataformas..."
        logger.info("=== ENCERRANDO TODAS AS PLATAFORMAS ===")

        for name, session in self.sessions.items():
            try:
                session.stop()
                logger.info(f"Sessão {name} encerrada")
            except Exception as e:
                logger.error(f"Erro ao encerrar {name}: {e}")

        self.last_action = "Todas as plataformas encerradas"

    def start_platform(self, name: str):
        """Inicia uma plataforma específica."""
        session = self.sessions.get(name)
        if not session:
            logger.warning(f"Plataforma '{name}' não encontrada")
            return
        if session.running:
            logger.warning(f"Plataforma '{name}' já está rodando")
            return
        logger.info(f"Iniciando plataforma: {name}")
        session.start_async()

    def stop_platform(self, name: str):
        """Para uma plataforma específica."""
        session = self.sessions.get(name)
        if not session:
            return
        session.stop()
        logger.info(f"Plataforma {name} parada")

    def pause_platform(self, name: str):
        """Pausa/retoma uma plataforma."""
        session = self.sessions.get(name)
        if session:
            session.pause()

    # ── State ─────────────────────────────────────────────────────────

    def get_platform_state(self, name: str) -> Dict[str, Any]:
        """Retorna estado de uma plataforma específica."""
        session = self.sessions.get(name)
        if not session:
            return {"platform": name, "status": "not_found"}
        return session.get_state()

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estado de todas as plataformas."""
        return {name: s.get_state() for name, s in self.sessions.items()}

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas agregadas de todas as plataformas."""
        total_profit = 0.0
        total_hits = 0
        total_misses = 0
        total_rounds = 0
        total_saldo = 0.0
        platforms_running = 0
        platforms_status = {}

        for name, session in self.sessions.items():
            state = session.get_state()
            total_profit += state.get("session_profit", 0.0)
            total_hits += state.get("session_hits", 0)
            total_misses += state.get("session_misses", 0)
            total_rounds += state.get("round_count", 0)
            total_saldo += state.get("saldo", 0.0)
            if state.get("running"):
                platforms_running += 1
            platforms_status[name] = state.get("status", "unknown")

        total_bets = total_hits + total_misses
        hit_rate = (total_hits / total_bets * 100) if total_bets > 0 else 0.0

        return {
            "total_profit": total_profit,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_rounds": total_rounds,
            "total_saldo": total_saldo,
            "hit_rate": hit_rate,
            "platforms_running": platforms_running,
            "platforms_total": len(self.sessions),
            "platforms_status": platforms_status,
        }

    @property
    def platform_names(self) -> List[str]:
        return list(self.sessions.keys())

    def is_any_running(self) -> bool:
        return any(s.running for s in self.sessions.values())
