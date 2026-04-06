"""
BettingExecutor - Execução de apostas via pyautogui (extraído do BotController).

Cada plataforma tem uma instância com suas coordenadas de tela.
Um mutex global garante que apenas UMA instância usa pyautogui por vez
(pyautogui não é thread-safe e opera em coordenadas absolutas de tela).

Uso:
    executor = BettingExecutor("brabet", profile_name="BB67%MID")
    executor.execute_bet(71.43, 1.95, chrome_hwnd=0x1234)
"""

import logging
import os
import random
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# DPI awareness (Windows) — sem isso, pyautogui
# clica em coordenadas erradas com scaling > 100%
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

_pyautogui_lock = threading.Lock()


class BettingExecutor:
    """Executa apostas preenchendo campos na tela via pyautogui.

    Cada instância guarda as coordenadas de tela (screen_areas) de UMA
    plataforma. O mutex global _pyautogui_lock garante exclusão mútua
    entre instâncias de plataformas diferentes.
    """

    def __init__(self, platform_name: str, profile_name: str = ""):
        self.platform_name = platform_name
        self.profile_name = profile_name
        self.screen_areas: Dict[str, Dict] = {}
        self._is_windows = os.name == "nt"

        if profile_name:
            self.load_profile(profile_name)

    def load_profile(self, profile_name: str) -> bool:
        """Carrega perfil de calibração de tela.

        Args:
            profile_name: Nome do perfil em profiles.json.

        Returns:
            True se perfil válido carregado.
        """
        try:
            from src.bot.calibration import get_profile, validate_profile
            profile_data = get_profile(profile_name)
            if not profile_data or not validate_profile(profile_data):
                logger.warning(
                    f"[{self.platform_name}] Perfil '{profile_name}' "
                    f"inválido - modo observação"
                )
                return False

            self.screen_areas = {
                "bet_value_1": profile_data.get("bet_value_area_1"),
                "target_1": profile_data.get("target_area_1"),
                "bet_button_1": profile_data.get("bet_button_area_1"),
            }

            if self.can_execute():
                self.profile_name = profile_name
                logger.info(
                    f"[{self.platform_name}] Perfil '{profile_name}' carregado"
                )
                return True

            self.screen_areas = {}
            return False

        except Exception as e:
            logger.error(
                f"[{self.platform_name}] Erro ao carregar perfil: {e}"
            )
            return False

    def calibrate(self) -> bool:
        """Roda wizard de calibracao e salva areas.

        Returns:
            True se calibracao concluida com sucesso.
        """
        from src.bot.calibration import (
            run_calibration_wizard,
        )
        profile_name = f"{self.platform_name}_cal"
        profile = run_calibration_wizard(profile_name)
        if not profile:
            logger.warning(
                f"[{self.platform_name}] "
                f"Calibracao cancelada"
            )
            return False

        self.screen_areas = {
            "bet_value_1": profile.get(
                "bet_value_area_1"
            ),
            "target_1": profile.get(
                "target_area_1"
            ),
            "bet_button_1": profile.get(
                "bet_button_area_1"
            ),
        }
        self.profile_name = profile_name
        logger.info(
            f"[{self.platform_name}] "
            f"Calibracao concluida"
        )
        return self.can_execute()

    def can_execute(self) -> bool:
        """Verifica se tem todas as areas calibradas."""
        required = [
            "bet_value_1", "target_1",
            "bet_button_1",
        ]
        return all(
            self.screen_areas.get(area)
            for area in required
        )

    def execute_bet(self, bet_value: float, target: float,
                    chrome_hwnd: int = 0) -> bool:
        """Executa uma aposta preenchendo os campos na tela.

        Adquire o mutex global antes de interagir com pyautogui.
        Se chrome_hwnd fornecido, traz a janela para frente primeiro.

        Args:
            bet_value: Valor da aposta em R$.
            target: Multiplicador alvo (ex: 1.95).
            chrome_hwnd: Handle da janela Chrome (win32, 0 = skip).

        Returns:
            True se aposta executada com sucesso.
        """
        if not self.can_execute():
            logger.warning(
                f"[{self.platform_name}] Sem calibração - aposta não executada"
            )
            return False

        with _pyautogui_lock:
            try:
                # Trazer janela Chrome para frente (se handle fornecido)
                if chrome_hwnd and self._is_windows:
                    self._focus_window(chrome_hwnd)
                    time.sleep(0.3)

                return self._fill_and_submit(bet_value, target)

            except Exception as e:
                logger.error(
                    f"[{self.platform_name}] Erro ao apostar: {e}"
                )
                return False

    def _fill_and_submit(self, bet_value: float, target: float) -> bool:
        """Preenche campos e clica no botão (dentro do mutex)."""
        import pyautogui
        import pyperclip

        bet_str = f"{max(1.0, bet_value):.2f}"
        target_str = f"{target:.2f}"

        area_value = self.screen_areas.get("bet_value_1")
        area_target = self.screen_areas.get("target_1")
        area_button = self.screen_areas.get("bet_button_1")

        if not all([area_value, area_target, area_button]):
            return False

        self._click_and_fill(pyautogui, pyperclip, area_value, bet_str)
        time.sleep(random.uniform(0.1, 0.2))
        self._click_and_fill(pyautogui, pyperclip, area_target, target_str)
        time.sleep(random.uniform(0.1, 0.2))
        self._click_area(pyautogui, area_button)
        time.sleep(1.0)

        logger.info(
            f"[{self.platform_name}] Aposta: R${bet_str} @ {target_str}x"
        )
        return True

    @staticmethod
    def _human_sleep(mean: float = 0.12, std: float = 0.04):
        """Delay humanizado (gauss em vez de uniforme)."""
        delay = max(0.03, random.gauss(mean, std))
        time.sleep(delay)

    @staticmethod
    def _click_and_fill(pyautogui, pyperclip, area: Dict, value: str):
        """Clica num campo, limpa e cola o valor (humanizado)."""
        # Offset aleatorio + duracao do movimento
        cx = area["x"] + area["width"] // 2 + random.randint(-3, 3)
        cy = area["y"] + area["height"] // 2 + random.randint(-2, 2)
        duration = random.uniform(0.15, 0.30)
        pyautogui.moveTo(cx, cy, duration=duration)
        pyautogui.click()
        BettingExecutor._human_sleep(0.12, 0.04)
        pyautogui.hotkey("ctrl", "a")
        BettingExecutor._human_sleep(0.07, 0.02)
        pyautogui.press("delete")
        BettingExecutor._human_sleep(0.07, 0.02)
        pyperclip.copy(value)
        pyautogui.hotkey("ctrl", "v")

    @staticmethod
    def _click_area(pyautogui, area: Dict):
        """Clica no centro de uma area (com humanizacao)."""
        cx = area["x"] + area["width"] // 2 + random.randint(-3, 3)
        cy = area["y"] + area["height"] // 2 + random.randint(-2, 2)
        duration = random.uniform(0.15, 0.30)
        pyautogui.moveTo(cx, cy, duration=duration)
        pyautogui.click()

    def _focus_window(self, hwnd: int):
        """Traz janela do Chrome para frente (Windows only)."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # SW_RESTORE = 9, para caso esteja minimizado
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        except Exception as e:
            logger.debug(
                f"[{self.platform_name}] Não foi possível focar janela: {e}"
            )

    @staticmethod
    def find_hwnd_by_pid(pid: int) -> int:
        """Encontra o HWND principal de um processo Chrome pelo PID (Windows).

        Enumera todas as janelas visíveis e retorna a maior janela
        que pertence ao PID (geralmente a janela principal do Chrome).

        Returns:
            HWND como int, ou 0 se não encontrado.
        """
        if not pid or os.name != "nt":
            return 0

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            results = []

            # Callback para EnumWindows
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                # Janela visível?
                if not user32.IsWindowVisible(hwnd):
                    return True
                # PID da janela
                proc_id = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
                if proc_id.value != pid:
                    return True
                # Título não vazio (ignora janelas auxiliares)
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    results.append((hwnd, width * height))
                return True

            user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

            if results:
                # Retorna a maior janela (principal do Chrome)
                results.sort(key=lambda x: x[1], reverse=True)
                return results[0][0]
        except Exception as e:
            logger.debug(f"find_hwnd_by_pid({pid}) erro: {e}")

        return 0
