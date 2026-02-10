"""
Router: WebSocket
Endpoints WebSocket para dados em tempo real.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Licenca, LogBot
from app.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


# ============================================================================
# FUNÇÕES AUXILIARES - CALCULAR MÉTRICAS
# ============================================================================


async def get_dashboard_metrics(db: AsyncSession) -> dict:
    """
    Calcula métricas do dashboard.

    Args:
        db: Sessão do banco de dados

    Returns:
        dict: Métricas calculadas
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ----- RECEITA -----
    # Receita hoje (soma de lucros de hoje)
    result = await db.execute(
        select(func.sum(LogBot.lucro))
        .where(LogBot.timestamp >= today_start)
    )
    revenue_today = result.scalar() or 0.0

    # Receita total
    result = await db.execute(select(func.sum(LogBot.lucro)))
    revenue_total = result.scalar() or 0.0

    # ----- LICENÇAS -----
    # Total de licenças
    result = await db.execute(select(func.count(Licenca.id)))
    total_licenses = result.scalar() or 0

    # Licenças ativas
    result = await db.execute(
        select(func.count(Licenca.id)).where(Licenca.ativa == True)
    )
    active_licenses = result.scalar() or 0

    # Licenças expirando em 3 dias
    expiring_date = now + timedelta(days=3)
    result = await db.execute(
        select(func.count(Licenca.id))
        .where(Licenca.ativa == True)
        .where(Licenca.data_expiracao <= expiring_date)
        .where(Licenca.data_expiracao > now)
    )
    expiring_licenses = result.scalar() or 0

    # ----- BOTS -----
    # Bots online (enviaram telemetria nos últimos 5 minutos)
    five_minutes_ago = now - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(func.distinct(LogBot.hwid)))
        .where(LogBot.timestamp >= five_minutes_ago)
    )
    bots_online = result.scalar() or 0

    # ----- APOSTAS -----
    # Total de apostas hoje
    result = await db.execute(
        select(func.count(LogBot.id))
        .where(LogBot.timestamp >= today_start)
        .where(LogBot.tipo == "bet")
    )
    bets_today = result.scalar() or 0

    # ----- MONTAR RESPOSTA -----
    return {
        "timestamp": now.isoformat(),
        "revenue": {
            "today": round(revenue_today, 2),
            "total": round(revenue_total, 2),
        },
        "licenses": {
            "total": total_licenses,
            "active": active_licenses,
            "expiring_soon": expiring_licenses,
        },
        "bots": {
            "online": bots_online,
            "total": active_licenses,  # Total = licenças ativas
        },
        "bets": {
            "today": bets_today,
        },
    }


# ============================================================================
# ENDPOINT: WEBSOCKET DASHBOARD ADMIN
# ============================================================================


@router.websocket("/dashboard/admin")
async def websocket_dashboard_admin(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket para dashboard admin.
    
    Envia métricas em tempo real a cada 2 segundos.
    
    Uso:
        const ws = new WebSocket("ws://localhost:8000/ws/dashboard/admin");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
    """
    # Conectar
    await manager.connect(websocket, "dashboard_admin")

    try:
        while True:
            # Calcular métricas
            metrics = await get_dashboard_metrics(db)

            # Enviar para este cliente
            await manager.send_personal_message(metrics, websocket)

            # Aguardar 2 segundos
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "dashboard_admin")
        print("🔌 Cliente desconectado do dashboard admin")
    except Exception as e:
        print(f"❌ Erro no WebSocket: {e}")
        manager.disconnect(websocket, "dashboard_admin")


# ============================================================================
# ENDPOINT: WEBSOCKET BOT STATUS (por HWID)
# ============================================================================


@router.websocket("/bot/{hwid}")
async def websocket_bot_status(
    websocket: WebSocket,
    hwid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket para status de um bot específico.
    
    Envia dados do bot em tempo real.
    
    Args:
        hwid: Hardware ID do bot
    """
    room = f"bot_{hwid}"
    await manager.connect(websocket, room)

    try:
        while True:
            # Buscar licença do bot
            result = await db.execute(
                select(Licenca).where(Licenca.hwid == hwid)
            )
            licenca = result.scalar_one_or_none()

            if not licenca:
                await manager.send_personal_message(
                    {"error": "Licença não encontrada"},
                    websocket,
                )
                await asyncio.sleep(5)
                continue

            # Verificar se bot está online (telemetria recente)
            five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            result = await db.execute(
                select(LogBot)
                .where(LogBot.hwid == hwid)
                .where(LogBot.timestamp >= five_minutes_ago)
                .order_by(LogBot.timestamp.desc())
                .limit(1)
            )
            last_activity = result.scalar_one_or_none()

            is_online = last_activity is not None

            # Calcular lucro do bot
            result = await db.execute(
                select(func.sum(LogBot.lucro)).where(LogBot.hwid == hwid)
            )
            total_profit = result.scalar() or 0.0

            # Contar apostas
            result = await db.execute(
                select(func.count(LogBot.id))
                .where(LogBot.hwid == hwid)
                .where(LogBot.tipo == "bet")
            )
            total_bets = result.scalar() or 0

            # Enviar status
            status = {
                "hwid": hwid,
                "online": is_online,
                "license": {
                    "active": licenca.ativa,
                    "expires_at": (
                        licenca.data_expiracao.isoformat()
                        if licenca.data_expiracao
                        else None
                    ),
                    "days_left": licenca.dias_restantes,
                },
                "stats": {
                    "total_profit": round(total_profit, 2),
                    "total_bets": total_bets,
                },
                "last_activity": (
                    last_activity.timestamp.isoformat() if last_activity else None
                ),
            }

            await manager.send_personal_message(status, websocket)

            # Aguardar 3 segundos
            await asyncio.sleep(3)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        print(f"🔌 Cliente desconectado do bot {hwid}")
    except Exception as e:
        print(f"❌ Erro no WebSocket bot {hwid}: {e}")
        manager.disconnect(websocket, room)
