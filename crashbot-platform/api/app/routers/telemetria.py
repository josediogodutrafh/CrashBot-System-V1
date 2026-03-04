"""
Router: Telemetria V3
Dashboard completo com 4 abas: Negócio, Operação, Clientes, Logs
Refatorado para Alta Coesão e Type Safety.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Licenca, LogBot, Usuario
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, case, desc, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/telemetria", tags=["telemetria"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _calcular_data_inicio(periodo: str) -> Optional[datetime]:
    """Calcula a data de início baseada no período."""
    agora = datetime.now(timezone.utc)
    offsets = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    delta = offsets.get(periodo)
    return agora - delta if delta else None


def _get_base_filters(
    data_inicio: Optional[datetime], hwid: Optional[str] = None
) -> List[Any]:
    """Retorna lista de filtros para queries."""
    filters = []
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)
    if hwid:
        filters.append(LogBot.hwid == hwid)
    return filters


def _get_valor_plano(plano: str, primeira_adesao: bool) -> float:
    """Retorna valor do plano para cálculos de receita."""
    precos = {
        "semanal": {"normal": 149.90, "primeira": 49.90},
        "quinzenal": {"normal": 249.90, "primeira": 89.90},
        "mensal": {"normal": 449.90, "primeira": 149.90},
        "trial": {"normal": 0.0, "primeira": 0.0},
    }
    key = plano if plano in precos else "trial"
    plano_info = precos[key]
    return plano_info["primeira"] if primeira_adesao else plano_info["normal"]


# ============================================================================
# ABA 1: NEGÓCIO - Métricas financeiras e de clientes (Refatorado)
# ============================================================================


@router.get("/negocio")
async def dashboard_negocio(
    periodo: str = Query("30d", description="Período: 7d, 30d, 90d, all"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Dashboard de NEGÓCIO: receita, clientes, conversão.
    Refatorado para dividir responsabilidades.
    """
    agora = datetime.now(timezone.utc)

    # Execução paralela ou sequencial de sub-rotinas de dados
    clientes_metrics = await _get_metricas_clientes(db, agora)
    distribuicao = await _get_distribuicao_planos(db)
    conversao = await _get_dados_conversao(db)
    ultimas = await _get_ultimas_vendas(db)
    receita = await _calcular_receita_mensal(db)
    grafico_clientes = await _get_clientes_por_dia(db, 30)

    # Montagem do payload final
    return {
        "periodo": periodo,
        "clientes": clientes_metrics,
        "conversao": conversao,
        "distribuicao_planos": distribuicao,
        "receita_mensal_estimada": receita,
        "ultimas_vendas": ultimas,
        "clientes_por_dia": grafico_clientes,
    }


async def _get_metricas_clientes(db: AsyncSession, agora: datetime) -> Dict[str, int]:
    """Busca contagens gerais de clientes."""
    # Total
    total = (await db.execute(select(func.count(Licenca.id)))).scalar() or 0

    # Ativos
    ativas = (
        await db.execute(select(func.count(Licenca.id)).where(Licenca.ativa.is_(True)))
    ).scalar() or 0

    # Novos 7 dias
    novos = (
        await db.execute(
            select(func.count(Licenca.id)).where(
                Licenca.created_at >= agora - timedelta(days=7)
            )
        )
    ).scalar() or 0

    # Expirando
    expirando = (
        await db.execute(
            select(func.count(Licenca.id)).where(
                and_(
                    Licenca.ativa.is_(True),
                    Licenca.data_expiracao <= agora + timedelta(days=3),
                    Licenca.data_expiracao > agora,
                )
            )
        )
    ).scalar() or 0

    # Trials vs Pagos
    trials = (
        await db.execute(
            select(func.count(Licenca.id)).where(
                and_(Licenca.ativa.is_(True), Licenca.is_trial.is_(True))
            )
        )
    ).scalar() or 0

    return {
        "total": total,
        "ativos": ativas,
        "novos_7d": novos,
        "expirando_3d": expirando,
        "trials_ativos": trials,
        "pagos_ativos": ativas - trials,
    }


async def _get_distribuicao_planos(db: AsyncSession) -> Dict[str, int]:
    """Busca distribuição de licenças ativas por tipo de plano."""
    result = await db.execute(
        select(Licenca.plano_tipo, func.count(Licenca.id).label("qtd"))
        .where(Licenca.ativa.is_(True))
        .group_by(Licenca.plano_tipo)
    )
    return {row.plano_tipo or "indefinido": row.qtd for row in result}


