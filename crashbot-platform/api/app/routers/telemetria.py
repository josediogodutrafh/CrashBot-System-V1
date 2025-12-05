"""
Router: Telemetria
Endpoints para telemetria avançada do bot.
Refatorado para conformidade com PEP8, Type Safety e Performance.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Licenca, LogBot, Usuario
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_

router = APIRouter(prefix="/api/v1/telemetria", tags=["telemetria"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _calcular_data_inicio(periodo: str) -> Optional[datetime]:
    """Calcula a data de início baseada no período usando dicionário (O(1))."""
    agora = datetime.now(timezone.utc)
    offsets = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = offsets.get(periodo)
    return agora - delta if delta else None


def _get_base_filters(
    data_inicio: Optional[datetime], hwid: Optional[str] = None
) -> List[Any]:
    """
    Retorna uma lista de filtros para ser desempacotada no where.
    """
    filters = []
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)
    if hwid:
        filters.append(LogBot.hwid == hwid)
    return filters


# ============================================================================
# ENDPOINT: DASHBOARD GERAL (Admin)
# ============================================================================


@router.get("/dashboard")
async def dashboard_telemetria(
    periodo: str = Query("7d", description="Período: 24h, 7d, 30d, all"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Dashboard geral de telemetria com métricas agregadas.
    """
    data_inicio = _calcular_data_inicio(periodo)
    filters = _get_base_filters(data_inicio)
    agora = datetime.now(timezone.utc)

    # 1. Estatísticas gerais
    stats_query = select(
        func.count(LogBot.id).label("total_logs"),
        func.count(func.distinct(LogBot.hwid)).label("bots_unicos"),
        func.count(func.distinct(LogBot.sessao_id)).label("sessoes"),
        func.sum(case((LogBot.tipo == "Round", LogBot.lucro), else_=0)).label(
            "lucro_total"
        ),
        func.sum(case((LogBot.tipo == "Round", 1), else_=0)).label("total_rounds"),
    )

    if filters:
        stats_query = stats_query.where(and_(*filters))

    stats_result = await db.execute(stats_query)
    stats = stats_result.first()

    # 2. Contagem por tipo
    tipos_query = select(LogBot.tipo, func.count(LogBot.id).label("quantidade"))
    if filters:
        tipos_query = tipos_query.where(and_(*filters))

    tipos_query = tipos_query.group_by(LogBot.tipo)

    tipos_result = await db.execute(tipos_query)
    tipos = {row.tipo: row.quantidade for row in tipos_result}

    # 3. Atividade por hora (últimas 24h)
    hora_corte = agora - timedelta(hours=24)
    hora_truncada = func.date_trunc("hour", LogBot.timestamp)
    atividade_query = (
        select(
            hora_truncada.label("hora"),
            func.count(LogBot.id).label("quantidade"),
        )
        .where(LogBot.timestamp >= hora_corte)
        .group_by(hora_truncada)
        .order_by(hora_truncada)
    )
    atividade_result = await db.execute(atividade_query)
    atividade_por_hora = [
        {
            "hora": row.hora.isoformat() if row.hora else None,
            "quantidade": row.quantidade,
        }
        for row in atividade_result
    ]

    # 4. Top 5 licenças por lucro
    top_licencas = await _get_top_licencas(db, filters)

    # 5. Bots ativos agora (última atividade < 5 min)
    bots_ativos_query = select(func.count(func.distinct(LogBot.hwid))).where(
        LogBot.timestamp >= agora - timedelta(minutes=5)
    )
    bots_ativos_result = await db.execute(bots_ativos_query)
    bots_ativos = bots_ativos_result.scalar() or 0

    return {
        "periodo": periodo,
        "resumo": {
            "total_logs": stats.total_logs if stats and stats.total_logs else 0,
            "bots_unicos": stats.bots_unicos if stats and stats.bots_unicos else 0,
            "sessoes": stats.sessoes if stats and stats.sessoes else 0,
            "lucro_total": (
                float(stats.lucro_total) if stats and stats.lucro_total else 0.0
            ),
            "total_rounds": stats.total_rounds if stats and stats.total_rounds else 0,
            "bots_ativos_agora": bots_ativos,
        },
        "por_tipo": tipos,
        "atividade_por_hora": atividade_por_hora,
        "top_licencas": top_licencas,
    }


async def _get_top_licencas(
    db: AsyncSession, base_filters: List[Any]
) -> List[Dict[str, Any]]:
    """Helper para buscar top licenças."""
    filters = base_filters.copy()
    filters.append(LogBot.tipo == "Round")

    top_licencas_query = (
        select(
            LogBot.hwid,
            func.sum(LogBot.lucro).label("lucro_total"),
            func.count(LogBot.id).label("total_rounds"),
        )
        .where(and_(*filters))
        .group_by(LogBot.hwid)
        .order_by(func.sum(LogBot.lucro).desc())
        .limit(5)
    )
    top_result = await db.execute(top_licencas_query)

    top_licencas = []
    for row in top_result:
        if row.hwid:
            licenca_query = select(Licenca.cliente_nome).where(Licenca.hwid == row.hwid)
            licenca_result = await db.execute(licenca_query)
            cliente_nome = licenca_result.scalar_one_or_none() or "Desconhecido"
        else:
            cliente_nome = "Desconhecido"

        top_licencas.append(
            {
                "hwid": f"{row.hwid[:12]}..." if row.hwid else "N/A",
                "cliente": cliente_nome,
                "lucro_total": float(row.lucro_total) if row.lucro_total else 0,
                "total_rounds": row.total_rounds,
            }
        )
    return top_licencas


