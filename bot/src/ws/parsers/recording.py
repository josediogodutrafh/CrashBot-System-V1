"""
Recording Mixin - Grava frames WS brutos para análise de protocolo.

Qualquer parser pode herdar RecordingMixin para capturar os frames
originais antes de processar. Útil para reverse-engineering de
plataformas novas.

Uso:
    class MeuParser(RecordingMixin, BaseParser):
        ...

    parser = MeuParser()
    parser.start_recording()  # Inicia gravação em data/recordings/
    events = parser.parse_frame(payload, opcode)  # Grava + parseia
    parser.stop_recording()   # Fecha arquivo
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RecordingMixin:
    """Mixin que grava frames WS brutos em arquivo JSONL.

    Cada linha do arquivo contém:
    {
        "ts": 1708100000.123,
        "opcode": 1,
        "payload": "...",
        "size": 1234
    }
    """

    _rec_file = None
    _rec_path: str = ""
    _rec_count: int = 0

    def start_recording(self, platform_name: str = ""):
        """Inicia gravação de frames brutos.

        Args:
            platform_name: Nome da plataforma (default: self.platform_name).
        """
        name = platform_name or getattr(self, "platform_name", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # data/recordings/ relativo ao projeto
        rec_dir = Path(__file__).parent.parent.parent.parent / "data" / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)

        self._rec_path = str(rec_dir / f"{name}_{ts}.jsonl")
        self._rec_file = open(self._rec_path, "a", encoding="utf-8")
        self._rec_count = 0
        logger.info(f"Gravação iniciada: {self._rec_path}")

    def record_frame(self, payload: str, opcode: int):
        """Grava um frame bruto no arquivo."""
        if not self._rec_file:
            return
        try:
            entry = {
                "ts": time.time(),
                "opcode": opcode,
                "payload": payload,
                "size": len(payload),
            }
            self._rec_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._rec_file.flush()
            self._rec_count += 1
        except Exception as e:
            logger.error(f"Erro ao gravar frame: {e}")

    def stop_recording(self):
        """Para gravação e fecha arquivo."""
        if self._rec_file:
            try:
                self._rec_file.close()
            except Exception:
                pass
            logger.info(
                f"Gravação encerrada: {self._rec_count} frames → {self._rec_path}"
            )
            self._rec_file = None

    @property
    def is_recording(self) -> bool:
        return self._rec_file is not None
