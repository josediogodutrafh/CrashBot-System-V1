"""
Config Panel - Initial bot configuration form (Flet).
Includes license validation before allowing bot start.
"""

import threading

import flet as ft

from src.gui.theme import (
    BG_CARD, BG_INPUT, NEON_GREEN, NEON_BLUE, NEON_RED, NEON_YELLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title, neon_button,
)
from src.security.license import load_saved_key, validate_license

# Setup options (internal names that match setups.py)
SETUP_INTERNAL = [
    "1/2", "1/2 + 1/2", "1/2 + 1/2 + 1/2",
    "1/2/4", "1/2/4 + 1/2/4", "1/2/4/8", "1/2/4/8/16",
]

SETUP_DISPLAY = [
    "Conservador (1/2)",
    "Moderado (1/2 + 1/2)",
    "Agressivo (1/2 + 1/2 + 1/2)",
    "Turbo (1/2/4)",
    "Turbo Duplo (1/2/4 + 1/2/4)",
    "Ultra (1/2/4/8)",
    "Maximo (1/2/4/8/16)",
]

GAIN_ACTIONS = ["encerrar", "suspender", "reinvestir"]
LOSS_ACTIONS = ["encerrar", "suspender"]

# Module-level state
_on_start_callback = None
_config_container = None
_license_validated = False

# Form fields
_field_license = None
_field_caixa = None
_field_banca = None
_dropdown_setup = None
_slider_meta = None
_slider_stoploss = None
_field_hours = None
_dropdown_gain = None
_field_gain_hours = None
_field_gain_reinvest = None
_dropdown_loss = None
_field_loss_hours = None
_check_premium = None
_txt_status = None
_txt_meta_val = None
_txt_sl_val = None
_txt_license_status = None
_txt_license_days = None
_btn_start = None
_btn_validate = None
_progress_license = None


def set_on_start(callback):
    """Set the callback for when user clicks start."""
    global _on_start_callback
    _on_start_callback = callback