# ============================================================================
# ENDPOINT: ESTATÍSTICAS POR LICENÇA (Admin)
# ============================================================================


@router.get("/licenca/{licenca_id}")
async def estatisticas_licenca(
    licenca_id: int,
    periodo: str = Query("7d", description="Período: 24h, 7d, 30d, all"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Estatísticas detalhadas de uma licença específica.
    """
    licenca_result = await db.execute(select(Licenca).where(Licenca.id == licenca_id))
    licenca = licenca_result.scalar_one_or_none()

    if not licenca:
        return {"error": "Licença não encontrada"}

    # Fix Pylance: Verificação explícita de None
    if licenca.hwid is None:
        return {
            "licenca": licenca.to_dict(),
            "estatisticas": None,
            "mensagem": "Licença ainda não foi ativada (sem HWID)",
        }

    # Fix Pylance: Cast explícito de Column[str] para str
    # Isso garante ao analisador estático que estamos lidando com o valor da string
    hwid: str = cast(str, licenca.hwid)

    data_inicio = _calcular_data_inicio(periodo)
    filters = _get_base_filters(data_inicio, hwid)

    # 1. Estatísticas gerais
    stats_query = select(
        func.count(LogBot.id).label("total_logs"),
        func.count(func.distinct(LogBot.sessao_id)).label("total_sessoes"),
        func.sum(case((LogBot.tipo == "Round", LogBot.lucro), else_=0)).label(
            "lucro_total"
        ),
        func.sum(case((LogBot.tipo == "Round", 1), else_=0)).label("total_rounds"),
        func.min(LogBot.timestamp).label("primeira_atividade"),
        func.max(LogBot.timestamp).label("ultima_atividade"),
    ).where(and_(*filters))

    stats_result = await db.execute(stats_query)
    stats = stats_result.first()

    total_rounds = stats.total_rounds if stats and stats.total_rounds else 0
    lucro_total = float(stats.lucro_total) if stats and stats.lucro_total else 0.0

    # 2. Win Rate
    wins, win_rate = await _calcular_win_rate(db, hwid, data_inicio, total_rounds)

    # 3. Histórico diário
    historico_diario = await _get_historico_diario(db, hwid, data_inicio)

    # 4. Últimas sessões
    sessoes = await _get_ultimas_sessoes(db, hwid, data_inicio)

    primeira_atv = (
        stats.primeira_atividade.isoformat()
        if stats and stats.primeira_atividade
        else None
    )
    ultima_atv = (
        stats.ultima_atividade.isoformat() if stats and stats.ultima_atividade else None
    )

    return {
        "licenca": licenca.to_dict(),
        "periodo": periodo,
        "estatisticas": {
            "total_logs": stats.total_logs if stats and stats.total_logs else 0,
            "total_sessoes": (
                stats.total_sessoes if stats and stats.total_sessoes else 0
            ),
            "total_rounds": total_rounds,
            "lucro_total": lucro_total,
            "vitorias": wins,
            "derrotas": total_rounds - wins,
            "win_rate": round(win_rate, 2),
            "primeira_atividade": primeira_atv,
            "ultima_atividade": ultima_atv,
        },
        "historico_diario": historico_diario,
        "ultimas_sessoes": sessoes,
    }


async def _calcular_win_rate(
    db, hwid: str, data_inicio: Optional[datetime], total_rounds: int
):
    """Helper para calcular taxa de vitória."""
    if total_rounds <= 0:
        return 0, 0.0

    filters = _get_base_filters(data_inicio, hwid)
    filters.append(LogBot.tipo == "Round")
    filters.append(LogBot.lucro > 0)

    wins_query = select(func.count(LogBot.id)).where(and_(*filters))

    wins_result = await db.execute(wins_query)
    wins = wins_result.scalar() or 0
    win_rate = (wins / total_rounds) * 100
    return wins, win_rate


async def _get_historico_diario(db, hwid: str, data_inicio: Optional[datetime]):
    """Helper para histórico diário."""
    filters = _get_base_filters(data_inicio, hwid)
    filters.append(LogBot.tipo == "Round")

    dia_truncado = func.date_trunc("day", LogBot.timestamp)
    historico_query = (
        select(
            dia_truncado.label("dia"),
            func.sum(LogBot.lucro).label("lucro"),
            func.count(LogBot.id).label("rounds"),
        )
        .where(LogBot.timestamp >= data_inicio)
        .where(LogBot.hwid == licenca.hwid)
        .where(LogBot.tipo == "Round")
        .group_by(dia_truncado)
        .order_by(dia_truncado)
    )
    historico_result = await db.execute(historico_query)
    return [
        {
            "dia": row.dia.strftime("%d/%m") if row.dia else None,
            "lucro": float(row.lucro) if row.lucro else 0,
            "rounds": row.rounds,
        }
        for row in historico_result
    ]


async def _get_ultimas_sessoes(db, hwid: str, data_inicio: Optional[datetime]):
    """Helper para últimas sessões."""
    filters = _get_base_filters(data_inicio, hwid)

    sessoes_query = (
        select(
            LogBot.sessao_id,
            func.min(LogBot.timestamp).label("inicio"),
            func.max(LogBot.timestamp).label("fim"),
            func.sum(LogBot.lucro).label("lucro"),
            func.count(LogBot.id).label("eventos"),
        )
        .where(and_(*filters))
        .group_by(LogBot.sessao_id)
        .order_by(func.max(LogBot.timestamp).desc())
        .limit(10)
    )
    sessoes_result = await db.execute(sessoes_query)

    return [
        {
            "sessao_id": row.sessao_id,
            "inicio": row.inicio.isoformat() if row.inicio else None,
            "fim": row.fim.isoformat() if row.fim else None,
            "duracao_minutos": (
                int((row.fim - row.inicio).total_seconds() / 60)
                if row.inicio and row.fim
                else 0
            ),
            "lucro": float(row.lucro) if row.lucro else 0,
            "eventos": row.eventos,
        }
        for row in sessoes_result
    ]


# ============================================================================
# ENDPOINT: LISTAR LICENÇAS COM ESTATÍSTICAS (Admin)
# ============================================================================


@router.get("/licencas-stats")
async def licencas_com_estatisticas(
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Lista todas as licenças com suas estatísticas de telemetria.
    """
    query = (
        select(
            Licenca,
            func.count(case((LogBot.tipo == "Round", 1))).label("total_rounds"),
            func.sum(case((LogBot.tipo == "Round", LogBot.lucro), else_=0)).label(
                "lucro_total"
            ),
            func.max(LogBot.timestamp).label("ultima_atividade"),
        )
        .outerjoin(LogBot, and_(Licenca.hwid == LogBot.hwid, Licenca.hwid.is_not(None)))
        .where(Licenca.ativa.is_(True))
        .group_by(Licenca.id)
        .order_by(Licenca.id.desc())
    )

    result = await db.execute(query)

    resultado = []
    agora = datetime.now(timezone.utc)

    for row in result:
        licenca, total_rounds, lucro_total, ultima_atividade = row

        # Determinar status
        status_bot = "nunca_usado"
        if ultima_atividade:
            last_act = cast(datetime, ultima_atividade)
            if last_act.tzinfo is None:
                last_act = last_act.replace(tzinfo=timezone.utc)

            minutos_inativo = (agora - last_act).total_seconds() / 60

            if minutos_inativo < 5:
                status_bot = "online"
            elif minutos_inativo < 60:
                status_bot = "recente"
            elif minutos_inativo < 1440:  # 24h
                status_bot = "hoje"
            else:
                status_bot = "inativo"
        elif licenca.hwid is not None:
            status_bot = "inativo"

        stats = {
            "total_rounds": total_rounds or 0,
            "lucro_total": float(lucro_total) if lucro_total else 0.0,
            "ultima_atividade": (
                ultima_atividade.isoformat() if ultima_atividade else None
            ),
            "status_bot": status_bot,
        }

        resultado.append({"licenca": licenca.to_dict(), "telemetria": stats})

    return resultado


# ============================================================================
# ENDPOINT: EXPORTAR DADOS (Admin)
# ============================================================================


@router.get("/exportar")
async def exportar_telemetria(
    formato: str = Query("json", description="Formato: json ou csv"),
    licenca_id: Optional[int] = None,
    periodo: str = Query("7d", description="Período: 24h, 7d, 30d, all"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Exporta dados de telemetria.
    """
    data_inicio = _calcular_data_inicio(periodo)
    filters = _get_base_filters(data_inicio)

    if licenca_id:
        licenca_result = await db.execute(
            select(Licenca).where(Licenca.id == licenca_id)
        )
        licenca = licenca_result.scalar_one_or_none()
        if licenca and licenca.hwid is not None:
            filters.append(LogBot.hwid == licenca.hwid)

    query = select(LogBot).order_by(LogBot.timestamp.desc())
    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query.limit(10000))
    logs = result.scalars().all()

    dados = [log.to_dict() for log in logs]

    if formato == "csv":
        output = io.StringIO()
        if dados:
            writer = csv.DictWriter(output, fieldnames=dados[0].keys())
            writer.writeheader()
            writer.writerows(dados)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=telemetria.csv"},
        )

    return {"formato": "json", "dados": dados, "total_registros": len(dados)}
