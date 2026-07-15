"""WebSocket API endpoint for real-time updates."""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.auth.manager import get_auth_manager
from core.config.settings import get_settings
from core.websocket import get_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Stream real-time updates to authenticated Web UI clients."""
    settings = get_settings()
    if settings.require_auth:
        token = websocket.query_params.get("token")
        if not token or not get_auth_manager().verify_token(token):
            await websocket.close(code=4401, reason="Authentication required")
            return

    manager = get_connection_manager()
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connection established",
                "client_id": client_id,
            }
        )
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        await manager.disconnect(websocket, client_id)
