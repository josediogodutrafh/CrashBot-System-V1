"""
Configuração global do pytest para CrashBot System.

Este arquivo é automaticamente carregado pelo pytest e contém
fixtures compartilhadas por todos os testes.
"""

import sys
from pathlib import Path

import pytest

# Adiciona diretórios ao PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
BOT_ROOT = PROJECT_ROOT / "CrashBot-System-V1"
sys.path.insert(0, str(BOT_ROOT / "CrashBot"))
sys.path.insert(0, str(BOT_ROOT / "Crash"))
sys.path.insert(0, str(PROJECT_ROOT / "crashbot-platform" / "api"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# ============================================
# FIXTURES GLOBAIS
# ============================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Retorna o diretório raiz do projeto."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def crashbot_dir(project_root: Path) -> Path:
    """Retorna o diretório do CrashBot v3.0."""
    return project_root / "CrashBot-System-V1" / "CrashBot"


@pytest.fixture(scope="session")
def crash_dir(project_root: Path) -> Path:
    """Retorna o diretório do Crash v2.0."""
    return project_root / "CrashBot-System-V1" / "Crash"


@pytest.fixture(scope="session")
def api_dir(project_root: Path) -> Path:
    """Retorna o diretório da API."""
    return project_root / "crashbot-platform" / "api"


@pytest.fixture
def sample_config() -> dict:
    """Configuração de exemplo para testes."""
    return {
        "version": "3.0.0",
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
        "telemetry": {
            "enabled": False,  # Desabilitado em testes
            "api_url": "http://localhost:8000",
        },
    }


@pytest.fixture
def mock_explosion_history() -> list[float]:
    """Histórico de explosões simulado para testes."""
    return [
        1.23,
        1.45,
        1.67,
        1.89,
        2.10,
        1.34,
        1.56,
        1.78,
        1.90,
        2.50,
        1.20,
        1.40,
        1.60,
        1.80,
        2.00,
    ]


# ============================================
# HOOKS DO PYTEST
# ============================================


def pytest_configure(config):
    """Configuração executada antes dos testes."""
    # Adiciona markers customizados
    config.addinivalue_line("markers", "slow: marca testes lentos")
    config.addinivalue_line("markers", "integration: testes de integração")
    config.addinivalue_line("markers", "unit: testes unitários")
    config.addinivalue_line("markers", "ml: testes relacionados a ML")
    config.addinivalue_line("markers", "vision: testes de visão computacional")
    config.addinivalue_line("markers", "api: testes de API")


def pytest_collection_modifyitems(config, items):
    """Modifica a coleção de testes antes de executar."""
    # Adiciona marker 'slow' automaticamente para testes ML
    for item in items:
        if "ml" in item.keywords or "vision" in item.keywords:
            item.add_marker(pytest.mark.slow)


# ============================================
# FIXTURES PARA MOCKING
# ============================================


@pytest.fixture
def mock_screen_capture(monkeypatch):
    """Mock para captura de tela."""
    import numpy as np

    def fake_capture(*args, **kwargs):
        # Retorna imagem fake 100x100 RGB
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # Aqui você pode usar monkeypatch para mockar mss ou opencv
    return fake_capture


@pytest.fixture
def mock_database(tmp_path):
    """Cria um banco de dados SQLite temporário para testes."""
    db_path = tmp_path / "test_crashbot.db"
    return str(db_path)


@pytest.fixture
def mock_api_client():
    """Mock para cliente da API."""

    class MockAPIClient:
        async def validate_license(self, key: str) -> dict:
            return {"valid": True, "expires_at": "2026-12-31"}

        async def send_telemetry(self, data: dict) -> bool:
            return True

    return MockAPIClient()


# ============================================
# FIXTURES PARA ASYNC
# ============================================


@pytest.fixture
def event_loop():
    """Cria um event loop para testes assíncronos."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================
# CONFIGURAÇÃO DE LOGGING PARA TESTES
# ============================================


@pytest.fixture(autouse=True)
def configure_test_logging():
    """Configura logging para testes (executa automaticamente)."""
    import logging

    # Reduz verbosidade durante testes
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s - %(name)s - %(message)s"
    )
    yield
    # Cleanup após teste
    logging.shutdown()
