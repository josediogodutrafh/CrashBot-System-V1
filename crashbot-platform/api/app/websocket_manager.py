"""
WebSocket Manager - Gerenciamento de conexões WebSocket
"""

from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """
    Gerencia conexões WebSocket.
    
    Permite criar "rooms" (salas) para diferentes usuários/grupos
    e fazer broadcast de mensagens para conexões específicas.
    """

    def __init__(self):
        """Inicializa o gerenciador."""
        # Dicionário de rooms: {room_name: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        """
        Aceita uma nova conexão WebSocket e adiciona a uma room.

        Args:
            websocket: Conexão WebSocket
            room: Nome da room (ex: "admin", "user_123")
        """
        await websocket.accept()
        
        if room not in self.active_connections:
            self.active_connections[room] = []
        
        self.active_connections[room].append(websocket)
        print(f"✅ Nova conexão na room '{room}'. Total: {len(self.active_connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str):
        """
        Remove uma conexão WebSocket de uma room.

        Args:
            websocket: Conexão WebSocket
            room: Nome da room
        """
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)
                print(f"❌ Conexão removida da room '{room}'. Restantes: {len(self.active_connections[room])}")
                
                # Remover room se vazia
                if len(self.active_connections[room]) == 0:
                    del self.active_connections[room]
                    print(f"🗑️  Room '{room}' removida (vazia)")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Envia mensagem para uma conexão específica.

        Args:
            message: Mensagem (será convertida para JSON)
            websocket: Conexão WebSocket destinatária
        """
        await websocket.send_json(message)

    async def broadcast(self, message: dict, room: str):
        """
        Envia mensagem para todas as conexões de uma room.

        Args:
            message: Mensagem (será convertida para JSON)
            room: Nome da room
        """
        if room not in self.active_connections:
            return

        # Lista de conexões mortas para remover depois
        dead_connections = []

        for connection in self.active_connections[room]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"⚠️  Erro ao enviar mensagem: {e}")
                dead_connections.append(connection)

        # Remover conexões mortas
        for dead in dead_connections:
            self.disconnect(dead, room)

    async def broadcast_all(self, message: dict):
        """
        Envia mensagem para TODAS as conexões de TODAS as rooms.

        Args:
            message: Mensagem (será convertida para JSON)
        """
        for room in list(self.active_connections.keys()):
            await self.broadcast(message, room)

    def get_room_count(self, room: str) -> int:
        """
        Retorna número de conexões em uma room.

        Args:
            room: Nome da room

        Returns:
            int: Número de conexões
        """
        if room not in self.active_connections:
            return 0
        return len(self.active_connections[room])

    def get_total_connections(self) -> int:
        """
        Retorna número total de conexões ativas.

        Returns:
            int: Total de conexões
        """
        return sum(len(connections) for connections in self.active_connections.values())


# Instância global do gerenciador
manager = ConnectionManager()
