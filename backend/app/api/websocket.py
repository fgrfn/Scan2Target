from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws.manager import get_ws_manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    manager = get_ws_manager()
    client_id = await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(client_id)
