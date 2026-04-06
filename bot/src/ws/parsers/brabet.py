"""
Brabet Parser - Decodifica o protocolo WebSocket da plataforma Brabet/crash.

Protocolo:
  - Frames podem ser texto (JSON direto) ou binários (base64 + zlib)
  - Estrutura: {"Head": {"Cmd": int}, "Body": {...}}
  - Outer Cmds: 1071 (GamePkg), 1089 (EndRound), 1009 (UserInfo), 1090 (Notify), 1100 (Tick)
  - Inner Cmds (dentro de GameJsonPkg): 1 (Start), 7 (PreDeal), 22 (Bet), 23 (ChangeBanker), 36 (DummyPlay)
"""

import base64
import json
import logging
import zlib
from typing import Dict, List

from src.ws.parsers.base import BaseParser, ParsedEvent
from src.ws.parsers.recording import RecordingMixin

logger = logging.getLogger(__name__)

# Outer commands (protocol layer)
CMD_GAME_PKG = 1071
CMD_HALL_END_ROUND = 1089
CMD_HALL_NOTIFY = 1090
CMD_TICK = 1100
CMD_USER_INFO = 1009

# Inner game commands (dentro de GameJsonPkg.JsonContent)
GAME_CMD_START = 1
GAME_CMD_PRE_DEAL = 7
GAME_CMD_BET = 22
GAME_CMD_CHANGE_BANKER = 23
GAME_CMD_DUMMY_PLAY = 36


class BrabetParser(RecordingMixin, BaseParser):
    """Parser para plataforma Brabet (e clones que usam mesmo protocolo)."""

    @property
    def platform_name(self) -> str:
        return "brabet"

    @property
    def game_tab_keywords(self) -> List[str]:
        return ["crash", "blaze", "brabet", "game", "casino", "apostas", "bet"]

    def parse_frame(self, payload: str, opcode: int = 1) -> List[ParsedEvent]:
        if self.is_recording:
            self.record_frame(payload, opcode)

        msg = self._decode_frame(payload, opcode)
        if msg is None:
            return []

        outer_cmd = msg.get("Head", {}).get("Cmd", 0)
        body = msg.get("Body", {})

        events = []

        if outer_cmd == CMD_GAME_PKG:
            events.extend(self._parse_game_pkg(body))
        elif outer_cmd == CMD_HALL_END_ROUND:
            ev = self._parse_end_round(body)
            if ev:
                events.append(ev)
        elif outer_cmd == CMD_USER_INFO:
            ev = self._parse_user_info(body)
            if ev:
                events.append(ev)
        # CMD_HALL_NOTIFY e CMD_TICK ignorados

        return events

    # ── Decodificação ────────────────────────────────────────────────────

    def _decode_frame(self, payload: str, opcode: int) -> dict | None:
        """Decodifica frame bruto (texto ou base64+zlib)."""
        msg = None

        # Estratégia 1: texto direto (opcode 1)
        if opcode == 1 or msg is None:
            try:
                msg = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                pass

        # Estratégia 2: base64 + zlib (opcode 2 / binary)
        if msg is None:
            try:
                raw = base64.b64decode(payload)
                try:
                    decoded = zlib.decompress(raw).decode("utf-8", errors="replace")
                except zlib.error:
                    try:
                        decoded = zlib.decompress(raw, -zlib.MAX_WBITS).decode(
                            "utf-8", errors="replace"
                        )
                    except zlib.error:
                        decoded = raw.decode("utf-8", errors="replace")
                msg = json.loads(decoded)
            except Exception:
                pass

        return msg

    # ── Parsers por comando ──────────────────────────────────────────────

    def _parse_game_pkg(self, body: Dict) -> List[ParsedEvent]:
        """Parseia GameJsonPkg (wrapper para comandos internos do jogo)."""
        game_pkg = body.get("GameJsonPkg", {})
        json_content = game_pkg.get("JsonContent", "")

        try:
            inner = json.loads(json_content)
        except (json.JSONDecodeError, TypeError):
            return []

        inner_cmd = inner.get("Head", {}).get("Cmd", 0)
        inner_body = inner.get("Body", {})
        events = []

        if inner_cmd == GAME_CMD_CHANGE_BANKER:
            cb = inner_body.get("ChangeBanker", {})
            events.append(ParsedEvent("betting_phase", {
                "bet_left_seconds": cb.get("BetLeftSecond", 0),
            }))

        elif inner_cmd == GAME_CMD_PRE_DEAL:
            pd = inner_body.get("PreDeal", {})
            events.append(ParsedEvent("pre_start", {
                "deal_second": pd.get("DealSecond", 0),
            }))

        elif inner_cmd == GAME_CMD_START:
            sg = inner_body.get("StartGame", {})
            events.append(ParsedEvent("game_start", {
                "start_time": sg.get("StartTime", 0),
            }))

        elif inner_cmd == GAME_CMD_BET:
            bet = inner_body.get("Bet", {})
            events.append(ParsedEvent("bet_placed", {
                "player_id": bet.get("BetPlayerID", 0),
                "nickname": bet.get("Nickname", ""),
                "amount": bet.get("BetGold", 0),
                "auto_cashout": bet.get("BetMulti", 0) / 100,
            }))

        elif inner_cmd == GAME_CMD_DUMMY_PLAY:
            dp = inner_body.get("DummyPlay", {})
            cards = dp.get("Cards", [])
            if cards:
                events.append(ParsedEvent("cashout", {
                    "multiplier": cards[0] / 100,
                    "player": dp.get("Nickname", ""),
                }))

        return events

    def _parse_end_round(self, body: Dict) -> ParsedEvent | None:
        """Parseia HallEndRound (resultado final)."""
        end_round = body.get("HallEndRound", {})
        end_info = end_round.get("EndInfo", {})
        table_cards = end_info.get("TableCards", "")
        round_id = end_round.get("Round", 0)
        duration = end_round.get("Duration", 0)

        crash_value = 0.0
        try:
            parts = table_cards.strip().split()
            if parts:
                crash_value = int(parts[0]) / 100
        except (ValueError, IndexError):
            logger.error(f"Erro ao parsear TableCards: '{table_cards}'")
            return None

        if crash_value < 1.0:
            return None

        return ParsedEvent("round_end", {
            "crash": crash_value,
            "round_id": round_id,
            "duration": duration,
            "begin_time": end_round.get("BeginTime", 0),
            "end_time": end_round.get("EndTime", 0),
        })

    def _parse_user_info(self, body: Dict) -> ParsedEvent | None:
        """Parseia UpdateUserinfo (saldo)."""
        user_info = body.get("UpdateUserinfo", {})
        gold_coin = user_info.get("GoldCoin", 0.0)

        if gold_coin > 0:
            return ParsedEvent("balance_update", {
                "balance": gold_coin,
            })
        return None
