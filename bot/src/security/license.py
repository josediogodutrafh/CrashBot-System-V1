"""
License validation client.

Validates license key + HWID against the API.
Caches the last valid key locally in config/.license
"""

import json
import logging
from pathlib import Path

import requests

from src.config import API_URL, BOT_VERSION, CONFIG_DIR
from src.security.hwid import get_hwid

logger = logging.getLogger(__name__)

LICENSE_FILE = CONFIG_DIR / ".license"
VALIDATE_ENDPOINT = f"{API_URL}/api/v1/validar"
VALIDATE_TIMEOUT = 15  # seconds


def load_saved_key() -> str:
    """Load previously saved license key from disk."""
    if LICENSE_FILE.exists():
        try:
            data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
            return data.get("chave", "")
        except Exception:
            return LICENSE_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_key(chave: str):
    """Save license key to disk for next session."""
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"chave": chave, "hwid": get_hwid()}
    LICENSE_FILE.write_text(json.dumps(data), encoding="utf-8")


def validate_license(chave: str) -> dict:
    """Validate a license key against the API.

    Returns:
        dict with keys:
            sucesso: bool
            mensagem: str
            dias_restantes: int | None
            telegram_chat_id: str | None
    """
    chave = chave.strip()
    if not chave:
        return {"sucesso": False, "mensagem": "Chave de licença não informada."}

    hwid = get_hwid()

    try:
        resp = requests.post(
            VALIDATE_ENDPOINT,
            json={"chave": chave, "hwid": hwid, "versao_bot": BOT_VERSION},
            timeout=VALIDATE_TIMEOUT,
        )

        if resp.status_code == 200:
            data = resp.json()

            # Servidor exige atualização
            if data.get("force_update"):
                download_url = data.get("download_url", "")
                if download_url:
                    try:
                        import webbrowser
                        webbrowser.open(download_url)
                    except Exception:
                        pass
                return {
                    "sucesso": False,
                    "mensagem": data.get("mensagem", "Atualização obrigatória."),
                    "force_update": True,
                    "download_url": download_url,
                }

            if data.get("sucesso"):
                save_key(chave)
            return data

        elif resp.status_code == 403:
            # HWID mismatch
            data = resp.json() if resp.text else {}
            return {
                "sucesso": False,
                "mensagem": data.get("detail", "Licença vinculada a outro computador."),
            }

        elif resp.status_code == 404:
            return {"sucesso": False, "mensagem": "Licença não encontrada."}

        elif resp.status_code == 429:
            return {"sucesso": False, "mensagem": "Muitas tentativas. Aguarde 1 minuto."}

        else:
            return {
                "sucesso": False,
                "mensagem": f"Erro do servidor ({resp.status_code}). Tente novamente.",
            }

    except requests.ConnectionError:
        return {
            "sucesso": False,
            "mensagem": "Sem conexão com o servidor. Verifique sua internet.",
        }
    except requests.Timeout:
        return {
            "sucesso": False,
            "mensagem": "Servidor demorou para responder. Tente novamente.",
        }
    except Exception as e:
        logger.error(f"License validation error: {e}")
        return {
            "sucesso": False,
            "mensagem": f"Erro inesperado: {e}",
        }
