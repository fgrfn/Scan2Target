"""WebSocket connection manager for real-time updates."""
import logging
from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str = "default"):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = set()
            self.active_connections[client_id].add(websocket)
        logger.debug(f"WebSocket connected: {client_id} (total: {self.get_connection_count()})")
    
    async def disconnect(self, websocket: WebSocket, client_id: str = "default"):
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].discard(websocket)
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
        logger.debug(f"WebSocket disconnected: {client_id} (total: {self.get_connection_count()})")
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    async def broadcast(self, message: dict, client_id: str = None):
        """
        Broadcast a message to connected clients.
        
        Args:
            message: Dictionary to send as JSON
            client_id: If specified, send only to this client. Otherwise broadcast to all.
        """
        message_json = json.dumps(message)
        
        async with self._lock:
            if client_id and client_id in self.active_connections:
                # Send to specific client
                disconnected = set()
                for connection in self.active_connections[client_id]:
                    try:
                        await connection.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error sending to {client_id}: {e}")
                        disconnected.add(connection)
                
                # Clean up disconnected
                for conn in disconnected:
                    self.active_connections[client_id].discard(conn)
            else:
                # Broadcast to all clients
                all_connections = []
                for conns in self.active_connections.values():
                    all_connections.extend(conns)
                
                disconnected = []
                for connection in all_connections:
                    try:
                        await connection.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error broadcasting: {e}")
                        disconnected.append(connection)
                
                # Clean up disconnected
                for conn in disconnected:
                    for client_conns in self.active_connections.values():
                        client_conns.discard(conn)
    
    async def send_job_update(self, job_data: dict):
        """Send a job status update to all connected clients."""
        await self.broadcast({
            "type": "job_update",
            "data": job_data
        })
    
    async def send_scanner_update(self, scanner_data: dict):
        """Send a scanner status update to all connected clients."""
        await self.broadcast({
            "type": "scanner_update",
            "data": scanner_data
        })


# Global connection manager instance
_manager: ConnectionManager = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global WebSocket connection manager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
