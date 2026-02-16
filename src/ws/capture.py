#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Capture - Captura dados do jogo Crash via Chrome DevTools Protocol.

Conecta ao Chrome com --remote-debugging-port=9222, intercepta o trafego
WebSocket do jogo e emite eventos parseados (crash, apostas, saldo, etc).

Uso:
    from src.ws.capture import CrashWSCapture, GamePhase

    ws = CrashWSCapture(port=9222)
    ws.connect()

    # Event-driven
    ws.on("round_end", lambda data: print(f"Crash: {data['crash']}x"))
    ws.on("balance_update", lambda data: print(f"Saldo: R${data['balance']:.2f}"))
    ws.start()

    # Ou polling
    crash = ws.get_last_crash()
    balance = ws.get_balance()
"""

import base64
import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
import zlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import sys

import requests
import websocket

logger = logging.getLogger(__name__)


# ── Constantes do protocolo ─────────────────────────────────────────────

# Outer commands (protocol layer)
CMD_GAME_PKG = 1071       # GameJsonPkg wrapper
CMD_HALL_END_ROUND = 1089  # Fim do round (crash value)
CMD_HALL_NOTIFY = 1090     # Notificacoes (join/leave)
CMD_TICK = 1100            # Heartbeat
CMD_USER_INFO = 1009       # Atualizacao de saldo

# Inner game commands (dentro de GameJsonPkg.JsonContent)
GAME_CMD_START = 1        # StartGame - multiplicador subindo
GAME_CMD_PRE_DEAL = 7     # PreDeal - 1s antes do start
GAME_CMD_BET = 22         # Bet - aposta de jogador
GAME_CMD_CHANGE_BANKER = 23  # ChangeBanker - inicio fase apostas
GAME_CMD_DUMMY_PLAY = 36  # DummyPlay - cashout durante round

# Keywords para detectar aba do jogo
GAME_TAB_KEYWORDS = [
    "crash", "blaze", "brabet", "game", "casino",
    "double", "mines", "apostas", "bet",
]


class GamePhase(Enum):
    """Fases do jogo crash."""
    UNKNOWN = "unknown"
    BETTING = "betting"       # Fase de apostas (BetLeftSecond > 0)
    PRE_START = "pre_start"   # 1s antes do inicio
    PLAYING = "playing"       # Multiplicador subindo
    CRASHED = "crashed"       # Round acabou, resultado disponivel


@dataclass
class RoundResult:
    """Resultado de um round."""
    round_id: int
    crash_value: float
    duration: int
    timestamp: str
    begin_time: int = 0
    end_time: int = 0


@dataclass
class CaptureStats:
    """Estatisticas da captura."""
    connected: bool = False
    frames_received: int = 0
    rounds_captured: int = 0
    errors: int = 0
    last_frame_time: float = 0.0
    uptime_seconds: float = 0.0


class CrashWSCapture:
    """Captura dados do jogo Crash via Chrome DevTools Protocol.

    Conecta ao Chrome DevTools, habilita Network domain e intercepta
    todos os frames WebSocket. Parseia o protocolo do jogo e emite
    eventos tipados via callbacks.
    """

    def __init__(self, port: int = 9222, auto_reconnect: bool = True):
        self.port = port
        self.auto_reconnect = auto_reconnect

        # WebSocket connection
        self._ws: Optional[websocket.WebSocket] = None
        self._devtools_url: Optional[str] = None
        self._ws_connections: Dict[str, str] = {}  # requestId -> url

        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Game state
        self.phase = GamePhase.UNKNOWN
        self.current_round: int = 0
        self.current_multiplier: float = 0.0
        self.last_crash: float = 0.0
        self.balance: float = 0.0
        self.bet_left_seconds: int = 0

        # History
        self.crash_history: deque = deque(maxlen=500)
        self.round_results: deque = deque(maxlen=100)

        # Callbacks: event_name -> [callback_fn]
        self._callbacks: Dict[str, List[Callable]] = {}

        # Stats
        self._stats = CaptureStats()
        self._start_time: float = 0.0

        # Last connection error (for UI display)
        self.last_error: str = ""

    # ── Chrome auto-launch ──────────────────────────────────────────────

    def _is_chrome_debug_running(self) -> bool:
        """Verifica se Chrome com debug port esta acessivel."""
        try:
            resp = requests.get(
                f"http://localhost:{self.port}/json/version",
                timeout=2,
            )
            return resp.status_code == 200
        except requests.ConnectionError:
            return False
        except Exception as e:
            logger.debug("_is_chrome_debug_running erro: %s", e)
            return False

    def _is_any_chrome_running(self) -> bool:
        """Verifica se qualquer processo Chrome esta rodando (Windows)."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe",
                 "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
            )
            return "chrome.exe" in result.stdout.lower()
        except Exception:
            return False

    def _kill_chrome(self) -> bool:
        """Fecha todos os processos Chrome (Windows)."""
        try:
            logger.info("Fechando processos Chrome...")
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe"],
                capture_output=True, timeout=10,
            )
            # Matar crashpad handler tambem (impede lock de perfil)
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome_crashpad_handler.exe"],
                capture_output=True, timeout=5,
            )
            time.sleep(3)  # Esperar processos e lock files liberarem
            return not self._is_any_chrome_running()
        except Exception as e:
            logger.error(f"Erro ao fechar Chrome: {e}")
            return False

    def _find_chrome_path(self) -> Optional[str]:
        """Encontra o executavel do Chrome no sistema."""
        system = platform.system()

        if system == "Windows":
            candidates = [
                Path(os.environ.get("PROGRAMFILES", ""))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", ""))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "Google/Chrome/Application/chrome.exe",
            ]
        elif system == "Darwin":  # macOS
            candidates = [
                Path("/Applications/Google Chrome.app"
                     "/Contents/MacOS/Google Chrome"),
            ]
        else:  # Linux
            candidates = [
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/google-chrome-stable"),
                Path("/usr/bin/chromium-browser"),
            ]

        for path in candidates:
            if path.exists():
                return str(path)

        # Fallback: procurar no PATH
        chrome = shutil.which("chrome") or shutil.which(
            "google-chrome"
        )
        return chrome

    def _get_bot_profile_dir(self) -> Path:
        """Return a dedicated Chrome profile directory for the bot.

        Uses a persistent directory next to the .exe (or project root in dev),
        so cookies/login persist between sessions. A separate profile avoids
        lock conflicts with the user's normal Chrome.
        """
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent.parent.parent
        profile = base / "crashbot_chrome_data"
        profile.mkdir(parents=True, exist_ok=True)
        return profile

    def _clean_profile_locks(self, profile_dir: Path):
        """Remove stale lock files from a Chrome profile directory."""
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            lock = profile_dir / name
            if lock.exists():
                try:
                    lock.unlink()
                    logger.info("Removido lock antigo: %s", name)
                except Exception as e:
                    logger.warning("Nao conseguiu remover %s: %s", name, e)

    def ensure_chrome_running(
        self, game_url: str = ""
    ) -> bool:
        """Garante que Chrome esta rodando com debug port.

        Estrategia:
        1. Se Chrome com debug port ja esta ativo → usa direto
        2. Senao → lanca Chrome com perfil dedicado do bot
           (coexiste com Chrome normal do usuario)

        Usa um --user-data-dir separado (crashbot_chrome_data/) para
        evitar conflitos de lock com o Chrome normal do usuario.
        Cookies/login do jogo persistem entre sessoes neste perfil.

        Returns:
            True se Chrome esta pronto para conexao.
        """
        # 1. Ja esta com debug port? Usar direto
        if self._is_chrome_debug_running():
            logger.info("Chrome debug ja esta rodando na porta %d", self.port)
            return True

        chrome_path = self._find_chrome_path()
        if not chrome_path:
            self.last_error = (
                "Chrome nao encontrado! "
                "Instale o Google Chrome."
            )
            logger.error(self.last_error)
            return False

        # 2. Preparar perfil dedicado do bot
        profile_dir = self._get_bot_profile_dir()
        self._clean_profile_locks(profile_dir)
        logger.info("Perfil do bot: %s", profile_dir)

        # 3. Lancar Chrome com debug port e perfil dedicado
        cmd = [
            chrome_path,
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
        ]

        if game_url:
            cmd.append(game_url)

        logger.info(
            "Lancando Chrome com debug port %d (perfil dedicado)...",
            self.port,
        )
        logger.info("Comando: %s", " ".join(cmd))

        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.last_error = f"Erro ao lancar Chrome: {e}"
            logger.error(self.last_error)
            return False

        # Aguardar Chrome ficar pronto (max 30s)
        logger.info("Aguardando Chrome responder na porta %d...", self.port)
        for i in range(60):
            time.sleep(0.5)
            if self._is_chrome_debug_running():
                logger.info(
                    "Chrome pronto com debug port (%0.1fs)",
                    (i + 1) * 0.5,
                )
                return True
            # Log a cada 5 segundos para diagnostico
            if (i + 1) % 10 == 0:
                secs = (i + 1) * 0.5
                running = self._is_any_chrome_running()
                logger.info(
                    "Aguardando Chrome... %.0fs (chrome.exe rodando: %s)",
                    secs, running,
                )

        # Chrome lancou mas sem debug port
        running = self._is_any_chrome_running()
        if running:
            self.last_error = (
                "Chrome abriu mas sem debug port. "
                "Feche TODAS as janelas e processos do Chrome "
                "(inclusive na bandeja) e tente novamente."
            )
        else:
            self.last_error = "Chrome nao iniciou apos 30s."

        logger.error(self.last_error)
        return False

    # ── Conexao ─────────────────────────────────────────────────────────

    def _find_game_tab(self) -> Optional[str]:
        """Encontra a aba do jogo no Chrome e retorna o WebSocket URL.

        Nunca conecta em paginas chrome://, about:blank ou new tab.
        Procura especificamente por abas com URLs de jogo.
        """
        try:
            resp = requests.get(
                f"http://localhost:{self.port}/json", timeout=5
            )
            tabs = resp.json()

            # Filtrar: apenas abas reais (type=page) com WS e URL valida
            valid_tabs = []
            for tab in tabs:
                url = tab.get("url", "")
                is_page = tab.get("type") == "page"
                ws_url = tab.get("webSocketDebuggerUrl", "")

                if not (is_page and ws_url):
                    continue

                # Ignorar paginas internas do Chrome (nunca funcionam)
                if url.startswith(("chrome://", "chrome-extension://",
                                   "about:", "edge://")):
                    continue

                valid_tabs.append(tab)

            # Primeiro: procurar por keywords do jogo
            for tab in valid_tabs:
                url = tab.get("url", "").lower()
                title = tab.get("title", "").lower()
                if any(kw in url or kw in title
                       for kw in GAME_TAB_KEYWORDS):
                    ws_url = tab["webSocketDebuggerUrl"]
                    logger.info(
                        f"Aba do jogo encontrada: "
                        f"{tab.get('title', '')[:50]} "
                        f"({tab.get('url', '')[:60]})"
                    )
                    return ws_url

            # Fallback: primeira aba real (http/https), NAO chrome://
            for tab in valid_tabs:
                url = tab.get("url", "")
                if url.startswith(("http://", "https://")):
                    logger.warning(
                        f"Aba do jogo nao detectada por keyword. "
                        f"Usando: {tab.get('url', '')[:60]}"
                    )
                    return tab["webSocketDebuggerUrl"]

            # Nenhuma aba valida encontrada
            page_count = sum(
                1 for t in tabs if t.get("type") == "page"
            )
            logger.warning(
                f"Nenhuma aba com site aberto ({page_count} abas, "
                f"mas todas sao chrome:// ou vazias)"
            )
            return None

        except requests.ConnectionError:
            logger.error(
                f"Chrome nao acessivel na porta {self.port}"
            )
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar aba do jogo: {e}")
            return None

    def is_chrome_ready(self) -> bool:
        """Verifica se Chrome com debug port esta rodando.
        Se nao, tenta lanca-lo automaticamente.

        Returns:
            True se Chrome esta pronto.
        """
        self.last_error = ""

        if self._is_chrome_debug_running():
            logger.info("Chrome debug port OK")
            return True

        logger.info("Chrome debug nao detectado, tentando lancar...")
        if self.ensure_chrome_running():
            return True

        # ensure_chrome_running sets self.last_error with details
        if not self.last_error:
            self.last_error = (
                "Chrome nao iniciou com debug port. "
                "Execute 'abrir_chrome_debug.bat' manualmente."
            )
        logger.error(f"is_chrome_ready FALHOU: {self.last_error}")
        return False

    def has_game_tab(self) -> bool:
        """Verifica se existe uma aba do jogo no Chrome.

        Returns:
            True se encontrou aba do jogo.
        """
        url = self._find_game_tab()
        return url is not None

    def connect(self) -> bool:
        """Conecta ao Chrome DevTools e habilita interceptacao de rede.

        Requisitos: Chrome rodando com debug port E aba do jogo aberta.

        Returns:
            True se conectou com sucesso.
        """
        self.last_error = ""
        logger.info("connect(): iniciando...")

        # Garantir Chrome rodando
        if not self.is_chrome_ready():
            logger.error("connect(): Chrome nao esta pronto")
            return False

        # Encontrar aba do jogo
        self._devtools_url = self._find_game_tab()
        if not self._devtools_url:
            self.last_error = (
                "Abra o site do jogo no Chrome que foi aberto "
                "(crash/brabet/blaze)"
            )
            logger.error(f"connect(): {self.last_error}")
            return False

        logger.info(
            f"connect(): aba encontrada, "
            f"ws_url={self._devtools_url[:80]}"
        )

        try:
            # Fechar conexao anterior se existir
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    pass

            logger.info("connect(): criando conexao WebSocket...")
            self._ws = websocket.create_connection(
                self._devtools_url, timeout=10
            )
            logger.info("connect(): conexao criada OK")

            # Habilitar Network domain
            self._ws.send(json.dumps({
                "id": 1, "method": "Network.enable"
            }))
            resp = json.loads(self._ws.recv())
            logger.info(f"connect(): Network.enable resp: {resp}")

            if resp.get("id") == 1 and "error" not in resp:
                self._stats.connected = True
                self.last_error = ""
                logger.info("connect(): SUCESSO - Network.enable OK")
                return True

            self.last_error = f"Network.enable falhou: {resp}"
            logger.error(self.last_error)
            return False

        except Exception as e:
            self.last_error = f"Erro ao conectar DevTools: {e}"
            logger.error(self.last_error)
            return False

    def disconnect(self):
        """Desconecta do Chrome DevTools."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._stats.connected = False
        logger.info("Desconectado do Chrome DevTools")

    # ── Event system ────────────────────────────────────────────────────

    def on(self, event: str, callback: Callable):
        """Registra callback para um evento do jogo.

        Eventos disponiveis:
            - "round_end": {crash, round_id, duration}
            - "balance_update": {balance}
            - "betting_phase": {bet_left_seconds}
            - "game_start": {start_time}
            - "multiplier_update": {multiplier, player}
            - "phase_change": {old_phase, new_phase}
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _emit(self, event: str, data: Dict):
        """Emite evento para todos os callbacks registrados."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Erro em callback '{event}': {e}")

    def _set_phase(self, new_phase: GamePhase):
        """Atualiza fase do jogo e emite evento se mudou."""
        if new_phase != self.phase:
            old = self.phase
            self.phase = new_phase
            self._emit("phase_change", {
                "old_phase": old.value,
                "new_phase": new_phase.value,
            })

    # ── Main loop ───────────────────────────────────────────────────────

    def start(self):
        """Inicia captura em thread daemon."""
        logger.info(
            f"start(): _running={self._running}, "
            f"connected={self._stats.connected}"
        )

        if self._running:
            logger.warning("Captura ja esta rodando")
            return

        if not self._stats.connected:
            logger.info("start(): nao conectado, tentando connect()...")
            if not self.connect():
                raise ConnectionError(
                    "Nao foi possivel conectar ao Chrome DevTools"
                )

        self._running = True
        self._start_time = time.time()
        logger.info("start(): iniciando _capture_loop thread...")
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="ws-capture"
        )
        self._thread.start()
        logger.info("Captura WebSocket iniciada")

    def stop(self):
        """Para a captura."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.disconnect()
        logger.info("Captura WebSocket parada")

    def _capture_loop(self):
        """Loop principal de captura (roda em thread daemon)."""
        reconnect_delay = 2

        while self._running:
            try:
                self._ws.settimeout(0.5)

                while self._running:
                    try:
                        msg = self._ws.recv()
                        self._process_devtools_message(msg)
                    except websocket.WebSocketTimeoutException:
                        continue
                    except websocket.WebSocketConnectionClosedException:
                        logger.warning("Conexao WebSocket fechada")
                        break
                    except Exception as e:
                        if "timed out" not in str(e):
                            logger.error(f"Erro no recv: {e}")
                            self._stats.errors += 1
                        continue

            except Exception as e:
                logger.error(f"Erro no loop de captura: {e}")
                self._stats.errors += 1

            # Reconnect
            if self._running and self.auto_reconnect:
                logger.info(
                    f"Reconectando em {reconnect_delay}s..."
                )
                self._stats.connected = False
                time.sleep(reconnect_delay)
                if self.connect():
                    reconnect_delay = 2
                else:
                    reconnect_delay = min(reconnect_delay * 2, 30)

    # ── Message processing ──────────────────────────────────────────────

    def _process_devtools_message(self, raw_msg: str):
        """Processa mensagem do Chrome DevTools Protocol."""
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        method = data.get("method", "")

        # WebSocket criado pelo jogo
        if method == "Network.webSocketCreated":
            params = data.get("params", {})
            req_id = params.get("requestId", "")
            url = params.get("url", "")
            self._ws_connections[req_id] = url
            logger.debug(f"WS criado: {url[:80]}")

        # Frame WebSocket recebido do servidor do jogo
        elif method == "Network.webSocketFrameReceived":
            params = data.get("params", {})
            response = params.get("response", {})
            payload = response.get("payloadData", "")
            opcode = response.get("opcode", 1)
            if payload:
                self._process_game_frame(payload, opcode)

        # Frame enviado ao servidor
        elif method == "Network.webSocketFrameSent":
            params = data.get("params", {})
            response = params.get("response", {})
            payload = response.get("payloadData", "")
            opcode = response.get("opcode", 1)
            if payload:
                self._process_game_frame(payload, opcode)

        # WebSocket fechado
        elif method == "Network.webSocketClosed":
            params = data.get("params", {})
            req_id = params.get("requestId", "")
            url = self._ws_connections.pop(req_id, "unknown")
            logger.debug(f"WS fechado: {url[:80]}")

    def _process_game_frame(self, payload: str, opcode: int = 1):
        """Decodifica e processa frame do jogo.

        Chrome DevTools Protocol:
          - opcode 1 (text): payloadData é string UTF-8
          - opcode 2 (binary): payloadData é base64-encoded
        """
        self._stats.frames_received += 1
        self._stats.last_frame_time = time.time()

        msg = None

        # Estrategia 1: texto direto (opcode 1 ou fallback)
        if opcode == 1 or msg is None:
            try:
                msg = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                pass

        # Estrategia 2: base64 + zlib (opcode 2 / binary frames)
        if msg is None:
            try:
                raw = base64.b64decode(payload)
                try:
                    decoded_str = zlib.decompress(raw).decode(
                        "utf-8", errors="replace"
                    )
                except zlib.error:
                    try:
                        decoded_str = zlib.decompress(
                            raw, -zlib.MAX_WBITS
                        ).decode("utf-8", errors="replace")
                    except zlib.error:
                        decoded_str = raw.decode("utf-8", errors="replace")
                msg = json.loads(decoded_str)
            except Exception:
                pass

        # Log amostral dos primeiros frames para diagnostico
        if self._stats.frames_received <= 5:
            sample = payload[:200] if len(payload) > 200 else payload
            if msg:
                cmd = msg.get("Head", {}).get("Cmd", "?")
                logger.warning(
                    f"[WS SAMPLE #{self._stats.frames_received}] "
                    f"opcode={opcode} cmd={cmd} keys={list(msg.keys())[:5]}"
                )
            else:
                logger.warning(
                    f"[WS SAMPLE #{self._stats.frames_received}] "
                    f"opcode={opcode} PARSE_FAILED payload={sample}"
                )

        if msg is None:
            return

        outer_cmd = msg.get("Head", {}).get("Cmd", 0)
        body = msg.get("Body", {})

        # Roteamento por comando
        if outer_cmd == CMD_GAME_PKG:
            self._handle_game_pkg(body)
        elif outer_cmd == CMD_HALL_END_ROUND:
            self._handle_end_round(body)
        elif outer_cmd == CMD_USER_INFO:
            self._handle_user_info(body)
        elif outer_cmd == CMD_HALL_NOTIFY:
            pass  # Join/leave - ignorar por enquanto
        elif outer_cmd == CMD_TICK:
            pass  # Heartbeat - ignorar
        elif outer_cmd != 0:
            # Comando desconhecido - log para analise
            logger.debug(
                f"Cmd desconhecido: {outer_cmd} body_keys={list(body.keys())[:5]}"
            )

    def _handle_game_pkg(self, body: Dict):
        """Processa GameJsonPkg (wrapper para comandos do jogo)."""
        game_pkg = body.get("GameJsonPkg", {})
        json_content = game_pkg.get("JsonContent", "")

        try:
            inner = json.loads(json_content)
        except (json.JSONDecodeError, TypeError):
            return

        inner_cmd = inner.get("Head", {}).get("Cmd", 0)
        inner_body = inner.get("Body", {})

        if inner_cmd == GAME_CMD_CHANGE_BANKER:
            self._handle_betting_phase(inner_body)
        elif inner_cmd == GAME_CMD_PRE_DEAL:
            self._handle_pre_deal(inner_body)
        elif inner_cmd == GAME_CMD_START:
            self._handle_game_start(inner_body)
        elif inner_cmd == GAME_CMD_BET:
            self._handle_bet(inner_body)
        elif inner_cmd == GAME_CMD_DUMMY_PLAY:
            self._handle_dummy_play(inner_body)

    # ── Event handlers ──────────────────────────────────────────────────

    def _handle_betting_phase(self, body: Dict):
        """Cmd 23 - ChangeBanker: inicio da fase de apostas."""
        cb = body.get("ChangeBanker", {})
        self.bet_left_seconds = cb.get("BetLeftSecond", 0)
        self._set_phase(GamePhase.BETTING)
        self._emit("betting_phase", {
            "bet_left_seconds": self.bet_left_seconds,
        })
        logger.debug(
            f"Fase apostas: {self.bet_left_seconds}s restantes"
        )

    def _handle_pre_deal(self, body: Dict):
        """Cmd 7 - PreDeal: 1 segundo antes do inicio."""
        pd = body.get("PreDeal", {})
        deal_second = pd.get("DealSecond", 0)
        self._set_phase(GamePhase.PRE_START)
        self._emit("pre_start", {"deal_second": deal_second})
        logger.debug("Pre-deal: round comeca em 1s")

    def _handle_game_start(self, body: Dict):
        """Cmd 1 - StartGame: multiplicador começa a subir."""
        sg = body.get("StartGame", {})
        start_time = sg.get("StartTime", 0)
        self.current_multiplier = 1.0
        self._set_phase(GamePhase.PLAYING)
        self._emit("game_start", {"start_time": start_time})
        logger.debug(f"Round iniciado: StartTime={start_time}")

    def _handle_bet(self, body: Dict):
        """Cmd 22 - Bet: aposta de um jogador."""
        bet = body.get("Bet", {})
        # BetMulti vem em centesimos (99900 = 999.00x auto-cashout)
        bet_multi_raw = bet.get("BetMulti", 0)
        bet_gold = bet.get("BetGold", 0)
        nickname = bet.get("Nickname", "")
        player_id = bet.get("BetPlayerID", 0)

        self._emit("bet_placed", {
            "player_id": player_id,
            "nickname": nickname,
            "amount": bet_gold,
            "auto_cashout": bet_multi_raw / 100,
        })

    def _handle_dummy_play(self, body: Dict):
        """Cmd 36 - DummyPlay: cashout de jogador (multiplicador real-time)."""
        dp = body.get("DummyPlay", {})
        cards = dp.get("Cards", [])
        nickname = dp.get("Nickname", "")

        if cards:
            # Cards[0] / 100 = multiplicador atual no momento do cashout
            multiplier = cards[0] / 100
            with self._lock:
                self.current_multiplier = multiplier

            self._emit("multiplier_update", {
                "multiplier": multiplier,
                "player": nickname,
            })

    def _handle_end_round(self, body: Dict):
        """Cmd 1089 - HallEndRound: resultado final do round."""
        end_round = body.get("HallEndRound", {})
        end_info = end_round.get("EndInfo", {})
        table_cards = end_info.get("TableCards", "")
        round_id = end_round.get("Round", 0)
        duration = end_round.get("Duration", 0)
        begin_time = end_round.get("BeginTime", 0)
        end_time = end_round.get("EndTime", 0)

        # TableCards: "183 0 0" -> primeiro numero / 100 = crash value
        crash_value = 0.0
        try:
            parts = table_cards.strip().split()
            if parts:
                crash_value = int(parts[0]) / 100
        except (ValueError, IndexError):
            logger.error(f"Erro ao parsear TableCards: '{table_cards}'")
            return

        if crash_value < 1.0:
            logger.warning(f"Crash value invalido: {crash_value}")
            return

        # Atualizar estado
        with self._lock:
            self.last_crash = crash_value
            self.current_round = round_id
            self.current_multiplier = crash_value

        self.crash_history.append(crash_value)
        self._stats.rounds_captured += 1

        result = RoundResult(
            round_id=round_id,
            crash_value=crash_value,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            begin_time=begin_time,
            end_time=end_time,
        )
        self.round_results.append(result)

        self._set_phase(GamePhase.CRASHED)

        self._emit("round_end", {
            "crash": crash_value,
            "round_id": round_id,
            "duration": duration,
            "begin_time": begin_time,
            "end_time": end_time,
        })

        logger.info(
            f"Round {round_id}: crash={crash_value:.2f}x "
            f"(duration={duration}s)"
        )

    def _handle_user_info(self, body: Dict):
        """Cmd 1009 - UpdateUserinfo: atualizacao de saldo."""
        user_info = body.get("UpdateUserinfo", {})
        gold_coin = user_info.get("GoldCoin", 0.0)

        if gold_coin > 0:
            old_balance = self.balance
            with self._lock:
                self.balance = gold_coin

            self._emit("balance_update", {
                "balance": gold_coin,
                "old_balance": old_balance,
                "diff": gold_coin - old_balance if old_balance > 0 else 0,
            })

            logger.debug(f"Saldo atualizado: R${gold_coin:.2f}")

    # ── Public API (polling) ────────────────────────────────────────────

    def get_last_crash(self) -> Optional[float]:
        """Retorna o ultimo valor de crash capturado."""
        with self._lock:
            return self.last_crash if self.last_crash > 0 else None

    def get_balance(self) -> Optional[float]:
        """Retorna o saldo atual do usuario."""
        with self._lock:
            return self.balance if self.balance > 0 else None

    def get_current_multiplier(self) -> Optional[float]:
        """Retorna o multiplicador atual durante a fase PLAYING."""
        with self._lock:
            if self.phase == GamePhase.PLAYING:
                return self.current_multiplier
            return None

    def get_game_phase(self) -> str:
        """Retorna a fase atual do jogo."""
        return self.phase.value

    def get_crash_history(self, n: int = 50) -> List[float]:
        """Retorna os ultimos N crashes."""
        return list(self.crash_history)[-n:]

    def get_stats(self) -> Dict:
        """Retorna estatisticas da captura."""
        self._stats.uptime_seconds = (
            time.time() - self._start_time if self._start_time else 0
        )
        return {
            "connected": self._stats.connected,
            "frames_received": self._stats.frames_received,
            "rounds_captured": self._stats.rounds_captured,
            "errors": self._stats.errors,
            "last_frame_time": self._stats.last_frame_time,
            "uptime_seconds": self._stats.uptime_seconds,
            "current_phase": self.phase.value,
            "last_crash": self.last_crash,
            "balance": self.balance,
        }

    def is_connected(self) -> bool:
        """Verifica se esta conectado e recebendo dados."""
        if not self._stats.connected:
            return False
        # Considerar desconectado se nao recebe frames ha 30s
        if self._stats.last_frame_time > 0:
            elapsed = time.time() - self._stats.last_frame_time
            if elapsed > 30:
                return False
        return True

    # ── Context manager ─────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.stop()
