"""
Client Notification Service
Serviço para enviar notificações aos CLIENTES via Telegram.

Este módulo é usado pelo BOT DESKTOP para notificar clientes sobre:
- HITs (acertos)
- MISSes (erros)
- Stop Loss atingido
- Meta atingida
- Alertas de expiração de licença

IMPORTANTE: Este arquivo deve ser colocado na API (crashbot-platform/api/app/services/)
O bot desktop fará requisições HTTP para enviar notificações.
"""

import os

import httpx

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ============================================================================
# TIPOS DE ALERTA
# ============================================================================


class AlertType:
    """Tipos de alerta para clientes."""

    HIT = "hit"
    MISS = "miss"
    STOP_LOSS = "stop_loss"
    META_ATINGIDA = "meta_atingida"
    LICENCA_EXPIRANDO = "licenca_expirando"
    SESSAO_INICIO = "sessao_inicio"
    SESSAO_FIM = "sessao_fim"
    RELATORIO_PERIODICO = "relatorio_periodico"


# ============================================================================
# TEMPLATES DE MENSAGENS
# ============================================================================


def _format_hit_message(data: dict) -> str:
    """Formata mensagem de HIT."""
    estrategia = data.get("estrategia", "N/A")
    alvo = data.get("alvo", 0)
    explosao = data.get("explosao", 0)
    saldo = data.get("saldo", 0)
    lucro = data.get("lucro", 0)

    return f"""
✅ *HIT!* | {estrategia}

🎯 Alvo: {alvo}x
💥 Explodiu: {explosao}x
💰 Lucro: R$ {lucro:+.2f}

*Saldo Atual: R$ {saldo:.2f}*
    """.strip()


def _format_miss_message(data: dict) -> str:
    """Formata mensagem de MISS."""
    estrategia = data.get("estrategia", "N/A")
    alvo = data.get("alvo", 0)
    explosao = data.get("explosao", 0)
    saldo = data.get("saldo", 0)
    prejuizo = data.get("prejuizo", 0)

    return f"""
❌ *MISS!* | {estrategia}

🎯 Alvo: {alvo}x
💥 Explodiu: {explosao}x
📉 Prejuízo: R$ {prejuizo:.2f}

*Saldo Atual: R$ {saldo:.2f}*
    """.strip()


def _format_stop_loss_message(data: dict) -> str:
    """Formata mensagem de Stop Loss."""
    saldo_inicial = data.get("saldo_inicial", 0)
    saldo_atual = data.get("saldo_atual", 0)
    perda_pct = data.get("perda_pct", 0)

    return f"""
🚨 *ALERTA DE STOP-LOSS!* 🚨

A banca caiu abaixo do limite de segurança.

💰 Início: R$ {saldo_inicial:.2f}
📉 Atual: R$ {saldo_atual:.2f}
⚠️ Perda: -{perda_pct:.1f}%

_Operações pausadas automaticamente._
    """.strip()


def _format_meta_atingida_message(data: dict) -> str:
    """Formata mensagem de Meta Atingida."""
    meta = data.get("meta", 0)
    saldo = data.get("saldo", 0)
    lucro_total = data.get("lucro_total", 0)
    tempo_suspensao = data.get("tempo_suspensao", "4 horas")

    return f"""
🏆 *META ATINGIDA!* 🏆

Parabéns! Você bateu a meta do dia!

🎯 Meta: R$ {meta:.2f}
💰 Saldo: R$ {saldo:.2f}
📈 Lucro: R$ {lucro_total:+.2f}

_Bot suspenso por {tempo_suspensao}._
_Aproveite para descansar! 😎_
    """.strip()


def _format_sessao_inicio_message(data: dict) -> str:
    """Formata mensagem de início de sessão."""
    modo = data.get("modo", "N/A")
    banca = data.get("banca", 0)
    meta = data.get("meta", 0)

    return f"""
🚀 *SESSÃO INICIADA*

📊 Modo: {modo}
💰 Banca: R$ {banca:.2f}
🎯 Meta: R$ {meta:.2f}

_Boa sorte! 🍀_
    """.strip()


def _format_sessao_fim_message(data: dict) -> str:
    """Formata mensagem de fim de sessão."""
    duracao = data.get("duracao", "00:00:00")
    saldo_inicial = data.get("saldo_inicial", 0)
    saldo_final = data.get("saldo_final", 0)
    lucro = saldo_final - saldo_inicial
    total_rodadas = data.get("total_rodadas", 0)

    resultado_emoji = "📈" if lucro >= 0 else "📉"
    resultado_cor = "+" if lucro >= 0 else ""

    return f"""
🏁 *SESSÃO ENCERRADA*

⏱️ Duração: {duracao}
🎰 Rodadas: {total_rodadas}

💰 Início: R$ {saldo_inicial:.2f}
💰 Final: R$ {saldo_final:.2f}
{resultado_emoji} Resultado: R$ {resultado_cor}{lucro:.2f}

_Até a próxima! 👋_
    """.strip()


