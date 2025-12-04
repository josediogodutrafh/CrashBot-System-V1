"""
Router: Pagamentos
Endpoints para integração com Mercado Pago.
"""

import os
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional  # <--- ADICIONADO

import mercadopago

# from app.config import settings  <-- Removido se não estiver usando
from app.database import get_db
from app.models import Licenca, Usuario
from app.services.email_service import enviar_email, template_licenca_criada
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()


router = APIRouter(prefix="/api/v1/pagamento", tags=["pagamento"])


# ============================================================================
# SCHEMAS
# ============================================================================


class CriarPagamentoRequest(BaseModel):
    """Request para criar pagamento."""

    plano: str  # experimental, semanal, mensal
    nome: str
    email: EmailStr
    whatsapp: str


class CriarPagamentoResponse(BaseModel):
    """Response com dados do pagamento."""

    payment_id: str
    init_point: str  # URL para redirecionar o cliente
    plano: str
    valor: float


# ============================================================================
# DADOS DOS PLANOS
# ============================================================================


PLANOS = {
    "experimental": {
        "nome": "Experimental",
        "preco": 29.90,
        "dias": 3,
        "descricao": "Plano Experimental - 3 dias de acesso",
    },
    "semanal": {
        "nome": "Semanal",
        "preco": 149.90,
        "dias": 7,
        "descricao": "Plano Semanal - 7 dias de acesso",
    },
    "mensal": {
        "nome": "Mensal",
        "preco": 499.90,
        "dias": 30,
        "descricao": "Plano Mensal - 30 dias de acesso",
    },
}


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def gerar_chave_licenca() -> str:
    """Gera uma chave de licença única no formato XXXX-XXXX-XXXX-XXXX."""
    caracteres = string.ascii_uppercase + string.digits
    partes = ["".join(secrets.choice(caracteres) for _ in range(4)) for _ in range(4)]
    return "-".join(partes)


# Contexto para hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def gerar_senha_temporaria(tamanho: int = 10) -> str:
    """Gera uma senha temporária segura."""
    caracteres = string.ascii_letters + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(tamanho))


def get_mp_sdk():
    """Retorna instância do SDK do Mercado Pago."""
    # Uso de walrus operator (:=) para simplificar
    if access_token := os.getenv("MP_ACCESS_TOKEN"):
        return mercadopago.SDK(access_token)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Mercado Pago não configurado",
    )


# ============================================================================
# ENDPOINT: CRIAR PAGAMENTO
# ============================================================================