def create() -> ft.Container:
    """Create the config form view."""
    global _config_container, _license_validated
    global _field_license, _field_caixa, _field_banca, _dropdown_setup
    global _slider_meta, _slider_stoploss, _field_hours
    global _dropdown_gain, _field_gain_hours, _field_gain_reinvest
    global _dropdown_loss, _field_loss_hours, _check_premium
    global _txt_status, _txt_meta_val, _txt_sl_val
    global _txt_license_status, _txt_license_days
    global _btn_start, _btn_validate, _progress_license

    _license_validated = False

    # License field - pre-fill with saved key
    saved_key = load_saved_key()
    _field_license = ft.TextField(
        label="Chave de Licenca", value=saved_key,
        hint_text="XXXX-XXXX-XXXX-XXXX",
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_YELLOW, focused_border_color=NEON_YELLOW,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        prefix_icon=ft.Icons.VPN_KEY,
        width=310,
    )
    _txt_license_status = ft.Text("", size=12, color=TEXT_SECONDARY)
    _txt_license_days = ft.Text("", size=11, color=TEXT_DIM)
    _progress_license = ft.ProgressRing(
        width=16, height=16, stroke_width=2,
        color=NEON_BLUE, visible=False,
    )
    _btn_validate = neon_button(
        "VALIDAR",
        icon=ft.Icons.VERIFIED_USER,
        color=NEON_YELLOW,
        on_click=_on_validate_click,
        width=120,
        height=42,
    )

    # Form fields
    _field_caixa = ft.TextField(
        label="Caixa (R$)", value="500",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=200,
    )
    _field_banca = ft.TextField(
        label="Banca (R$)", value="100",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=200,
    )
    _dropdown_setup = ft.Dropdown(
        label="Setup",
        options=[ft.dropdown.Option(key=internal, text=display)
                 for internal, display in zip(SETUP_INTERNAL, SETUP_DISPLAY)],
        value="1/2 + 1/2",
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=420,
    )

    _txt_meta_val = ft.Text("= R$ 100.00", size=12, color=TEXT_SECONDARY)
    _slider_meta = ft.Slider(
        min=5, max=100, value=20, divisions=19,
        label="{value}%", active_color=NEON_GREEN,
        on_change=_on_meta_change,
    )
    _txt_sl_val = ft.Text("= R$ 500.00", size=12, color=TEXT_SECONDARY)
    _slider_stoploss = ft.Slider(
        min=10, max=100, value=100, divisions=18,
        label="{value}%", active_color=NEON_BLUE,
        on_change=_on_sl_change,
    )
    _field_hours = ft.TextField(
        label="Horas de Sessao (0 = infinito)", value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=250,
    )

    _dropdown_gain = ft.Dropdown(
        label="Acao ao Atingir Meta",
        options=[ft.dropdown.Option(a) for a in GAIN_ACTIONS],
        value="encerrar",
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=200,
    )
    _field_gain_hours = ft.TextField(
        label="Suspender (horas)", value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=140,
    )
    _field_gain_reinvest = ft.TextField(
        label="Reinvestir (%)", value="50",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=140,
    )

    _dropdown_loss = ft.Dropdown(
        label="Acao ao Atingir Stop Loss",
        options=[ft.dropdown.Option(a) for a in LOSS_ACTIONS],
        value="encerrar",
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=200,
    )
    _field_loss_hours = ft.TextField(
        label="Suspender (horas)", value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=BG_INPUT, color=TEXT_PRIMARY,
        border_color=NEON_BLUE, focused_border_color=NEON_BLUE,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        width=140,
    )

    _check_premium = ft.Checkbox(
        label="Operar apenas em horarios Premium",
        value=False,
        check_color="white", active_color=NEON_GREEN,
        label_style=ft.TextStyle(color=TEXT_PRIMARY),
    )

    _txt_status = ft.Text("", size=14, color=NEON_GREEN)

    # Start button - disabled until license validated
    _btn_start = neon_button(
        "INICIAR BOT",
        icon=ft.Icons.PLAY_ARROW,
        color=NEON_GREEN,
        on_click=_on_start_click,
        width=280,
        height=50,
    )
    _btn_start.disabled = True

    # Build form layout
    form = ft.Column([
        # Title
        ft.Row([
            ft.Icon(ft.Icons.ROCKET_LAUNCH, size=32, color=NEON_GREEN),
            ft.Text("CRASHBOT", size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text("v3.1", size=14, color=TEXT_DIM),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),

        ft.Divider(color=TEXT_DIM, height=30),

        # License (FIRST - required)
        section_title("LICENCA", ft.Icons.VPN_KEY),
        ft.Row([
            _field_license,
            _btn_validate,
            _progress_license,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        _txt_license_status,
        _txt_license_days,

        ft.Divider(color=TEXT_DIM, height=20),

        # Financial
        section_title("FINANCEIRO", ft.Icons.ACCOUNT_BALANCE_WALLET),
        ft.Row([_field_caixa, _field_banca], spacing=20),

        ft.Divider(color=TEXT_DIM, height=20),

        # Strategy
        section_title("ESTRATEGIA", ft.Icons.PSYCHOLOGY),
        _dropdown_setup,

        ft.Divider(color=TEXT_DIM, height=20),

        # Stop Gain
        section_title("STOP GAIN", ft.Icons.TRENDING_UP),
        ft.Row([
            ft.Text("Meta:", size=13, color=TEXT_SECONDARY, width=60),
            ft.Container(_slider_meta, expand=True),
            _txt_meta_val,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        # Stop Loss
        section_title("STOP LOSS", ft.Icons.TRENDING_DOWN),
        ft.Row([
            ft.Text("Limite:", size=13, color=TEXT_SECONDARY, width=60),
            ft.Container(_slider_stoploss, expand=True),
            _txt_sl_val,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        ft.Divider(color=TEXT_DIM, height=20),

        # Session
        section_title("SESSAO", ft.Icons.TIMER),
        _field_hours,

        ft.Divider(color=TEXT_DIM, height=20),

        # Actions
        section_title("ACOES", ft.Icons.SETTINGS),
        ft.Row([_dropdown_gain, _field_gain_hours, _field_gain_reinvest], spacing=12),
        ft.Row([_dropdown_loss, _field_loss_hours], spacing=12),

        ft.Divider(color=TEXT_DIM, height=20),

        # Premium
        _check_premium,

        ft.Divider(color=TEXT_DIM, height=20),

        # Start button
        ft.Row([_btn_start], alignment=ft.MainAxisAlignment.CENTER),

        _txt_status,
    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
       scroll=ft.ScrollMode.AUTO)

    _config_container = card_container(form, width=500, padding=30)

    return ft.Row(
        [_config_container],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=True,
    )


def hide(page: ft.Page):
    """Hide the config view."""
    if _config_container and _config_container.parent:
        # Remove the wrapping Row
        parent = _config_container.parent
        page.controls.remove(parent)


def set_status(text: str):
    """Update the status text."""
    if _txt_status:
        _txt_status.value = text


def get_config() -> dict:
    """Read all form fields and return config dict."""
    caixa = float(_field_caixa.value or 500)
    banca = float(_field_banca.value or 100)
    meta_pct = float(_slider_meta.value or 20)
    sl_pct = float(_slider_stoploss.value or 100)

    return {
        "caixa": caixa,
        "banca": banca,
        "setup_name": _dropdown_setup.value or "1/2 + 1/2",
        "stop_gain_pct": meta_pct,
        "stop_loss_pct": sl_pct,
        "session_hours": float(_field_hours.value or 0),
        "gain_action": _dropdown_gain.value or "encerrar",
        "gain_suspend_hours": float(_field_gain_hours.value or 1),
        "gain_reinvest_pct": float(_field_gain_reinvest.value or 50),
        "loss_action": _dropdown_loss.value or "encerrar",
        "loss_suspend_hours": float(_field_loss_hours.value or 1),
        "premium_only": _check_premium.value or False,
    }


# =============================================================================
# LICENSE VALIDATION
# =============================================================================

def _on_validate_click(e):
    """Handle validate license button click."""
    chave = (_field_license.value or "").strip()
    if not chave:
        _set_license_error("Insira sua chave de licenca.")
        return

    # Show loading state
    _btn_validate.disabled = True
    _progress_license.visible = True
    _txt_license_status.value = "Validando..."
    _txt_license_status.color = TEXT_SECONDARY
    _txt_license_days.value = ""
    _safe_update()

    # Validate in background thread to not freeze UI
    def _do_validate():
        result = validate_license(chave)
        # Schedule UI update back on main thread
        if _field_license and _field_license.page:
            _field_license.page.run_task(lambda: _handle_validation_result(result))

    threading.Thread(target=_do_validate, daemon=True).start()


async def _handle_validation_result(result: dict):
    """Process validation result on UI thread."""
    global _license_validated

    _btn_validate.disabled = False
    _progress_license.visible = False

    if result.get("sucesso"):
        _license_validated = True
        _field_license.border_color = NEON_GREEN
        _txt_license_status.value = "Licenca valida!"
        _txt_license_status.color = NEON_GREEN

        dias = result.get("dias_restantes")
        if dias is not None:
            if dias <= 3:
                _txt_license_days.value = f"Expira em {dias} dia(s) - Renove!"
                _txt_license_days.color = NEON_RED
            elif dias <= 7:
                _txt_license_days.value = f"Expira em {dias} dias"
                _txt_license_days.color = NEON_YELLOW
            else:
                _txt_license_days.value = f"{dias} dias restantes"
                _txt_license_days.color = NEON_GREEN
        else:
            _txt_license_days.value = "Licenca vitalicia"
            _txt_license_days.color = NEON_GREEN

        # Enable start button
        _btn_start.disabled = False
    else:
        _license_validated = False
        _set_license_error(result.get("mensagem", "Licenca invalida."))
        _btn_start.disabled = True

    _safe_update()


def _set_license_error(msg: str):
    """Display license error message."""
    _field_license.border_color = NEON_RED
    _txt_license_status.value = msg
    _txt_license_status.color = NEON_RED
    _txt_license_days.value = ""
    _btn_validate.disabled = False
    _progress_license.visible = False
    _safe_update()


def _safe_update():
    """Safely trigger page update."""
    try:
        if _field_license and _field_license.page:
            _field_license.page.update()
    except Exception:
        pass


# =============================================================================
# START + SLIDER CALLBACKS
# =============================================================================

def _on_start_click(e):
    """Handle start button click - only works if license is validated."""
    if not _license_validated:
        _set_license_error("Valide sua licenca antes de iniciar.")
        return

    if _on_start_callback:
        cfg = get_config()
        set_status("Iniciando bot...")
        _on_start_callback(cfg)


def _on_meta_change(e):
    """Update meta value display."""
    if _txt_meta_val and _field_caixa:
        caixa = float(_field_caixa.value or 500)
        pct = float(_slider_meta.value or 20)
        _txt_meta_val.value = f"= R$ {caixa * pct / 100:.2f}"
        if _txt_meta_val.page:
            _txt_meta_val.page.update()


def _on_sl_change(e):
    """Update stop loss value display."""
    if _txt_sl_val and _field_caixa:
        caixa = float(_field_caixa.value or 500)
        pct = float(_slider_stoploss.value or 100)
        _txt_sl_val.value = f"= R$ {caixa * pct / 100:.2f}"
        if _txt_sl_val.page:
            _txt_sl_val.page.update()


def update(state: dict) -> None:
    """Config panel doesn't need updates during dashboard mode."""
    pass