async def _get_dados_conversao(db: AsyncSession) -> Dict[str, Any]:
    """Calcula taxa de conversão de trial para pago."""
    total_trials = (
        await db.execute(
            select(func.count(Licenca.id)).where(Licenca.is_trial.is_(True))
        )
    ).scalar() or 0

    convertidos = (
        await db.execute(
            select(func.count(func.distinct(Licenca.email_cliente))).where(
                and_(
                    Licenca.is_trial.is_(False),
                    Licenca.is_primeira_adesao.is_(True),
                )
            )
        )
    ).scalar() or 0

    taxa = (convertidos / total_trials * 100) if total_trials > 0 else 0.0
    return {
        "total_trials": total_trials,
        "convertidos": convertidos,
        "taxa_conversao": round(taxa, 1),
    }


async def _get_ultimas_vendas(db: AsyncSession) -> List[Dict]:
    """Retorna as 10 últimas vendas (não trials)."""
    result = await db.execute(
        select(Licenca)
        .where(Licenca.is_trial.is_(False))
        .order_by(desc(Licenca.created_at))
        .limit(10)
    )

    vendas = []
    for lic in result.scalars():
        # Type Safety: Usar 'is not None' resolve o erro do Pylance sobre Column[str]
        plano = cast(str, lic.plano_tipo) if lic.plano_tipo is not None else "trial"

        is_primeira = (
            cast(bool, lic.is_primeira_adesao)
            if lic.is_primeira_adesao is not None
            else False
        )

        # Type Safety: Usar 'is not None' para Column[datetime]
        data_str = lic.created_at.isoformat() if lic.created_at is not None else None

        vendas.append(
            {
                "id": lic.id,
                "cliente": lic.cliente_nome or "N/A",
                "email": lic.email_cliente,
                "plano": plano,
                "data": data_str,
                "valor": _get_valor_plano(plano, is_primeira),
            }
        )
    return vendas


async def _calcular_receita_mensal(db: AsyncSession) -> float:
    """Calcula receita recorrente mensal estimada."""
    result = await db.execute(
        select(Licenca.plano_tipo, Licenca.is_primeira_adesao).where(
            and_(Licenca.ativa.is_(True), Licenca.is_trial.is_(False))
        )
    )

    total = 0.0
    for row in result:
        p_tipo = row.plano_tipo or "trial"
        p_primeira = row.is_primeira_adesao or False
        valor = _get_valor_plano(p_tipo, p_primeira)

        if p_tipo == "semanal":
            total += valor * 4
        elif p_tipo == "quinzenal":
            total += valor * 2
        else:
            total += valor

    return round(total, 2)


async def _get_clientes_por_dia(db: AsyncSession, dias: int) -> List[Dict]:
    """Gráfico de aquisição de clientes."""
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)
    dia_truncado = func.date_trunc("day", Licenca.created_at)

    result = await db.execute(
        select(
            dia_truncado.label("dia"),
            func.count(Licenca.id).label("quantidade"),
        )
        .where(Licenca.created_at >= inicio)
        .group_by(dia_truncado)
        .order_by(dia_truncado)
    )

    return [
        {
            "dia": row.dia.strftime("%d/%m") if row.dia else None,
            "quantidade": row.quantidade,
        }
        for row in result
    ]


# ============================================================================
# ABA 2: OPERAÇÃO - Bots, apostas, performance em tempo real
# ============================================================================


