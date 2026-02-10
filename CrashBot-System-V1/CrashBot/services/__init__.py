#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SERVICES MODULE

Serviços externos e integrações:
- NotificationService: Telegram + Sons
- LicenseService: Validação de licença
- TelemetryService: Envio de telemetria
- DatabaseService: Persistência de dados

Uso:
    from services import (
        get_notifications,
        get_licensing,
        get_telemetry,
        get_database,
    )

    # Notificações
    notifications = get_notifications()
    notifications.send_telegram("Teste")

    # Licença
    licensing = get_licensing()
    result = licensing.validate("CHAVE", "email@test.com")

    # Telemetria
    telemetry = get_telemetry()
    telemetry.send("event_name", {"data": 123})

    # Database
    db = get_database()
    db.start_session("sess_001", 1000.0, "MODERADO")
"""

# Database
from services.database import (
    BetRecord,
    DatabaseService,
    ExplosionRecord,
    SessionRecord,
    get_database,
    reset_database,
)

# Licensing
from services.licensing import (
    LicenseResult,
    LicenseService,
    LicenseStatus,
    get_hwid,
    get_licensing,
    reset_licensing,
)

# Notifications
from services.notifications import (
    NotificationService,
    SoundType,
    get_notifications,
    reset_notifications,
)

# Telemetry
from services.telemetry import (
    TelemetryPayload,
    TelemetryService,
    get_telemetry,
    reset_telemetry,
)

__all__ = [
    # Notifications
    "NotificationService",
    "SoundType",
    "get_notifications",
    "reset_notifications",
    # Licensing
    "LicenseService",
    "LicenseResult",
    "LicenseStatus",
    "get_licensing",
    "reset_licensing",
    "get_hwid",
    # Telemetry
    "TelemetryService",
    "TelemetryPayload",
    "get_telemetry",
    "reset_telemetry",
    # Database
    "DatabaseService",
    "SessionRecord",
    "BetRecord",
    "ExplosionRecord",
    "get_database",
    "reset_database",
]
