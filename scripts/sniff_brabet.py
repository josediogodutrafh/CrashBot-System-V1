#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BRABET CRASH - WEBSOCKET SNIFFER

Mata todo Chrome, abre limpo com debug, conecta e captura.
Zero configuração. Só executar.

    python scripts/sniff_brabet.py
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import sys
import time
import zlib
from datetime import datetime
from typing import Any, Dict, List, Optional

# Fix encoding Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

CDP_PORT = 9222
BRABET_URL = "https://www.brabet.com/?f=game_Crash"
LOG_FILE = "brabet_ws_log.jsonl"
DEBUG_PROFILE = os.path.join(os.environ.get("TEMP", "."), "chrome-debug-crashbot")

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("sniffer")


# ═══════════════════════════════════════════════════════════════════════════════
# CHROME
# ═══════════════════════════════════════════════════════════════════════════════


def find_chrome() -> Optional[str]:
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def kill_chrome():
    """Mata TODOS os processos do Chrome."""
    print("[1/4] Matando todos os processos do Chrome...")
    subprocess.run(
        ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    print("      OK - Chrome fechado")


def launch_chrome(url: str) -> bool:
    """Abre Chrome limpo com debug."""
    chrome = find_chrome()
    if not chrome:
        print("ERRO: Chrome nao encontrado!")
        return False

    print(f"[2/4] Abrindo Chrome com debug (porta {CDP_PORT})...")

    cmd = [
        chrome,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={DEBUG_PROFILE}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        url,
    ]

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("      OK - Chrome aberto")
    return True


def wait_chrome(timeout: int = 60) -> bool:
    """Espera Chrome responder na porta CDP."""
    import urllib.request

    print(f"[3/4] Aguardando Chrome responder (max {timeout}s)...")

    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(
                f"http://localhost:{CDP_PORT}/json", timeout=2
            )
            tabs = json.loads(req.read())
            if tabs:
                print(f"      OK - Chrome pronto ({len(tabs)} tab(s))")
                return True
        except Exception:
            pass
        time.sleep(1)
        elapsed = int(time.time() - start)
        print(f"      Aguardando... {elapsed}s", end="\r")

    print("\n      FALHOU - Chrome nao respondeu")
    return False


def get_game_tab() -> Optional[dict]:
    """Encontra tab da Brabet."""
    import urllib.request

    req = urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json", timeout=5)
    tabs = json.loads(req.read())

    # Procura tab da Brabet
    for tab in tabs:
        url = tab.get("url", "").lower()
        if "brabet" in url or "crash" in url:
            return tab

    # Fallback: primeira tab com webSocketDebuggerUrl
    for tab in tabs:
        if tab.get("webSocketDebuggerUrl"):
            return tab

    return tabs[0] if tabs else None


# ═══════════════════════════════════════════════════════════════════════════════
# SNIFFER
# ═══════════════════════════════════════════════════════════════════════════════


class BrabetSniffer:
    """Intercepta WebSocket do Crash via Chrome DevTools Protocol."""

    def __init__(self):
        self.explosions: List[Dict[str, Any]] = []
        self.ws_urls: List[str] = []
        self.total_msgs = 0
        self.total_decoded = 0
        self.total_json = 0
        self.total_explosions = 0
        self.total_rounds = 0
        self.start_time = datetime.now()
        self.decoded_samples: List[str] = []

        # Estado do jogo
        self.current_round: Optional[int] = None
        self.game_phase = "unknown"  # betting, running, crashed
        self.last_cashouts: List[float] = []  # Cashouts da rodada atual
        self.hall_end_samples: List[str] = []  # HallEndRound completos

        # Limpa log anterior
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

    def run(self) -> None:
        """Conecta ao CDP e inicia captura."""
        import websocket

        tab = get_game_tab()
        if not tab:
            print("ERRO: Nenhuma tab encontrada")
            return

        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            print("ERRO: Tab sem webSocketDebuggerUrl")
            return

        print(f"[4/4] Conectando ao DevTools...")
        print(f"      Tab: {tab.get('title', 'N/A')}")
        print(f"      URL: {tab.get('url', 'N/A')[:60]}")

        ws = websocket.WebSocket()
        ws.connect(ws_url)

        # Habilita captura de rede
        ws.send(json.dumps({"id": 1, "method": "Network.enable", "params": {}}))
        ws.recv()  # resposta

        print("      OK - Conectado!")
        print()
        print("=" * 60)
        print("  CAPTURA ATIVA - Aguardando explosoes...")
        print("  Ctrl+C para parar")
        print("=" * 60)
        print()

        try:
            while True:
                raw = ws.recv()
                data = json.loads(raw)
                method = data.get("method", "")

                if method == "Network.webSocketCreated":
                    url = data["params"].get("url", "")
                    if url not in self.ws_urls:
                        self.ws_urls.append(url)
                        log.info(f"[WS] {url}")

                elif method == "Network.webSocketFrameReceived":
                    payload = data["params"]["response"]["payloadData"]
                    self._process(payload, "recv")

                elif method == "Network.webSocketFrameSent":
                    payload = data["params"]["response"]["payloadData"]
                    self._process(payload, "sent")

        except KeyboardInterrupt:
            print("\n\nCaptura encerrada pelo usuario.")
        except Exception as e:
            print(f"\nErro: {e}")
        finally:
            ws.close()
            self._summary()

    def _decode_payload(self, payload: str) -> str:
        """Tenta decodificar payload base64+zlib."""
        # Tenta base64 -> zlib
        try:
            raw_bytes = base64.b64decode(payload)
            decoded = zlib.decompress(raw_bytes).decode("utf-8")
            return decoded
        except Exception:
            pass

        # Tenta base64 -> zlib (wbits=-15, raw deflate)
        try:
            raw_bytes = base64.b64decode(payload)
            decoded = zlib.decompress(raw_bytes, -zlib.MAX_WBITS).decode("utf-8")
            return decoded
        except Exception:
            pass

        # Tenta base64 -> zlib (wbits=16+MAX, gzip)
        try:
            raw_bytes = base64.b64decode(payload)
            decoded = zlib.decompress(raw_bytes, 16 + zlib.MAX_WBITS).decode("utf-8")
            return decoded
        except Exception:
            pass

        # Tenta so base64
        try:
            decoded = base64.b64decode(payload).decode("utf-8")
            return decoded
        except Exception:
            pass

        # Retorna original
        return payload

    def _process(self, payload: str, direction: str) -> None:
        """Processa frame WebSocket (com decode base64+zlib)."""
        if not payload:
            return

        self.total_msgs += 1
        now = datetime.now()

        # Tenta decodificar (base64+zlib)
        # "eJ"/"eN" = zlib+b64, mas tenta pra qualquer payload nao-JSON
        decoded = payload
        was_encoded = False
        try:
            json.loads(payload)
            # Ja e JSON puro, nao precisa decodificar
            decoded = payload
        except (json.JSONDecodeError, ValueError):
            decoded = self._decode_payload(payload)
            if decoded != payload:
                was_encoded = True

        if was_encoded:
            self.total_decoded += 1
            # Salva amostras das primeiras 10 msgs decodificadas
            if len(self.decoded_samples) < 10:
                self.decoded_samples.append(decoded[:500])

        # Salva no log (decoded)
        entry = {
            "t": now.isoformat(),
            "d": direction,
            "encoded": was_encoded,
            "p": decoded[:1000],
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Tenta JSON
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            # Payload raw
            arrow = "<-" if direction == "recv" else "->"
            prefix = "[DEC] " if was_encoded else ""
            if len(decoded) < 500:
                log.info(f"  {arrow} {prefix}{decoded[:300]}")
            else:
                log.info(f"  {arrow} {prefix}{decoded[:200]}...")
            self._try_raw(decoded, now)
            return

        # JSON valido!
        self.total_json += 1

        # Analisa com protocolo Brabet
        self._analyze(data, now)

    # ═══════════════════════════════════════════════════════════
    # PROTOCOLO BRABET
    # ═══════════════════════════════════════════════════════════
    #
    # Estrutura externa: {"Head": {"Cmd": X}, "Body": {...}}
    #
    # Cmd 1071 = GameJsonPkg (JsonContent com JSON aninhado)
    #   Inner Cmd 1  = StartGame (inicio rodada)
    #   Inner Cmd 7  = PreDeal (countdown)
    #   Inner Cmd 22 = Bet (aposta: BetMulti, BetGold)
    #   Inner Cmd 23 = ChangeBanker (nova rodada)
    #   Inner Cmd 36 = DummyPlay (cashout: Cards[0]/100 = mult)
    #
    # Cmd 1089 = HallEndRound (FIM DA RODADA = EXPLOSAO!)
    # Cmd 1090 = HallNotify (join/leave)
    # Cmd 1100 = Tick (heartbeat)
    # ═══════════════════════════════════════════════════════════

    def _analyze(self, data: dict, ts: datetime) -> None:
        """Analisa mensagem do protocolo Brabet."""
        if not isinstance(data, dict):
            return

        head = data.get("Head", {})
        body = data.get("Body", {})
        cmd = head.get("Cmd", 0)

        # ── Cmd 1089: HallEndRound (EXPLOSAO!) ──
        if cmd == 1089:
            self._handle_hall_end_round(body, ts, data)
            return

        # ── Cmd 1071: GameJsonPkg (eventos do jogo) ──
        if cmd == 1071:
            pkg = body.get("GameJsonPkg", {})
            json_str = pkg.get("JsonContent", "")
            if json_str:
                try:
                    inner = json.loads(json_str)
                    self._handle_game_event(inner, ts)
                except json.JSONDecodeError:
                    pass
            return

        # ── Cmd 1090: HallNotify ──
        if cmd == 1090:
            return  # Ignorar join/leave

        # ── Cmd 1100: Tick ──
        if cmd == 1100:
            return  # Ignorar heartbeat

    def _handle_game_event(self, inner: dict, ts: datetime) -> None:
        """Processa evento do jogo (JsonContent parseado)."""
        head = inner.get("Head", {})
        body = inner.get("Body", {})
        cmd = head.get("Cmd", 0)

        # Cmd 23: ChangeBanker = Nova rodada (fase de apostas)
        if cmd == 23:
            cb = body.get("ChangeBanker", {})
            bet_secs = cb.get("BetLeftSecond", 0)
            self.game_phase = "betting"
            self.last_cashouts = []
            log.info(f"  -- NOVA RODADA (apostas: {bet_secs}s) --")

        # Cmd 1: StartGame = Jogo comecou
        elif cmd == 1:
            sg = body.get("StartGame", {})
            self.game_phase = "running"
            self.last_cashouts = []
            log.info(f"  >> JOGO INICIADO (round time: {sg.get('StartTime', '?')})")

        # Cmd 7: PreDeal = Countdown
        elif cmd == 7:
            pd = body.get("PreDeal", {})
            secs = pd.get("DealSecond", 0)
            log.info(f"  .. Pre-deal: {secs}s")

        # Cmd 36: DummyPlay = Cashout de jogador
        elif cmd == 36:
            dp = body.get("DummyPlay", {})
            cards = dp.get("Cards", [])
            nickname = dp.get("Nickname", "?")
            if cards and len(cards) >= 1:
                mult_raw = cards[0]
                mult = mult_raw / 100.0
                self.last_cashouts.append(mult)
                log.info(f"  $$ Cashout: {nickname} em {mult:.2f}x")

        # Cmd 22: Bet (silencioso - muitas msgs)
        elif cmd == 22:
            pass  # Apostas sao muitas, nao logar

    def _handle_hall_end_round(self, body: dict, ts: datetime, full_data: dict) -> None:
        """Processa HallEndRound - FIM DA RODADA (EXPLOSAO!)."""
        her = body.get("HallEndRound", {})
        round_id = her.get("Round", 0)
        self.total_rounds += 1

        # Salva HallEndRound completo para debug
        full_json = json.dumps(full_data, ensure_ascii=False)
        if len(self.hall_end_samples) < 5:
            self.hall_end_samples.append(full_json)

        # Log completo do HallEndRound no arquivo
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            entry = {
                "t": ts.isoformat(),
                "type": "HALL_END_ROUND",
                "full": full_data,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Extrai crash de EndInfo.TableCards
        crash_mult = self._extract_crash_from_end_round(her)

        if crash_mult is not None:
            self._explosion(crash_mult, ts, her)
        else:
            # Nao encontrou - dump para debug
            end_info = her.get("EndInfo", {})
            log.info(f"  ?? Round #{round_id} sem crash. EndInfo: {end_info}")
            log.info(f"     Campos HallEndRound: {list(her.keys())}")

        self.game_phase = "crashed"
        self.last_cashouts = []

    def _extract_crash_from_end_round(self, her: dict) -> Optional[float]:
        """Extrai multiplicador do crash de HallEndRound.

        O crash esta em EndInfo.TableCards: "254 0 0"
        Primeiro numero / 100 = multiplicador (2.54x)
        """
        end_info = her.get("EndInfo", {})
        table_cards = end_info.get("TableCards", "")

        if table_cards:
            parts = table_cards.strip().split()
            if parts:
                try:
                    raw_val = int(parts[0])
                    mult = raw_val / 100.0
                    if mult >= 1.0:
                        return mult
                except (ValueError, IndexError):
                    pass

        return None

    def _try_raw(self, payload: str, ts: datetime) -> None:
        """Tenta extrair dados de texto raw (nao-JSON)."""
        # Procura padroes numericos que possam ser multiplicadores
        m = re.search(r"(\d+\.\d{2})x", payload, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                if 1.0 <= v <= 1000.0:
                    self._explosion(v, ts, {"raw": payload[:100]})
            except ValueError:
                pass

    def _explosion(self, mult: float, ts: datetime, raw: Any) -> None:
        """Registra explosao."""
        self.total_explosions += 1
        self.explosions.append({"m": mult, "t": ts.isoformat()})

        icon = "🔴" if mult < 2.0 else ("🟡" if mult < 5.0 else "🟢")

        print()
        print(f"  {icon} EXPLOSAO #{self.total_explosions}: {mult:.2f}x  [{ts.strftime('%H:%M:%S')}]")

        if len(self.explosions) >= 3:
            last = [e["m"] for e in self.explosions[-5:]]
            print(f"     Ultimos: {last}")
        print()

    def _summary(self) -> None:
        """Resumo final."""
        dur = (datetime.now() - self.start_time).total_seconds()

        print()
        print("=" * 70)
        print("  RESUMO")
        print("=" * 70)
        print(f"  Duracao:       {dur:.0f}s")
        print(f"  Mensagens:     {self.total_msgs}")
        print(f"  Decodificadas: {self.total_decoded}")
        print(f"  JSON valido:   {self.total_json}")
        print(f"  Rodadas:       {self.total_rounds}")
        print(f"  Explosoes:     {self.total_explosions}")

        if self.explosions:
            mults = [e["m"] for e in self.explosions]
            print()
            print(f"  Media:   {sum(mults)/len(mults):.2f}x")
            print(f"  Min:     {min(mults):.2f}x")
            print(f"  Max:     {max(mults):.2f}x")
            print(f"  Ultimos: {[round(m, 2) for m in mults[-10:]]}")

        if self.hall_end_samples:
            print()
            print("  HALL_END_ROUND COMPLETOS (para debug):")
            print("  " + "-" * 66)
            for i, sample in enumerate(self.hall_end_samples[:3], 1):
                # Pretty print truncado
                try:
                    obj = json.loads(sample)
                    pretty = json.dumps(obj, indent=2, ensure_ascii=False)
                    lines = pretty.split("\n")
                    print(f"  [{i}]")
                    for line in lines[:40]:
                        print(f"      {line}")
                    if len(lines) > 40:
                        print(f"      ... ({len(lines) - 40} linhas restantes)")
                    print()
                except Exception:
                    print(f"  [{i}] {sample[:500]}")
                    print()

        print(f"\n  Log: {os.path.abspath(LOG_FILE)}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    print()
    print("=" * 60)
    print("  BRABET CRASH - WEBSOCKET SNIFFER")
    print("=" * 60)
    print()

    # 1. Mata Chrome
    kill_chrome()

    # 2. Abre Chrome limpo
    if not launch_chrome(BRABET_URL):
        return

    # 3. Espera Chrome
    if not wait_chrome(timeout=60):
        print()
        print("Tente manualmente:")
        print(f'  "{find_chrome()}" --remote-debugging-port={CDP_PORT} --user-data-dir="{DEBUG_PROFILE}" "{BRABET_URL}"')
        return

    # 4. Espera usuario
    print()
    print("-" * 60)
    print("  O Chrome abriu na Brabet.")
    print("  1. Faca login (se necessario)")
    print("  2. Abra o jogo Crash")
    print("  3. Pressione ENTER aqui quando estiver no jogo")
    print("-" * 60)
    print()

    input("  >>> ENTER para iniciar captura... ")

    # 5. Captura
    sniffer = BrabetSniffer()
    sniffer.run()


if __name__ == "__main__":
    main()
