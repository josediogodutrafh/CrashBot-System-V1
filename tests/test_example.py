"""
Testes de exemplo para demonstrar a estrutura de testes.

Execute com:
    pytest tests/test_example.py
    pytest tests/test_example.py -v
    pytest tests/test_example.py -k "test_config"
"""

import pytest


# ============================================
# TESTES UNITÁRIOS
# ============================================


@pytest.mark.unit
def test_sample_config(sample_config):
    """Testa se a configuração de exemplo está válida."""
    assert sample_config["version"] == "3.0.0"
    assert "strategy" in sample_config
    assert "ml" in sample_config
    assert sample_config["strategy"]["threshold"] == 2.0


@pytest.mark.unit
def test_explosion_history(mock_explosion_history):
    """Testa se o histórico de explosões é válido."""
    assert len(mock_explosion_history) == 15
    assert all(isinstance(x, float) for x in mock_explosion_history)
    assert all(x > 0 for x in mock_explosion_history)


@pytest.mark.unit
def test_project_paths(project_root, crashbot_dir, crash_dir, api_dir):
    """Testa se os caminhos do projeto existem."""
    assert project_root.exists()
    assert crashbot_dir.exists()
    assert crash_dir.exists()
    # API pode não existir se não instalada
    # assert api_dir.exists()


# ============================================
# TESTES DE INTEGRAÇÃO
# ============================================


@pytest.mark.integration
def test_database_creation(mock_database):
    """Testa criação de banco de dados temporário."""
    import sqlite3
    from pathlib import Path

    # Cria uma tabela de teste
    conn = sqlite3.connect(mock_database)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            value TEXT
        )
    """
    )
    cursor.execute("INSERT INTO test_table (value) VALUES (?)", ("test",))
    conn.commit()

    # Verifica se foi criado
    cursor.execute("SELECT * FROM test_table")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "test"

    conn.close()
    assert Path(mock_database).exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_api_client(mock_api_client):
    """Testa mock do cliente da API."""
    result = await mock_api_client.validate_license("TEST-KEY-123")
    assert result["valid"] is True
    assert "expires_at" in result

    telemetry_sent = await mock_api_client.send_telemetry({"test": "data"})
    assert telemetry_sent is True


# ============================================
# TESTES PARAMETRIZADOS
# ============================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        (1.0, True),
        (2.0, True),
        (1.5, True),
        (0.0, False),  # Zero não é válido
        (-1.0, False),  # Negativo não é válido
    ],
)
def test_explosion_value_validation(value, expected):
    """Testa validação de valores de explosão."""

    def is_valid_explosion(v: float) -> bool:
        return v > 0

    assert is_valid_explosion(value) == expected


# ============================================
# TESTES LENTOS (ML/VISION)
# ============================================


@pytest.mark.slow
@pytest.mark.ml
def test_ml_placeholder():
    """Placeholder para testes de ML (lentos)."""
    # Simula processamento lento
    import time

    time.sleep(0.1)
    assert True


@pytest.mark.slow
@pytest.mark.vision
def test_vision_placeholder():
    """Placeholder para testes de visão computacional (lentos)."""
    # Simula processamento lento
    import time

    time.sleep(0.1)
    assert True


# ============================================
# TESTES COM FIXTURES CUSTOMIZADAS
# ============================================


@pytest.fixture
def sample_bet_data():
    """Fixture local para dados de aposta."""
    return {
        "amount": 10.0,
        "target": 1.85,
        "timestamp": "2026-02-09T12:00:00",
        "result": "win",
    }


@pytest.mark.unit
def test_bet_data_structure(sample_bet_data):
    """Testa estrutura de dados de aposta."""
    assert "amount" in sample_bet_data
    assert "target" in sample_bet_data
    assert sample_bet_data["amount"] > 0
    assert sample_bet_data["target"] >= 1.0


# ============================================
# TESTES DE EXCEÇÕES
# ============================================


@pytest.mark.unit
def test_division_by_zero():
    """Testa se exceções são levantadas corretamente."""
    with pytest.raises(ZeroDivisionError):
        _ = 1 / 0


@pytest.mark.unit
def test_invalid_config_raises():
    """Testa se configuração inválida levanta exceção."""

    def validate_config(config: dict):
        if "version" not in config:
            raise ValueError("Config must have 'version' field")

    with pytest.raises(ValueError, match="version"):
        validate_config({})


# ============================================
# TESTES SKIP/XFAIL
# ============================================


@pytest.mark.skip(reason="Feature não implementada ainda")
def test_future_feature():
    """Teste para feature futura."""
    assert False


@pytest.mark.xfail(reason="Bug conhecido #123")
def test_known_bug():
    """Teste que falha devido a bug conhecido."""
    assert 1 == 2  # Bug conhecido


# ============================================
# COMANDOS ÚTEIS
# ============================================
"""
# Rodar todos os testes
pytest

# Rodar com verbosidade
pytest -v

# Rodar testes específicos
pytest tests/test_example.py
pytest tests/test_example.py::test_sample_config

# Rodar apenas testes unitários
pytest -m unit

# Rodar excluindo testes lentos
pytest -m "not slow"

# Rodar com coverage
pytest --cov=CrashBot --cov-report=html

# Rodar em paralelo (requer pytest-xdist)
pytest -n auto

# Mostrar print statements
pytest -s

# Parar no primeiro erro
pytest -x

# Mostrar top 10 testes mais lentos
pytest --durations=10
"""
