"""WebSocket API endpoint for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket import get_connection_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job and scanner updates.
    
    Connect to: ws://localhost/api/v1/ws
    
    Message types received:
    - job_update: Job status changes
    - scanner_update: Scanner availability changes
    
    Example message:
    {
        "type": "job_update",
        "data": {
            "id": "job-uuid",
            "status": "completed",
            "device_id": "scanner_1",
            "target_id": "target_1",
            ...
        }
    }
    """
    manager = get_connection_manager()
    client_id = f"client_{id(websocket)}"
    
    await manager.connect(websocket, client_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "client_id": client_id
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (like ping/pong)
            data = await websocket.receive_text()
            
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket, client_id)
