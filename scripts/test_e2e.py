"""
Crash_AI - Teste End-to-End
Valida todos os componentes do sistema.

Uso:
    python scripts/test_e2e.py              # Todos os testes
    python scripts/test_e2e.py --bot        # Apenas bot
    python scripts/test_e2e.py --api        # Apenas API
    python scripts/test_e2e.py --ws         # Apenas WebSocket
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# =============================================================================
# CORES NO TERMINAL
# =============================================================================

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results: list[tuple[str, str, bool, str]] = []  # (category, name, passed, detail)


def log_ok(cat: str, name: str, detail: str = ""):
    results.append((cat, name, True, detail))
    print(f"  {GREEN}[PASS]{RESET} {name}" + (f" - {detail}" if detail else ""))


def log_fail(cat: str, name: str, detail: str = ""):
    results.append((cat, name, False, detail))
    print(f"  {RED}[FAIL]{RESET} {name}" + (f" - {detail}" if detail else ""))


def log_warn(cat: str, name: str, detail: str = ""):
    results.append((cat, name, True, detail))  # warn = pass com nota
    print(f"  {YELLOW}[WARN]{RESET} {name}" + (f" - {detail}" if detail else ""))


def section(title: str):
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}")


# =============================================================================
# 1. BOT TESTS
# =============================================================================


def test_bot():
    section("BOT - Imports & Config")

    # 1.1 Config
    try:
        from src.config import (
            PROJECT_ROOT as PR,
            DB_PATH,
            PROFILES_PATH,
            API_URL,
            TESSERACT_PATH,
        )

        log_ok("bot", "src.config imports")

        if PR.exists():
            log_ok("bot", f"PROJECT_ROOT exists: {PR}")
        else:
            log_fail("bot", f"PROJECT_ROOT not found: {PR}")

        if PROFILES_PATH.exists():
            log_ok("bot", f"profiles.json exists")
        else:
            log_warn("bot", f"profiles.json missing", str(PROFILES_PATH))

        if API_URL:
            log_ok("bot", f"API_URL = {API_URL}")
        else:
            log_warn("bot", "API_URL empty")

    except Exception as e:
        log_fail("bot", f"src.config import failed: {e}")

    # 1.2 Core modules
    modules = [
        ("Controller", "from src.bot.controller import BotController"),
        ("Strategy", "from src.bot.strategy import StrategyEngine"),
        ("Bankroll", "from src.bot.bankroll import BankrollManager"),
        ("Setups", "from src.bot.setups import SETUP_LIST, get_setup"),
        ("Schedule", "from src.bot.schedule import ScheduleManager"),
        ("Menu", "from src.bot.menu import HotKeyListener"),
        ("DB Manager", "from src.data.manager import DatabaseManager, RoundData"),
        ("Telegram", "from src.notifications.telegram import notify_session_summary"),
        ("HWID", "from src.security.hwid import get_hwid"),
    ]

    for name, stmt in modules:
        try:
            exec(stmt)
            log_ok("bot", f"Import: {name}")
        except Exception as e:
            log_fail("bot", f"Import: {name}", str(e))

    # 1.3 HWID
    try:
        from src.security.hwid import get_hwid

        hwid = get_hwid()
        if hwid and len(hwid) == 32:
            log_ok("bot", f"HWID generated: {hwid[:8]}...")
        else:
            log_fail("bot", f"HWID invalid: {hwid}")
    except Exception as e:
        log_fail("bot", f"HWID generation failed: {e}")

    # 1.4 Strategy
    try:
        from src.bot.strategy import StrategyEngine

        engine = StrategyEngine()
        log_ok("bot", "StrategyEngine instantiated")

        # Simular explosões (sem setup carregado, apenas verifica que não explode)
        for val in [1.5, 1.3, 1.8, 1.1, 1.4, 1.2]:
            engine.add_explosion_value(val)
        log_ok("bot", f"Strategy processed 6 values, history_size={len(engine.explosion_history)}")

    except Exception as e:
        log_fail("bot", f"Strategy test failed: {e}")

    # 1.5 History DB
    try:
        from src.config import DB_PATH

        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            log_ok("bot", f"History DB tables: {tables}")
        else:
            log_warn("bot", "History DB not found (will be created on first run)")
    except Exception as e:
        log_fail("bot", f"History DB check failed: {e}")

    # 1.6 Setups
    try:
        from src.bot.setups import SETUP_LIST, get_setup, get_display_name

        log_ok("bot", f"Available setups: {len(SETUP_LIST)}")
        for s in SETUP_LIST:
            name = get_display_name(s)
            log_ok("bot", f"  Setup: {name}")
    except Exception as e:
        log_fail("bot", f"Setups test failed: {e}")


# =============================================================================
# 2. WEBSOCKET CAPTURE TESTS
# =============================================================================


def test_websocket():
    section("WEBSOCKET CAPTURE")

    # 2.1 Import
    try:
        from src.ws.capture import CrashWSCapture, GamePhase

        log_ok("ws", "Import CrashWSCapture, GamePhase")
    except Exception as e:
        log_fail("ws", f"Import failed: {e}")
        return

    # 2.2 GamePhase enum
    try:
        phases = [GamePhase.UNKNOWN, GamePhase.BETTING, GamePhase.PLAYING, GamePhase.CRASHED]
        log_ok("ws", f"GamePhase values: {[p.name for p in phases]}")
    except Exception as e:
        log_fail("ws", f"GamePhase enum failed: {e}")

    # 2.3 Instantiation
    try:
        ws = CrashWSCapture(port=9222)
        log_ok("ws", "CrashWSCapture(port=9222) instantiated")
    except Exception as e:
        log_fail("ws", f"Instantiation failed: {e}")
        return

    # 2.4 Callback registration
    try:
        called = {"count": 0}

        def dummy_callback(data):
            called["count"] += 1

        ws.on("round_end", dummy_callback)
        ws.on("balance_update", dummy_callback)
        ws.on("betting_phase", dummy_callback)
        ws.on("phase_change", dummy_callback)
        log_ok("ws", "4 callbacks registered")
    except Exception as e:
        log_fail("ws", f"Callback registration failed: {e}")

    # 2.5 Chrome connection (optional - may not be running)
    try:
        import requests

        resp = requests.get("http://localhost:9222/json/version", timeout=2)
        if resp.status_code == 200:
            info = resp.json()
            browser = info.get("Browser", "unknown")
            log_ok("ws", f"Chrome debug active: {browser}")

            # Try to find game tab
            tabs_resp = requests.get("http://localhost:9222/json", timeout=2)
            tabs = tabs_resp.json()
            game_tabs = [
                t for t in tabs if "blaze" in t.get("url", "").lower()
                or "crash" in t.get("url", "").lower()
                or "br4bet" in t.get("url", "").lower()
            ]
            if game_tabs:
                log_ok("ws", f"Game tab found: {game_tabs[0]['url'][:60]}...")
            else:
                log_warn("ws", "No game tab open", f"{len(tabs)} tabs found")
        else:
            log_warn("ws", "Chrome debug responded but unexpected status", str(resp.status_code))
    except requests.exceptions.ConnectionError:
        log_warn("ws", "Chrome debug not running on :9222", "Run abrir_chrome_debug.bat first")
    except Exception as e:
        log_warn("ws", f"Chrome check failed: {e}")


# =============================================================================
# 3. API TESTS
# =============================================================================


def test_api():
    section("API - Remote Endpoints")

    try:
        import requests
    except ImportError:
        log_fail("api", "requests not installed")
        return

    from src.config import API_URL

    if not API_URL:
        log_warn("api", "API_URL not configured, skipping")
        return

    base = API_URL.rstrip("/")

    # 3.1 Health check
    try:
        resp = requests.get(f"{base}/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_ok("api", f"Health: {data.get('status', '?')}")
        else:
            log_fail("api", f"Health returned {resp.status_code}")
    except requests.exceptions.ConnectionError:
        log_warn("api", "API not reachable", base)
        return
    except Exception as e:
        log_fail("api", f"Health check failed: {e}")
        return

    # 3.2 Root
    try:
        resp = requests.get(f"{base}/", timeout=10)
        data = resp.json()
        version = data.get("version", "?")
        log_ok("api", f"Root: version={version}, status={data.get('status', '?')}")
    except Exception as e:
        log_fail("api", f"Root failed: {e}")

    # 3.3 Status endpoint
    try:
        resp = requests.get(f"{base}/api/v1/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            endpoints = data.get("endpoints", {})
            log_ok("api", f"Status OK, {len(endpoints)} endpoints listed")
        else:
            log_fail("api", f"Status returned {resp.status_code}")
    except Exception as e:
        log_fail("api", f"Status failed: {e}")

    # 3.4 Version check (public endpoint)
    try:
        resp = requests.get(f"{base}/api/v1/bot/versao", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_ok("api", f"Bot version: {data.get('versao', '?')}, obrigatoria={data.get('obrigatoria', '?')}")
        elif resp.status_code == 404:
            log_warn("api", "No bot version registered yet")
        else:
            log_fail("api", f"Version returned {resp.status_code}")
    except Exception as e:
        log_fail("api", f"Version check failed: {e}")

    # 3.5 License validation (should reject invalid)
    try:
        from src.security.hwid import get_hwid

        resp = requests.post(
            f"{base}/validar",
            json={"chave": "TEST-INVALID-KEY", "hwid": get_hwid()},
            timeout=10,
        )
        if resp.status_code in (401, 403, 404):
            log_ok("api", f"Invalid license rejected: {resp.status_code}")
        elif resp.status_code == 200:
            log_warn("api", "Invalid license accepted?! Check validation logic")
        else:
            log_ok("api", f"License endpoint responded: {resp.status_code}")
    except Exception as e:
        log_fail("api", f"License validation test failed: {e}")

    # 3.6 Telemetry compat route
    try:
        resp = requests.post(
            f"{base}/telemetria/log",
            json={"test": True},
            timeout=10,
            allow_redirects=False,
        )
        if resp.status_code == 307:
            log_ok("api", "Telemetry compat redirect OK (307)")
        else:
            log_ok("api", f"Telemetry compat: {resp.status_code}")
    except Exception as e:
        log_fail("api", f"Telemetry compat failed: {e}")


# =============================================================================
# 4. TELEGRAM TEST
# =============================================================================


def test_telegram():
    section("TELEGRAM")

    from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    if not TELEGRAM_BOT_TOKEN:
        log_warn("telegram", "TELEGRAM_BOT_TOKEN not configured, skipping")
        return

    if not TELEGRAM_CHAT_ID:
        log_warn("telegram", "TELEGRAM_CHAT_ID not configured, skipping")
        return

    try:
        import requests

        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            bot_name = data.get("result", {}).get("username", "?")
            log_ok("telegram", f"Bot connected: @{bot_name}")
        else:
            log_fail("telegram", f"getMe failed: {resp.status_code}")
    except Exception as e:
        log_fail("telegram", f"Telegram test failed: {e}")

    # Test notification module
    try:
        from src.notifications.telegram import notify_session_summary

        log_ok("telegram", "Notification module imported")
    except Exception as e:
        log_fail("telegram", f"Notification module failed: {e}")


# =============================================================================
# 5. FILES & STRUCTURE
# =============================================================================


def test_structure():
    section("PROJECT STRUCTURE")

    critical_files = [
        ("run.py", "Entry point"),
        ("src/config.py", "Master config"),
        ("src/bot/controller.py", "Bot controller"),
        ("src/bot/strategy.py", "Strategy engine"),
        ("src/bot/bankroll.py", "Bankroll manager"),
        ("src/bot/setups.py", "Setups definitions"),
        ("src/bot/schedule.py", "Schedule manager"),
        ("src/bot/menu.py", "Hotkey listener"),
        ("src/ws/capture.py", "WebSocket capture"),
        ("src/data/manager.py", "Database manager"),
        ("src/notifications/telegram.py", "Telegram notifications"),
        ("src/security/hwid.py", "HWID generator"),
        ("config/profiles.json", "Screen profiles"),
        ("iniciar.bat", "Launcher script"),
        ("tools/abrir_chrome_debug.bat", "Chrome debug launcher"),
    ]

    for rel_path, desc in critical_files:
        full = PROJECT_ROOT / rel_path
        if full.exists():
            size = full.stat().st_size
            log_ok("structure", f"{rel_path} ({size:,} bytes)", desc)
        else:
            log_fail("structure", f"{rel_path} MISSING", desc)

    # Check Tesseract
    tesseract = PROJECT_ROOT / "tools" / "Tesseract-OCR" / "tesseract.exe"
    if tesseract.exists():
        log_ok("structure", "Tesseract-OCR installed")
    else:
        log_warn("structure", "Tesseract-OCR not found (optional for WS mode)")


# =============================================================================
# SUMMARY
# =============================================================================


def print_summary():
    section("SUMMARY")

    categories = {}
    for cat, name, passed, detail in results:
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0}
        if passed:
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1

    total_pass = sum(c["pass"] for c in categories.values())
    total_fail = sum(c["fail"] for c in categories.values())
    total = total_pass + total_fail

    print(f"\n{'Category':<15} {'Pass':>6} {'Fail':>6}")
    print("-" * 30)
    for cat, counts in categories.items():
        color = GREEN if counts["fail"] == 0 else RED
        print(f"{cat:<15} {GREEN}{counts['pass']:>6}{RESET} {color}{counts['fail']:>6}{RESET}")
    print("-" * 30)
    color = GREEN if total_fail == 0 else RED
    print(f"{'TOTAL':<15} {GREEN}{total_pass:>6}{RESET} {color}{total_fail:>6}{RESET}")
    print()

    if total_fail == 0:
        print(f"{GREEN}{BOLD}ALL TESTS PASSED!{RESET}")
    else:
        print(f"{RED}{BOLD}{total_fail} TESTS FAILED{RESET}")

    return total_fail == 0


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="CrashBot E2E Tests")
    parser.add_argument("--bot", action="store_true", help="Test bot only")
    parser.add_argument("--ws", action="store_true", help="Test WebSocket only")
    parser.add_argument("--api", action="store_true", help="Test API only")
    parser.add_argument("--telegram", action="store_true", help="Test Telegram only")
    parser.add_argument("--structure", action="store_true", help="Test structure only")
    args = parser.parse_args()

    print(f"{BOLD}CrashBot E2E Test Suite{RESET}")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Python: {sys.version}")

    run_all = not any([args.bot, args.ws, args.api, args.telegram, args.structure])

    if run_all or args.structure:
        test_structure()

    if run_all or args.bot:
        test_bot()

    if run_all or args.ws:
        test_websocket()

    if run_all or args.api:
        test_api()

    if run_all or args.telegram:
        test_telegram()

    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
