#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - MAIN ENTRY POINT

Ponto de entrada principal da aplicação.

Uso:
    python main.py              # Inicia com GUI
    python main.py --headless   # Inicia sem GUI (modo servidor)
    python main.py --calibrate  # Abre calibração
    python main.py --version    # Mostra versão
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Adiciona diretório raiz ao path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# ═══════════════════════════════════════════════════════════════════════════════
# VERSÃO E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

__version__ = "3.0.0"
__author__ = "TucunaréBot"
__app_name__ = "TucunareBot"

CONFIG_FILE = "config.json"
LOG_DIR = "logs"
DATA_DIR = "data"
MODELS_DIR = "models"


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP DE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════


def setup_logging(level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Configura sistema de logging.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Se True, também salva em arquivo

    Returns:
        Logger configurado
    """
    # Cria diretório de logs
    if log_to_file:
        Path(LOG_DIR).mkdir(exist_ok=True)

    # Formato
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_to_file:
        log_filename = (
            f"{LOG_DIR}/crashbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        handlers.append(logging.FileHandler(log_filename, encoding="utf-8"))

    # Configura
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # Logger principal
    logger = logging.getLogger("crashbot")
    logger.info(f"Logging configurado: level={level}, file={log_to_file}")

    return logger


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP DE DIRETÓRIOS
# ═══════════════════════════════════════════════════════════════════════════════


def setup_directories() -> None:
    """Cria diretórios necessários."""
    dirs = [LOG_DIR, DATA_DIR, MODELS_DIR, "assets/templates"]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════


def load_config() -> Dict[str, Any]:
    """
    Carrega configuração do arquivo.

    Returns:
        Dicionário de configuração
    """
    default_config = {
        "version": __version__,
        "strategy": {
            "threshold": 2.0,
            "lows_needed": 8,
            "target": 1.85,
            "base_bet_divisor": 15,
            "max_dobra": 4,
        },
        "ml": {
            "use_lstm": True,
            "use_rl": True,
            "weight_rules": 0.4,
            "weight_lstm": 0.3,
            "weight_rl": 0.3,
        },
        "monitors": {},
        "telemetry": {
            "enabled": True,
            "api_url": "",
        },
    }

    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge com defaults
                for key, value in default_config.items():
                    if key not in loaded:
                        loaded[key] = value
                return loaded
        except Exception as e:
            logging.warning(f"Erro ao carregar config: {e}. Usando padrões.")

    return default_config


def save_config(config: Dict[str, Any]) -> bool:
    """
    Salva configuração em arquivo.

    Args:
        config: Dicionário de configuração

    Returns:
        True se salvou com sucesso
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar config: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE DEPENDÊNCIAS
# ═══════════════════════════════════════════════════════════════════════════════


def check_dependencies() -> Dict[str, bool]:
    """
    Verifica dependências instaladas.

    Returns:
        Dicionário com status de cada dependência
    """
    deps = {}

    # Core
    try:
        import numpy

        deps["numpy"] = True
    except ImportError:
        deps["numpy"] = False

    try:
        import cv2

        deps["opencv"] = True
    except ImportError:
        deps["opencv"] = False

    try:
        import pytesseract

        deps["pytesseract"] = True
    except ImportError:
        deps["pytesseract"] = False

    try:
        import pyautogui

        deps["pyautogui"] = True
    except ImportError:
        deps["pyautogui"] = False

    # GUI
    try:
        import dearpygui

        deps["dearpygui"] = True
    except ImportError:
        deps["dearpygui"] = False

    # ML (opcional)
    try:
        import torch

        deps["pytorch"] = True
    except ImportError:
        deps["pytorch"] = False

    try:
        import stable_baselines3

        deps["stable_baselines3"] = True
    except ImportError:
        deps["stable_baselines3"] = False

    try:
        import optuna

        deps["optuna"] = True
    except ImportError:
        deps["optuna"] = False

    return deps


def print_dependencies(deps: Dict[str, bool]) -> None:
    """Imprime status das dependências."""
    print("\n📦 Dependências:")
    print("-" * 40)

    core_deps = ["numpy", "opencv", "pytesseract", "pyautogui", "dearpygui"]
    ml_deps = ["pytorch", "stable_baselines3", "optuna"]

    print("  Core:")
    for dep in core_deps:
        status = "✅" if deps.get(dep, False) else "❌"
        print(f"    {status} {dep}")

    print("  ML (opcional):")
    for dep in ml_deps:
        status = "✅" if deps.get(dep, False) else "⚠️"
        print(f"    {status} {dep}")

    print()


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════


class CrashBotApp:
    """
    Classe principal da aplicação.

    Gerencia:
    - Inicialização de componentes
    - Loop principal
    - Integração GUI <-> Engine
    """

    def __init__(self, config: Dict[str, Any], headless: bool = False):
        """
        Inicializa a aplicação.

        Args:
            config: Configuração carregada
            headless: Se True, roda sem GUI
        """
        self._config = config
        self._headless = headless
        self._running = False
        self._bot_thread: Optional[threading.Thread] = None

        # Componentes (lazy init)
        self._gui = None
        self._detector = None
        self._trigger = None
        self._martingale = None
        self._decision_engine = None
        self._executor = None
        self._collector = None

        # Logger
        self._logger = logging.getLogger("crashbot.app")
        self._logger.info("CrashBotApp inicializado")

    def _init_core(self) -> bool:
        """Inicializa componentes core."""
        try:
            from core.constants import BotConstants
            from core.events import get_event_bus
            from core.state import get_state

            # Inicializa singletons
            get_event_bus()
            get_state()

            self._logger.info("Core inicializado")
            return True

        except Exception as e:
            self._logger.error(f"Erro ao inicializar core: {e}")
            return False

    def _init_engine(self) -> bool:
        """Inicializa componentes do engine."""
        try:
            # Vision
            from engine.vision import get_detector

            self._detector = get_detector()

            # Strategy
            from engine.strategy import get_martingale, get_trigger

            self._trigger = get_trigger()
            self._martingale = get_martingale()

            # Configura trigger
            strategy_config = self._config.get("strategy", {})
            self._trigger.configure(
                threshold=strategy_config.get("threshold", 2.0),
                lows_needed=strategy_config.get("lows_needed", 8),
            )

            # Configura martingale
            self._martingale.configure(
                max_dobra=strategy_config.get("max_dobra", 4),
            )

            # ML / Decision Engine
            from engine.ml import get_collector, get_decision_engine

            ml_config = self._config.get("ml", {})
            self._decision_engine = get_decision_engine(
                use_lstm=ml_config.get("use_lstm", False),
                use_rl=ml_config.get("use_rl", False),
            )
            self._decision_engine.configure_weights(
                rules=ml_config.get("weight_rules", 0.4),
                lstm=ml_config.get("weight_lstm", 0.3),
                rl=ml_config.get("weight_rl", 0.3),
            )

            self._collector = get_collector()

            # Trading
            from engine.trading import get_executor

            self._executor = get_executor()

            self._logger.info("Engine inicializado")
            return True

        except Exception as e:
            self._logger.error(f"Erro ao inicializar engine: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _init_gui(self) -> bool:
        """Inicializa interface gráfica."""
        if self._headless:
            return True

        try:
            from gui import MainWindow

            self._gui = MainWindow()
            self._gui.setup()

            # Configura callbacks
            self._gui.set_callbacks(
                on_start=self._on_gui_start,
                on_stop=self._on_gui_stop,
                on_config_change=self._on_config_change,
            )

            self._logger.info("GUI inicializada")
            return True

        except Exception as e:
            self._logger.error(f"Erro ao inicializar GUI: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _on_gui_start(self) -> None:
        """Callback quando usuário clica em Iniciar."""
        self._logger.info("Iniciando bot...")
        self._start_bot()

    def _on_gui_stop(self) -> None:
        """Callback quando usuário clica em Parar."""
        self._logger.info("Parando bot...")
        self._stop_bot()

    def _on_config_change(self, config: Dict) -> None:
        """Callback quando configuração muda."""
        self._config.update(config)
        save_config(self._config)
        self._logger.info("Configuração atualizada")

    def _start_bot(self) -> None:
        """Inicia o bot em thread separada."""
        if self._running:
            return

        self._running = True
        self._bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self._bot_thread.start()

    def _stop_bot(self) -> None:
        """Para o bot."""
        self._running = False

        if self._bot_thread:
            self._bot_thread.join(timeout=5)
            self._bot_thread = None

    def _bot_loop(self) -> None:
        """Loop principal do bot."""
        from core.events import BotEvent, emit

        self._logger.info("Bot loop iniciado")

        explosions_history = []

        while self._running:
            try:
                # 1. Detecta explosão
                if self._detector:
                    detection = self._detector.detect_all()

                    if detection and detection.get("explosion"):
                        explosion_value = detection["explosion"]

                        # Evita duplicatas
                        if (
                            not explosions_history
                            or explosions_history[-1] != explosion_value
                        ):
                            explosions_history.append(explosion_value)

                            # Emite evento
                            emit(
                                BotEvent.EXPLOSION_DETECTED, {"value": explosion_value}
                            )

                            # Adiciona ao collector
                            if self._collector:
                                self._collector.add_explosion(explosion_value)

                            # Atualiza trigger
                            if self._trigger:
                                trigger_result = self._trigger.add_explosion(
                                    explosion_value
                                )

                                status = self._trigger.get_status()
                                emit(
                                    BotEvent.TRIGGER_PROGRESS,
                                    {
                                        "current": status.current_count,
                                        "needed": status.needed,
                                    },
                                )

                            # 2. Obtém decisão
                            if self._decision_engine:
                                decision = self._decision_engine.get_decision(
                                    explosions=explosions_history[-20:],
                                )

                                # 3. Executa se necessário
                                if decision.should_bet and self._executor:
                                    bet_info = decision.bet_info

                                    if bet_info:
                                        result = self._executor.place_bet(
                                            amount=bet_info.amount,
                                            target=decision.suggested_target,
                                        )

                                        if result.success:
                                            emit(
                                                BotEvent.BET_PLACED,
                                                {
                                                    "amount": bet_info.amount,
                                                    "target": decision.suggested_target,
                                                },
                                            )

                # Pequena pausa
                time.sleep(0.5)

            except Exception as e:
                self._logger.error(f"Erro no bot loop: {e}")
                time.sleep(1)

        self._logger.info("Bot loop encerrado")

    def run(self) -> int:
        """
        Executa a aplicação.

        Returns:
            Código de saída (0 = sucesso)
        """
        self._logger.info(f"Iniciando {__app_name__} v{__version__}")

        # Inicializa componentes
        if not self._init_core():
            return 1

        if not self._init_engine():
            self._logger.warning("Engine não inicializado completamente")

        if not self._init_gui():
            if not self._headless:
                return 1

        # Executa
        try:
            if self._headless:
                self._logger.info("Modo headless - Ctrl+C para sair")
                self._start_bot()

                while self._running:
                    time.sleep(1)
            else:
                self._gui.run()

        except KeyboardInterrupt:
            self._logger.info("Interrompido pelo usuário")

        finally:
            self._stop_bot()
            self._logger.info("Aplicação encerrada")

        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    """Parse argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description=f"{__app_name__} v{__version__} - Bot de Trading Automatizado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"{__app_name__} v{__version__}",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa sem interface gráfica",
    )

    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Abre ferramenta de calibração",
    )

    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Verifica dependências instaladas",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nível de log (default: INFO)",
    )

    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Não salva logs em arquivo",
    )

    return parser.parse_args()


def print_banner() -> None:
    """Imprime banner de início."""
    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚀 CRASHBOT v{__version__}                                        ║
║   Bot de Trading Automatizado com IA                          ║
║                                                               ║
║   © 2024 {__author__}                                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    """
    Função principal.

    Returns:
        Código de saída
    """
    # Parse argumentos
    args = parse_args()

    # Banner
    print_banner()

    # Setup logging
    logger = setup_logging(
        level=args.log_level,
        log_to_file=not args.no_log_file,
    )

    # Setup diretórios
    setup_directories()

    # Verifica dependências
    deps = check_dependencies()

    if args.check_deps:
        print_dependencies(deps)
        return 0

    # Verifica dependências críticas
    critical = ["numpy", "opencv", "pyautogui"]
    missing = [d for d in critical if not deps.get(d, False)]

    if missing:
        print(f"\n❌ Dependências críticas faltando: {', '.join(missing)}")
        print("   Execute: pip install -r requirements.txt")
        return 1

    if not args.headless and not deps.get("dearpygui", False):
        print("\n❌ DearPyGui não instalado (necessário para GUI)")
        print("   Execute: pip install dearpygui")
        print("   Ou use: python main.py --headless")
        return 1

    # Carrega configuração
    config = load_config()

    # Modo calibração
    if args.calibrate:
        print("\n🔧 Modo calibração ainda não implementado")
        print("   Use a interface gráfica para calibrar")
        return 0

    # Cria e executa aplicação
    app = CrashBotApp(config=config, headless=args.headless)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
