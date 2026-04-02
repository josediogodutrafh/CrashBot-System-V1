"""
Service: Verificação WhatsApp
Gerencia envio e validação de códigos de verificação via WhatsApp.
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# Armazenamento temporário de códigos (em produção, usar Redis ou banco)
# Formato: {whatsapp: {"codigo": "123456", "expira": datetime, "tentativas": 0}}
_codigos_pendentes: dict = {}


class WhatsAppVerificationService:
    """Serviço de verificação de WhatsApp por código."""

    def __init__(self):
        self.instance_id = os.getenv("ZAPI_INSTANCE_ID")
        self.token = os.getenv("ZAPI_TOKEN")
        self.codigo_tamanho = 6
        self.codigo_validade_minutos = 10
        self.max_tentativas = 3

    def _gerar_codigo(self) -> str:
        """Gera código numérico de 6 dígitos."""
        return "".join(random.choices(string.digits, k=self.codigo_tamanho))

    def _formatar_telefone(self, telefone: str) -> str:
        """Formata telefone para padrão internacional."""
        # Remove tudo que não é dígito
        phone = "".join(filter(str.isdigit, telefone))
        
        # Adiciona código do Brasil se necessário
        if len(phone) == 11:  # DDD + número
            phone = f"55{phone}"
        elif len(phone) == 10:  # DDD + número antigo (8 dígitos)
            phone = f"55{phone}"
        
        return phone

    async def enviar_codigo(self, whatsapp: str) -> dict:
        """
        Envia código de verificação via WhatsApp.
        
        Args:
            whatsapp: Número do WhatsApp
            
        Returns:
            dict: {"sucesso": bool, "mensagem": str}
        """
        if not self.instance_id or not self.token:
            return {
                "sucesso": False,
                "mensagem": "Serviço de WhatsApp não configurado"
            }

        # Gerar código
        codigo = self._gerar_codigo()
        telefone_formatado = self._formatar_telefone(whatsapp)
        
        # Salvar código com expiração
        _codigos_pendentes[telefone_formatado] = {
            "codigo": codigo,
            "expira": datetime.now(timezone.utc) + timedelta(minutes=self.codigo_validade_minutos),
            "tentativas": 0,
            "whatsapp_original": whatsapp
        }

        # Montar mensagem
        mensagem = f""" *CrashBot - Código de Verificação*

Seu código de verificação é:

*{codigo}*

 Este código expira em {self.codigo_validade_minutos} minutos.

 Se você não solicitou este código, ignore esta mensagem."""

        # Enviar via Z-API
        url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.token}/send-text"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={"phone": telefone_formatado, "message": mensagem},
                    timeout=15.0,
                )
                
                if response.status_code == 200:
                    print(f" Código enviado para {telefone_formatado}")
                    return {
                        "sucesso": True,
                        "mensagem": "Código enviado! Verifique seu WhatsApp."
                    }
                else:
                    print(f" Erro Z-API: {response.status_code} - {response.text}")
                    return {
                        "sucesso": False,
                        "mensagem": "Erro ao enviar código. Verifique o número."
                    }
                    
        except Exception as e:
            print(f" Erro ao enviar código: {e}")
            return {
                "sucesso": False,
                "mensagem": f"Erro de conexão: {str(e)}"
            }

    def validar_codigo(self, whatsapp: str, codigo: str) -> dict:
        """
        Valida código de verificação.
        
        Args:
            whatsapp: Número do WhatsApp
            codigo: Código digitado pelo usuário
            
        Returns:
            dict: {"valido": bool, "mensagem": str}
        """
        telefone_formatado = self._formatar_telefone(whatsapp)
        
        # Verificar se existe código pendente
        dados = _codigos_pendentes.get(telefone_formatado)
        
        if not dados:
            return {
                "valido": False,
                "mensagem": "Nenhum código pendente. Solicite um novo código."
            }

        # Verificar expiração
        if datetime.now(timezone.utc) > dados["expira"]:
            del _codigos_pendentes[telefone_formatado]
            return {
                "valido": False,
                "mensagem": "Código expirado. Solicite um novo código."
            }

        # Verificar tentativas
        if dados["tentativas"] >= self.max_tentativas:
            del _codigos_pendentes[telefone_formatado]
            return {
                "valido": False,
                "mensagem": "Muitas tentativas. Solicite um novo código."
            }

        # Incrementar tentativas
        dados["tentativas"] += 1

        # Validar código
        if codigo == dados["codigo"]:
            del _codigos_pendentes[telefone_formatado]
            return {
                "valido": True,
                "mensagem": "Código válido!"
            }
        else:
            tentativas_restantes = self.max_tentativas - dados["tentativas"]
            return {
                "valido": False,
                "mensagem": f"Código incorreto. {tentativas_restantes} tentativas restantes."
            }

    def limpar_codigos_expirados(self):
        """Remove códigos expirados do armazenamento."""
        agora = datetime.now(timezone.utc)
        expirados = [
            tel for tel, dados in _codigos_pendentes.items()
            if agora > dados["expira"]
        ]
        for tel in expirados:
            del _codigos_pendentes[tel]


# Instância global
whatsapp_verification = WhatsAppVerificationService()
