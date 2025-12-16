"""
Service: Google Calendar
Gerencia agendamentos de treinamento via Google Calendar API.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class GoogleCalendarService:
    """Serviço de integração com Google Calendar."""

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        self.token_file = "google_token.json"

        # Tokens (carregados do arquivo ou obtidos via OAuth)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

        # Carregar tokens salvos
        self._load_tokens()

    def _load_tokens(self):
        """Carrega tokens salvos do arquivo."""
        import json

        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
        except Exception as e:
            print(f"Erro ao carregar tokens: {e}")

    def _save_tokens(self):
        """Salva tokens no arquivo."""
        import json

        try:
            with open(self.token_file, "w") as f:
                json.dump(
                    {
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                    },
                    f,
                )
        except Exception as e:
            print(f"Erro ao salvar tokens: {e}")

    def get_auth_url(self) -> str:
        """Gera URL para autorização OAuth."""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar",
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Troca código de autorização por tokens."""
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code != 200:
                return {"success": False, "message": f"Erro: {response.text}"}

            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.refresh_token = tokens.get("refresh_token")
            self._save_tokens()
            return {
                "success": True,
                "message": "Autenticação realizada com sucesso!",
            }

    async def refresh_access_token(self) -> bool:
        """Renova o access token usando o refresh token."""
        if not self.refresh_token:
            return False

        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access_token")
                self._save_tokens()
                return True
            return False

    async def _make_request(self, method: str, url: str, **kwargs) -> dict:
        """Faz requisição autenticada para a API do Google."""
        if not self.access_token:
            return {"error": "Não autenticado. Acesse /api/v1/calendar/auth"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await getattr(client, method)(url, headers=headers, **kwargs)

            # Se token expirou, tenta renovar
            if response.status_code == 401:
                if await self.refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    response = await getattr(client, method)(
                        url, headers=headers, **kwargs
                    )
                else:
                    return {
                        "error": (
                            "Token expirado. " "Reautentique em /api/v1/calendar/auth"
                        )
                    }

            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": response.text}

    async def listar_horarios_disponiveis(
        self,
        data_inicio: datetime,
        data_fim: datetime,
    ) -> dict:
        """
        Lista horários disponíveis para agendamento.
        Busca eventos existentes e retorna slots livres.
        """
        # Buscar eventos existentes no período
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        params = {
            "timeMin": f"{data_inicio.isoformat()}Z",
            "timeMax": f"{data_fim.isoformat()}Z",
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        result = await self._make_request("get", url, params=params)

        if "error" in result:
            return result

        eventos_ocupados = []
        for evento in result.get("items", []):
            inicio = evento.get("start", {}).get("dateTime")
            fim = evento.get("end", {}).get("dateTime")
            if inicio and fim:
                eventos_ocupados.append(
                    {
                        "inicio": inicio,
                        "fim": fim,
                        "titulo": evento.get("summary", "Ocupado"),
                    }
                )

        # Gerar slots disponíveis (10h às 18h, 30min cada)
        slots_disponiveis = []
        current = data_inicio.replace(hour=10, minute=0, second=0, microsecond=0)

        while current < data_fim:
            # Pular fins de semana
            if current.weekday() < 5:  # Segunda a Sexta
                hora = current.hour
                if 10 <= hora < 18:  # 10h às 18h
                    slot_fim = current + timedelta(minutes=30)

                    # Verificar se slot está ocupado
                    ocupado = False
                    for evento in eventos_ocupados:
                        evt_inicio = datetime.fromisoformat(
                            evento["inicio"].replace("Z", "+00:00")
                        ).replace(tzinfo=None)

                        evt_fim = datetime.fromisoformat(
                            evento["fim"].replace("Z", "+00:00")
                        ).replace(tzinfo=None)

                        # Verifica sobreposição (De Morgan: not (A or B))
                        # Se o slot termina depois que o evento começa E
                        # o slot começa antes do evento terminar -> Colisão
                        if slot_fim > evt_inicio and current < evt_fim:
                            ocupado = True
                            break

                    if not ocupado:
                        slots_disponiveis.append(
                            {
                                "inicio": current.isoformat(),
                                "fim": slot_fim.isoformat(),
                                "disponivel": True,
                            }
                        )

            current += timedelta(minutes=30)

        return {
            "slots": slots_disponiveis,
            "total": len(slots_disponiveis),
        }

    async def criar_agendamento(
        self,
        titulo: str,
        descricao: str,
        data_hora: datetime,
        duracao_minutos: int = 30,
        email_convidado: Optional[str] = None,
        nome_convidado: Optional[str] = None,
        whatsapp_convidado: Optional[str] = None,
    ) -> dict:
        """
        Cria um evento de treinamento no Google Calendar.
        Automaticamente adiciona Google Meet.
        """
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

        # Horário de Brasília (UTC-3)
        inicio = data_hora
        fim = data_hora + timedelta(minutes=duracao_minutos)

        descricao_completa = f"""
 TREINAMENTO CRASHBOT

 Cliente: {nome_convidado or 'N/A'}
 Email: {email_convidado or 'N/A'}
 WhatsApp: {whatsapp_convidado or 'N/A'}

{descricao}

---
Agendado automaticamente via CrashBot
        """.strip()

        evento = {
            "summary": titulo,
            "description": descricao_completa,
            "start": {
                "dateTime": inicio.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": fim.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "America/Sao_Paulo",
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": f"crashbot-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                },
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60 * 24},  # 24h antes
                    {"method": "popup", "minutes": 60},  # 1h antes
                ],
            },
        }

        # Adicionar convidado se tiver email
        if email_convidado:
            evento["attendees"] = [{"email": email_convidado}]

        # Criar evento com conferência
        result = await self._make_request(
            "post",
            f"{url}?conferenceDataVersion=1&sendUpdates=all",
            json=evento,
        )

        if "error" in result:
            return result

        # Extrair link do Meet
        meet_link = None
        if "conferenceData" in result:
            entry_points = result["conferenceData"].get("entryPoints", [])
            for entry in entry_points:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break

        return {
            "success": True,
            "evento_id": result.get("id"),
            "titulo": result.get("summary"),
            "inicio": result.get("start", {}).get("dateTime"),
            "fim": result.get("end", {}).get("dateTime"),
            "meet_link": meet_link,
            "link_evento": result.get("htmlLink"),
        }

    async def cancelar_agendamento(self, evento_id: str) -> dict:
        """Cancela um agendamento existente."""
        url = (
            "https://www.googleapis.com/calendar/v3/calendars/primary/events/"
            f"{evento_id}"
        )

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.delete(url, headers=headers)

            if response.status_code == 204:
                return {"success": True, "message": "Agendamento cancelado"}
            else:
                return {"success": False, "message": response.text}

    def is_authenticated(self) -> bool:
        """Verifica se está autenticado."""
        return self.access_token is not None


# Instância global
google_calendar = GoogleCalendarService()
