"""WebSocket endpoint for real-time dashboard updates."""
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str = None):
    """WebSocket for real-time dashboard updates. Auth via query token or first message."""
    # For dev: accept without token; in production validate JWT from token= or first message
    user_id = token or "anonymous"
    await manager.connect(websocket, user_id)
    try:
        await manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_id,
        )
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(
                {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                user_id,
            )
            # Simulate periodic metrics update (in production: Kafka/queue)
            import asyncio
            await asyncio.sleep(30)
            await manager.send_personal_message(
                {
                    "type": "metrics_update",
                    "data": {
                        "new_emails": 5,
                        "new_spam": 2,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
                user_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)