@router.post("/criar", response_model=CriarPagamentoResponse)
async def criar_pagamento(
    dados: CriarPagamentoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Cria um pagamento no Mercado Pago.

    Args:
        dados: Dados do cliente e plano escolhido

    Returns:
        CriarPagamentoResponse: URL para pagamento
    """
    # Validar plano
    if dados.plano not in PLANOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plano inválido. Escolha: {', '.join(PLANOS.keys())}",
        )

    plano = PLANOS[dados.plano]

    # Gerar ID único para referência
    external_reference = f"{dados.plano}_{uuid.uuid4().hex[:12]}"

    # Configurar SDK
    sdk = get_mp_sdk()

    # URL base para callbacks
    base_url = str(request.base_url).rstrip("/")

    # Criar preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": f"CrashBot - {plano['nome']}",
                "description": plano["descricao"],
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": plano["preco"],
            }
        ],
        "payer": {
            "name": dados.nome,
            "email": dados.email,
        },
        "external_reference": external_reference,
        "back_urls": {
            "success": "https://crashbot-loja.vercel.app/pagamento/sucesso",
            "failure": "https://crashbot-loja.vercel.app/pagamento/falha",
            "pending": "https://crashbot-loja.vercel.app/pagamento/pendente",
        },
        "auto_return": "approved",
        "notification_url": f"{base_url}/api/v1/pagamento/webhook",
        "metadata": {
            "plano": dados.plano,
            "dias": plano["dias"],
            "nome": dados.nome,
            "email": dados.email,
            "whatsapp": dados.whatsapp,
        },
        "payment_methods": {
            "excluded_payment_types": [],
            "excluded_payment_methods": [],
            "installments": 12,
        },
    }

    # Criar preferência
    try:
        preference_response = sdk.preference().create(preference_data)
        print(f"Resposta MP: {preference_response}")  # Debug

        if preference_response.get("status") not in [200, 201]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro Mercado Pago: {preference_response}",
            )

        preference = preference_response["response"]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar pagamento: {str(e)}",
        )

    return CriarPagamentoResponse(
        payment_id=preference["id"],
        init_point=preference["init_point"],
        plano=dados.plano,
        valor=plano["preco"],
    )


# ============================================================================
# ENDPOINT: WEBHOOK (Notificação do Mercado Pago)
# ============================================================================


@router.post("/webhook")
async def webhook_mercadopago(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe notificações do Mercado Pago quando um pagamento é aprovado.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}

    # Verificar tipo de notificação
    if body.get("type") != "payment":
        return {"status": "ok"}

    # Obter ID do pagamento
    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        return {"status": "ok"}

    # Buscar detalhes do pagamento
    sdk = get_mp_sdk()

    try:
        payment_response = sdk.payment().get(payment_id)
        payment = payment_response["response"]
    except Exception as e:
        print(f"Erro ao buscar pagamento: {e}")
        return {"status": "error"}

    # Verificar se foi aprovado
    if payment.get("status") != "approved":
        return {"status": "ok", "payment_status": payment.get("status")}

    # Extrair metadados
    metadata = payment.get("metadata", {})
    plano = metadata.get("plano")
    dias = metadata.get("dias")
    nome = metadata.get("nome")
    email = metadata.get("email")
    whatsapp = metadata.get("whatsapp")

    if not plano or not dias:
        print("Metadados incompletos")
        return {"status": "error", "message": "Metadados incompletos"}

    # Verificar se já existe licença para este pagamento
    result = await db.execute(
        select(Licenca).where(Licenca.payment_id == str(payment_id))
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"Licença já existe para pagamento {payment_id}")
        return {"status": "ok", "message": "Licença já criada"}

    # Criar nova licença
    chave = gerar_chave_licenca()
    data_expiracao = datetime.now(timezone.utc) + timedelta(days=int(dias))

    nova_licenca = Licenca(
        chave=chave,
        ativa=True,
        data_expiracao=data_expiracao,
        cliente_nome=nome,
        email_cliente=email,
        whatsapp=whatsapp,
        plano_tipo=plano,
        payment_id=str(payment_id),
    )

    db.add(nova_licenca)
    await db.commit()

    print(f"✅ Licença criada: {chave} para {email}")

    # ========================================================================
    # CRIAR CONTA DO CLIENTE (se não existir)
    # ========================================================================
    senha_temporaria = None

    # Verificar se já existe usuário com este email
    result_user = await db.execute(select(Usuario).where(Usuario.email == email))
    usuario_existente = result_user.scalar_one_or_none()

    if not usuario_existente:
        # Gerar senha temporária
        senha_temporaria = gerar_senha_temporaria()
        senha_hash = pwd_context.hash(senha_temporaria)

        # Criar novo usuário (cliente, não admin)
        novo_usuario = Usuario(
            email=email,
            senha_hash=senha_hash,
            nome=nome,
            is_admin=False,
            is_active=True,
        )

        db.add(novo_usuario)
        await db.commit()
        print(f"✅ Usuário criado: {email}")
    else:
        print(f"ℹ️ Usuário já existe: {email}")
        senha_temporaria = "(sua senha atual)"

    # ========================================================================
    # ENVIAR EMAIL COM LICENÇA
    # ========================================================================
    try:
        html_email = template_licenca_criada(
            nome=nome or "Cliente",
            email=email,
            senha=senha_temporaria,
            chave_licenca=chave,
            plano=plano,
            dias=int(dias),
        )

        await enviar_email(
            para=email,
            assunto="🎉 Sua licença CrashBot está pronta!",
            html=html_email,
        )
    except Exception as e:
        print(f"⚠️ Erro ao enviar email: {e}")
        # Não falha o webhook se o email falhar

    return {
        "status": "ok",
        "licenca": chave,
        "usuario_criado": usuario_existente is None,
    }


# ============================================================================
# ENDPOINTS: RETORNO DO PAGAMENTO
# ============================================================================


@router.get("/sucesso")
async def pagamento_sucesso(
    request: Request,
    # CORREÇÃO: Usamos Optional[str] para permitir None
    collection_id: Optional[str] = None,
    collection_status: Optional[str] = None,
    external_reference: Optional[str] = None,
    payment_type: Optional[str] = None,
    merchant_order_id: Optional[str] = None,
    preference_id: Optional[str] = None,
    site_id: Optional[str] = None,
    processing_mode: Optional[str] = None,
    merchant_account_id: Optional[str] = None,
):
    """Página de retorno para pagamento aprovado."""
    # Redirecionar para página de sucesso na loja
    return {
        "status": "success",
        "message": "Pagamento aprovado! Você receberá a licença por e-mail em instantes.",
        "collection_id": collection_id,
        "external_reference": external_reference,
    }


@router.get("/falha")
async def pagamento_falha():
    """Página de retorno para pagamento recusado."""
    return {
        "status": "failure",
        "message": "Pagamento recusado. Por favor, tente novamente.",
    }


@router.get("/pendente")
async def pagamento_pendente():
    """Página de retorno para pagamento pendente."""
    return {
        "status": "pending",
        "message": "Pagamento pendente. Aguardando confirmação.",
    }
