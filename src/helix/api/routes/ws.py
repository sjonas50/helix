"""WebSocket endpoint for real-time approval notifications and workflow status.

Requires JWT authentication via query parameter (WebSocket doesn't support
Authorization headers in browser clients).
"""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from helix.auth.tokens import decode_token, validate_token_claims

logger = structlog.get_logger()

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections per org."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

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
            try:
                await conn.send_json(message)
            except Exception:
                logger.warning("ws.broadcast_failed", org_id=org_id)


manager = ConnectionManager()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    """Authenticated WebSocket for real-time notifications.

    Connect with: ws://host/api/v1/ws?token=<jwt>
    The token is validated and org_id is extracted from claims.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    try:
        claims = decode_token(token)
        is_valid, error = validate_token_claims(claims)
        if not is_valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=error)
            return
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    org_id = claims.org_id
    await manager.connect(websocket, org_id)
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
