"""WebSocket endpoint for real-time approval notifications and workflow status."""

import contextlib

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger()

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections per org."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}  # org_id -> connections

    async def connect(self, websocket: WebSocket, org_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(org_id, []).append(websocket)
        logger.info("ws.connected", org_id=org_id)

    def disconnect(self, websocket: WebSocket, org_id: str) -> None:
        conns = self.active_connections.get(org_id, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info("ws.disconnected", org_id=org_id)

    async def broadcast_to_org(self, org_id: str, message: dict) -> None:
        """Send message to all connections for an org."""
        for conn in self.active_connections.get(org_id, []):
            with contextlib.suppress(Exception):
                await conn.send_json(message)


manager = ConnectionManager()


@router.websocket("/api/v1/ws/{org_id}")
async def websocket_endpoint(websocket: WebSocket, org_id: str) -> None:
    """WebSocket for real-time approval notifications and workflow status.

    In production, also subscribes to Redis pub/sub for the org's channel.
    """
    await manager.connect(websocket, org_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Echo back for now; in production, handle subscription requests
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