def _format_relatorio_periodico_message(data: dict) -> str:
    """Formata relatório periódico (30 min)."""
    modo = data.get("modo", "N/A")
    saldo = data.get("saldo", 0)
    rodadas = data.get("rodadas", 0)
    hits = data.get("hits", 0)
    misses = data.get("misses", 0)
    lucro_sessao = data.get("lucro_sessao", 0)

    taxa_acerto = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0
    resultado_emoji = "📈" if lucro_sessao >= 0 else "📉"

    return f"""
📊 *RELATÓRIO (30 min)*

🎮 Modo: {modo}
💰 Saldo: R$ {saldo:.2f}

📈 Rodadas: {rodadas}
✅ HITs: {hits}
❌ MISSes: {misses}
🎯 Taxa: {taxa_acerto:.1f}%

{resultado_emoji} Lucro Sessão: R$ {lucro_sessao:+.2f}
    """.strip()


def _format_licenca_expirando_message(data: dict) -> str:
    """Formata alerta de licença expirando."""
    dias = data.get("dias_restantes", 0)
    data_expiracao = data.get("data_expiracao", "N/A")

    urgencia = "⚠️" if dias > 1 else "🚨"

    return f"""
{urgencia} *LICENÇA EXPIRANDO!*

Sua licença expira em *{dias} dia(s)*.
📅 Data: {data_expiracao}

Renove agora para não perder acesso!
🔗 tucunarebot.com.br
    """.strip()


# ============================================================================
# FUNÇÃO PRINCIPAL DE ENVIO
# ============================================================================


async def send_client_notification(
    chat_id: str,
    alert_type: str,
    data: dict,
) -> bool:
    """
    Envia notificação para um cliente específico via Telegram.

    Args:
        chat_id: ID do chat do Telegram do cliente
        alert_type: Tipo do alerta (AlertType)
        data: Dados específicos do alerta

    Returns:
        bool: True se enviado com sucesso
    """
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN não configurado")
        return False

    if not chat_id:
        print("⚠️ chat_id não fornecido")
        return False

    # Selecionar template baseado no tipo
    formatters = {
        AlertType.HIT: _format_hit_message,
        AlertType.MISS: _format_miss_message,
        AlertType.STOP_LOSS: _format_stop_loss_message,
        AlertType.META_ATINGIDA: _format_meta_atingida_message,
        AlertType.SESSAO_INICIO: _format_sessao_inicio_message,
        AlertType.SESSAO_FIM: _format_sessao_fim_message,
        AlertType.RELATORIO_PERIODICO: _format_relatorio_periodico_message,
        AlertType.LICENCA_EXPIRANDO: _format_licenca_expirando_message,
    }

    formatter = formatters.get(alert_type)
    if not formatter:
        print(f"⚠️ Tipo de alerta desconhecido: {alert_type}")
        return False

    message = formatter(data)

    # Enviar via Telegram
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                print(f"✅ Notificação {alert_type} enviada para {chat_id}")
                return True
            else:
                print(f"❌ Erro ao enviar: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"❌ Erro ao enviar notificação: {e}")
        return False


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================================================


async def notify_hit(
    chat_id: str,
    estrategia: str,
    alvo: float,
    explosao: float,
    saldo: float,
    lucro: float,
) -> bool:
    """Notifica cliente sobre um HIT."""
    return await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.HIT,
        data={
            "estrategia": estrategia,
            "alvo": alvo,
            "explosao": explosao,
            "saldo": saldo,
            "lucro": lucro,
        },
    )


async def notify_miss(
    chat_id: str,
    estrategia: str,
    alvo: float,
    explosao: float,
    saldo: float,
    prejuizo: float,
) -> bool:
    """Notifica cliente sobre um MISS."""
    return await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.MISS,
        data={
            "estrategia": estrategia,
            "alvo": alvo,
            "explosao": explosao,
            "saldo": saldo,
            "prejuizo": prejuizo,
        },
    )


async def notify_stop_loss(
    chat_id: str, saldo_inicial: float, saldo_atual: float, perda_pct: float
) -> bool:
    """Notifica cliente sobre Stop Loss atingido."""
    return await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.STOP_LOSS,
        data={
            "saldo_inicial": saldo_inicial,
            "saldo_atual": saldo_atual,
            "perda_pct": perda_pct,
        },
    )


async def notify_meta_atingida(
    chat_id: str, meta: float, saldo: float, lucro_total: float
) -> bool:
    """Notifica cliente sobre Meta Atingida."""
    return await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.META_ATINGIDA,
        data={
            "meta": meta,
            "saldo": saldo,
            "lucro_total": lucro_total,
            "tempo_suspensao": "4 horas",
        },
    )
