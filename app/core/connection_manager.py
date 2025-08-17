from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # { chatroom_id: [WebSocket, WebSocket, ...] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, chatroom_id: int, websocket: WebSocket):
        await websocket.accept()
        if chatroom_id not in self.active_connections:
            self.active_connections[chatroom_id] = []
        self.active_connections[chatroom_id].append(websocket)

    def disconnect(self, chatroom_id: int, websocket: WebSocket):
        if chatroom_id in self.active_connections:
            self.active_connections[chatroom_id].remove(websocket)
            if not self.active_connections[chatroom_id]:  # No more users in room
                del self.active_connections[chatroom_id]

    async def broadcast(self, chatroom_id: int, message: dict):
        print("Broadcasting to room:", chatroom_id, "message:", message)

        if chatroom_id in self.active_connections:
            for connection in self.active_connections[chatroom_id]:
                await connection.send_json(message)


manager = ConnectionManager()