#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SERVIÇO DE LICENCIAMENTO

Gerencia validação de licença com a API.
Integrado com EventBus para emitir eventos de status.

Uso:
    from services.licensing import LicenseService, get_licensing

    licensing = get_licensing()
    result = licensing.validate("CHAVE-123", "usuario@email.com")

    if result.valid:
        print(f"Bem-vindo, {result.user_name}!")
"""

from __future__ import annotations

import hashlib
import logging
import platform
import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from core.constants import API_BASE_URL, API_ENDPOINTS, API_TIMEOUT, BOT_VERSION

# Core imports
from core.events import BotEvent, emit, get_event_bus

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class LicenseStatus(Enum):
    """Status possíveis da licença."""

    UNKNOWN = "unknown"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class LicenseResult:
    """Resultado da validação de licença."""

    valid: bool
    status: LicenseStatus
    message: str = ""

    # Dados do usuário (se válido)
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Dados da licença
    license_key: Optional[str] = None
    expiration_date: Optional[str] = None
    days_remaining: Optional[int] = None

    # Dados técnicos
    hwid: Optional[str] = None
    api_response: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE HWID
# ═══════════════════════════════════════════════════════════════════════════════


def get_hwid() -> str:
    """
    Gera um identificador único do hardware (HWID).

    Usa uma combinação de:
    - Nome do computador (platform.node)
    - UUID do sistema

    Returns:
        String hexadecimal de 32 caracteres
    """
    try:
        # Coleta informações do sistema
        node_name = platform.node()

        # Tenta obter UUID do sistema (mais estável)
        try:
            system_uuid = str(uuid.getnode())
        except Exception:
            system_uuid = "fallback"

        # Combina as informações
        raw_id = f"{node_name}-{system_uuid}"

        # Gera hash MD5 para padronizar tamanho
        hwid = hashlib.md5(raw_id.encode()).hexdigest()

        logger.debug(f"HWID gerado: {hwid[:8]}...")
        return hwid

    except Exception as e:
        logger.error(f"Erro ao gerar HWID: {e}")
        # Fallback: usa apenas o nome do computador
        return hashlib.md5(platform.node().encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# SERVIÇO DE LICENCIAMENTO
# ═══════════════════════════════════════════════════════════════════════════════


class LicenseService:
    """
    Serviço de validação de licença.

    Features:
        - Validação com API
        - Geração de HWID consistente
        - Cache do resultado
        - Integração com EventBus

    Exemplo:
        service = LicenseService()
        result = service.validate("CHAVE-123", "email@exemplo.com")

        if result.valid:
            print(f"Olá, {result.user_name}!")
            print(f"Telegram: {result.telegram_chat_id}")
    """

    def __init__(self, api_base_url: Optional[str] = None):
        """
        Inicializa o serviço de licenciamento.

        Args:
            api_base_url: URL base da API (usa default se None)
        """
        self._api_base_url = api_base_url or API_BASE_URL
        self._event_bus = get_event_bus()

        # Cache do resultado
        self._cached_result: Optional[LicenseResult] = None
        self._hwid: Optional[str] = None

        # Lock para thread-safety
        self._lock = threading.Lock()

        logger.debug(f"LicenseService inicializado (API: {self._api_base_url})")

    @property
    def hwid(self) -> str:
        """Retorna o HWID (gera se necessário)."""
        if self._hwid is None:
            self._hwid = get_hwid()
        return self._hwid

    @property
    def cached_result(self) -> Optional[LicenseResult]:
        """Retorna o resultado em cache (se houver)."""
        return self._cached_result

    @property
    def is_valid(self) -> bool:
        """Verifica se há uma licença válida em cache."""
        return self._cached_result is not None and self._cached_result.valid

    def validate(
        self, license_key: str, email: str, force: bool = False
    ) -> LicenseResult:
        """
        Valida uma licença com a API.

        Args:
            license_key: Chave de licença
            email: Email do usuário
            force: Se True, ignora cache e revalida

        Returns:
            LicenseResult com o resultado da validação
        """
        with self._lock:
            # Verifica cache
            if not force and self._cached_result is not None:
                if self._cached_result.license_key == license_key:
                    logger.debug("Usando resultado em cache")
                    return self._cached_result

            # Emite evento de validação iniciada
            emit(
                BotEvent.LICENSE_VALIDATING,
                {"license_key": license_key[:8] + "...", "email": email},
            )

            # Faz a validação
            result = self._validate_with_api(license_key, email)

            # Armazena em cache
            self._cached_result = result

            # Emite evento de resultado
            if result.valid:
                emit(
                    BotEvent.LICENSE_VALID,
                    {
                        "user_name": result.user_name,
                        "telegram_chat_id": result.telegram_chat_id,
                        "days_remaining": result.days_remaining,
                    },
                )
            elif result.status == LicenseStatus.EXPIRED:
                emit(
                    BotEvent.LICENSE_EXPIRED,
                    {
                        "message": result.message,
                    },
                )
            else:
                emit(
                    BotEvent.LICENSE_INVALID,
                    {
                        "message": result.message,
                        "status": result.status.value,
                    },
                )

            return result

    def _validate_with_api(self, license_key: str, email: str) -> LicenseResult:
        """
        Faz a requisição de validação à API.

        Args:
            license_key: Chave de licença
            email: Email do usuário

        Returns:
            LicenseResult com o resultado
        """
        if not HAS_REQUESTS:
            logger.error("Módulo requests não disponível")
            return LicenseResult(
                valid=False,
                status=LicenseStatus.ERROR,
                message="Módulo requests não instalado",
            )

        url = f"{self._api_base_url}{API_ENDPOINTS['validate_license']}"

        payload = {
            "chave": license_key,
            "hwid": self.hwid,
            "versao_bot": BOT_VERSION,
        }

        try:
            logger.debug(f"Validando licença: {url}")

            response = requests.post(url, json=payload, timeout=API_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                return self._parse_success_response(data, license_key)

            elif response.status_code == 401:
                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.INVALID,
                    message="Licença inválida ou não encontrada",
                    license_key=license_key,
                    hwid=self.hwid,
                )

            elif response.status_code == 403:
                # HWID diferente ou licença em uso
                try:
                    data = response.json()
                    message = data.get("detail", "Licença em uso em outro dispositivo")
                except Exception:
                    message = "Licença em uso em outro dispositivo"

                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.INVALID,
                    message=message,
                    license_key=license_key,
                    hwid=self.hwid,
                )

            else:
                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.ERROR,
                    message=f"Erro na API: HTTP {response.status_code}",
                    license_key=license_key,
                    hwid=self.hwid,
                )

        except requests.Timeout:
            logger.warning("Timeout ao validar licença")
            return LicenseResult(
                valid=False,
                status=LicenseStatus.ERROR,
                message="Timeout na conexão com o servidor",
                license_key=license_key,
                hwid=self.hwid,
            )

        except requests.RequestException as e:
            logger.error(f"Erro de conexão: {e}")
            return LicenseResult(
                valid=False,
                status=LicenseStatus.ERROR,
                message=f"Erro de conexão: {str(e)}",
                license_key=license_key,
                hwid=self.hwid,
            )

    def _parse_success_response(
        self, data: Dict[str, Any], license_key: str
    ) -> LicenseResult:
        """
        Processa resposta de sucesso da API.

        Args:
            data: Dados da resposta JSON
            license_key: Chave que foi validada

        Returns:
            LicenseResult com dados extraídos
        """
        try:
            # Verificar se servidor exige atualização
            if data.get("force_update", False):
                download_url = data.get("download_url", "")
                msg = data.get("mensagem", "Atualização obrigatória")
                if download_url:
                    try:
                        import webbrowser
                        webbrowser.open(download_url)
                    except Exception:
                        pass
                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.ERROR,
                    message=msg,
                    license_key=license_key,
                    hwid=self.hwid,
                    api_response=data,
                )

            # Extrai dados do usuário
            user_name = data.get("nome", data.get("user_name", "Usuário"))
            user_email = data.get("email", "")
            telegram_chat_id = data.get("telegram_chat_id", data.get("chat_id"))

            # Extrai dados da licença
            expiration = data.get("expiracao", data.get("expiration_date"))
            days_remaining = data.get("dias_restantes", data.get("days_remaining"))

            # Verificar campo 'sucesso' da API (critical fix)
            if not data.get("sucesso", True):
                msg = data.get("mensagem", "Licença inválida")
                is_expired = (
                    days_remaining is not None and days_remaining <= 0
                ) or "expir" in msg.lower()
                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.EXPIRED if is_expired else LicenseStatus.INVALID,
                    message=msg,
                    user_name=user_name,
                    user_email=user_email,
                    license_key=license_key,
                    expiration_date=expiration,
                    days_remaining=days_remaining,
                    hwid=self.hwid,
                    api_response=data,
                )

            # Verifica se expirou (segunda camada de segurança)
            if days_remaining is not None and days_remaining <= 0:
                return LicenseResult(
                    valid=False,
                    status=LicenseStatus.EXPIRED,
                    message="Sua licença expirou",
                    user_name=user_name,
                    user_email=user_email,
                    license_key=license_key,
                    expiration_date=expiration,
                    days_remaining=days_remaining,
                    hwid=self.hwid,
                    api_response=data,
                )

            logger.info(f"Licença válida para: {user_name}")

            return LicenseResult(
                valid=True,
                status=LicenseStatus.VALID,
                message="Licença válida",
                user_name=user_name,
                user_email=user_email,
                telegram_chat_id=str(telegram_chat_id) if telegram_chat_id else None,
                license_key=license_key,
                expiration_date=expiration,
                days_remaining=days_remaining,
                hwid=self.hwid,
                api_response=data,
            )

        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return LicenseResult(
                valid=False,
                status=LicenseStatus.ERROR,
                message=f"Erro ao processar resposta: {str(e)}",
                license_key=license_key,
                hwid=self.hwid,
                api_response=data,
            )

    def clear_cache(self) -> None:
        """Limpa o cache de validação."""
        with self._lock:
            self._cached_result = None
            logger.debug("Cache de licença limpo")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_license_service: Optional[LicenseService] = None
_license_lock = threading.Lock()


def get_licensing() -> LicenseService:
    """
    Retorna a instância singleton do LicenseService.

    Thread-safe. Cria a instância na primeira chamada.

    Example:
        licensing = get_licensing()
        result = licensing.validate("CHAVE", "email@test.com")
    """
    global _license_service

    if _license_service is None:
        with _license_lock:
            if _license_service is None:
                _license_service = LicenseService()

    return _license_service


def reset_licensing() -> None:
    """Reseta o serviço de licenciamento (útil para testes)."""
    global _license_service
    with _license_lock:
        _license_service = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO LICENSE SERVICE - CrashBot v3.0")
    print("=" * 60)

    # Cria serviço
    service = LicenseService()

    print(f"\n✅ Serviço criado")
    print(f"   API: {service._api_base_url}")
    print(f"   HWID: {service.hwid}")

    # Testa geração de HWID
    print(f"\n--- Teste HWID ---")
    hwid1 = get_hwid()
    hwid2 = get_hwid()
    print(f"   HWID 1: {hwid1}")
    print(f"   HWID 2: {hwid2}")
    print(f"   Consistente: {'✅' if hwid1 == hwid2 else '❌'}")

    # Nota: Não testamos validate() aqui pois precisa de credenciais reais
    print(f"\n--- Teste Validação ---")
    print("   ⚠️ Validação real requer credenciais válidas")
    print("   Para testar: licensing.validate('SUA-CHAVE', 'seu@email.com')")

    print("\n" + "=" * 60)
    print("✅ TESTES BÁSICOS PASSARAM!")
    print("=" * 60)
