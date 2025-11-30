"""Target persistence repository."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
import json

from app.core.database import get_db
from app.core.targets.models import TargetConfig


class TargetRepository:
    """Repository for target persistence."""
    
    def __init__(self):
        self.db = get_db()
    
    def create(self, target: TargetConfig) -> TargetConfig:
        """Create a new target in the database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO targets (id, type, name, config, enabled, description, is_favorite, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                target.id,
                target.type,
                target.name,
                json.dumps(target.config),
                1 if target.enabled else 0,
                target.description,
                1 if target.is_favorite else 0,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
        return target
    
    def get(self, target_id: str) -> Optional[TargetConfig]:
        """Get a target by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM targets WHERE id = ?", (target_id,))
            row = cursor.fetchone()
            
            if row:
                return TargetConfig(
                    id=row['id'],
                    type=row['type'],
                    name=row['name'],
                    config=json.loads(row['config']),
                    enabled=bool(row['enabled']),
                    description=row['description'],
                    is_favorite=bool(row['is_favorite']) if 'is_favorite' in row.keys() else False
                )
        return None
    
    def update(self, target: TargetConfig) -> TargetConfig:
        """Update an existing target."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE targets 
                SET type = ?, name = ?, config = ?, enabled = ?, description = ?, is_favorite = ?, updated_at = ?
                WHERE id = ?
            """, (
                target.type,
                target.name,
                json.dumps(target.config),
                1 if target.enabled else 0,
                target.description,
                1 if target.is_favorite else 0,
                datetime.utcnow().isoformat(),
                target.id
            ))
        return target
    
    def list(self) -> List[TargetConfig]:
        """List all targets."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM targets ORDER BY is_favorite DESC, name")
            rows = cursor.fetchall()
            
            return [
                TargetConfig(
                    id=row['id'],
                    type=row['type'],
                    name=row['name'],
                    config=json.loads(row['config']),
                    enabled=bool(row['enabled']),
                    description=row['description'],
                    is_favorite=bool(row['is_favorite']) if 'is_favorite' in row.keys() else False
                )
                for row in rows
            ]
    
    def delete(self, target_id: str) -> bool:
        """Delete a target."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM targets WHERE id = ?", (target_id,))
            return cursor.rowcount > 0
