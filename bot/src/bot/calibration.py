"""
Calibration Module - Screen area selection wizard + profile management.

Extracted from controller.py for reuse by GUI Flet config panel.
Uses Tkinter overlay for area selection (click+drag on semi-transparent fullscreen).
"""

import json
import logging
import tkinter as tk
from pathlib import Path
from typing import Optional

from src.config import PROFILES_PATH

logger = logging.getLogger(__name__)

# Required keys for a valid profile
REQUIRED_KEYS = ("bet_value_area_1", "target_area_1", "bet_button_area_1")

# Human-readable labels for each area
AREA_LABELS = {
    "bet_value_area_1": "CAMPO VALOR DA APOSTA (R$)",
    "target_area_1": "CAMPO MULTIPLICADOR ALVO (2.00x)",
    "bet_button_area_1": "BOTAO APOSTAR",
}


# =============================================================================
# PROFILE I/O
# =============================================================================

def _load_config() -> dict:
    """Load the full profiles.json config."""
    if not PROFILES_PATH.exists():
        return {}
    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler {PROFILES_PATH}: {e}")
        return {}


def _save_config(config: dict) -> bool:
    """Save the full profiles.json config."""
    try:
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar {PROFILES_PATH}: {e}")
        return False


def load_profiles() -> dict:
    """Return dict of all profiles {name: {areas...}}."""
    config = _load_config()
    return config.get("profiles", {})


def get_profile_names() -> list:
    """Return list of profile names."""
    return list(load_profiles().keys())


def get_profile(name: str) -> Optional[dict]:
    """Return a single profile by name, or None."""
    return load_profiles().get(name)


def validate_profile(profile: dict) -> bool:
    """Check if profile has all 3 required areas with valid coordinates."""
    if not profile:
        return False
    for key in REQUIRED_KEYS:
        area = profile.get(key)
        if not area:
            return False
        if not all(k in area for k in ("x", "y", "width", "height")):
            return False
        if area["width"] <= 0 or area["height"] <= 0:
            return False
    return True


def save_profile(name: str, data: dict) -> bool:
    """Save a profile to profiles.json."""
    config = _load_config()
    if "profiles" not in config:
        config["profiles"] = {}
    config["profiles"][name] = data
    return _save_config(config)


def delete_profile(name: str) -> bool:
    """Delete a profile from profiles.json."""
    config = _load_config()
    profiles = config.get("profiles", {})
    if name in profiles:
        del profiles[name]
        config["profiles"] = profiles
        return _save_config(config)
    return False


# =============================================================================
# TKINTER OVERLAY WIZARD
# =============================================================================

def select_area_visual(title: str) -> Optional[dict]:
    """Open fullscreen Tkinter overlay for area selection.

    Returns {x, y, width, height} or None if cancelled.
    """
    result = {"x": 0, "y": 0, "width": 0, "height": 0}
    start_x, start_y = 0, 0
    rect = [None]

    def on_press(event):
        nonlocal start_x, start_y
        # Coordenadas absolutas da tela
        start_x = event.x_root
        start_y = event.y_root
        if rect[0]:
            canvas.delete(rect[0])
        rect[0] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline='#00FF00', width=3,
        )

    def on_drag(event):
        if rect[0]:
            # Canvas coords para desenho visual
            cx1 = min(
                start_x - root.winfo_rootx(),
                event.x,
            )
            cy1 = min(
                start_y - root.winfo_rooty(),
                event.y,
            )
            cx2 = max(
                start_x - root.winfo_rootx(),
                event.x,
            )
            cy2 = max(
                start_y - root.winfo_rooty(),
                event.y,
            )
            canvas.coords(
                rect[0], cx1, cy1, cx2, cy2,
            )

    def on_release(event):
        # Coordenadas absolutas da tela
        x1 = min(start_x, event.x_root)
        y1 = min(start_y, event.y_root)
        x2 = max(start_x, event.x_root)
        y2 = max(start_y, event.y_root)

        width = x2 - x1
        height = y2 - y1

        if width > 5 and height > 5:
            result["x"] = x1
            result["y"] = y1
            result["width"] = width
            result["height"] = height

        root.quit()
        root.destroy()

    def on_cancel(event):
        result["width"] = 0
        root.quit()
        root.destroy()

    # Forcar DPI awareness para coordenadas corretas
    import os
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.attributes('-topmost', True)
    root.configure(bg='black')

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    canvas = tk.Canvas(
        root, width=screen_w, height=screen_h,
        bg='black', highlightthickness=0, cursor='cross'
    )
    canvas.pack()

    canvas.create_text(
        screen_w // 2, 40,
        text=f">>> {title}",
        font=('Arial', 28, 'bold'), fill='white'
    )
    canvas.create_text(
        screen_w // 2, 80,
        text="CLIQUE e ARRASTE para selecionar a area | ESC = cancelar",
        font=('Arial', 16), fill='yellow'
    )

    canvas.bind('<ButtonPress-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)
    root.bind('<Escape>', on_cancel)

    root.mainloop()

    if result["width"] > 0:
        return result
    return None


def run_calibration_wizard(profile_name: str) -> Optional[dict]:
    """Run the full 3-step calibration wizard.

    Args:
        profile_name: Name to save the profile as.

    Returns:
        The profile dict if successful, None if cancelled.
    """
    items = [
        ("bet_value_area_1", AREA_LABELS["bet_value_area_1"]),
        ("target_area_1", AREA_LABELS["target_area_1"]),
        ("bet_button_area_1", AREA_LABELS["bet_button_area_1"]),
    ]

    profile = {}
    for key, label in items:
        area = select_area_visual(label)
        if not area:
            logger.info("Calibracao cancelada pelo usuario")
            return None
        profile[key] = area

    if save_profile(profile_name, profile):
        logger.info(f"Perfil '{profile_name}' salvo com sucesso")
        return profile

    return None
