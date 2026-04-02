"""
Service: Google Calendar
Gerencia agendamentos de treinamento via Google Calendar API.
"""

import json
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
        """Carrega tokens da Variável de Ambiente (Render) ou arquivo local."""
        try:
            # 1. TENTA LER DA VARIÁVEL DE AMBIENTE (PRIORIDADE NO SERVIDOR)
            env_token = os.getenv("GOOGLE_TOKEN_JSON_CONTENT")
            if env_token:
                print("🔹 Carregando tokens via Variável de Ambiente (Render)...")
                data = json.loads(env_token)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                return

            # 2. SE NÃO TIVER VARIÁVEL, TENTA LER DO ARQUIVO (LOCAL)
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
            else:
                print("⚠️ Nenhum token encontrado (Nem arquivo, nem ENV).")

        except Exception as e:
            print(f"❌ Erro ao carregar tokens: {e}")

    def _save_tokens(self):
        """Salva tokens no arquivo (Apenas localmente)."""
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
            # No Render, pode dar erro de permissão de escrita, o que é normal e ignorável
            print(f"Aviso: Não foi possível salvar token no disco: {e}")

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
            return {"error": "Não autenticado. Configure GOOGLE_TOKEN_JSON_CONTENT."}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await getattr(client, method)(url, headers=headers, **kwargs)

            # Se token expirou (401), tenta renovar
            if response.status_code == 401:
                print("🔄 Token expirado. Tentando renovar...")
                if await self.refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    response = await getattr(client, method)(
                        url, headers=headers, **kwargs
                    )
                else:
                    return {"error": "Token expirado e falha na renovação."}

            if response.status_code in [200, 201, 204]:
                if response.status_code == 204:
                    return {}
                return response.json()
            else:
                return {"error": f"Google API Erro: {response.text}"}

    async def _buscar_eventos_ocupados(
        self, data_inicio: datetime, data_fim: datetime
    ) -> list[tuple[datetime, datetime]]:
        """
        Método auxiliar: Busca eventos na API e retorna lista de tuplas.
        """
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        params = {
            "timeMin": f"{data_inicio.isoformat()}Z",
            "timeMax": f"{data_fim.isoformat()}Z",
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        result = await self._make_request("get", url, params=params)

        if "error" in result:
            return []

        eventos_processados = []
        for evento in result.get("items", []):
            inicio_str = evento.get("start", {}).get("dateTime")
            fim_str = evento.get("end", {}).get("dateTime")

            if inicio_str and fim_str:
                # Remove o Z e converte para naive para facilitar comparação local
                inicio_dt = datetime.fromisoformat(
                    inicio_str.replace("Z", "+00:00")
                ).replace(tzinfo=None)

                fim_dt = datetime.fromisoformat(fim_str.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )

                eventos_processados.append((inicio_dt, fim_dt))

        return eventos_processados

    def _verificar_colisao(
        self,
        slot_inicio: datetime,
        slot_fim: datetime,
        eventos_ocupados: list[tuple[datetime, datetime]],
    ) -> bool:
        """Verifica se um slot colide com algum evento."""
        return any(
            slot_inicio < evt_fim and slot_fim > evt_inicio
            for evt_inicio, evt_fim in eventos_ocupados
        )

    async def listar_horarios_disponiveis(
        self,
        data_inicio: datetime,
        data_fim: datetime,
    ) -> dict:
        """Lista horários disponíveis para agendamento."""
        eventos_ocupados = await self._buscar_eventos_ocupados(data_inicio, data_fim)
        slots_disponiveis = []

        # Começa as 10h
        current = data_inicio.replace(hour=10, minute=0, second=0, microsecond=0)

        while current < data_fim:
            if current.weekday() < 5:  # Seg-Sex
                if 10 <= current.hour < 18:  # 10h as 18h
                    slot_fim = current + timedelta(minutes=30)
                    if not self._verificar_colisao(current, slot_fim, eventos_ocupados):
                        slots_disponiveis.append(
                            {
                                "inicio": current.isoformat(),
                                "fim": slot_fim.isoformat(),
                                "disponivel": True,
                            }
                        )

            current += timedelta(minutes=30)
            if current.hour >= 18:
                current += timedelta(days=1)
                current = current.replace(hour=10, minute=0)

        return {"slots": slots_disponiveis, "total": len(slots_disponiveis)}

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
        """Cria evento no Google Calendar com Meet."""
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

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
                "dateTime": data_hora.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {"dateTime": fim.isoformat(), "timeZone": "America/Sao_Paulo"},
            "conferenceData": {
                "createRequest": {
                    "requestId": f"crashbot-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                },
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60 * 24},
                    {"method": "popup", "minutes": 60},
                ],
            },
        }

        if email_convidado:
            evento["attendees"] = [{"email": email_convidado}]

        # URL com parâmetro para criar o Meet
        full_url = f"{url}?conferenceDataVersion=1&sendUpdates=all"

        result = await self._make_request("post", full_url, json=evento)

        if "error" in result:
            return result

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
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{evento_id}"
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.delete(url, headers=headers)
            if response.status_code == 204:
                return {"success": True, "message": "Agendamento cancelado"}
            return {"success": False, "message": response.text}

    def is_authenticated(self) -> bool:
        return self.access_token is not None


# Instância global
google_calendar = GoogleCalendarService()