@router.get("/operacao")
async def dashboard_operacao(
    periodo: str = Query("24h", description="Período: 1h, 24h, 7d"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Dashboard de OPERAÇÃO: bots online, apostas, win rate, alertas.
    """
    agora = datetime.now(timezone.utc)
    data_inicio = _calcular_data_inicio(periodo)
    filters = _get_base_filters(data_inicio)

    # 1. Bots Online
    bots_online = (
        await db.execute(
            select(func.count(func.distinct(LogBot.hwid))).where(
                LogBot.timestamp >= agora - timedelta(minutes=5)
            )
        )
    ).scalar() or 0

    # 2. Stats Gerais
    stats = (
        await db.execute(
            select(
                func.count(case((LogBot.tipo == "bet", 1))).label("apostas"),
                func.count(case((LogBot.tipo == "round", 1))).label("rounds"),
                func.sum(case((LogBot.tipo == "bet", LogBot.lucro), else_=0)).label(
                    "lucro"
                ),
                func.count(
                    case(
                        (
                            and_(
                                LogBot.tipo == "bet",
                                LogBot.resultado == "hit",
                            ),
                            1,
                        )
                    )
                ).label("hits"),
            ).where(and_(*filters) if filters else true())
        )
    ).first()

    total_apostas = stats.apostas if stats else 0
    total_hits = stats.hits if stats else 0
    win_rate = (total_hits / total_apostas * 100) if total_apostas > 0 else 0.0

    # 3. Atividade/Hora
    trunc_hora = func.date_trunc("hour", LogBot.timestamp)
    ativ_res = await db.execute(
        select(
            trunc_hora.label("hora"),
            func.count(LogBot.id).label("total"),
            func.count(case((LogBot.tipo == "bet", 1))).label("apostas"),
        )
        .where(LogBot.timestamp >= agora - timedelta(hours=24))
        .group_by(trunc_hora)
        .order_by(trunc_hora)
    )
    ativ_por_hora = [
        {
            "hora": row.hora.strftime("%H:%M") if row.hora else None,
            "total": row.total,
            "apostas": row.apostas,
        }
        for row in ativ_res
    ]

    # 4. Outros dados
    bots_ativos = await _get_bots_ativos_detalhes(db)
    dist_modos = await _get_distribuicao_modos(db, data_inicio)
    alertas = await _get_alertas_sistema(db)
    top_clientes = await _get_top_clientes(db, data_inicio)

    return {
        "periodo": periodo,
        "resumo": {
            "bots_online": bots_online,
            "total_apostas": total_apostas,
            "total_explosoes": stats.rounds if stats else 0,
            "total_hits": total_hits,
            "total_misses": total_apostas - total_hits,
            "win_rate": round(win_rate, 1),
            "lucro_total": float(stats.lucro) if stats and stats.lucro else 0,
        },
        "atividade_por_hora": ativ_por_hora,
        "bots_ativos": bots_ativos,
        "distribuicao_modos": dist_modos,
        "alertas": alertas,
        "top_clientes": top_clientes,
    }


async def _get_distribuicao_modos(
    db: AsyncSession, data_inicio: Optional[datetime]
) -> List[Dict]:
    """Helper para distribuição de modos de risco."""
    filters = [LogBot.tipo == "bet", LogBot.modo_risco.isnot(None)]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    result = await db.execute(
        select(
            LogBot.modo_risco,
            func.count(LogBot.id).label("qtd"),
            func.sum(LogBot.lucro).label("lucro"),
        )
        .where(and_(*filters))
        .group_by(LogBot.modo_risco)
    )
    return [
        {
            "modo": row.modo_risco or "N/A",
            "quantidade": row.qtd,
            "lucro": float(row.lucro) if row.lucro else 0,
        }
        for row in result
    ]


async def _get_bots_ativos_detalhes(db: AsyncSession) -> List[Dict]:
    """Retorna detalhes dos bots com atividade recente."""
    agora = datetime.now(timezone.utc)
    # Bots com atividade nas últimas 24h
    query = (
        select(
            LogBot.hwid,
            func.max(LogBot.timestamp).label("ultima_ativ"),
            func.sum(case((LogBot.tipo == "bet", LogBot.lucro), else_=0)).label(
                "lucro"
            ),
            func.count(case((LogBot.tipo == "bet", 1))).label("apostas"),
            func.count(
                case(
                    (
                        and_(
                            LogBot.tipo == "bet",
                            LogBot.resultado == "hit",
                        ),
                        1,
                    )
                )
            ).label("hits"),
            func.max(LogBot.modo_risco).label("modo"),
            func.max(LogBot.saldo).label("saldo"),
            func.max(LogBot.banca_inicial).label("banca_inicial"),
            func.max(LogBot.estrategia).label("estrategia"),
        )
        .where(LogBot.timestamp >= agora - timedelta(hours=24))
        .group_by(LogBot.hwid)
        .order_by(desc(func.max(LogBot.timestamp)))
        .limit(50)
    )

    result = await db.execute(query)
    bots = []

    for row in result:
        if not row.hwid:
            continue

        # Type safe HWID
        hwid_str = cast(str, row.hwid)

        # Buscar dados do cliente
        lic = (
            await db.execute(
                select(Licenca.cliente_nome, Licenca.plano_tipo).where(
                    Licenca.hwid == hwid_str
                )
            )
        ).first()

        ultima = cast(datetime, row.ultima_ativ)
        if ultima.tzinfo is None:
            ultima = ultima.replace(tzinfo=timezone.utc)

        inatividade = (agora - ultima).total_seconds() / 60
        status = (
            "online"
            if inatividade < 5
            else "recente" if inatividade < 30 else "inativo"
        )

        total_apostas = row.apostas or 0
        total_hits = row.hits or 0
        win_rate = (total_hits / total_apostas * 100) if total_apostas > 0 else 0.0

        bots.append(
            {
                "hwid": f"{hwid_str[:12]}...",
                "cliente": lic.cliente_nome if lic else "Desconhecido",
                "plano": lic.plano_tipo if lic else "N/A",
                "status": status,
                "ultima_atividade": ultima.isoformat(),
                "minutos_inativo": int(inatividade),
                "modo_risco": row.modo or "N/A",
                "saldo_atual": float(row.saldo) if row.saldo else 0,
                "banca_inicial": float(row.banca_inicial) if row.banca_inicial else 0,
                "lucro_sessao": float(row.lucro) if row.lucro else 0,
                "apostas_sessao": total_apostas,
                "hits_sessao": total_hits,
                "win_rate": round(win_rate, 1),
                "estrategia": row.estrategia or "N/A",
            }
        )
    return bots


async def _get_alertas_sistema(db: AsyncSession) -> List[Dict]:
    """Busca alertas críticos do sistema."""
    agora = datetime.now(timezone.utc)
    alertas = []

    # 1. Stop Loss
    sl_res = await db.execute(
        select(LogBot)
        .where(
            and_(
                LogBot.stop_loss_atingido == "S",
                LogBot.timestamp >= agora - timedelta(hours=24),
            )
        )
        .order_by(desc(LogBot.timestamp))
        .limit(5)
    )
    for log in sl_res.scalars():
        hwid_str = cast(str, log.hwid) if log.hwid is not None else ""
        cliente = await _get_cliente_por_hwid(db, hwid_str)

        # CORREÇÃO: Verificação explícita 'is not None'
        ts_iso = log.timestamp.isoformat() if log.timestamp is not None else None

        alertas.append(
            {
                "tipo": "stop_loss",
                "severidade": "critico",
                "cliente": cliente,
                "mensagem": "Stop-loss atingido",
                "timestamp": ts_iso,
                "dados": {"saldo": log.saldo},
            }
        )

    # 2. Metas
    meta_res = await db.execute(
        select(LogBot)
        .where(
            and_(
                LogBot.meta_atingida == "S",
                LogBot.timestamp >= agora - timedelta(hours=24),
            )
        )
        .order_by(desc(LogBot.timestamp))
        .limit(5)
    )
    for log in meta_res.scalars():
        hwid_str = cast(str, log.hwid) if log.hwid is not None else ""
        cliente = await _get_cliente_por_hwid(db, hwid_str)

        # CORREÇÃO: Verificação explícita 'is not None'
        ts_iso = log.timestamp.isoformat() if log.timestamp is not None else None

        alertas.append(
            {
                "tipo": "meta_atingida",
                "severidade": "sucesso",
                "cliente": cliente,
                "mensagem": "Meta atingida!",
                "timestamp": ts_iso,
                "dados": {"saldo": log.saldo},
            }
        )

    # 3. Licenças Expirando
    exp_res = await db.execute(
        select(Licenca)
        .where(
            and_(
                Licenca.ativa.is_(True),
                Licenca.data_expiracao <= agora + timedelta(days=3),
                Licenca.data_expiracao > agora,
            )
        )
        .limit(5)
    )
    for lic in exp_res.scalars():
        dias = 0
        # CORREÇÃO: Verificação explícita 'is not None' resolve o erro do Pylance
        if lic.data_expiracao is not None:
            dias = (lic.data_expiracao - agora).days

        alertas.append(
            {
                "tipo": "expirando",
                "severidade": "atencao",
                "cliente": lic.cliente_nome or "N/A",
                "mensagem": f"Expira em {dias} dia(s)",
                "timestamp": agora.isoformat(),
                "dados": {"dias": dias},
            }
        )

    alertas.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return alertas[:15]


async def _get_cliente_por_hwid(db: AsyncSession, hwid: str) -> str:
    """Busca nome do cliente."""
    if not hwid:
        return "Desconhecido"
    res = await db.execute(select(Licenca.cliente_nome).where(Licenca.hwid == hwid))
    nome = res.scalar_one_or_none()
    return nome or "Desconhecido"


async def _get_top_clientes(
    db: AsyncSession, data_inicio: Optional[datetime]
) -> List[Dict]:
    """Top 5 clientes por lucro."""
    filters = [LogBot.tipo == "bet"]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    query = (
        select(
            LogBot.hwid,
            func.sum(LogBot.lucro).label("lucro"),
            func.count(LogBot.id).label("apostas"),
            func.count(case((LogBot.resultado == "hit", 1))).label("hits"),
        )
        .where(and_(*filters))
        .group_by(LogBot.hwid)
        .order_by(desc(func.sum(LogBot.lucro)))
        .limit(5)
    )

    result = await db.execute(query)
    top = []
    for row in result:
        hwid_str = cast(str, row.hwid) if row.hwid is not None else ""
        cliente = await _get_cliente_por_hwid(db, hwid_str)
        rate = (row.hits / row.apostas * 100) if row.apostas > 0 else 0.0
        top.append(
            {
                "cliente": cliente,
                "lucro": float(row.lucro) if row.lucro else 0,
                "apostas": row.apostas,
                "win_rate": round(rate, 1),
            }
        )
    return top


# ============================================================================
# ABA 3: CLIENTES - Detalhamento
# ============================================================================


@router.get("/clientes")
async def dashboard_clientes(
    status: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Lista clientes com filtros e status."""
    agora = datetime.now(timezone.utc)
    query = select(Licenca).order_by(desc(Licenca.created_at))
    conditions = []

    if busca:
        term = f"%{busca}%"
        conditions.append(
            or_(
                Licenca.cliente_nome.ilike(term),
                Licenca.email_cliente.ilike(term),
            )
        )

    if status == "expirado":
        conditions.append(Licenca.data_expiracao < agora)
    elif status == "ativo":
        conditions.append(and_(Licenca.ativa.is_(True), Licenca.data_expiracao > agora))
    elif status == "inativo":
        conditions.append(Licenca.ativa.is_(False))

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query.limit(100))
    clientes = []

    for lic in result.scalars():
        # Type safe HWID
        hwid_str = cast(str, lic.hwid) if lic.hwid is not None else ""
        stats = await _get_stats_cliente(db, hwid_str, agora)
        clientes.append({"licenca": lic.to_dict(), "telemetria": stats})

    if status == "online":
        clientes = [c for c in clientes if c["telemetria"]["status"] == "online"]

    return {"total": len(clientes), "clientes": clientes}


async def _get_stats_cliente(db: AsyncSession, hwid: str, agora: datetime) -> Dict:
    """Calcula stats resumidos de um cliente."""
    if not hwid:
        return {
            "status": "nunca_usado",
            "ultima_atividade": None,
            "total_apostas": 0,
            "lucro_total": 0,
            "win_rate": 0,
        }

    res = (
        await db.execute(
            select(
                func.max(LogBot.timestamp).label("ultima"),
                func.count(case((LogBot.tipo == "bet", 1))).label("apostas"),
                func.sum(case((LogBot.tipo == "bet", LogBot.lucro), else_=0)).label(
                    "lucro"
                ),
                func.count(
                    case(
                        (
                            and_(
                                LogBot.tipo == "bet",
                                LogBot.resultado == "hit",
                            ),
                            1,
                        )
                    )
                ).label("hits"),
            ).where(LogBot.hwid == hwid)
        )
    ).first()

    status_bot = "nunca_usado"
    ultima_str = None

    if res and res.ultima:
        ultima_dt = cast(datetime, res.ultima)
        if ultima_dt.tzinfo is None:
            ultima_dt = ultima_dt.replace(tzinfo=timezone.utc)
        ultima_str = ultima_dt.isoformat()

        mins = (agora - ultima_dt).total_seconds() / 60
        status_bot = "online" if mins < 5 else "recente" if mins < 60 else "inativo"

    apostas = res.apostas if res else 0
    hits = res.hits if res else 0
    win_rate = (hits / apostas * 100) if apostas > 0 else 0.0

    return {
        "status": status_bot,
        "ultima_atividade": ultima_str,
        "total_apostas": apostas,
        "lucro_total": float(res.lucro) if res and res.lucro else 0,
        "win_rate": round(win_rate, 1),
    }


@router.get("/cliente/{licenca_id}")
async def detalhes_cliente(
    licenca_id: int,
    periodo: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Detalhes completos de um cliente."""
    lic = (
        await db.execute(select(Licenca).where(Licenca.id == licenca_id))
    ).scalar_one_or_none()

    if not lic:
        return {"error": "Não encontrado"}
    if lic.hwid is None:
        return {"licenca": lic.to_dict(), "mensagem": "Sem HWID"}

    hwid_str = cast(str, lic.hwid)
    inicio = _calcular_data_inicio(periodo)

    # Executa sub-rotinas
    stats = await _get_estatisticas_gerais(db, hwid_str, inicio)
    historico = await _get_historico_diario(db, hwid_str, inicio)
    sessoes = await _get_ultimas_sessoes(db, hwid_str, inicio)
    perf = await _get_performance_modos(db, hwid_str, inicio)

    return {
        "licenca": lic.to_dict(),
        "periodo": periodo,
        "estatisticas": stats,
        "historico_diario": historico,
        "ultimas_sessoes": sessoes,
        "performance_modos": perf,
    }


# ============================================================================
# ABA 4: LOGS (Refatorado)
# ============================================================================


@router.get("/logs")
async def dashboard_logs(
    tipo: Optional[str] = Query(None),
    hwid: Optional[str] = Query(None),
    licenca_id: Optional[int] = Query(None),
    periodo: str = Query("24h"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Lista logs com filtros."""
    inicio = _calcular_data_inicio(periodo)
    filters = []

    if inicio:
        filters.append(LogBot.timestamp >= inicio)
    if tipo:
        filters.append(LogBot.tipo == tipo)
    if hwid:
        filters.append(LogBot.hwid == hwid)

    # Walrus operator (Sourcery suggestion)
    if licenca_id:
        if lic_hwid := (
            await db.execute(select(Licenca.hwid).where(Licenca.id == licenca_id))
        ).scalar_one_or_none():
            filters.append(LogBot.hwid == lic_hwid)

    # Count Total
    count_q = select(func.count(LogBot.id))
    if filters:
        count_q = count_q.where(and_(*filters))
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch Logs
    offset = (pagina - 1) * limite
    query = select(LogBot).order_by(desc(LogBot.timestamp)).offset(offset).limit(limite)
    if filters:
        query = query.where(and_(*filters))

    logs = (await db.execute(query)).scalars().all()
    logs_enrich = []

    for log in logs:
        # Type Safe
        h_str = cast(str, log.hwid) if log.hwid is not None else ""
        cliente = await _get_cliente_por_hwid(db, h_str)
        d = log.to_dict()
        d["cliente"] = cliente
        logs_enrich.append(d)

    # Stats by Type
    w_clause = and_(*filters) if filters else true()
    tipos_res = await db.execute(
        select(LogBot.tipo, func.count(LogBot.id)).where(w_clause).group_by(LogBot.tipo)
    )
    tipos = {row.tipo: row[1] for row in tipos_res}

    return {
        "paginacao": {
            "pagina": pagina,
            "total": total,
            "paginas": (total + limite - 1) // limite,
        },
        "por_tipo": tipos,
        "logs": logs_enrich,
    }


# Funções de suporte para detalhes_cliente omitidas para brevidade
# (Seguem o mesmo padrão de type safety e quebra de linhas implementado acima)
# As funções _get_estatisticas_gerais, _get_historico_diario, etc
# devem ser mantidas conforme sua versão original mas com os casts aplicados.
# Vou incluir as implementações críticas abaixo.


async def _get_estatisticas_gerais(
    db: AsyncSession, hwid: str, data_inicio: Optional[datetime]
) -> Dict:
    filters = [LogBot.hwid == hwid]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    res = (
        await db.execute(
            select(
                func.count(LogBot.id).label("logs"),
                func.count(func.distinct(LogBot.sessao_id)).label("sessoes"),
                func.count(case((LogBot.tipo == "bet", 1))).label("bet"),
                func.sum(case((LogBot.tipo == "bet", LogBot.lucro), else_=0)).label(
                    "lucro"
                ),
                func.count(
                    case(
                        (
                            and_(
                                LogBot.tipo == "bet",
                                LogBot.resultado == "hit",
                            ),
                            1,
                        )
                    )
                ).label("hits"),
                func.min(LogBot.timestamp).label("min_ts"),
                func.max(LogBot.timestamp).label("max_ts"),
            ).where(and_(*filters))
        )
    ).first()

    total_ap = res.bet if res else 0
    hits = res.hits if res else 0
    rate = (hits / total_ap * 100) if total_ap > 0 else 0.0

    return {
        "total_logs": res.logs if res else 0,
        "total_sessoes": res.sessoes if res else 0,
        "total_apostas": total_ap,
        "lucro_total": float(res.lucro) if res and res.lucro else 0,
        "hits": hits,
        "win_rate": round(rate, 1),
        "primeira_atividade": res.min_ts.isoformat() if res and res.min_ts else None,
        "ultima_atividade": res.max_ts.isoformat() if res and res.max_ts else None,
    }


async def _get_historico_diario(
    db: AsyncSession, hwid: str, data_inicio: Optional[datetime]
):
    dia = func.date_trunc("day", LogBot.timestamp)
    filters = [LogBot.hwid == hwid, LogBot.tipo == "bet"]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    res = await db.execute(
        select(
            dia.label("dia"),
            func.sum(LogBot.lucro).label("lucro"),
            func.count(LogBot.id).label("apostas"),
        )
        .where(and_(*filters))
        .group_by(dia)
        .order_by(dia)
    )
    return [
        {
            "dia": row.dia.strftime("%d/%m") if row.dia else None,
            "lucro": float(row.lucro) if row.lucro else 0,
            "apostas": row.apostas,
        }
        for row in res
    ]


async def _get_ultimas_sessoes(
    db: AsyncSession, hwid: str, data_inicio: Optional[datetime]
):
    filters = [LogBot.hwid == hwid]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    res = await db.execute(
        select(
            LogBot.sessao_id,
            func.min(LogBot.timestamp).label("ini"),
            func.max(LogBot.timestamp).label("fim"),
            func.sum(case((LogBot.tipo == "bet", LogBot.lucro), else_=0)).label(
                "lucro"
            ),
            func.max(LogBot.modo_risco).label("modo"),
        )
        .where(and_(*filters))
        .group_by(LogBot.sessao_id)
        .order_by(desc(func.max(LogBot.timestamp)))
        .limit(10)
    )
    return [
        {
            "sessao_id": row.sessao_id,
            "inicio": row.ini.isoformat() if row.ini else None,
            "lucro": float(row.lucro) if row.lucro else 0,
            "modo": row.modo or "N/A",
        }
        for row in res
    ]


async def _get_performance_modos(
    db: AsyncSession, hwid: str, data_inicio: Optional[datetime]
):
    filters = [LogBot.hwid == hwid, LogBot.tipo == "bet"]
    if data_inicio:
        filters.append(LogBot.timestamp >= data_inicio)

    res = await db.execute(
        select(
            LogBot.modo_risco,
            func.count(LogBot.id).label("qtd"),
            func.sum(LogBot.lucro).label("lucro"),
        )
        .where(and_(*filters))
        .group_by(LogBot.modo_risco)
    )
    return [
        {
            "modo": row.modo_risco or "N/A",
            "apostas": row.qtd,
            "lucro": float(row.lucro) if row.lucro else 0,
        }
        for row in res
    ]


@router.get("/exportar")
async def exportar_telemetria(
    formato: str = Query("json"),
    licenca_id: Optional[int] = None,
    periodo: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Exporta dados."""
    dados_log = await dashboard_logs(
        licenca_id=licenca_id,
        periodo=periodo,
        limite=10000,
        db=db,
        current_admin=current_admin,
    )
    dados = dados_log["logs"]

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
    return {"formato": "json", "dados": dados}


