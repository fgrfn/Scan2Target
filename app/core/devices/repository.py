"""Device repository for managing printers and scanners in database."""
from typing import List, Optional
from datetime import datetime
import json

from core.database import get_db


class DeviceRecord:
    """Device data model."""
    
    def __init__(
        self,
        id: str,
        device_type: str,
        name: str,
        uri: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        connection_type: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        is_favorite: bool = False,
        last_seen: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.device_type = device_type  # 'printer' or 'scanner'
        self.name = name
        self.uri = uri
        self.make = make
        self.model = model
        self.connection_type = connection_type
        self.description = description
        self.is_active = is_active
        self.is_favorite = is_favorite
        self.last_seen = last_seen
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'device_type': self.device_type,
            'name': self.name,
            'uri': self.uri,
            'make': self.make,
            'model': self.model,
            'connection_type': self.connection_type,
            'description': self.description,
            'is_active': self.is_active,
            'is_favorite': self.is_favorite,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DeviceRepository:
    """Repository for device persistence."""
    
    def __init__(self):
        self.db = get_db()
    
    def add_device(self, device: DeviceRecord) -> None:
        """Add a new device to the database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO devices 
                (id, device_type, name, uri, make, model, connection_type, description, is_active, is_favorite, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                device.id,
                device.device_type,
                device.name,
                device.uri,
                device.make,
                device.model,
                device.connection_type,
                device.description,
                1 if device.is_active else 0,
                1 if device.is_favorite else 0
            ))
    
    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        """Get a device by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_device(row)
            return None
    
    def list_devices(self, device_type: Optional[str] = None, active_only: bool = True) -> List[DeviceRecord]:
        """
        List all devices.
        
        Args:
            device_type: Filter by 'printer' or 'scanner' (None = all)
            active_only: Only return active devices
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM devices WHERE 1=1"
            params = []
            
            if device_type:
                query += " AND device_type = ?"
                params.append(device_type)
            
            if active_only:
                query += " AND is_active = 1"
            
            query += " ORDER BY is_favorite DESC, created_at DESC"
            
            cursor.execute(query, params)
            return [self._row_to_device(row) for row in cursor.fetchall()]
    
    def device_exists(self, uri: str) -> bool:
        """Check if a device with this URI already exists."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM devices WHERE uri = ?", (uri,))
            row = cursor.fetchone()
            return row['count'] > 0
    
    def update_last_seen(self, device_id: str) -> None:
        """Update the last_seen timestamp for a device."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices 
                SET last_seen = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (device_id,))
    
    def remove_device(self, device_id: str) -> bool:
        """
        Remove a device from the database.
        
        Returns:
            True if device was removed, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            return cursor.rowcount > 0
    
    def deactivate_device(self, device_id: str) -> bool:
        """
        Mark a device as inactive (soft delete).
        
        Returns:
            True if device was deactivated, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (device_id,))
            return cursor.rowcount > 0
    
    def _row_to_device(self, row) -> DeviceRecord:
        """Convert database row to DeviceRecord."""
        return DeviceRecord(
            id=row['id'],
            device_type=row['device_type'],
            name=row['name'],
            uri=row['uri'],
            make=row['make'],
            model=row['model'],
            connection_type=row['connection_type'],
            description=row['description'],
            is_active=bool(row['is_active']),
            is_favorite=bool(row['is_favorite']) if 'is_favorite' in row.keys() else False,
            last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
